"""
MOEX ISS REST API Client
Документация: https://iss.moex.com/iss/reference/
"""

import time
import requests
import pandas as pd
from datetime import datetime, timedelta

MOEX_BASE  = "https://iss.moex.com/iss"
BOARD      = "TQBR"       # Основной режим торгов акциями
IDX_BOARD  = "SNDX"       # Индексы
FX_BOARD   = "CETS"       # Валютный рынок

# ── TTL-кэш ──────────────────────────────────────────────────────────────────
_CACHE: dict = {}

def _get(key: str, ttl: int = 300):
    entry = _CACHE.get(key)
    if entry and time.time() - entry[1] < ttl:
        return entry[0]
    return None

def _set(key: str, value):
    _CACHE[key] = (value, time.time())

def clear_cache():
    _CACHE.clear()

# ── История цен акции ─────────────────────────────────────────────────────────
def history(ticker: str, days: int = 165) -> pd.DataFrame:
    """
    OHLCV-история за последние N дней с основного режима TQBR.
    Возвращает DataFrame с колонками: TRADEDATE, OPEN, HIGH, LOW, CLOSE, VOLUME, WAPRICE.
    """
    key = f"hist_{ticker}_{days}"
    if (c := _get(key)) is not None:
        return c

    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_till = datetime.now().strftime("%Y-%m-%d")
    url = (f"{MOEX_BASE}/history/engines/stock/markets/shares"
           f"/boards/{BOARD}/securities/{ticker}.json")

    all_rows: list = []
    start = 0
    while True:
        try:
            r = requests.get(url, params={"from": date_from, "till": date_till,
                                          "start": start, "iss.meta": "off"},
                             timeout=15)
            block = r.json().get("history", {})
            cols, rows = block.get("columns", []), block.get("data", [])
        except Exception:
            break
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 100:
            break
        start += 100

    if not all_rows:
        _set(key, pd.DataFrame())
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=cols)
    df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"])
    df = df[df["CLOSE"].notna()].sort_values("TRADEDATE").reset_index(drop=True)
    _set(key, df)
    return df


# ── Текущая котировка ─────────────────────────────────────────────────────────
def quote(ticker: str) -> dict:
    """
    Текущие рыночные данные: LAST, OPEN, HIGH, LOW, VOLUME, CHANGE, LASTTOPREVPRICE.
    """
    key = f"quote_{ticker}"
    if (c := _get(key, ttl=60)) is not None:
        return c

    url = (f"{MOEX_BASE}/engines/stock/markets/shares"
           f"/boards/{BOARD}/securities/{ticker}.json")
    result = {}
    try:
        j = requests.get(url, params={"iss.meta": "off"}, timeout=10).json()
        for section in ("securities", "marketdata"):
            block = j.get(section, {})
            cols, rows = block.get("columns", []), block.get("data", [])
            if rows:
                result.update(dict(zip(cols, rows[0])))
    except Exception:
        pass
    _set(key, result)
    return result


# ── Дивиденды ─────────────────────────────────────────────────────────────────
def dividends(ticker: str) -> pd.DataFrame:
    """История дивидендов: SECID, ISIN, REGISTRYCLOSEDATE, VALUE, CURRENCYID."""
    key = f"div_{ticker}"
    if (c := _get(key, ttl=3600)) is not None:
        return c

    url = f"{MOEX_BASE}/securities/{ticker}/dividends.json"
    try:
        j = requests.get(url, params={"iss.meta": "off"}, timeout=10).json()
        block = j.get("dividends", {})
        cols, rows = block.get("columns", []), block.get("data", [])
        result = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame()
    except Exception:
        result = pd.DataFrame()
    _set(key, result)
    return result


# ── История индекса ───────────────────────────────────────────────────────────
def index_history(idx: str = "IMOEX", days: int = 165) -> pd.DataFrame:
    """История индекса MOEX (IMOEX, RTSI)."""
    key = f"idxh_{idx}_{days}"
    if (c := _get(key)) is not None:
        return c

    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_till = datetime.now().strftime("%Y-%m-%d")
    url = (f"{MOEX_BASE}/history/engines/stock/markets/index"
           f"/boards/{IDX_BOARD}/securities/{idx}.json")

    all_rows, start = [], 0
    while True:
        try:
            r = requests.get(url, params={"from": date_from, "till": date_till,
                                          "start": start, "iss.meta": "off"},
                             timeout=15)
            block = r.json().get("history", {})
            cols, rows = block.get("columns", []), block.get("data", [])
        except Exception:
            break
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < 100:
            break
        start += 100

    if not all_rows:
        _set(key, pd.DataFrame())
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=cols)
    df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"])
    df = df.sort_values("TRADEDATE").reset_index(drop=True)
    _set(key, df)
    return df


# ── Текущий курс USD/RUB c MOEX ───────────────────────────────────────────────
def usdrub() -> float | None:
    """Текущий курс USD/RUB с валютного рынка MOEX (инструмент USD000UTSTOM)."""
    key = "usdrub"
    if (c := _get(key, ttl=120)) is not None:
        return c

    url = (f"{MOEX_BASE}/engines/currency/markets/selt"
           f"/boards/{FX_BOARD}/securities/USD000UTSTOM.json")
    try:
        j = requests.get(url, params={"iss.meta": "off"}, timeout=10).json()
        md = j.get("marketdata", {})
        cols, rows = md.get("columns", []), md.get("data", [])
        if rows:
            row_d = dict(zip(cols, rows[0]))
            rate = row_d.get("LAST") or row_d.get("WAPRICE")
            if rate:
                _set(key, float(rate))
                return float(rate)
    except Exception:
        pass
    return None


# ── Текущее значение индекса MOEX/RTS ────────────────────────────────────────
def index_quote(idx: str = "IMOEX") -> dict:
    """Текущее значение и изменение индекса."""
    key = f"iq_{idx}"
    if (c := _get(key, ttl=60)) is not None:
        return c

    url = (f"{MOEX_BASE}/engines/stock/markets/index"
           f"/boards/{IDX_BOARD}/securities/{idx}.json")
    result = {}
    try:
        j = requests.get(url, params={"iss.meta": "off"}, timeout=10).json()
        for section in ("securities", "marketdata"):
            block = j.get(section, {})
            cols, rows = block.get("columns", []), block.get("data", [])
            if rows:
                result.update(dict(zip(cols, rows[0])))
    except Exception:
        pass
    _set(key, result)
    return result


# ── Список всех акций TQBR ───────────────────────────────────────────────────
def all_securities() -> pd.DataFrame:
    """Полный список торгуемых акций на TQBR с базовыми данными."""
    key = "all_secs"
    if (c := _get(key, ttl=3600)) is not None:
        return c

    url = (f"{MOEX_BASE}/engines/stock/markets/shares"
           f"/boards/{BOARD}/securities.json")
    try:
        j = requests.get(url, params={"iss.meta": "off"}, timeout=15).json()
        sec = j.get("securities", {})
        cols, rows = sec.get("columns", []), sec.get("data", [])
        result = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame()
    except Exception:
        result = pd.DataFrame()
    _set(key, result)
    return result
