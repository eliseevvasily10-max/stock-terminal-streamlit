from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf


POPULAR_COMPANIES = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "AMD": "AMD",
    "AVGO": "Broadcom",
    "JPM": "JPMorgan",
    "V": "Visa",
    "MA": "Mastercard",
    "XOM": "Exxon Mobil",
    "KO": "Coca-Cola",
    "PEP": "PepsiCo",
    "COST": "Costco",
    "WMT": "Walmart",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "BAC": "Bank of America",
    "CVX": "Chevron",
    "SBER": "Сбер",
    "GAZP": "Газпром",
    "LKOH": "Лукойл",
    "ROSN": "Роснефть",
    "GMKN": "Норникель",
    "PLZL": "Полюс",
    "MTSS": "МТС",
    "RTKM": "Ростелеком",
    "YDEX": "Яндекс",
    "VKCO": "VK",
    "MGNT": "Магнит",
    "VTBR": "ВТБ",
}
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "XOM", "SBER", "GAZP", "LKOH", "YDEX"]
RUSSIAN_TICKERS = {
    "SBER", "GAZP", "LKOH", "ROSN", "GMKN", "PLZL", "MTSS", "RTKM", "YDEX", "VKCO", "MGNT", "VTBR"
}
BENCHMARK_TICKER = "SPY"
MOEX_BENCHMARK_TICKER = "IMOEX"
MOEX_BASE_URL = "https://iss.moex.com/iss"
RISK_FREE_TICKER = "^IRX"
PEER_GROUPS = {
    "Банки": {"US": ["JPM", "BAC", "C"], "RU": ["SBER", "VTBR"]},
    "Энергетика": {"US": ["XOM", "CVX"], "RU": ["GAZP", "LKOH", "ROSN"]},
    "Интернет и платформы": {"US": ["GOOGL", "META", "AMZN"], "RU": ["YDEX", "VKCO"]},
    "Ритейл": {"US": ["WMT", "COST", "AMZN"], "RU": ["MGNT"]},
    "Металлы и сырье": {"US": ["FCX", "NEM"], "RU": ["GMKN", "PLZL"]},
}
POSITIVE_NEWS_KEYWORDS = [
    "beat", "growth", "upgrade", "partnership", "record", "expansion", "dividend", "buyback",
    "рост", "прибыль", "дивиденд", "рекорд", "запуск",
]
NEGATIVE_NEWS_KEYWORDS = [
    "miss", "downgrade", "lawsuit", "probe", "fine", "decline", "debt", "slump",
    "иск", "штраф", "долг", "убыт", "слаб",
]


@dataclass
class Recommendation:
    label: str
    color: str
    score: float
    reasons: list[str]
    caveats: list[str]


def configure_page() -> None:
    st.set_page_config(
        page_title="Yahoo Finance Equity Dashboard",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        :root {
            --bg: #f4f1e8;
            --card: rgba(255, 250, 240, 0.88);
            --ink: #18222f;
            --muted: #576271;
            --line: rgba(24, 34, 47, 0.08);
            --accent: #0b6e4f;
            --accent-2: #d77a61;
            --accent-3: #1f4e79;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(215, 122, 97, 0.12), transparent 28%),
                radial-gradient(circle at top left, rgba(11, 110, 79, 0.12), transparent 24%),
                linear-gradient(180deg, #f7f3ea 0%, #f1eee7 100%);
            color: var(--ink);
        }

        h1, h2, h3 {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--ink);
            letter-spacing: -0.03em;
        }

        p, li, div, label, span {
            font-family: 'IBM Plex Sans', sans-serif;
        }

        .hero {
            padding: 1.4rem 1.6rem;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(247, 237, 217, 0.92));
            border: 1px solid rgba(24, 34, 47, 0.07);
            box-shadow: 0 18px 40px rgba(24, 34, 47, 0.08);
            margin-bottom: 1rem;
        }

        .metric-card, .news-card, .summary-card {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: var(--card);
            box-shadow: 0 12px 28px rgba(24, 34, 47, 0.05);
            margin-bottom: 0.75rem;
        }

        .metric-title {
            color: var(--muted);
            font-size: 0.86rem;
            margin-bottom: 0.2rem;
        }

        .metric-value {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 700;
            line-height: 1.1;
        }

        .metric-subtext {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.25rem;
        }

        .section-label {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--accent-3);
            margin-bottom: 0.25rem;
            font-weight: 600;
        }

        .recommendation-pill {
            display: inline-block;
            padding: 0.42rem 0.78rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.86rem;
            color: white;
            margin-bottom: 0.5rem;
        }

        .ticker-header {
            padding-top: 0.75rem;
            margin-top: 1rem;
            border-top: 1px solid rgba(24, 34, 47, 0.08);
        }

        .caption-text {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .news-card a {
            color: var(--accent-3);
            font-weight: 600;
            text-decoration: none;
        }

        .news-card a:hover {
            text-decoration: underline;
        }

        [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_tickers(raw: str) -> list[str]:
    tokens = [item.strip().upper() for item in raw.replace("\n", ",").split(",")]
    unique = []
    seen = set()
    for token in tokens:
        if token and token not in seen:
            unique.append(token)
            seen.add(token)
    return unique


@st.cache_data(ttl=900, show_spinner=False)
def search_quotes(query: str) -> list[dict[str, str]]:
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []
    search = safe_call(lambda: yf.Search(cleaned, max_results=8), None)
    quotes = safe_call(lambda: search.quotes, []) if search is not None else []
    results: list[dict[str, str]] = []
    for item in quotes:
        symbol = str(item.get("symbol") or "").upper()
        exchange = str(item.get("exchange") or item.get("exchDisp") or "")
        if not symbol or symbol.endswith(".ME"):
            continue
        if exchange not in {"NMS", "NYQ", "NAS", "PCX", "ASE", "BTS"} and "." in symbol:
            continue
        short_name = item.get("shortname") or item.get("longname") or item.get("displayName") or symbol
        results.append({"symbol": symbol, "label": f"{symbol} — {short_name}", "exchange": "Yahoo"})

    moex_payload = safe_call(
        lambda: requests.get(
            f"{MOEX_BASE_URL}/securities.json",
            params={"q": cleaned, "iss.meta": "off"},
            timeout=20,
        ).json(),
        {},
    )
    moex_block = moex_payload.get("securities", {})
    moex_columns = moex_block.get("columns", [])
    for row in moex_block.get("data", [])[:12]:
        item = dict(zip(moex_columns, row))
        symbol = str(item.get("secid") or "").upper()
        if not symbol:
            continue
        group = str(item.get("group") or "").lower()
        type_name = str(item.get("type") or "").lower()
        if "stock_shares" not in group and "share" not in type_name and symbol not in RUSSIAN_TICKERS:
            continue
        short_name = item.get("shortname") or item.get("emitent_title") or item.get("name") or symbol
        results.append({"symbol": symbol, "label": f"{symbol} — {short_name}", "exchange": "MOEX"})

    seen = set()
    unique_results = []
    for item in results:
        if item["symbol"] not in seen:
            unique_results.append(item)
            seen.add(item["symbol"])
    return unique_results


def add_tickers_to_state(new_tickers: list[str]) -> None:
    existing = st.session_state.get("selected_tickers", DEFAULT_TICKERS.copy())
    merged = []
    seen = set()
    for ticker in existing + new_tickers:
        if ticker and ticker not in seen:
            merged.append(ticker)
            seen.add(ticker)
    st.session_state["selected_tickers"] = merged


def format_human_number(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    absolute = abs(float(value))
    if absolute >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:,.0f}"


def format_currency(value: Any, symbol: str = "$") -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    absolute = abs(float(value))
    if absolute >= 1_000_000_000_000:
        return f"{symbol}{value / 1_000_000_000_000:.2f}T"
    if absolute >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{symbol}{value / 1_000:.2f}K"
    return f"{symbol}{value:,.2f}"


def format_percent(value: Any, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_number(value: Any, digits: int = 2) -> str:
    numeric = to_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:,.{digits}f}"


def currency_symbol(currency_code: str | None) -> str:
    return "₽" if currency_code == "RUB" else "$"


def clamp(value: float | None, minimum: float, maximum: float) -> float | None:
    if value is None:
        return None
    return max(minimum, min(maximum, value))


def safe_call(func: Any, default: Any) -> Any:
    try:
        return func()
    except Exception:  # noqa: BLE001
        return default


def sanitize_for_cache(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if is_dataclass(value):
        return sanitize_for_cache(asdict(value))
    if isinstance(value, np.generic):
        scalar = value.item()
        if isinstance(scalar, float) and np.isnan(scalar):
            return None
        return scalar
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): sanitize_for_cache(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_cache(item) for item in value]
    return str(value)


def normalize_recommendation_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Recommendation):
        return asdict(value)
    if isinstance(value, dict):
        return {
            "label": str(value.get("label") or "Держать"),
            "color": str(value.get("color") or "#b17800"),
            "score": to_float(value.get("score")) or 0.0,
            "reasons": [str(item) for item in value.get("reasons", [])],
            "caveats": [str(item) for item in value.get("caveats", [])],
        }
    return {
        "label": "Держать",
        "color": "#b17800",
        "score": 0.0,
        "reasons": ["Недостаточно надежных данных для уверенного сигнала."],
        "caveats": [str(value)] if value else ["Требуется обновить данные по тикеру."],
    }


def normalize_frame(frame: Any) -> pd.DataFrame:
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    return pd.DataFrame()


def fix_mojibake(text: str) -> str:
    if not isinstance(text, str):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
        return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{fix_mojibake(title)}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtext">{fix_mojibake(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def statement_value(frame: pd.DataFrame | None, row_names: list[str]) -> float | None:
    if frame is None or frame.empty:
        return None
    normalized_index = {str(index).strip().lower(): index for index in frame.index}
    for candidate in row_names:
        actual = normalized_index.get(candidate.lower())
        if actual is None:
            continue
        series = frame.loc[actual]
        if isinstance(series, pd.Series):
            series = series.dropna()
            if not series.empty:
                return to_float(series.iloc[0])
    return None


def get_news_value(item: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = item
        found = True
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found and current not in (None, "", []):
            return current
    return None


def extract_news(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extracted = []
    for item in news_items[:6]:
        title = get_news_value(item, ("content", "title"), ("title",))
        link = get_news_value(
            item,
            ("content", "canonicalUrl", "url"),
            ("content", "clickThroughUrl", "url"),
            ("link",),
        )
        publisher = get_news_value(
            item,
            ("content", "provider", "displayName"),
            ("publisher",),
        )
        summary = get_news_value(item, ("content", "summary"), ("summary",))
        publish_time = get_news_value(
            item,
            ("content", "pubDate"),
            ("providerPublishTime",),
        )
        extracted.append(
            {
                "title": title or "Без заголовка",
                "link": link,
                "publisher": publisher or "Yahoo Finance",
                "summary": summary or "",
                "publish_time": publish_time,
            }
        )
    return extracted


def normalize_download_frame(data: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(how="all")


@st.cache_data(ttl=900, show_spinner=False)
def download_history(ticker: str, period: str) -> pd.DataFrame:
    history = yf.download(
        tickers=ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    return normalize_download_frame(history)


@st.cache_data(ttl=900, show_spinner=False)
def download_close_pair(ticker: str, benchmark: str, period: str = "1y") -> pd.DataFrame:
    data = yf.download(
        tickers=[ticker, benchmark],
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    close = data.get("Close")
    if close is None:
        return pd.DataFrame()
    if isinstance(close, pd.Series):
        close = close.to_frame(name=ticker)
    close = close.dropna(how="all")
    if isinstance(close.columns, pd.MultiIndex):
        close.columns = close.columns.get_level_values(-1)
    close.columns = [str(column) for column in close.columns]
    return close


@st.cache_data(ttl=900, show_spinner=False)
def get_risk_free_rate() -> float:
    data = yf.download(
        tickers=RISK_FREE_TICKER,
        period="1mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    data = normalize_download_frame(data)
    if data.empty or "Close" not in data:
        return 0.04
    latest = to_float(data["Close"].dropna().iloc[-1])
    if latest is None:
        return 0.04
    return latest / 100


def get_fast_info(asset: yf.Ticker) -> dict[str, Any]:
    fast_info_obj = safe_call(lambda: asset.fast_info, {})
    if hasattr(fast_info_obj, "items"):
        return sanitize_for_cache(dict(fast_info_obj.items()))
    if isinstance(fast_info_obj, dict):
        return sanitize_for_cache(fast_info_obj)
    return {}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_asset_payload(ticker: str) -> dict[str, Any]:
    asset = yf.Ticker(ticker)
    return {
        "info": sanitize_for_cache(safe_call(lambda: asset.info, {})) or {},
        "fast_info": get_fast_info(asset),
        "news": extract_news(safe_call(lambda: asset.news or [], [])),
        "income_stmt": normalize_frame(safe_call(lambda: asset.income_stmt, pd.DataFrame())),
        "balance_sheet": normalize_frame(safe_call(lambda: asset.balance_sheet, pd.DataFrame())),
        "cashflow": normalize_frame(safe_call(lambda: asset.cashflow, pd.DataFrame())),
    }


@st.cache_data(ttl=900, show_spinner=False)
def moex_request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = requests.get(f"{MOEX_BASE_URL}/{path}", params=params or {}, timeout=8)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


def table_from_iss(payload: dict[str, Any], name: str) -> pd.DataFrame:
    block = payload.get(name, {})
    return pd.DataFrame(block.get("data", []), columns=block.get("columns", []))


@st.cache_data(ttl=900, show_spinner=False)
def fetch_moex_snapshot(ticker: str) -> dict[str, Any]:
    payload = moex_request(
        f"engines/stock/markets/shares/boards/TQBR/securities/{ticker.upper()}.json",
        params={"iss.meta": "off"},
    )
    marketdata = table_from_iss(payload, "marketdata")
    securities = table_from_iss(payload, "securities")
    md_row = marketdata.iloc[0].to_dict() if not marketdata.empty else {}
    sec_row = securities.iloc[0].to_dict() if not securities.empty else {}
    last_price = (
        to_float(md_row.get("LAST"))
        or to_float(md_row.get("MARKETPRICE"))
        or to_float(md_row.get("LCLOSEPRICE"))
        or to_float(sec_row.get("PREVPRICE"))
    )
    return {
        "ticker": ticker.upper(),
        "board": sec_row.get("BOARDID") or "TQBR",
        "name": sec_row.get("SHORTNAME") or sec_row.get("SECNAME") or ticker.upper(),
        "full_name": sec_row.get("SECNAME") or sec_row.get("SHORTNAME") or ticker.upper(),
        "currency": "RUB",
        "last_price": last_price,
        "turnover": to_float(md_row.get("VALTODAY_RUR")) or to_float(md_row.get("VALTODAY")),
        "num_trades": to_float(md_row.get("NUMTRADES")),
        "market_cap": to_float(md_row.get("ISSUECAPITALIZATION")),
        "update_time": md_row.get("UPDATETIME"),
    }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_moex_candles(ticker: str, months: int = 6, market: str = "shares", board: str = "TQBR") -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 31)
    if market == "shares":
        path = f"engines/stock/markets/shares/boards/{board}/securities/{ticker.upper()}/candles.json"
    else:
        path = f"engines/stock/markets/{market}/securities/{ticker.upper()}/candles.json"
    payload = moex_request(
        path,
        params={"iss.meta": "off", "from": start_date.isoformat(), "till": end_date.isoformat(), "interval": 24},
    )
    candles = table_from_iss(payload, "candles")
    if candles.empty:
        return pd.DataFrame()
    candles["Date"] = pd.to_datetime(candles["begin"])
    candles = candles.rename(columns={"open": "Open", "close": "Close", "high": "High", "low": "Low", "volume": "Volume"})
    return candles.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]].sort_index()


def combine_relative_frame(history: pd.DataFrame, benchmark_history: pd.DataFrame, ticker: str, benchmark_name: str) -> pd.DataFrame:
    if history.empty or benchmark_history.empty:
        return pd.DataFrame()
    joined = pd.concat(
        [
            history["Close"].rename(ticker),
            benchmark_history["Close"].rename(benchmark_name),
        ],
        axis=1,
    )
    return joined.dropna(how="any")


def analyze_news_signal(news: list[dict[str, Any]]) -> dict[str, Any]:
    positive = 0
    negative = 0
    headlines: list[str] = []
    for item in news[:6]:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        pos_hits = sum(keyword in text for keyword in POSITIVE_NEWS_KEYWORDS)
        neg_hits = sum(keyword in text for keyword in NEGATIVE_NEWS_KEYWORDS)
        if pos_hits > neg_hits:
            positive += 1
            headlines.append(f"Позитивный фон: {item.get('title', 'новость')}")
        elif neg_hits > pos_hits:
            negative += 1
            headlines.append(f"Негативный фон: {item.get('title', 'новость')}")
    return {"positive": positive, "negative": negative, "headlines": headlines[:3]}


def compute_analytics_for_market(
    ticker: str,
    history: pd.DataFrame,
    relative: pd.DataFrame,
    benchmark_name: str,
    info: dict[str, Any],
    fast_info: dict[str, Any],
    income_stmt: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    latest_override: float | None = None,
    market_cap_override: float | None = None,
) -> dict[str, Any]:
    beta = compute_beta(relative, ticker, benchmark_name)
    market_return = compute_total_return(relative.get(benchmark_name))
    stock_1y_return = compute_total_return(relative.get(ticker))
    risk_free = get_risk_free_rate()
    capm_expected = risk_free + beta * (market_return - risk_free) if beta is not None and market_return is not None else None
    latest_close = latest_price(history, info, fast_info, latest_override)
    five_month_return = price_return(history)
    market_cap = to_float(market_cap_override) or to_float(info.get("marketCap"))
    enterprise_value = to_float(info.get("enterpriseValue"))
    analyst_target = to_float(info.get("targetMeanPrice"))
    analyst_upside = analyst_target / latest_close - 1 if latest_close not in (None, 0) and analyst_target is not None else None
    revenue = statement_value(income_stmt, ["Total Revenue", "Operating Revenue"])
    net_income = statement_value(income_stmt, ["Net Income"])
    ebitda = statement_value(income_stmt, ["EBITDA", "Normalized EBITDA"])
    operating_income = statement_value(income_stmt, ["Operating Income", "EBIT"])
    pretax_income = statement_value(income_stmt, ["Pretax Income", "Pretax Income From Continuing Operations"])
    income_tax_expense = statement_value(income_stmt, ["Tax Provision", "Income Tax Expense"])
    interest_expense = statement_value(income_stmt, ["Interest Expense", "Net Interest Income"])
    free_cash_flow = statement_value(cashflow, ["Free Cash Flow"])
    operating_cash_flow = statement_value(cashflow, ["Operating Cash Flow"])
    total_debt = statement_value(balance_sheet, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"])
    cash = statement_value(balance_sheet, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Equivalents"])
    current_assets = statement_value(balance_sheet, ["Current Assets", "Total Current Assets"])
    current_liabilities = statement_value(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])
    total_equity = statement_value(balance_sheet, ["Stockholders Equity", "Total Equity Gross Minority Interest"])
    tax_rate = clamp(abs(income_tax_expense) / pretax_income, 0.0, 0.45) if pretax_income not in (None, 0) and income_tax_expense is not None and pretax_income > 0 else clamp(to_float(info.get("effectiveTaxRate")), 0.0, 0.45)
    cost_of_equity = capm_expected
    cost_of_debt = clamp(abs(interest_expense) / total_debt, 0.0, 0.30) if total_debt not in (None, 0) and interest_expense is not None else None
    wacc = None
    if market_cap is not None and market_cap > 0 and total_debt is not None and cost_of_equity is not None:
        capital_base = market_cap + total_debt
        if capital_base > 0:
            debt_component = (total_debt / capital_base) * cost_of_debt * (1 - (tax_rate or 0.21)) if cost_of_debt is not None else 0.0
            wacc = (market_cap / capital_base) * cost_of_equity + debt_component
    nopat = operating_income * (1 - (tax_rate or 0.21)) if operating_income is not None else None
    invested_capital = total_debt + total_equity - (cash or 0.0) if total_debt is not None and total_equity is not None else None
    if invested_capital is not None and invested_capital <= 0:
        invested_capital = None
    roic = nopat / invested_capital if nopat is not None and invested_capital not in (None, 0) else None
    current_ratio = current_assets / current_liabilities if current_assets is not None and current_liabilities not in (None, 0) else None
    net_debt = total_debt - (cash or 0.0) if total_debt is not None else None
    debt_to_ebitda = total_debt / ebitda if total_debt is not None and ebitda not in (None, 0) else None
    net_debt_to_ebitda = net_debt / ebitda if net_debt is not None and ebitda not in (None, 0) else None
    fcf_margin = free_cash_flow / revenue if free_cash_flow is not None and revenue not in (None, 0) else None
    operating_cf_margin = operating_cash_flow / revenue if operating_cash_flow is not None and revenue not in (None, 0) else None
    ev_to_sales = enterprise_value / revenue if enterprise_value is not None and revenue not in (None, 0) else None
    return {
        "latest_close": latest_close,
        "beta": beta,
        "risk_free": risk_free,
        "market_return": market_return,
        "stock_1y_return": stock_1y_return,
        "capm_expected": capm_expected,
        "five_month_return": five_month_return,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "analyst_target": analyst_target,
        "analyst_upside": analyst_upside,
        "revenue": revenue,
        "net_income": net_income,
        "ebitda": ebitda,
        "operating_income": operating_income,
        "free_cash_flow": free_cash_flow,
        "operating_cash_flow": operating_cash_flow,
        "total_debt": total_debt,
        "cash": cash,
        "tax_rate": tax_rate,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "wacc": wacc,
        "roic": roic,
        "current_ratio": current_ratio,
        "net_debt": net_debt,
        "debt_to_ebitda": debt_to_ebitda,
        "net_debt_to_ebitda": net_debt_to_ebitda,
        "fcf_margin": fcf_margin,
        "operating_cf_margin": operating_cf_margin,
        "ev_to_sales": ev_to_sales,
    }


def compute_analytics(
    ticker: str,
    history: pd.DataFrame,
    relative: pd.DataFrame,
    info: dict[str, Any],
    fast_info: dict[str, Any],
    income_stmt: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, Any]:
    beta = compute_beta(relative, ticker, BENCHMARK_TICKER)
    market_return = compute_total_return(relative.get(BENCHMARK_TICKER))
    stock_1y_return = compute_total_return(relative.get(ticker))
    risk_free = get_risk_free_rate()
    capm_expected = None
    if beta is not None and market_return is not None:
        capm_expected = risk_free + beta * (market_return - risk_free)

    latest_close_value = latest_price(history, info, fast_info)
    five_month_return = price_return(history)
    market_cap = to_float(info.get("marketCap"))
    enterprise_value = to_float(info.get("enterpriseValue"))
    analyst_target = to_float(info.get("targetMeanPrice"))
    analyst_upside = None
    if latest_close_value is not None and analyst_target is not None and latest_close_value > 0:
        analyst_upside = analyst_target / latest_close_value - 1

    revenue = statement_value(income_stmt, ["Total Revenue", "Operating Revenue"])
    net_income = statement_value(income_stmt, ["Net Income"])
    ebitda = statement_value(income_stmt, ["EBITDA", "Normalized EBITDA"])
    operating_income = statement_value(income_stmt, ["Operating Income", "EBIT"])
    pretax_income = statement_value(income_stmt, ["Pretax Income", "Pretax Income From Continuing Operations"])
    income_tax_expense = statement_value(income_stmt, ["Tax Provision", "Income Tax Expense"])
    interest_expense = statement_value(income_stmt, ["Interest Expense", "Net Interest Income"])
    free_cash_flow = statement_value(cashflow, ["Free Cash Flow"])
    operating_cash_flow = statement_value(cashflow, ["Operating Cash Flow"])
    total_debt = statement_value(balance_sheet, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"])
    cash = statement_value(
        balance_sheet,
        ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Equivalents"],
    )
    current_assets = statement_value(balance_sheet, ["Current Assets", "Total Current Assets"])
    current_liabilities = statement_value(balance_sheet, ["Current Liabilities", "Total Current Liabilities"])
    total_equity = statement_value(balance_sheet, ["Stockholders Equity", "Total Equity Gross Minority Interest"])

    tax_rate = None
    if pretax_income is not None and pretax_income > 0 and income_tax_expense is not None:
        tax_rate = clamp(abs(income_tax_expense) / pretax_income, 0.0, 0.45)
    if tax_rate is None:
        tax_rate = clamp(to_float(info.get("effectiveTaxRate")), 0.0, 0.45)

    cost_of_equity = capm_expected
    cost_of_debt = None
    if total_debt is not None and total_debt > 0 and interest_expense is not None:
        cost_of_debt = clamp(abs(interest_expense) / total_debt, 0.0, 0.30)

    wacc = None
    if market_cap is not None and market_cap > 0 and total_debt is not None and cost_of_equity is not None:
        capital_base = market_cap + total_debt
        if capital_base > 0:
            debt_component = 0.0
            if cost_of_debt is not None:
                debt_component = (total_debt / capital_base) * cost_of_debt * (1 - (tax_rate or 0.21))
            wacc = (market_cap / capital_base) * cost_of_equity + debt_component

    nopat = None
    if operating_income is not None:
        nopat = operating_income * (1 - (tax_rate or 0.21))

    invested_capital = None
    if total_debt is not None and total_equity is not None:
        invested_capital = total_debt + total_equity - (cash or 0.0)
        if invested_capital <= 0:
            invested_capital = None

    roic = None
    if nopat is not None and invested_capital is not None:
        roic = nopat / invested_capital

    current_ratio = None
    if current_assets is not None and current_liabilities not in (None, 0):
        current_ratio = current_assets / current_liabilities

    net_debt = total_debt - (cash or 0.0) if total_debt is not None else None
    debt_to_ebitda = total_debt / ebitda if total_debt is not None and ebitda not in (None, 0) else None
    net_debt_to_ebitda = net_debt / ebitda if net_debt is not None and ebitda not in (None, 0) else None
    fcf_margin = free_cash_flow / revenue if free_cash_flow is not None and revenue not in (None, 0) else None
    operating_cf_margin = operating_cash_flow / revenue if operating_cash_flow is not None and revenue not in (None, 0) else None
    ev_to_sales = enterprise_value / revenue if enterprise_value is not None and revenue not in (None, 0) else None

    return {
        "latest_close": latest_close_value,
        "beta": beta,
        "risk_free": risk_free,
        "market_return": market_return,
        "stock_1y_return": stock_1y_return,
        "capm_expected": capm_expected,
        "five_month_return": five_month_return,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "analyst_target": analyst_target,
        "analyst_upside": analyst_upside,
        "revenue": revenue,
        "net_income": net_income,
        "ebitda": ebitda,
        "operating_income": operating_income,
        "free_cash_flow": free_cash_flow,
        "operating_cash_flow": operating_cash_flow,
        "total_debt": total_debt,
        "cash": cash,
        "tax_rate": tax_rate,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "wacc": wacc,
        "roic": roic,
        "current_ratio": current_ratio,
        "net_debt": net_debt,
        "debt_to_ebitda": debt_to_ebitda,
        "net_debt_to_ebitda": net_debt_to_ebitda,
        "fcf_margin": fcf_margin,
        "operating_cf_margin": operating_cf_margin,
        "ev_to_sales": ev_to_sales,
    }


@st.cache_data(ttl=900, show_spinner=False)
def load_stock_bundle(ticker: str) -> dict[str, Any]:
    history_6m = download_history(ticker, "6mo")
    relative = download_close_pair(ticker, BENCHMARK_TICKER, "1y")
    payload = fetch_asset_payload(ticker)
    info = payload["info"]
    fast_info = payload["fast_info"]
    analytics = compute_analytics(
        ticker=ticker,
        history=history_6m,
        relative=relative,
        info=info,
        fast_info=fast_info,
        income_stmt=payload["income_stmt"],
        balance_sheet=payload["balance_sheet"],
        cashflow=payload["cashflow"],
    )
    if history_6m.empty and not info and not payload["news"]:
        raise ValueError("No market data found for this ticker.")
    recommendation = build_recommendation(
        ticker=ticker,
        info=info,
        analytics=analytics,
    )

    bundle = {
        "ticker": ticker,
        "history": history_6m,
        "info": info,
        "fast_info": fast_info,
        "news": payload["news"],
        "income_stmt": payload["income_stmt"],
        "balance_sheet": payload["balance_sheet"],
        "cashflow": payload["cashflow"],
        "analytics": analytics,
        "recommendation": recommendation,
        "news_signal": analyze_news_signal(payload["news"]),
        "source": "yahoo",
        "source_label": "Yahoo Finance",
        "company_name": info.get("shortName") or info.get("longName") or POPULAR_COMPANIES.get(ticker, ticker),
        "currency": str(info.get("currency") or "USD"),
        "snapshot": {},
    }
    return sanitize_for_cache(bundle)


@st.cache_data(ttl=900, show_spinner=False)
def load_moex_bundle(ticker: str) -> dict[str, Any]:
    moex = fetch_moex_snapshot(ticker)
    history = fetch_moex_candles(ticker, months=6, market="shares", board=moex["board"])
    benchmark = fetch_moex_candles(MOEX_BENCHMARK_TICKER, months=12, market="index")
    relative = combine_relative_frame(history, benchmark, ticker, MOEX_BENCHMARK_TICKER)
    yahoo_symbol = f"{ticker}.ME"
    payload = fetch_asset_payload(yahoo_symbol)
    info = payload["info"]
    fast_info = payload["fast_info"]
    if moex["market_cap"] is not None:
        info["marketCap"] = moex["market_cap"]
    analytics = compute_analytics_for_market(
        ticker=ticker,
        history=history if not history.empty else download_history(yahoo_symbol, "6mo"),
        relative=relative,
        benchmark_name=MOEX_BENCHMARK_TICKER,
        info=info,
        fast_info=fast_info,
        income_stmt=payload["income_stmt"],
        balance_sheet=payload["balance_sheet"],
        cashflow=payload["cashflow"],
        latest_override=moex["last_price"],
        market_cap_override=moex["market_cap"],
    )
    news_signal = analyze_news_signal(payload["news"])
    recommendation = build_recommendation(ticker=ticker, info=info, analytics=analytics)
    bundle = {
        "ticker": ticker,
        "history": history,
        "info": info,
        "fast_info": fast_info,
        "news": payload["news"],
        "income_stmt": payload["income_stmt"],
        "balance_sheet": payload["balance_sheet"],
        "cashflow": payload["cashflow"],
        "analytics": analytics,
        "recommendation": recommendation,
        "news_signal": news_signal,
        "source": "moex",
        "source_label": "MOEX + Yahoo Finance",
        "company_name": moex["full_name"] or info.get("shortName") or info.get("longName") or ticker,
        "currency": "RUB",
        "snapshot": moex,
    }
    return sanitize_for_cache(bundle)


def load_company_bundle(ticker: str) -> dict[str, Any]:
    return load_moex_bundle(ticker) if ticker in RUSSIAN_TICKERS else load_stock_bundle(ticker)


def latest_price(
    history: pd.DataFrame,
    info: dict[str, Any],
    fast_info: dict[str, Any],
    latest_override: float | None = None,
) -> float | None:
    for candidate in [
        latest_override,
        info.get("currentPrice"),
        fast_info.get("lastPrice"),
        fast_info.get("regularMarketPreviousClose"),
    ]:
        value = to_float(candidate)
        if value is not None:
            return value
    if history.empty:
        return None
    close_column = "Adj Close" if "Adj Close" in history else "Close"
    return to_float(history[close_column].dropna().iloc[-1])


def compute_total_return(series: pd.Series | None) -> float | None:
    if series is None:
        return None
    clean = series.dropna()
    if len(clean) < 2:
        return None
    return float(clean.iloc[-1] / clean.iloc[0] - 1)


def compute_beta(frame: pd.DataFrame, ticker: str, benchmark: str) -> float | None:
    if frame.empty or ticker not in frame or benchmark not in frame:
        return None
    returns = frame[[ticker, benchmark]].pct_change().dropna()
    if len(returns) < 40:
        return None
    market_variance = returns[benchmark].var()
    if market_variance == 0:
        return None
    covariance = returns[ticker].cov(returns[benchmark])
    return float(covariance / market_variance)


def price_return(history: pd.DataFrame) -> float | None:
    if history.empty:
        return None
    close_column = "Adj Close" if "Adj Close" in history else "Close"
    close = history[close_column].dropna()
    if len(close) < 2:
        return None
    return float(close.iloc[-1] / close.iloc[0] - 1)


def build_recommendation(
    ticker: str,
    info: dict[str, Any],
    analytics: dict[str, Any],
) -> Recommendation:
    score = 0.0
    reasons: list[str] = []
    caveats: list[str] = []

    rev_growth = to_float(info.get("revenueGrowth"))
    earnings_growth = to_float(info.get("earningsGrowth")) or to_float(info.get("earningsQuarterlyGrowth"))
    profit_margin = to_float(info.get("profitMargins"))
    roe = to_float(info.get("returnOnEquity"))
    debt_to_equity = to_float(info.get("debtToEquity"))
    forward_pe = to_float(info.get("forwardPE"))
    trailing_pe = to_float(info.get("trailingPE"))
    peg = to_float(info.get("pegRatio"))
    analyst_target = analytics["analyst_target"]
    latest_close = analytics["latest_close"]
    five_month_return = analytics["five_month_return"]
    beta = analytics["beta"]
    capm_expected = analytics["capm_expected"]
    stock_1y_return = analytics["stock_1y_return"]
    analyst_upside = analytics["analyst_upside"]
    current_ratio = analytics["current_ratio"]
    net_debt_to_ebitda = analytics["net_debt_to_ebitda"]
    roic = analytics["roic"]
    wacc = analytics["wacc"]
    fcf_margin = analytics["fcf_margin"]

    if rev_growth is not None:
        if rev_growth >= 0.08:
            score += 1.0
            reasons.append(f"Выручка растет на {format_percent(rev_growth)}")
        elif rev_growth < 0:
            score -= 1.0
            caveats.append(f"Выручка снижается на {format_percent(rev_growth)}")

    if earnings_growth is not None:
        if earnings_growth >= 0.08:
            score += 1.0
            reasons.append(f"Прибыль растет на {format_percent(earnings_growth)}")
        elif earnings_growth < 0:
            score -= 1.0
            caveats.append(f"Динамика прибыли отрицательная: {format_percent(earnings_growth)}")

    if profit_margin is not None:
        if profit_margin >= 0.15:
            score += 0.75
            reasons.append(f"Высокая маржа прибыли: {format_percent(profit_margin)}")
        elif profit_margin < 0:
            score -= 1.0
            caveats.append("Компания убыточна по чистой марже")

    if roe is not None:
        if roe >= 0.18:
            score += 0.5
            reasons.append(f"ROE на сильном уровне: {format_percent(roe)}")
        elif roe < 0:
            score -= 0.5
            caveats.append("Отрицательный ROE указывает на слабую эффективность капитала")

    if debt_to_equity is not None:
        if debt_to_equity <= 80:
            score += 0.25
            reasons.append(f"Умеренная долговая нагрузка: D/E {debt_to_equity:.1f}")
        elif debt_to_equity >= 180:
            score -= 0.75
            caveats.append(f"Высокая долговая нагрузка: D/E {debt_to_equity:.1f}")

    if forward_pe is not None:
        if forward_pe < 20:
            score += 0.5
            reasons.append(f"Forward P/E выглядит умеренным: {forward_pe:.1f}")
        elif forward_pe > 35:
            score -= 0.75
            caveats.append(f"Forward P/E уже высокий: {forward_pe:.1f}")

    if trailing_pe is not None and forward_pe is not None and forward_pe < trailing_pe:
        score += 0.25
        reasons.append("Forward P/E ниже trailing P/E, рынок ждет улучшения прибыли")

    if peg is not None:
        if 0 < peg <= 1.5:
            score += 0.5
            reasons.append(f"PEG близок к разумной зоне: {peg:.2f}")
        elif peg > 2.5:
            score -= 0.5
            caveats.append(f"PEG {peg:.2f} намекает на дорогую оценку относительно роста")

    if latest_close is not None and analyst_target is not None and analyst_upside is not None:
        if analyst_upside >= 0.15:
            score += 0.75
            reasons.append(f"Средняя цель аналитиков выше цены на {format_percent(analyst_upside)}")
        elif analyst_upside <= -0.1:
            score -= 0.75
            caveats.append(f"Цель аналитиков ниже текущей цены на {format_percent(abs(analyst_upside))}")

    if five_month_return is not None:
        if five_month_return >= 0.15:
            score += 0.4
            reasons.append(f"За 5 месяцев акция прибавила {format_percent(five_month_return)}")
        elif five_month_return <= -0.15:
            score -= 0.5
            caveats.append(f"За 5 месяцев акция просела на {format_percent(abs(five_month_return))}")

    if beta is not None:
        if beta <= 1.1:
            score += 0.2
            reasons.append(f"Beta {beta:.2f} указывает на умеренный рыночный риск")
        elif beta >= 1.6:
            score -= 0.5
            caveats.append(f"Beta {beta:.2f} говорит о повышенной волатильности")

    if capm_expected is not None and stock_1y_return is not None:
        if stock_1y_return >= capm_expected + 0.05:
            score += 0.25
            reasons.append("Фактическая доходность за 1 год опережает CAPM-ожидание")
        elif stock_1y_return <= capm_expected - 0.1:
            score -= 0.4
            caveats.append("Доходность за 1 год заметно отстает от CAPM-ожидания")

    if roic is not None and wacc is not None:
        spread = roic - wacc
        if spread >= 0.02:
            score += 0.75
            reasons.append(f"ROIC выше WACC на {format_percent(spread)}")
        elif spread <= -0.01:
            score -= 0.75
            caveats.append(f"ROIC ниже WACC на {format_percent(abs(spread))}")

    if current_ratio is not None:
        if current_ratio >= 1.3:
            score += 0.2
            reasons.append(f"Ликвидность в норме: current ratio {current_ratio:.2f}")
        elif current_ratio < 1.0:
            score -= 0.4
            caveats.append(f"Current ratio {current_ratio:.2f} ниже 1.0")

    if net_debt_to_ebitda is not None:
        if net_debt_to_ebitda <= 2.0:
            score += 0.25
            reasons.append(f"Net debt / EBITDA контролируемый: {net_debt_to_ebitda:.2f}")
        elif net_debt_to_ebitda >= 4.0:
            score -= 0.6
            caveats.append(f"Net debt / EBITDA уже высокий: {net_debt_to_ebitda:.2f}")

    if fcf_margin is not None:
        if fcf_margin >= 0.10:
            score += 0.35
            reasons.append(f"Хорошая FCF маржа: {format_percent(fcf_margin)}")
        elif fcf_margin < 0:
            score -= 0.5
            caveats.append("Свободный денежный поток отрицательный")

    if score >= 2.75:
        label = "Покупать"
        color = "#0b6e4f"
    elif score >= 0.9:
        label = "Держать"
        color = "#b17800"
    else:
        label = "Продавать"
        color = "#b23a48"

    if not reasons:
        reasons.append(f"По {ticker} недостаточно сильных фундаментальных драйверов для агрессивной ставки")
    if not caveats:
        caveats.append("Явных критических красных флагов по базовым метрикам не видно")

    return Recommendation(label=label, color=color, score=score, reasons=reasons[:5], caveats=caveats[:5])


def build_recommendation_breakdown(info: dict[str, Any], analytics: dict[str, Any]) -> pd.DataFrame:
    factor_rows: list[tuple[str, str, str, str]] = []

    def add_row(name: str, raw_value: str, signal: str, explanation: str) -> None:
        factor_rows.append((name, raw_value, signal, explanation))

    revenue_growth = to_float(info.get("revenueGrowth"))
    if revenue_growth is not None:
        signal = "Buy" if revenue_growth >= 0.08 else "Sell" if revenue_growth < 0 else "Neutral"
        explanation = "Рост выручки поддерживает оценку" if signal == "Buy" else "Снижение выручки ухудшает сигнал" if signal == "Sell" else "Рост выручки умеренный"
        add_row("Revenue growth", format_percent(revenue_growth), signal, explanation)

    earnings_growth = to_float(info.get("earningsGrowth")) or to_float(info.get("earningsQuarterlyGrowth"))
    if earnings_growth is not None:
        signal = "Buy" if earnings_growth >= 0.08 else "Sell" if earnings_growth < 0 else "Neutral"
        explanation = "Прибыль растет и подтверждает momentum" if signal == "Buy" else "Прибыль сжимается" if signal == "Sell" else "Рост прибыли невыраженный"
        add_row("Earnings growth", format_percent(earnings_growth), signal, explanation)

    profit_margin = to_float(info.get("profitMargins"))
    if profit_margin is not None:
        signal = "Buy" if profit_margin >= 0.15 else "Sell" if profit_margin < 0 else "Neutral"
        explanation = "Высокая маржа дает запас прочности" if signal == "Buy" else "Отрицательная маржа — красный флаг" if signal == "Sell" else "Маржа средняя"
        add_row("Profit margin", format_percent(profit_margin), signal, explanation)

    roic = analytics.get("roic")
    wacc = analytics.get("wacc")
    if roic is not None and wacc is not None:
        spread = roic - wacc
        signal = "Buy" if spread >= 0.02 else "Sell" if spread <= -0.01 else "Neutral"
        explanation = "ROIC выше WACC: компания создает стоимость" if signal == "Buy" else "ROIC ниже WACC: капитал используется слабо" if signal == "Sell" else "Разница между ROIC и WACC небольшая"
        add_row("ROIC vs WACC", format_percent(spread), signal, explanation)

    analyst_upside = analytics.get("analyst_upside")
    if analyst_upside is not None:
        signal = "Buy" if analyst_upside >= 0.15 else "Sell" if analyst_upside <= -0.10 else "Neutral"
        explanation = "Цели аналитиков выше текущей цены" if signal == "Buy" else "Средняя цель ниже текущей цены" if signal == "Sell" else "Upside ограничен"
        add_row("Analyst upside", format_percent(analyst_upside), signal, explanation)

    five_month_return = analytics.get("five_month_return")
    if five_month_return is not None:
        signal = "Buy" if five_month_return >= 0.15 else "Sell" if five_month_return <= -0.15 else "Neutral"
        explanation = "Сильный momentum за 5 месяцев" if signal == "Buy" else "Слабый momentum за 5 месяцев" if signal == "Sell" else "Momentum смешанный"
        add_row("5M price return", format_percent(five_month_return), signal, explanation)

    beta = analytics.get("beta")
    if beta is not None:
        signal = "Sell" if beta >= 1.6 else "Buy" if beta <= 1.1 else "Neutral"
        explanation = "Низкая beta снижает рыночный риск" if signal == "Buy" else "Высокая beta повышает волатильность" if signal == "Sell" else "Риск близок к рынку"
        add_row("Beta", format_number(beta), signal, explanation)

    net_debt_to_ebitda = analytics.get("net_debt_to_ebitda")
    if net_debt_to_ebitda is not None:
        signal = "Buy" if net_debt_to_ebitda <= 2.0 else "Sell" if net_debt_to_ebitda >= 4.0 else "Neutral"
        explanation = "Долг контролируемый" if signal == "Buy" else "Долговая нагрузка высокая" if signal == "Sell" else "Долг приемлемый"
        add_row("Net debt / EBITDA", format_number(net_debt_to_ebitda), signal, explanation)

    current_ratio = analytics.get("current_ratio")
    if current_ratio is not None:
        signal = "Buy" if current_ratio >= 1.3 else "Sell" if current_ratio < 1.0 else "Neutral"
        explanation = "Краткосрочная ликвидность комфортная" if signal == "Buy" else "Ликвидность слабая" if signal == "Sell" else "Ликвидность нейтральная"
        add_row("Current ratio", format_number(current_ratio), signal, explanation)

    fcf_margin = analytics.get("fcf_margin")
    if fcf_margin is not None:
        signal = "Buy" if fcf_margin >= 0.10 else "Sell" if fcf_margin < 0 else "Neutral"
        explanation = "Свободный денежный поток поддерживает оценку" if signal == "Buy" else "FCF отрицательный" if signal == "Sell" else "FCF умеренный"
        add_row("FCF margin", format_percent(fcf_margin), signal, explanation)

    return pd.DataFrame(factor_rows, columns=["Фактор", "Значение", "Сигнал", "Почему это важно"])


def build_decision_narrative(bundle: dict[str, Any]) -> str:
    recommendation = normalize_recommendation_payload(bundle.get("recommendation"))
    ticker = bundle["ticker"]
    reasons = recommendation["reasons"][:3]
    caveats = recommendation["caveats"][:2]
    news_signal = bundle.get("news_signal", {"positive": 0, "negative": 0})
    if recommendation["label"] == "Покупать":
        base = f"По {ticker} модель склоняется к покупке: сильные сигналы идут от факторов {', '.join(reasons).lower()}."
    elif recommendation["label"] == "Держать":
        base = f"По {ticker} модель дает нейтральный сигнал: есть поддержка со стороны {', '.join(reasons[:2]).lower()}, но риски тоже заметны."
    else:
        base = f"По {ticker} модель склоняется к продаже: слабые места концентрируются в блоке {', '.join(caveats).lower()}."
    if news_signal["positive"] > news_signal["negative"]:
        return base + " Новостной фон сейчас скорее поддерживает бычий сценарий."
    if news_signal["negative"] > news_signal["positive"]:
        return base + " Новостной фон сейчас добавляет осторожности."
    return base + " Новостной поток не дает явного перекоса в одну сторону."


def build_company_insights(bundle: dict[str, Any]) -> list[str]:
    analytics = bundle["analytics"]
    insights = [build_decision_narrative(bundle)]
    if analytics["roic"] is not None and analytics["wacc"] is not None:
        spread = analytics["roic"] - analytics["wacc"]
        if spread >= 0.03:
            insights.append("Компания создает стоимость: ROIC заметно выше WACC.")
        elif spread <= -0.01:
            insights.append("Компания пока не покрывает стоимость капитала: ROIC ниже WACC.")
    if analytics["net_debt_to_ebitda"] is not None:
        if analytics["net_debt_to_ebitda"] <= 2.0:
            insights.append("Баланс выглядит относительно здоровым: долг контролируем по EBITDA.")
        elif analytics["net_debt_to_ebitda"] >= 4.0:
            insights.append("Долговая нагрузка уже высокая и может ограничивать upside для акционеров.")
    for line in bundle.get("news_signal", {}).get("headlines", [])[:2]:
        insights.append(line)
    if analytics["five_month_return"] is not None and analytics["analyst_upside"] is not None:
        if analytics["five_month_return"] < 0 and analytics["analyst_upside"] > 0.15:
            insights.append("Цена была слабой в последние месяцы, но консенсус аналитиков все еще видит заметный upside.")
        elif analytics["five_month_return"] > 0.2 and analytics["analyst_upside"] < 0.05:
            insights.append("Бумага уже сильно выросла, поэтому пространство для дальнейшего роста может быть ограничено.")
    return insights[:5]


def render_key_metrics_strip(bundle: dict[str, Any]) -> None:
    analytics = bundle["analytics"]
    symbol = currency_symbol(bundle.get("currency"))
    metrics = st.columns(6)
    with metrics[0]:
        metric_card("Цена", format_currency(analytics["latest_close"], symbol), "Последняя котировка")
    with metrics[1]:
        metric_card("5M return", format_percent(analytics["five_month_return"]), "Динамика за 5 месяцев")
    with metrics[2]:
        metric_card("Market Cap", format_currency(analytics["market_cap"], symbol), "Размер компании")
    with metrics[3]:
        metric_card("Beta", format_number(analytics["beta"]), "Рыночный риск")
    with metrics[4]:
        metric_card("WACC", format_percent(analytics["wacc"]), "Стоимость капитала")
    with metrics[5]:
        metric_card("Debt / EBITDA", format_number(analytics["net_debt_to_ebitda"]), "Долговая нагрузка")


def make_price_figure(history: pd.DataFrame, ticker: str) -> go.Figure:
    figure = go.Figure()
    close_column = "Adj Close" if "Adj Close" in history else "Close"
    figure.add_trace(
        go.Scatter(
            x=history.index,
            y=history[close_column],
            mode="lines",
            name=ticker,
            line={"color": "#1f4e79", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(31, 78, 121, 0.10)",
        )
    )
    figure.update_layout(
        height=420,
        margin={"l": 12, "r": 12, "t": 24, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.4)",
        hovermode="x unified",
        xaxis={"title": "", "showgrid": False},
        yaxis={"title": "Price", "gridcolor": "rgba(24,34,47,0.08)"},
        showlegend=False,
    )
    return figure


def render_company_snapshot(bundle: dict[str, Any]) -> None:
    info = bundle["info"]
    analytics = bundle["analytics"]
    recommendation = normalize_recommendation_payload(bundle.get("recommendation"))
    breakdown = build_recommendation_breakdown(info, analytics)
    decision_narrative = build_decision_narrative(bundle)

    company_name = bundle.get("company_name") or info.get("shortName") or info.get("longName") or bundle["ticker"]
    sector = info.get("sector") or ("Российский рынок" if bundle.get("source") == "moex" else "n/a")
    industry = info.get("industry") or "n/a"
    dividend_yield = to_float(info.get("dividendYield"))
    source_label = bundle.get("source_label", "Yahoo Finance")
    snapshot = bundle.get("snapshot", {})
    symbol = currency_symbol(bundle.get("currency"))

    st.markdown(
        f"""
        <div class="summary-card">
            <div class="section-label">{bundle["ticker"]} • {source_label}</div>
            <h3 style="margin:0;">{company_name}</h3>
            <div class="caption-text">{sector} • {industry}</div>
            <div style="margin-top:0.9rem;">
                <span class="recommendation-pill" style="background:{recommendation["color"]};">{recommendation["label"]}</span>
            </div>
            <div class="caption-text">Скоринг-модель: {recommendation["score"]:.2f}. Это аналитическая эвристика по рыночным и фундаментальным данным, а не инвестиционная рекомендация.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    compact_left, compact_right = st.columns(2)
    with compact_left:
        metric_card("Analyst upside", format_percent(analytics["analyst_upside"]), "Средняя цель аналитиков vs текущая цена")
        metric_card("Dividend yield", format_percent(dividend_yield), "Если компания выплачивает дивиденды")
        if bundle.get("source") == "moex":
            metric_card("MOEX turnover", format_currency(snapshot.get("turnover"), "₽"), f"Сделки за день • {snapshot.get('update_time') or 'время не указано'}")
    with compact_right:
        metric_card("CAPM expected return", format_percent(analytics["capm_expected"]), "Ожидаемая доходность по модели CAPM")
        metric_card("Факт. доходность за 1 год", format_percent(analytics["stock_1y_return"]), "Сравнение с CAPM и рынком")
        metric_card("Текущая цена", format_currency(analytics["latest_close"], symbol), "Последняя котировка по рынку")

    st.markdown('<div class="section-label">Решение модели</div>', unsafe_allow_html=True)
    st.markdown(decision_narrative)
    st.markdown('<div class="section-label">Почему модель так думает</div>', unsafe_allow_html=True)
    for reason in recommendation["reasons"]:
        st.markdown(f"- {fix_mojibake(reason)}")
    st.markdown('<div class="section-label" style="margin-top:0.8rem;">На что смотреть осторожно</div>', unsafe_allow_html=True)
    for caveat in recommendation["caveats"]:
        st.markdown(f"- {fix_mojibake(caveat)}")
    st.markdown('<div class="section-label" style="margin-top:0.8rem;">Расшифровка сигнала</div>', unsafe_allow_html=True)
    st.dataframe(breakdown, use_container_width=True, hide_index=True)


def render_financials(bundle: dict[str, Any]) -> None:
    info = bundle["info"]
    analytics = bundle["analytics"]
    symbol = currency_symbol(bundle.get("currency"))

    st.markdown('<div class="section-label">Финансовые показатели</div>', unsafe_allow_html=True)
    row1 = st.columns(3)
    with row1[0]:
        metric_card("Выручка", format_currency(analytics["revenue"], symbol), "Последний доступный период")
    with row1[1]:
        metric_card("Net income", format_currency(analytics["net_income"], symbol), "Чистая прибыль")
    with row1[2]:
        metric_card("EBITDA", format_currency(analytics["ebitda"], symbol), "Операционная прибыль до амортизации")

    row2 = st.columns(3)
    with row2[0]:
        metric_card("Free cash flow", format_currency(analytics["free_cash_flow"], symbol), "Свободный денежный поток")
    with row2[1]:
        metric_card("Operating cash flow", format_currency(analytics["operating_cash_flow"], symbol), "Операционный денежный поток")
    with row2[2]:
        metric_card("Cash / Debt", f"{format_currency(analytics['cash'], symbol)} / {format_currency(analytics['total_debt'], symbol)}", "Ликвидность и долговая нагрузка")

    multiples = pd.DataFrame(
        [
            ("Trailing P/E", format_number(info.get("trailingPE"))),
            ("Forward P/E", format_number(info.get("forwardPE"))),
            ("PEG", format_number(info.get("pegRatio"))),
            ("Price / Book", format_number(info.get("priceToBook"))),
            ("P / Sales", format_number(info.get("priceToSalesTrailing12Months"))),
            ("EV / EBITDA", format_number(info.get("enterpriseToEbitda"))),
            ("EV / Sales", format_number(analytics["ev_to_sales"])),
            ("Profit margin", format_percent(to_float(info.get("profitMargins")))),
            ("Operating margin", format_percent(to_float(info.get("operatingMargins")))),
            ("ROE", format_percent(to_float(info.get("returnOnEquity")))),
            ("ROA", format_percent(to_float(info.get("returnOnAssets")))),
            ("ROIC", format_percent(analytics["roic"])),
            ("WACC", format_percent(analytics["wacc"])),
            ("FCF margin", format_percent(analytics["fcf_margin"])),
            ("Operating CF margin", format_percent(analytics["operating_cf_margin"])),
            ("Current ratio", format_number(analytics["current_ratio"])),
            ("Debt / EBITDA", format_number(analytics["debt_to_ebitda"])),
            ("Net debt / EBITDA", format_number(analytics["net_debt_to_ebitda"])),
            ("Cost of equity", format_percent(analytics["cost_of_equity"])),
            ("Cost of debt", format_percent(analytics["cost_of_debt"])),
            ("Tax rate", format_percent(analytics["tax_rate"])),
            ("Revenue growth", format_percent(to_float(info.get("revenueGrowth")))),
            ("Earnings growth", format_percent(to_float(info.get("earningsGrowth")) or to_float(info.get("earningsQuarterlyGrowth")))),
        ],
        columns=["Metric", "Value"],
    )
    st.dataframe(multiples, use_container_width=True, hide_index=True)
    st.caption("WACC и ROIC здесь приближенные: cost of equity считается через CAPM, cost of debt — как interest expense / debt после налогового щита.")


def render_news(bundle: dict[str, Any]) -> None:
    st.markdown('<div class="section-label">Ключевые новости</div>', unsafe_allow_html=True)
    news = bundle["news"]
    if not news:
        st.info("Yahoo Finance не вернул свежие новости по этому тикеру.")
        return
    for item in news:
        publish_label = format_publish_time(item["publish_time"])
        link_html = f'<a href="{item["link"]}" target="_blank">Открыть новость</a>' if item["link"] else ""
        summary = item["summary"] or "Краткое описание не было передано в ответе API."
        st.markdown(
            f"""
            <div class="news-card">
                <div class="metric-title">{item["publisher"]} • {publish_label}</div>
                <div style="font-weight:700; font-size:1rem; margin:0.2rem 0 0.45rem 0;">{item["title"]}</div>
                <div class="caption-text">{summary}</div>
                <div style="margin-top:0.55rem;">{link_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def format_publish_time(value: Any) -> str:
    if value is None:
        return "Дата не указана"
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            return value
    return str(value)


def render_chart(bundle: dict[str, Any]) -> None:
    st.markdown('<div class="section-label">Динамика цены за последние 5 месяцев</div>', unsafe_allow_html=True)
    history = bundle["history"].copy()
    if history.empty:
        st.error("По тикеру не удалось получить ценовой ряд.")
        return
    cutoff = history.index.max() - pd.DateOffset(months=5)
    clipped = history[history.index >= cutoff]
    figure = make_price_figure(clipped, bundle["ticker"])
    st.plotly_chart(figure, use_container_width=True)
    total_return = price_return(clipped)
    if total_return is not None:
        st.caption(f"Изменение цены за 5 месяцев: {format_percent(total_return)}")


def render_dashboard(tickers: list[str]) -> None:
    for ticker in tickers:
        st.markdown(f'<div class="ticker-header"></div>', unsafe_allow_html=True)
        try:
            bundle = load_company_bundle(ticker)
        except Exception as error:  # noqa: BLE001
            st.error(f"{ticker}: не удалось загрузить данные терминала. Детали: {error}")
            continue

        render_key_metrics_strip(bundle)

        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            render_chart(bundle)
        with right:
            render_company_snapshot(bundle)

        financials_col, news_col = st.columns([1.05, 0.95], gap="large")
        with financials_col:
            render_financials(bundle)
        with news_col:
            render_news(bundle)


def build_peer_comparison_table(bundles: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for bundle in bundles:
        analytics = bundle["analytics"]
        info = bundle["info"]
        rows.append(
            {
                "Ticker": bundle["ticker"],
                "Компания": bundle.get("company_name") or bundle["ticker"],
                "Рынок": "Россия" if bundle.get("source") == "moex" else "США",
                "Цена": format_currency(analytics["latest_close"], currency_symbol(bundle.get("currency"))),
                "5M return": format_percent(analytics["five_month_return"]),
                "Market Cap": format_currency(analytics["market_cap"], currency_symbol(bundle.get("currency"))),
                "Revenue growth": format_percent(info.get("revenueGrowth")),
                "Profit margin": format_percent(info.get("profitMargins")),
                "ROIC": format_percent(analytics["roic"]),
                "WACC": format_percent(analytics["wacc"]),
                "Debt / EBITDA": format_number(analytics["net_debt_to_ebitda"]),
                "Forward P/E": format_number(info.get("forwardPE")),
                "EV / EBITDA": format_number(info.get("enterpriseToEbitda")),
                "Решение": normalize_recommendation_payload(bundle.get("recommendation"))["label"],
            }
        )
    return pd.DataFrame(rows)


def build_group_insights(group_name: str, table: pd.DataFrame) -> list[str]:
    insights: list[str] = []
    if table.empty:
        return insights
    margin_series = pd.to_numeric(table["Profit margin"].str.replace("%", "", regex=False), errors="coerce")
    if margin_series.notna().any():
        best = table.loc[margin_series.idxmax()]
        insights.append(f"В группе «{group_name}» лидер по марже — {best['Компания']} ({best['Ticker']}).")
    roic_series = pd.to_numeric(table["ROIC"].str.replace("%", "", regex=False), errors="coerce")
    if roic_series.notna().any():
        best = table.loc[roic_series.idxmax()]
        insights.append(f"Лучшая отдача на капитал в группе у {best['Компания']} ({best['ROIC']}).")
    pe_series = pd.to_numeric(table["Forward P/E"], errors="coerce")
    if pe_series.notna().any():
        best = table.loc[pe_series.idxmin()]
        insights.append(f"Самая дешевая бумага по forward P/E в группе — {best['Компания']} ({best['Forward P/E']}).")
    debt_series = pd.to_numeric(table["Debt / EBITDA"], errors="coerce")
    if debt_series.notna().any():
        best = table.loc[debt_series.idxmin()]
        insights.append(f"Наиболее комфортная долговая нагрузка в группе у {best['Компания']} ({best['Debt / EBITDA']}).")
    return insights[:4]


def render_peer_comparison() -> None:
    st.markdown('<div class="section-label">Сравнение российских и американских компаний</div>', unsafe_allow_html=True)
    selected_groups = st.multiselect(
        "Индустрии для сравнения",
        options=list(PEER_GROUPS.keys()),
        default=["Банки", "Энергетика", "Интернет и платформы", "Ритейл"],
    )
    for group_name in selected_groups:
        mapping = PEER_GROUPS[group_name]
        bundles = []
        for ticker in mapping["US"] + mapping["RU"]:
            try:
                bundles.append(load_company_bundle(ticker))
            except Exception:
                continue
        if not bundles:
            st.warning(f"Для группы «{group_name}» не удалось получить данные.")
            continue
        table = build_peer_comparison_table(bundles)
        st.markdown(f"### {group_name}")
        st.dataframe(table, use_container_width=True, hide_index=True)
        for insight in build_group_insights(group_name, table):
            st.markdown(f"- {insight}")


def render_global_insights(tickers: list[str]) -> None:
    st.markdown('<div class="section-label">Лента инсайтов</div>', unsafe_allow_html=True)
    for ticker in tickers:
        try:
            bundle = load_company_bundle(ticker)
        except Exception:
            continue
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="section-label">{bundle["ticker"]} • {bundle.get("source_label", "Yahoo Finance")}</div>
                <h3 style="margin:0;">{bundle.get("company_name") or bundle["ticker"]}</h3>
                <div class="caption-text">{build_decision_narrative(bundle)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for insight in build_company_insights(bundle)[1:]:
            st.markdown(f"- {insight}")


def render_top_controls() -> list[str]:
    if "selected_tickers" not in st.session_state:
        st.session_state["selected_tickers"] = DEFAULT_TICKERS.copy()
    if "search_results_selection" not in st.session_state:
        st.session_state["search_results_selection"] = []

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Поиск компаний</div>', unsafe_allow_html=True)
    top_left, top_mid, top_right = st.columns([1.2, 1.0, 0.8], gap="large")
    with top_left:
        search_query = st.text_input(
            "Поиск компаний или тикеров",
            placeholder="Например: Apple, NVDA, JPMorgan, Coca-Cola",
            label_visibility="collapsed",
        )
    with top_mid:
        manual_input = st.text_input(
            "Добавить тикеры вручную",
            placeholder="Например: AMD, ORCL, SAP",
            label_visibility="collapsed",
        )
    with top_right:
        if st.button("Добавить тикеры", use_container_width=True):
            add_tickers_to_state(parse_tickers(manual_input))

    results = search_quotes(search_query) if search_query.strip() else []
    selected_from_results: list[str] = []
    if results:
        result_map = {f"{item['label']} ({item['exchange']})".strip(): item["symbol"] for item in results}
        selected_labels = st.multiselect(
            "Результаты поиска Yahoo Finance / MOEX",
            options=list(result_map.keys()),
            key="search_results_selection",
        )
        selected_from_results = [result_map[label] for label in selected_labels]
        if st.button("Добавить из поиска"):
            add_tickers_to_state(selected_from_results)

    available_options = list(dict.fromkeys(st.session_state["selected_tickers"] + list(POPULAR_COMPANIES.keys())))
    selected = st.multiselect(
        "Компании в дашборде",
        options=available_options,
        default=st.session_state["selected_tickers"],
        format_func=lambda ticker: f"{ticker} — {POPULAR_COMPANIES.get(ticker, 'Custom')}",
    )
    st.session_state["selected_tickers"] = selected
    st.caption("Можно искать компании через Yahoo и MOEX сверху, добавлять тикеры вручную и сразу убирать лишние из списка терминала.")
    st.markdown("</div>", unsafe_allow_html=True)
    return selected or DEFAULT_TICKERS


def main() -> None:
    configure_page()
    st.markdown(
        """
        <div class="hero">
            <div class="section-label">Market Terminal</div>
            <h1 style="margin:0;">Аналог mini-Bloomberg: Yahoo Finance + MOEX, сравнение рынков и объяснимые инсайты</h1>
            <p class="caption-text" style="margin-top:0.55rem;">
                Терминал собирает котировки, новости и фундаментальные показатели по акциям США и России.
                Для американских бумаг используется Yahoo Finance, для российских — связка MOEX ISS API и Yahoo Finance.
                Внутри есть обзорный терминал, вкладка сравнений по индустриям и лента познавательных инсайтов.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tickers = render_top_controls()

    st.sidebar.header("Параметры")
    st.sidebar.caption("США: Yahoo Finance")
    st.sidebar.caption("Россия: MOEX ISS API + Yahoo Finance")
    st.sidebar.caption("Benchmark: SPY для США, IMOEX для России")
    st.sidebar.caption("Risk-free proxy: 13-week Treasury Bill (^IRX)")
    st.sidebar.caption("WACC: market cap + debt, cost of equity from CAPM, after-tax cost of debt")
    st.sidebar.caption("Источники: Yahoo Finance chart / quote / news / financial statements + MOEX ISS")

    if st.sidebar.button("Обновить данные", use_container_width=True):
        st.cache_data.clear()

    tab_terminal, tab_compare, tab_insights = st.tabs(["Терминал", "Сравнение RU vs US", "Инсайты"])
    with tab_terminal:
        render_dashboard(tickers)
    with tab_compare:
        render_peer_comparison()
    with tab_insights:
        render_global_insights(tickers)


if __name__ == "__main__":
    main()
