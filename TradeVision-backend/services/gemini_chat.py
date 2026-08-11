"""
Gemini-backed chat, grounded in real TradeVision data via function calling.

WHY FUNCTION CALLING AND NOT A PROMPT DUMP
An LLM asked "what is JKH trading at?" will answer from training data, confidently
and wrongly — the CSE is thin enough that any memorised figure is stale by months.
So the model gets no prices in its prompt. It gets TOOLS, and the only numbers it
can state are ones this process fetched from the CSE API or produced with the
XGBoost engine during the request.

WHAT LIVES HERE AND WHAT DOES NOT
This module owns the Gemini transport, the tool DECLARATIONS (the schemas the
model sees), and the tool loop. It does NOT implement the tools: handlers are
passed in by api/routes/chat.py, which is the layer allowed to reach the engine
and sentiment singletons in api/dependencies.py. Keeping the implementations out
means services/ never imports api/.

The app must boot with no API key and with google-genai absent, matching the
lazy-singleton rule in api/dependencies.py: a missing dependency degrades one
endpoint, it does not stop the container.
"""

import json
import os
import threading

# Number of times the model may ask for tools before it must answer in prose.
# A confused model will otherwise re-request the same tool indefinitely, and each
# round trip costs a real API call.
MAX_TOOL_ROUNDS = 5

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Low but not zero: this is factual Q&A over fetched numbers, not creative work.
_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))

_client = None
_client_lock = threading.Lock()


class GeminiUnavailableError(RuntimeError):
    """No API key, or the SDK is not installed. A 503 condition, not a bug."""


class GeminiChatError(RuntimeError):
    """The Gemini call itself failed."""


SYSTEM_PROMPT = """\
You are the TradeVision assistant. TradeVision analyses stocks on the Colombo \
Stock Exchange (CSE) in Sri Lanka, combining live CSE market data with an \
XGBoost price-direction model and FinBERT news sentiment.

Rules you must follow:

1. NEVER state a price, change, volume, index level or prediction from memory. \
Call a tool. If a tool fails, say the data is unavailable — do not estimate.
2. CSE symbols look like JKH.N0000 (ticker root, then a dot, then the security \
code). Users will often type just "JKH" or the company name. If a user provides a \
company name (like "Hayleys" or "haylees"), YOU MUST use the `search_symbols` tool \
to find the correct symbol (e.g. HAYL.N0000) BEFORE calling `get_stock_analysis` \
or `get_quote`. Do not pass company names directly to those tools. If a symbol \
is not listed, say so.
3. When you quote a prediction, always give its `as_of` date and repeat any \
`warnings` it carries. The warnings matter: Yahoo Finance has stopped updating \
many CSE symbols, so a prediction can be months old even though the live CSE \
price beside it is current. Never present a stale prediction as a forecast for \
tomorrow.
4. When providing an analysis, you MUST explicitly state the exact news sentiment \
score and label (e.g., 'Bullish (0.65)'), as well as the model's exact predicted \
trend and confidence percentage. Do not just summarize the trend; give the specific \
numbers. If asked whether to buy or sell, remind them that TradeVision does not give \
financial advice.
5. Prices are in Sri Lankan rupees (LKR). Write them as "Rs 19.90".
6. Be brief. Two or three short paragraphs at most, and prefer a short list when \
reporting several stocks.
"""

# Schemas the model sees. Plain dicts rather than SDK types so this module can be
# imported without google-genai installed; the SDK coerces them on use.
# Functions taking no arguments declare no `parameters` block at all.
TOOL_DECLARATIONS: list[dict] = [
    {
        "name": "get_stock_analysis",
        "description": (
            "Run TradeVision's full analysis for one CSE stock: XGBoost next-day "
            "direction with probability, the technical indicator summary, the "
            "as_of date of the newest real trading bar, and any data warnings. "
            "Use this for any question about a prediction, forecast, outlook, or "
            "whether a stock looks strong or weak."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {
                    "type": "STRING",
                    "description": "CSE ticker, e.g. JKH.N0000. Short form 'JKH' is accepted.",
                },
                "include_news": {
                    "type": "BOOLEAN",
                    "description": (
                        "ALWAYS pass true to ensure the FinBERT sentiment score is "
                        "fetched and included in the response."
                    ),
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_quote",
        "description": (
            "Live CSE quote for one stock: last traded price, change, change "
            "percent, volume, turnover, day high/low/open, previous close and "
            "market cap. This is the current market price — use it for "
            "'what is X trading at' questions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {
                    "type": "STRING",
                    "description": "CSE ticker, e.g. JKH.N0000. Short form 'JKH' is accepted.",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_top_gainers",
        "description": "Today's biggest percentage gainers on the CSE (up to 10).",
    },
    {
        "name": "get_top_losers",
        "description": "Today's biggest percentage losers on the CSE (up to 10).",
    },
    {
        "name": "get_most_active",
        "description": "Today's most actively traded CSE counters by share volume (up to 10).",
    },
    {
        "name": "get_market_overview",
        "description": (
            "Exchange-level state: whether the market is open or closed, the ASPI "
            "index level and its daily change, total turnover and share volume for "
            "the session, and the number of listed companies."
        ),
    },
    {
        "name": "list_symbols",
        "description": (
            "Every company listed on the CSE, as symbol and name only. Use this to "
            "find a ticker when the user names a company instead of a symbol."
        ),
    },
    {
        "name": "search_symbols",
        "description": (
            "Search for a CSE ticker symbol by company name. Use this to find the "
            "correct symbol when the user asks about a company (e.g. 'Hayleys' or "
            "'Sampath Bank') before calling other tools."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Company name or part of it to search for, e.g. 'Sampath'.",
                },
            },
            "required": ["query"],
        },
    },
]

_DECLARED_NAMES = {d["name"] for d in TOOL_DECLARATIONS}


def is_available() -> bool:
    """True if a chat request could succeed. Cheap — no network call."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def get_client():
    """
    Lazily-built Gemini client.

    Imported inside the function so a missing google-genai package surfaces as a
    503 on /chat rather than an ImportError that stops the app from starting.
    """
    global _client
    if _client is not None:
        return _client

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiUnavailableError(
            "AI chat is not configured: GEMINI_API_KEY is not set on the server."
        )

    with _client_lock:
        if _client is None:
            try:
                # pyrefly: ignore [missing-import]
                from google import genai
            except ImportError as e:
                raise GeminiUnavailableError(
                    "AI chat is unavailable: the google-genai package is not installed."
                ) from e
            try:
                _client = genai.Client(api_key=key)
            except Exception as e:
                raise GeminiUnavailableError(f"Could not initialise the Gemini client: {e}") from e
    return _client


def _text_of(response) -> str:
    """
    Concatenate the text parts of a response.

    Done by hand rather than via `response.text`, which is documented to warn or
    return None when a candidate also carries non-text parts — exactly the case
    in a tool-calling conversation.
    """
    chunks: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None):
                chunks.append(part.text)
    return "".join(chunks).strip()


def _to_contents(messages: list[dict], types) -> list:
    """Map our {role, content} history onto Gemini's Content list."""
    contents = []
    for message in messages:
        text = str(message.get("content") or "").strip()
        if not text:
            continue
        # Gemini names the assistant role "model"; anything not from the user is
        # treated as ours, so a stray role cannot inject a fake user turn.
        role = "user" if message.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    return contents


def _run_tool(name: str, args: dict, handlers: dict) -> dict:
    """
    Execute one tool call.

    Never raises. A failure is returned to the model as an `error` field so it can
    tell the user the data is unavailable — which is far better than a 500 that
    loses the whole conversation turn.

    The result is always wrapped in a dict because Gemini's function-response
    part requires an object, not a bare list.
    """
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"Tool '{name}' is not available on this server."}
    try:
        result = handler(**args)
    except TypeError as e:
        # The model invented an argument name, or omitted a required one.
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}

    return result if isinstance(result, dict) else {"result": result}


def _describe(name: str, args: dict) -> str:
    """'get_quote(symbol=JKH.N0000)' — shown in the UI so grounding is visible."""
    if not args:
        return f"{name}()"
    inner = ", ".join(f"{k}={v}" for k, v in args.items())
    return f"{name}({inner})"


def chat(messages: list[dict], handlers: dict, symbol: str | None = None) -> dict:
    """
    Answer the latest message, calling `handlers` as the model requests them.

    `messages` is the full conversation as [{role, content}] — the browser resends
    it every turn, so there is no server-side session to keep. `symbol` is the
    ticker the user is currently looking at, which is what makes "should I buy
    this?" resolvable.

    Returns {reply, tools_used, warnings}. Raises GeminiUnavailableError (503) or
    GeminiChatError (502).
    """
    if not messages:
        raise GeminiChatError("No messages to respond to.")

    missing = _DECLARED_NAMES - set(handlers)
    if missing:
        # A declaration with no handler would be offered to the model and then
        # fail at call time. Catch the wiring mistake here instead.
        raise GeminiChatError(f"Tool handlers missing for: {', '.join(sorted(missing))}")

    client = get_client()
    # pyrefly: ignore [missing-import]
    from google.genai import types

    system_prompt = SYSTEM_PROMPT
    if symbol:
        system_prompt += (
            f"\nThe user is currently viewing {symbol} in TradeVision. Resolve "
            f'bare references like "this stock" or "it" to {symbol}.\n'
        )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
        # Tools are executed here, not by the SDK: the handlers are blocking and
        # need the error handling in _run_tool.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=_TEMPERATURE,
    )

    contents = _to_contents(messages, types)
    if not contents:
        raise GeminiChatError("No messages to respond to.")

    tools_used: list[str] = []
    warnings: list[str] = []

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = client.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
        except Exception as e:
            raise GeminiChatError(f"Gemini request failed: {e}") from e

        calls = getattr(response, "function_calls", None) or []
        if not calls:
            reply = _text_of(response)
            if not reply:
                raise GeminiChatError("Gemini returned an empty response.")
            return {"reply": reply, "tools_used": tools_used, "warnings": warnings}

        # The model's own turn must go back in the history verbatim, or the
        # function responses below have nothing to attach to.
        contents.append(response.candidates[0].content)

        response_parts = []
        for call in calls:
            args = dict(call.args or {})
            tools_used.append(_describe(call.name, args))
            result = _run_tool(call.name, args, handlers)
            if "error" in result:
                warnings.append(str(result["error"]))
            response_parts.append(
                types.Part.from_function_response(name=call.name, response=result)
            )

        contents.append(types.Content(role="tool", parts=response_parts))

    # Ran out of rounds. Ask once more with tools withdrawn, so the user gets an
    # answer built from what was already fetched instead of an error.
    warnings.append(
        f"Stopped after {MAX_TOOL_ROUNDS} data lookups; answering from what was gathered."
    )
    try:
        final = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt, temperature=_TEMPERATURE
            ),
        )
    except Exception as e:
        raise GeminiChatError(f"Gemini request failed: {e}") from e

    reply = _text_of(final)
    if not reply:
        raise GeminiChatError(
            f"Gemini kept requesting data after {MAX_TOOL_ROUNDS} rounds without answering."
        )
    return {"reply": reply, "tools_used": tools_used, "warnings": warnings}


def compact(value, limit: int = 4000) -> dict:
    """
    Shrink a tool result that would otherwise dominate the context window.

    Used by the symbol list (285 rows). Serialising to measure is deliberate: the
    model pays for the JSON, so the JSON is what should be measured.
    """
    text = json.dumps(value)
    if len(text) <= limit:
        return value if isinstance(value, dict) else {"result": value}
    if isinstance(value, list):
        kept = value[: max(1, len(value) * limit // len(text))]
        return {
            "result": kept,
            "truncated": True,
            "note": f"Showing {len(kept)} of {len(value)} rows.",
        }
    return {"result": text[:limit], "truncated": True}
