"""
Free-text -> canonical CSE ticker resolution.

WHY THIS MODULE EXISTS
People do not type tickers. They type "haylees stock", "john keels", "sampath".
ticker_registry.resolve_open() cannot help with any of those: it is a
normalizer, so it turns "Hayleys" into the syntactically valid but nonexistent
"HAYLEYS.N0000" and hands it downstream, where the Yahoo fetch fails with a
message about a missing price feed. The symbol was never the problem — the NAME
was never resolved.

The obvious alternative — hand the model the whole company list and let it pick —
was already in place via the chat `list_symbols` tool and did not work. The list
is 285 rows, ~17KB of JSON, and gemini_chat.compact() trimmed it to the first 65
rows to protect the context window. Everything from "C I C HOLDINGS" onward was
invisible, so HAYLEYS, JOHN KEELLS, SAMPATH and DIALOG could not be found no
matter how many times the model looked. Name matching belongs here, in code,
where it is deterministic and testable, and where all 285 rows are always in play.

MATCHING
A scored cascade, best score wins (see _score_company):

  1.00       canonical symbol       "HAYL.N0000"
  0.99       ticker root            "HAYL"
  0.97       core name, exact       "hayleys"        -> HAYLEYS PLC
  0.95       full name, exact       "hayleys plc"
  0.80-0.93  every query word appears in the name, scaled by how much of the
             name the query covers, so "hayleys" beats "hayleys fabric" for HAYL
  0.30-0.79  difflib similarity, which is what catches misspellings

"Core" is the name minus legal-form noise (PLC, LIMITED, THE, OF). Distinguishing
words are NOT stripped: "JOHN KEELLS HOLDINGS", "JOHN KEELLS HOTELS" and "JOHN
KEELLS" are three different listed companies and HOLDINGS/HOTELS is the only
thing telling them apart.

The fuzzy tier is SPREAD across its band rather than clamped to the top of it.
Clamping was tried first and broke ambiguity detection: "haylees" scores 0.86
against HAYLEYS and 0.77 against HAYLEYS FABRIC, and flattening both to one
ceiling value made a clear winner look like a coin toss.

The 0.72 raw floor below the fuzzy tier is measured, not guessed. Against the
live 285-name listing, real misspellings land at 0.77 and above ("samapth" ->
SAMPATH BANK 0.77, "haylees" -> HAYLEYS 0.86, "distileries" -> DISTILLERIES
0.86), while queries for companies that are simply not on the CSE peak at 0.68
("tesla" 0.675, "apple inc" 0.655, "expolanka" 0.643 — Expolanka is no longer in
the exchange listing). A floor between those two clusters is what makes "not
listed" an answer this module is willing to give.

SHARE CLASSES
19 CSE names map to more than one symbol — AGST.N0000 and AGST.X0000 are both
"AGSTAR PLC" (voting and non-voting). Same root means same company, so the tie
is broken toward .N0000 (voting ordinary, by far the most traded) rather than
reported as ambiguity. Different roots with close scores IS real ambiguity and is
reported, because guessing between two unrelated companies is how a user ends up
reading a confident prediction for a stock they never asked about.

The company list comes from cse_api.all_companies(), so it is the live exchange
listing rather than a hardcoded table that silently rots. The 9 curated
ticker_registry names are folded in as extra aliases: they are the names people
actually say ("Dialog" for "DIALOG AXIATA PLC").
"""

import re
from difflib import SequenceMatcher

from services import cse_api
from services.cache import TTLCache
from services.ticker_registry import _normalize, all_tickers

# Legal form and grammatical filler only. Anything that could distinguish two
# listed companies must stay — see SHARE CLASSES above.
_NOISE_WORDS = frozenset({
    "PLC", "LTD", "LIMITED", "COMPANY", "CO", "PUBLIC", "INC",
    "CORPORATION", "CORP", "THE", "OF", "AND",
})

# Stripped from the QUERY ONLY, never from a company name. "predict about hayleys
# stock" arrives here with words that are about the question rather than the
# company, and "JKH stock" must still resolve as the ticker JKH. These are not in
# _NOISE_WORDS because several are real name words: SHARE, CAPITAL and INVESTMENT
# all appear in CSE company names.
_QUERY_FILLER = frozenset({
    "STOCK", "STOCKS", "SHARE", "SHARES", "SHAREPRICE", "PRICE", "PRICES",
    "TICKER", "SYMBOL", "QUOTE", "PREDICT", "PREDICTION", "FORECAST",
    "ANALYSE", "ANALYZE", "ANALYSIS", "OUTLOOK", "ABOUT", "FOR", "PLEASE",
})

# Post-scaling floor. Below this a match is a coincidence rather than a guess
# worth acting on.
MIN_SCORE = 0.30

# Raw difflib floor for the fuzzy tier, and the band its scores are spread over.
# See the calibration note in the module docstring for where 0.72 comes from.
_FUZZY_RAW_FLOOR = 0.72
_FUZZY_BAND = (MIN_SCORE, 0.79)

# Two different companies scoring this close means the query genuinely does not
# pick one out, unless the leader is a near-exact match.
_AMBIGUOUS_MARGIN = 0.06
_CONFIDENT_SCORE = 0.94

# Voting ordinary shares. Preferred when one company lists several classes.
_PREFERRED_CLASS = "N0000"

# Matches ticker-shaped input, so "HAYL.N0000" and "JKH" are never sent down the
# name-matching path. Anchored and length-bounded: a company name like "MTD
# WALKERS" must not read as a ticker.
_TICKER_SHAPED = re.compile(r"^[A-Z][A-Z0-9]{1,7}(\.[A-Z]\d{4})?$")

# The index is derived from a TTL-cached upstream list; this second cache just
# avoids rebuilding the normalized forms on every keystroke of a chat turn.
_index_cache = TTLCache(60.0)


def _clean(text: str) -> str:
    """Uppercase, punctuation to space, whitespace collapsed."""
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", text.upper()).split())


def _core(full: str) -> str:
    """
    `full` minus legal-form noise, e.g. "HAYLEYS PLC" -> "HAYLEYS".

    Falls back to `full` when stripping would empty the string: "THE COMPANY OF
    ..." style names exist and an empty core would match every query equally.
    """
    kept = [w for w in full.split() if w not in _NOISE_WORDS]
    return " ".join(kept) if kept else full


class Candidate:
    """One scored company. `score` is comparable only within a single query."""

    __slots__ = ("symbol", "name", "score", "matched_on")

    def __init__(self, symbol: str, name: str, score: float, matched_on: str):
        self.symbol = symbol
        self.name = name
        self.score = score
        # "symbol" | "root" | "name" | "words" | "fuzzy" — reported to the model
        # so it can say how it read the question instead of implying certainty.
        self.matched_on = matched_on

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "score": round(self.score, 3),
            "matched_on": self.matched_on,
        }

    def __repr__(self) -> str:
        return f"Candidate({self.symbol!r}, {self.score:.3f}, {self.matched_on})"


class _Entry:
    """A listed company with its match keys precomputed."""

    __slots__ = ("symbol", "name", "root", "cls", "full", "core", "tokens", "aliases")

    def __init__(self, symbol: str, name: str):
        self.symbol = symbol
        self.name = name
        root, _, cls = symbol.partition(".")
        self.root = root
        self.cls = cls
        self.full = _clean(name)
        self.core = _core(self.full)
        self.tokens = set(self.core.split())
        # Extra core-form names that should resolve to this symbol.
        self.aliases: set[str] = set()


def _build_index() -> list[_Entry]:
    """
    Every listed company, match keys precomputed, curated aliases folded in.

    Raises CseApiError when the exchange listing cannot be fetched — callers turn
    that into "market data unavailable", which is the truth. Guessing from a
    stale hardcoded list would be worse.
    """
    entries = [
        _Entry(_normalize(str(row["symbol"])), str(row.get("name") or row["symbol"]))
        for row in cse_api.all_companies()
        if row.get("symbol")
    ]

    by_symbol = {e.symbol: e for e in entries}
    for ticker in all_tickers():
        entry = by_symbol.get(ticker.symbol)
        if entry is None:
            continue
        alias = _core(_clean(ticker.name))
        # Only worth storing when it differs from what the CSE already calls the
        # company; "Hayleys" adds nothing to "HAYLEYS PLC" but "Dialog" does.
        if alias and alias != entry.core:
            entry.aliases.add(alias)

    return entries


def _index() -> list[_Entry]:
    hit = _index_cache.get("index")
    if hit is None:
        hit = _build_index()
        _index_cache.set("index", hit)
    return hit


def _similarity(query: str, target: str) -> float:
    """
    difflib ratio, taking the better of whole-string and best-single-word.

    The per-word pass is what makes a long official name reachable from the one
    word a person actually says: "distilleries" against "DISTILLERIES SRI LANKA"
    scores 0.55 as a whole string but 1.0 on its best word.
    """
    whole = SequenceMatcher(None, query, target).ratio()
    words = target.split()
    if len(words) <= 1:
        return whole
    best_word = max(SequenceMatcher(None, query, w).ratio() for w in words)
    # Discounted: matching one word out of five is weaker evidence than matching
    # the whole name, and without the discount "LANKA" would match half the
    # exchange at 1.0.
    return max(whole, best_word * 0.9)


def _score_company(entry: _Entry, query_full: str, query_core: str,
                   query_tokens: set[str]) -> tuple[float, str]:
    """Best score this company achieves for the query, and how it got there."""
    if query_core in {entry.core, *entry.aliases}:
        return 0.97, "name"
    if query_full == entry.full:
        return 0.95, "name"

    # Every word the user typed appears in the name. Scaled by coverage so a
    # query naming the company outright ranks above one naming a subsidiary:
    # "hayleys" covers all of HAYLEYS but half of HAYLEYS FABRIC.
    if query_tokens and query_tokens <= entry.tokens:
        coverage = len(query_tokens) / max(len(entry.tokens), 1)
        return 0.80 + 0.13 * coverage, "words"

    best = max(
        _similarity(query_core, entry.core),
        *(_similarity(query_core, alias) for alias in entry.aliases or {entry.core}),
    )
    # Held below the exact tiers: a fuzzy hit must never outrank a real name.
    return min(best, 0.79), "fuzzy"


def _prefer(a: Candidate, b: Candidate) -> Candidate:
    """
    Pick between two candidates for the same company (same ticker root).

    Voting ordinary shares win. Without this, "COMMERCIAL BANK" resolves to
    whichever of COMB.N0000 / COMB.X0000 the exchange happened to list first.
    """
    if a.score != b.score:
        return a if a.score > b.score else b
    a_pref = a.symbol.endswith(_PREFERRED_CLASS)
    b_pref = b.symbol.endswith(_PREFERRED_CLASS)
    if a_pref != b_pref:
        return a if a_pref else b
    return a if a.symbol <= b.symbol else b


def search(query: str, limit: int = 5) -> list[Candidate]:
    """
    Companies matching `query`, best first, one row per company.

    `query` may be a ticker, a ticker root, a company name, or a misspelling of
    one. Returns [] for empty input or when nothing clears MIN_SCORE.
    """
    text = (query or "").strip()
    if not text:
        return []

    entries = _index()

    # A ticker-shaped query is a ticker. Resolving it by name would let
    # "MGT.N0000" drift to something whose name happens to contain "MGT".
    upper = text.upper()
    if _TICKER_SHAPED.match(upper):
        key = _normalize(upper)
        root = key.split(".")[0]
        exact = [e for e in entries if e.symbol == key]
        if exact:
            return [Candidate(exact[0].symbol, exact[0].name, 1.0, "symbol")]
        same_root = [e for e in entries if e.root == root]
        if same_root:
            # Requested class is not listed but the company is — offer its
            # classes rather than reporting the company as unlisted.
            rows = [Candidate(e.symbol, e.name, 0.99, "root") for e in same_root]
            rows.sort(key=lambda c: (not c.symbol.endswith(_PREFERRED_CLASS), c.symbol))
            return rows[:limit]
        # Unlisted but well-formed: fall through to name matching, then let the
        # caller decide. Delisted tickers and typo'd names both land here.

    query_full = _clean(text)
    if not query_full:
        return []
    query_core = _core(query_full)
    query_tokens = set(query_core.split())

    # One entry per company (root), so share classes do not fill the result list.
    best_by_root: dict[str, Candidate] = {}
    for entry in entries:
        score, matched_on = _score_company(entry, query_full, query_core, query_tokens)
        if score < MIN_SCORE:
            continue
        candidate = Candidate(entry.symbol, entry.name, score, matched_on)
        existing = best_by_root.get(entry.root)
        best_by_root[entry.root] = _prefer(existing, candidate) if existing else candidate

    ranked = sorted(best_by_root.values(), key=lambda c: (-c.score, c.symbol))
    return ranked[:limit]


def resolve(query: str) -> dict:
    """
    Resolve free text to one CSE symbol, or explain why it could not be.

    Returns a dict shaped for a Gemini tool response — flat, JSON-safe, and
    self-explanatory, because the model has to turn it into a sentence:

      found      bool
      symbol     canonical ticker, when found
      name       company name as the CSE lists it
      score      0-1 confidence
      matched_on how it matched (symbol/root/name/words/fuzzy)
      ambiguous  True when a different company scored nearly as well; the
                 caller should ask rather than analyse the leader
      candidates the ranked alternatives, always present when any matched

    Never raises for an unmatched query — "not listed" is an answer, not a fault.
    A CseApiError from the listing fetch does propagate: that is a real outage
    and must not be reported as "no such company".
    """
    matches = search(query, limit=5)

    if not matches:
        return {
            "found": False,
            "query": query,
            "error": (
                f"No company on the CSE matches {query!r}. It may not be listed, "
                f"or be listed under a different name."
            ),
            "candidates": [],
        }

    best = matches[0]
    others = [c for c in matches[1:] if c.symbol.split(".")[0] != best.symbol.split(".")[0]]

    # Same company, several share classes -> not ambiguous, _prefer already chose.
    ambiguous = bool(
        others
        and best.score < _CONFIDENT_SCORE
        and best.score - others[0].score < _AMBIGUOUS_MARGIN
    )

    return {
        "found": True,
        "query": query,
        "symbol": best.symbol,
        "name": best.name,
        "score": round(best.score, 3),
        "matched_on": best.matched_on,
        "ambiguous": ambiguous,
        "candidates": [c.as_dict() for c in matches],
    }


def clear_cache() -> None:
    """Drop the built index. For tests, and after cse_api.clear_cache()."""
    _index_cache.clear()
