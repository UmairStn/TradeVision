"""
Request/response models for POST /api/v1/chat.

Snake_case on the wire, matching schemas/prediction.py and schemas/market.py; the
frontend maps to camelCase in one place (src/services/api.ts).
"""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One turn. `role` is 'user' or 'assistant' — the browser owns the history."""

    role: str = Field(description="'user' or 'assistant'.", examples=["user"])
    content: str = Field(description="The message text.")


class ChatContext(BaseModel):
    """What the user is looking at, so bare references like 'this stock' resolve."""

    symbol: str | None = Field(
        default=None,
        description="CSE ticker currently on screen, e.g. JKH.N0000.",
        examples=["JKH.N0000"],
    )


class ChatRequest(BaseModel):
    """
    The whole conversation, every turn.

    Stateless by design: there is no session store until auth and the database
    land, so the client resends history. The server trims it (see MAX_HISTORY in
    routes/chat.py) rather than trusting the client not to send megabytes.
    """

    messages: list[ChatMessage] = Field(
        description="Conversation so far, oldest first. The last entry should be the user's.",
        min_length=1,
    )
    context: ChatContext | None = Field(
        default=None, description="Optional page context passed to the model."
    )


class ChatResponse(BaseModel):
    reply: str = Field(description="The assistant's answer.")
    tools_used: list[str] = Field(
        default_factory=list,
        description=(
            "Data lookups performed for this answer, e.g. 'get_quote(symbol=JKH.N0000)'. "
            "Surfaced in the UI so the grounding is visible rather than implied."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Tool failures or truncation the user should know about.",
    )
