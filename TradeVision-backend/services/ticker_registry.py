"""
CSE ticker registry — company-name lookup and symbol normalization.

Maps a user-supplied symbol to:

  1. Canonical ticker  ("HAYL.N0000")  — what the API accepts and returns.
  2. Company name      ("Hayleys")     — what the news scraper searches for. The
     scraper queries Google News by NAME, not ticker (see services/scraper.py),
     so this is the registry's main remaining job.
  3. Yahoo symbol      ("HAYL-N0000.CM") — for price fetching.

THE REGISTRY NO LONGER LIMITS PREDICTION. It used to: `asset_id` was a model
input feature whose tree splits only covered the nine training companies, so an
unlisted ticker had no valid value and had to be rejected. That feature was
removed when the model was retrained cross-sectionally, so ANY CSE ticker can now
be predicted. `asset_id` is retained purely as historical metadata and is not
passed to the model.

Two resolvers, for two different needs:

  * resolve()      — strict. Raises UnknownTickerError for unlisted symbols.
  * resolve_open() — permissive. Synthesises an entry for unlisted symbols so the
                     API can serve any ticker. This is what the route uses.
"""


class UnknownTickerError(ValueError):
    """Raised by the strict resolver when a symbol has no registry entry."""


class Ticker:
    __slots__ = ("symbol", "name", "asset_id", "yahoo_symbol", "is_known")

    def __init__(
        self,
        symbol: str,
        name: str,
        asset_id: int | None,
        yahoo_symbol: str,
        is_known: bool = True,
    ):
        self.symbol = symbol
        self.name = name
        # Historical only — the retrained model does not consume this.
        self.asset_id = asset_id
        self.yahoo_symbol = yahoo_symbol
        # False for synthesised entries: the name is a guess, so news quality
        # will be poor. Callers surface this rather than silently pretending.
        self.is_known = is_known

    def __repr__(self) -> str:
        return f"Ticker({self.symbol!r}, known={self.is_known})"


# Curated entries: real company names, which the news scraper needs to build a
# useful Google News query. Order is no longer meaningful.
_TICKERS = [
    Ticker("COMB.N0000", "Commercial Bank of Ceylon", 0, "COMB-N0000.CM"),
    Ticker("DFCC.N0000", "DFCC Bank",                 1, "DFCC-N0000.CM"),
    Ticker("DIAL.N0000", "Dialog Axiata",             2, "DIAL-N0000.CM"),
    Ticker("HAYL.N0000", "Hayleys",                   3, "HAYL-N0000.CM"),
    Ticker("HNB.N0000",  "Hatton National Bank",      4, "HNB-N0000.CM"),
    Ticker("JKH.N0000",  "John Keells Holdings",      5, "JKH-N0000.CM"),
    Ticker("LIOC.N0000", "Lanka IOC",                 6, "LIOC-N0000.CM"),
    Ticker("NDB.N0000",  "National Development Bank", 7, "NDB-N0000.CM"),
    Ticker("SAMP.N0000", "Sampath Bank",              8, "SAMP-N0000.CM"),
]

_BY_SYMBOL = {t.symbol: t for t in _TICKERS}

# Short form ("JKH") -> canonical, built from the same list so it cannot drift.
_BY_SHORT = {t.symbol.split(".")[0]: t for t in _TICKERS}


def _normalize(symbol: str) -> str:
    """
    Normalize any accepted input form to the canonical one.

    Accepts "HAYL.N0000", "HAYL", "HAYL-N0000.CM", and any casing/whitespace.
    Bare roots gain the default ".N0000" series suffix, which covers voting
    ordinary shares — by far the most commonly traded class.
    """
    key = symbol.strip().upper()

    # Yahoo form: HAYL-N0000.CM -> HAYL.N0000
    if key.endswith(".CM"):
        key = key[:-3].replace("-", ".")

    if "." not in key:
        key = f"{key}.N0000"

    return key


def resolve(symbol: str) -> Ticker:
    """
    Strict lookup. Raises UnknownTickerError for anything not in the registry.

    Kept for callers that genuinely need a curated company name. The API route
    uses resolve_open() instead.
    """
    if not symbol or not symbol.strip():
        raise UnknownTickerError("No symbol provided.")

    key = _normalize(symbol)

    if key in _BY_SYMBOL:
        return _BY_SYMBOL[key]

    root = key.split(".")[0]
    if root in _BY_SHORT:
        return _BY_SHORT[root]

    raise UnknownTickerError(
        f"Unknown ticker {symbol!r}. Known symbols: {', '.join(supported_symbols())}."
    )


def resolve_open(symbol: str) -> Ticker:
    """
    Permissive lookup — returns a usable Ticker for ANY well-formed CSE symbol.

    Registry hit  -> the curated entry, with the real company name.
    Registry miss -> a synthesised entry (is_known=False) whose "name" is the
                     ticker root. Prediction is unaffected: the model needs only
                     price history. News quality degrades, because the root is a
                     poor Google News query, and callers surface that rather than
                     presenting a weak result as a strong one.

    Still raises UnknownTickerError on empty or malformed input — an unparseable
    symbol is a client error, not something to guess at.
    """
    if not symbol or not symbol.strip():
        raise UnknownTickerError("No symbol provided.")

    key = _normalize(symbol)
    root = key.split(".")[0]

    if key in _BY_SYMBOL:
        return _BY_SYMBOL[key]
    if root in _BY_SHORT:
        return _BY_SHORT[root]

    if not root.isalnum():
        raise UnknownTickerError(
            f"Malformed ticker {symbol!r}. Expected a form like 'JKH.N0000' or 'JKH'."
        )

    return Ticker(
        symbol=key,
        name=root,
        asset_id=None,
        yahoo_symbol=key.replace(".", "-") + ".CM",
        is_known=False,
    )


def supported_symbols() -> list[str]:
    """
    Symbols with curated company names.

    NOT a limit on what can be predicted — resolve_open() serves any ticker.
    """
    return [t.symbol for t in _TICKERS]


def all_tickers() -> list[Ticker]:
    return list(_TICKERS)

