"""
Colombo Stock Exchange live market data (www.cse.lk/api).

The ONLY module that knows CSE's wire format. Everything above it — routes,
schemas, the Gemini tools — sees the normalized dicts produced by _to_quote().
Keeping that boundary tight matters because the upstream API is undocumented in
practice and its field names are inconsistent (see NAMING below).

WHY THIS EXISTS ALONGSIDE price_data.py
services/price_data.py feeds the MODEL. This module feeds the SCREEN. They are
deliberately separate: the XGBoost artifact was trained on Yahoo's unadjusted
daily bars, and services/features.py is the single source of truth for feature
engineering, so routing CSE prices into build_feature_row() would shift every
feature away from what training saw. CSE data is additive — display only. It
must never reach the feature path.

The payoff is real: Yahoo has stopped updating CSE symbols and forward-fills the
last known close with Volume 0, so the model's `as_of` can be months behind. This
module is where a genuinely current price comes from.

NAMING
Upstream spelling is not self-consistent and is reproduced here verbatim rather
than corrected, because these strings are the wire protocol:

  * the endpoint is `topLooses`, not `topLosers` (which returns HTTP 400)
  * `tradeSummary` wraps its rows in `reqTradeSummery`
  * the market totals endpoint is `marketSummery`
  * share volume is `sharevolume` in tradeSummary but `shareVolume` in
    mostActiveTrades

Every one of those is mapped in exactly one place below.

TRANSPORT
All endpoints are POST. A GET returns 405 METHOD_NOT_ALLOWED. The market lists
take no parameters; the chart endpoint takes a numeric stockId plus a period.
"""

import os
import threading

# pyrefly: ignore [missing-import]
import requests

from services.cache import TTLCache
from services.ticker_registry import _normalize

BASE_URL = os.getenv("CSE_API_BASE", "https://www.cse.lk/api")

# Short: these are live intraday numbers and the whole point of this module is
# that they are fresher than the model's feed. Long enough that a page render
# hitting summary + quote + symbols costs one upstream call, not three.
_LIST_TTL = float(os.getenv("CSE_CACHE_TTL", "60"))

# Listings change on the scale of months, so the symbol -> stockId map can be
# held far longer than the prices it was extracted from.
_IDS_TTL = float(os.getenv("CSE_IDS_CACHE_TTL", "3600"))

_TIMEOUT = float(os.getenv("CSE_TIMEOUT", "15"))

_cache = TTLCache(_LIST_TTL)
_ids_cache = TTLCache(_IDS_TTL)

# One pooled session rather than a fresh connection per call. Guarded because
# FastAPI dispatches this module's work across threadpool workers.
_session_lock = threading.Lock()
_session: "requests.Session | None" = None


class CseApiError(RuntimeError):
    """Live market data could not be retrieved from the CSE."""


def _get_session() -> "requests.Session":
    global _session
    with _session_lock:
        if _session is None:
            s = requests.Session()
            # cse.lk sits behind a filter that rejects requests with no
            # browser-shaped User-Agent.
            s.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.cse.lk/",
            })
            _session = s
        return _session


def _post(path: str, **form) -> object:
    """
    POST to a CSE endpoint and return the decoded JSON.

    POST is not a choice: these endpoints reject GET with 405. Parameters go as
    form fields (application/x-www-form-urlencoded), which requests does by
    default for `data=`.

    Retried once on timeout/connection failure. cse.lk intermittently drops a
    request — observed in testing — and every endpoint here is semantically a
    read, so replaying one is safe. Retrying is much cheaper than letting a
    single blip blank a list on the page.
    """
    url = f"{BASE_URL}/{path}"
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            resp = _get_session().post(url, data=form or None, timeout=_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            continue
        except requests.RequestException as e:
            # Anything else (malformed URL, too many redirects) will not fix
            # itself on a replay.
            raise CseApiError(f"CSE request to {path} failed: {e}") from e

        if resp.status_code != 200:
            # The upstream error body names the missing parameter, which is the
            # only useful diagnostic when an endpoint's contract changes.
            raise CseApiError(
                f"CSE {path} returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as e:
            raise CseApiError(f"CSE {path} returned non-JSON: {resp.text[:200]}") from e

    raise CseApiError(f"CSE request to {path} failed after 2 attempts: {last_error}")


def _cached(key: str, producer):
    """TTL-cache wrapper. Only successful results are cached."""
    hit = _cache.get(key)
    if hit is not None:
        return hit
    value = producer()
    _cache.set(key, value)
    return value


def _num(value, default=0.0) -> float:
    """CSE sends numbers as floats, nulls, and occasionally strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_market_cap(value) -> str | None:
    """
    352913806546.2 -> "353B". Display-only; the raw float is kept alongside it.
    """
    n = _num(value, default=0.0)
    if n <= 0:
        return None
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= divisor:
            return f"{n / divisor:.4g}{suffix}"
    return f"{n:.0f}"


# --- normalization ------------------------------------------------------------

def _to_quote(raw: dict, summary: dict | None = None) -> dict:
    """
    Map any CSE row to the canonical quote shape.

    `raw` is the row from whichever endpoint was called; `summary` is the
    matching tradeSummary row when one exists. THE SUMMARY IS NOT OPTIONAL IN
    PRACTICE for the movers endpoints — see the enrichment note in _movers().

    Field-name divergence between endpoints is resolved here and nowhere else:
      * price change percent is `percentageChange` in tradeSummary but
        `changePercentage` in topGainers/topLooses
      * share volume is `sharevolume` in tradeSummary but `shareVolume` in
        mostActiveTrades
    """
    src = summary or {}

    def pick(*keys, default=None):
        """First key present with a non-null value, checking raw then summary."""
        for source in (raw, src):
            for key in keys:
                if source.get(key) is not None:
                    return source[key]
        return default

    symbol = str(pick("symbol", default="") or "")
    market_cap_raw = pick("marketCap")

    return {
        "symbol": _normalize(symbol) if symbol else "",
        # tradeSummary is the only endpoint carrying company names, so an
        # un-enriched row falls back to the ticker rather than an empty cell.
        "name": str(pick("name", default=symbol) or symbol),
        "price": _num(pick("price", "lastTradedPrice", "closingPrice")),
        "change": _num(pick("change")),
        "change_percent": _num(pick("percentageChange", "changePercentage")),
        "volume": _num(pick("sharevolume", "shareVolume")),
        "turnover": _num(pick("turnover")),
        "trades": _num(pick("tradevolume", "tradeVolume")),
        "previous_close": _num(pick("previousClose")) or None,
        "day_high": _num(pick("high")) or None,
        "day_low": _num(pick("low")) or None,
        "day_open": _num(pick("open")) or None,
        "market_cap": _format_market_cap(market_cap_raw),
        "market_cap_value": _num(market_cap_raw) or None,
        "last_traded_time": int(_num(pick("lastTradedTime", "tradeDate"))) or None,
    }


def _summary_rows() -> list[dict]:
    """Raw tradeSummary rows — every listed company (~285), richest payload."""
    def fetch():
        payload = _post("tradeSummary")
        if not isinstance(payload, dict):
            raise CseApiError(f"tradeSummary returned {type(payload).__name__}, expected object")
        rows = payload.get("reqTradeSummery")  # upstream misspelling
        if not isinstance(rows, list):
            raise CseApiError("tradeSummary response had no reqTradeSummery list")
        return rows

    return _cached("tradeSummary", fetch)


def _summary_by_symbol() -> dict[str, dict]:
    """
    tradeSummary indexed by canonical symbol.

    Read by both the movers enrichment join and the symbol -> stockId map, so one
    upstream call serves every caller for the cache window.
    """
    def build():
        return {
            _normalize(str(row.get("symbol") or "")): row
            for row in _summary_rows()
            if row.get("symbol")
        }

    return _cached("tradeSummary:index", build)


def _movers(path: str) -> list[dict]:
    """
    A movers endpoint (topGainers / topLooses / mostActiveTrades), enriched.

    WHY THE JOIN IS REQUIRED, NOT AN OPTIMIZATION
    These endpoints are thin. topGainers/topLooses carry only symbol, price,
    change and changePercentage — no company name, no volume, no market cap.
    mostActiveTrades is thinner still and carries NO PRICE AT ALL, only volume
    and turnover. The UI needs all of those, so each row is joined against
    tradeSummary by symbol.

    A symbol absent from tradeSummary keeps its thin row instead of being
    dropped: a gainer with a blank market cap is still a true gainer.
    """
    def fetch():
        payload = _post(path)
        if not isinstance(payload, list):
            raise CseApiError(f"{path} returned {type(payload).__name__}, expected array")
        index = _summary_by_symbol()
        return [
            _to_quote(row, index.get(_normalize(str(row.get("symbol") or ""))))
            for row in payload
            if row.get("symbol")
        ]

    return _cached(f"movers:{path}", fetch)


# --- public API ---------------------------------------------------------------

def top_gainers() -> list[dict]:
    """Biggest percentage gainers. Upstream caps this at 10 rows."""
    return _movers("topGainers")


def top_losers() -> list[dict]:
    """
    Biggest percentage losers. Upstream caps this at 10 rows.

    The endpoint is `topLooses`; `topLosers` is a 400. Not a typo here.
    """
    return _movers("topLooses")


def most_active() -> list[dict]:
    """
    Most actively traded counters. Upstream caps this at 10 rows.

    Note for anyone extending this: the raw row's `percentageShareVolume` is a
    share-volume figure, NOT a price change percent. Mapping it to change_percent
    would render plausible, wrong numbers. Price and change come from the
    tradeSummary join instead.
    """
    return _movers("mostActiveTrades")


def all_companies() -> list[dict]:
    """Every listed company (~285) with full quote detail."""
    def build():
        return [_to_quote(row, row) for row in _summary_rows() if row.get("symbol")]

    return _cached("companies", build)


def quote(symbol: str) -> dict:
    """
    One company's live quote, read from the cached tradeSummary index.

    Raises CseApiError for a symbol the CSE does not list — distinct from the
    permissive resolve_open() behaviour, because here the absence is a fact about
    the exchange rather than a guess about a name.
    """
    key = _normalize(symbol)
    row = _summary_by_symbol().get(key)
    if row is None:
        raise CseApiError(f"{key} is not listed in the CSE trade summary.")
    return _to_quote(row, row)


def market_status() -> str:
    """'Market Open' / 'Market Closed' / 'Pre Open' as reported by the CSE."""
    def fetch():
        payload = _post("marketStatus")
        if isinstance(payload, dict):
            return str(payload.get("status") or "Unknown")
        return "Unknown"

    return _cached("marketStatus", fetch)


def market_indices() -> dict:
    """
    Exchange-level figures for the Home page: ASPI level and change, plus
    total turnover, share volume and trade count for the session.

    Two upstream calls. Each degrades independently — a missing ASPI should not
    blank out turnover — so failures return None fields rather than raising.
    """
    def fetch():
        aspi: dict = {}
        totals: dict = {}
        try:
            payload = _post("aspiData")
            if isinstance(payload, dict):
                aspi = payload
        except CseApiError as e:
            print(f"[cse_api] aspiData unavailable: {e}")
        try:
            payload = _post("marketSummery")  # upstream misspelling
            if isinstance(payload, dict):
                totals = payload
        except CseApiError as e:
            print(f"[cse_api] marketSummery unavailable: {e}")

        return {
            "aspi": _num(aspi.get("value")) or None,
            "aspi_change": _num(aspi.get("change")) or None,
            "aspi_change_percent": _num(aspi.get("percentage")) or None,
            "turnover": _num(totals.get("tradeVolume")) or None,
            "share_volume": _num(totals.get("shareVolume")) or None,
            "trades": int(_num(totals.get("trades"))) or None,
            "listed_companies": len(_summary_by_symbol()) or None,
        }

    return _cached("indices", fetch)


def stock_id(symbol: str) -> int:
    """
    The numeric id the chart endpoints require.

    The chart endpoints take `stockId`, not a symbol — passing a symbol returns
    "stockId parameter is missing". The id is tradeSummary's `id` field, which is
    the same value the movers endpoints report as `securityId` (JKH = 297).
    """
    key = _normalize(symbol)

    def build():
        return {
            _normalize(str(row.get("symbol") or "")): int(_num(row.get("id")))
            for row in _summary_rows()
            if row.get("symbol") and row.get("id") is not None
        }

    hit = _ids_cache.get("stock_ids")
    if hit is None:
        hit = build()
        _ids_cache.set("stock_ids", hit)

    found = hit.get(key)
    if not found:
        raise CseApiError(f"No CSE stockId for {key}; the symbol may not be listed.")
    return found


def intraday(symbol: str) -> list[dict]:
    """
    Today's per-trade tick series for one symbol.

    NOT a substitute for daily OHLC history. The chart endpoint returns only 5
    daily bars for ANY period >= 7 (verified against period=7/30/90/180/365), so
    the analyzer's 1W/1M/3M chart is served from price_data.get_price_history()
    instead. period=1 is the one genuinely useful mode: full intraday ticks.

    Point fields are single letters: p=price, h=high, l=low, q=quantity,
    t=epoch millis, c=change, pc=percent change.
    """
    sid = stock_id(symbol)

    def fetch():
        payload = _post("companyChartDataByStock", stockId=sid, period=1)
        if not isinstance(payload, dict):
            raise CseApiError("companyChartDataByStock returned a non-object payload")
        points = payload.get("chartData")
        if not isinstance(points, list):
            return []
        return [
            {
                "time": int(_num(p.get("t"))) or None,
                "price": _num(p.get("p")),
                "high": _num(p.get("h")) or None,
                "low": _num(p.get("l")) or None,
                "quantity": _num(p.get("q")),
            }
            for p in points
            if p.get("p") is not None
        ]

    return _cached(f"intraday:{sid}", fetch)


def historical_5day(symbol: str) -> list[dict]:
    """
    The 5 daily OHLC bars provided by the CSE chart API.
    Used by the prediction engine to feed the 5-day Short-Memory model.
    """
    sid = stock_id(symbol)

    def fetch():
        payload = _post("companyChartDataByStock", stockId=sid, period=7)
        if not isinstance(payload, dict):
            raise CseApiError("companyChartDataByStock returned a non-object payload")
        points = payload.get("chartData")
        if not isinstance(points, list):
            return []
        return [
            {
                "time": int(_num(p.get("t"))) or None,
                "price": _num(p.get("p")),
                "high": _num(p.get("h")) or None,
                "low": _num(p.get("l")) or None,
                "quantity": _num(p.get("q")),
            }
            for p in points
            if p.get("p") is not None
        ]

    return _cached(f"historical_5day:{sid}", fetch)


def clear_cache() -> None:
    """Drop every cached response. For tests and manual refresh."""
    _cache.clear()
    _ids_cache.clear()
