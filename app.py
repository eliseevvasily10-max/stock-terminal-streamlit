"""
Bloomberg-style Terminal  —  NYSE/NASDAQ + Московская Биржа (MOEX ISS)
Для начинающих трейдеров: обучающие подсказки, технические индикаторы, риск-разбор.

Запуск:  python app.py   →   http://127.0.0.1:8050
"""

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import json, time, re, math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
import dash
from dash import ALL, Input, Output, State, callback_context, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import moex_client as moex

# ══════════════════════════════════════════════════════════════════════════════
# 2. ЦВЕТОВАЯ СХЕМА (Bloomberg dark)
# ══════════════════════════════════════════════════════════════════════════════
BG      = "#070d14"
PANEL   = "#0e1621"
PANEL2  = "#141e2d"
PANEL3  = "#0a1220"
BORDER  = "#1e2d40"
BORDER2 = "#243447"
TEXT    = "#d1dce8"
TEXT2   = "#6b8199"
TEXT3   = "#3d5166"
ACCENT  = "#1d9bf0"
GREEN   = "#00c875"
RED     = "#f4212e"
YELLOW  = "#ffd700"
ORANGE  = "#ff8c00"
PURPLE  = "#a78bfa"

MONO = "'JetBrains Mono','Cascadia Code','Consolas',monospace"
SANS = "'Inter','Segoe UI',system-ui,sans-serif"

TAB_S  = {"color":TEXT2,"backgroundColor":PANEL, "border":"none","padding":"7px 11px","fontSize":"12px"}
TAB_AS = {"color":TEXT, "backgroundColor":BG,"border":f"2px solid {ACCENT}",
          "borderBottom":"none","padding":"7px 11px","fontSize":"12px"}

# ══════════════════════════════════════════════════════════════════════════════
# 3. КОНСТАНТЫ — АКЦИИ
# ══════════════════════════════════════════════════════════════════════════════
US_SECTORS: dict[str,dict[str,str]] = {
    "💻 Technology":  {"AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","GOOGL":"Alphabet",
                       "META":"Meta","TSLA":"Tesla","AMZN":"Amazon"},
    "🏦 Financials":  {"JPM":"JPMorgan","BRK-B":"Berkshire","BAC":"BofA",
                       "GS":"Goldman Sachs","V":"Visa","MA":"Mastercard"},
    "🏥 Healthcare":  {"JNJ":"J&J","UNH":"UnitedHealth","LLY":"Eli Lilly",
                       "ABBV":"AbbVie","PFE":"Pfizer"},
    "🛒 Consumer":    {"PG":"P&G","KO":"Coca-Cola","WMT":"Walmart","COST":"Costco"},
    "⚡ Energy":      {"XOM":"ExxonMobil","CVX":"Chevron"},
}

RU_SECTORS: dict[str,dict[str,str]] = {
    "💻 Технологии":  {"YDEX":"Яндекс","OZON":"Ozon","VKCO":"VK",
                       "POSI":"Positive Tech","ASTR":"Астра"},
    "🏦 Финансы":     {"SBER":"Сбербанк","TCSG":"Т-Банк","VTBR":"ВТБ",
                       "MOEX":"Мосбиржа","BSPB":"БСП"},
    "⛽ Нефть/газ":   {"GAZP":"Газпром","LKOH":"Лукойл","NVTK":"Новатэк",
                       "ROSN":"Роснефть","SNGS":"Сургут","TATN":"Татнефть"},
    "🛒 Потребит.":   {"MGNT":"Магнит","FIVE":"X5 Group","LENT":"Лента"},
    "⚙️ Металлы":    {"GMKN":"Норникель","CHMF":"Северсталь",
                       "NLMK":"НЛМК","PLZL":"Полюс","MAGN":"ММК"},
    "📡 Телеком":     {"MTSS":"МТС","RTKM":"Ростелеком"},
}

ALL_US = {s:n for d in US_SECTORS.values()  for s,n in d.items()}
ALL_RU = {s:n for d in RU_SECTORS.values() for s,n in d.items()}

TICKER_SECTOR: dict[str,str] = {}
for _sec,_stk in {**US_SECTORS,**RU_SECTORS}.items():
    for _sym in _stk: TICKER_SECTOR[_sym] = _sec

SECTOR_PE_BENCH = {
    "💻 Technology":28.0,"💻 Технологии":18.0,
    "🏦 Financials":13.0,"🏦 Финансы":6.0,
    "🏥 Healthcare":22.0,"🛒 Consumer":24.0,
    "🛒 Потребит.":10.0,"⚡ Energy":12.0,
    "⛽ Нефть/газ":4.5,"⚙️ Металлы":8.0,"📡 Телеком":9.0,
}

COMPARISON_SECTORS = [
    {"label":"⚡ Нефть и газ",
     "us":{"XOM":"ExxonMobil","CVX":"Chevron"},
     "ru":{"GAZP":"Газпром","LKOH":"Лукойл","NVTK":"Новатэк","ROSN":"Роснефть"}},
    {"label":"🏦 Банки",
     "us":{"JPM":"JPMorgan","BAC":"BofA","GS":"Goldman","V":"Visa"},
     "ru":{"SBER":"Сбербанк","TCSG":"Т-Банк","VTBR":"ВТБ","MOEX":"Мосбиржа"}},
    {"label":"💻 Технологии",
     "us":{"AAPL":"Apple","MSFT":"Microsoft","GOOGL":"Alphabet","META":"Meta"},
     "ru":{"YDEX":"Яндекс","OZON":"Ozon","VKCO":"VK","POSI":"Positive"}},
    {"label":"🛒 Ритейл",
     "us":{"WMT":"Walmart","COST":"Costco","KO":"Coca-Cola","PG":"P&G"},
     "ru":{"MGNT":"Магнит","FIVE":"X5 Group","LENT":"Лента"}},
    {"label":"⚙️ Металлы",
     "us":{"FCX":"Freeport","NUE":"Nucor","STLD":"Steel Dyn."},
     "ru":{"GMKN":"Норникель","CHMF":"Северсталь","NLMK":"НЛМК","PLZL":"Полюс"}},
]

MARKET_STRIP_YF = [
    ("S&P 500","^GSPC"),("NASDAQ","^IXIC"),("DOW","^DJI"),
    ("VIX","^VIX"),("RTS","^RTSI"),
    ("BRENT","BZ=F"),("GOLD","GC=F"),("USD/RUB","USDRUB=X"),("BTC","BTC-USD"),
]

POS_KW = ["beat","exceed","surpass","record","upgrade","outperform","growth","profit",
          "dividend","buyback","rally","surge","strong","raised","buy","overweight",
          "bullish","partnership","acquisition","breakthrough","expansion"]
NEG_KW = ["miss","below","downgrade","underperform","loss","decline","cut","lawsuit",
          "investigation","fine","penalty","layoff","recall","warning","sell",
          "bearish","debt","probe","fraud","disappointing","concern","lowered"]

# Глоссарий для новичков
GLOSSARY = {
    "P/E": ("P/E (Price-to-Earnings) — коэффициент цена/прибыль",
             "Показывает, сколько рублей/долларов инвесторы платят за $1 прибыли компании. "
             "P/E=15 → вы платите $15 за каждый $1 годовой прибыли.\n"
             "🟢 <15 — дёшево   ⚪ 15-25 — нормально   🔴 >30 — дорого"),
    "P/B": ("P/B (Price-to-Book) — цена к балансовой стоимости",
             "Сколько платите за $1 чистых активов компании. "
             "P/B<1 → торгуется ниже реальной стоимости активов.\n"
             "🟢 <1.5 — дёшево   ⚪ 1.5-4 — нормально   🔴 >8 — дорого"),
    "ROE": ("ROE (Return on Equity) — рентабельность капитала",
             "Сколько прибыли компания получает на каждый $1 вложенного акционерами капитала.\n"
             "🟢 >20% — отлично   ⚪ 10-20% — нормально   🔴 <0% — убыток"),
    "EV/EBITDA": ("EV/EBITDA — стоимость бизнеса к операционной прибыли",
                   "Показывает за сколько лет бизнес окупит себя исходя из текущей прибыли.\n"
                   "🟢 <8x — дёшево   ⚪ 8-15x — нормально   🔴 >20x — дорого"),
    "Beta": ("Beta (β) — рыночный риск акции",
              "Показывает, насколько акция движется вместе с рынком.\n"
              "β=1.0 → движется как рынок   β=0.5 → вдвое спокойнее рынка\n"
              "β=2.0 → вдвое волатильнее   β<0 → движется против рынка"),
    "CAPM": ("CAPM — ожидаемая доходность по модели ценообразования",
              "Формула: CAPM = Rf + β × (Rm − Rf)\n"
              "Rf = безрисковая ставка (US Treasury)   Rm = доходность рынка (~10%)\n"
              "Это минимальная доходность, которую требует рынок за данный уровень риска."),
    "WACC": ("WACC — средневзвешенная стоимость капитала",
              "Минимальная доходность, которую компания должна получать, чтобы не терять стоимость.\n"
              "WACC = (E/V)·Re + (D/V)·Rd·(1−T)\n"
              "Если ROE > WACC → компания создаёт стоимость. Если ROE < WACC → разрушает."),
    "RSI": ("RSI (Relative Strength Index) — индекс относительной силы",
             "Технический индикатор от 0 до 100 для определения перекупленности/перепроданности.\n"
             "🔴 >70 — перекуплен (возможна коррекция)   🟡 30-70 — нейтрально\n"
             "🟢 <30 — перепродан (возможный отскок)"),
    "Free Cash Flow": ("FCF — свободный денежный поток",
                        "Деньги, которые остаются после всех расходов на развитие бизнеса.\n"
                        "FCF > 0 → компания реально зарабатывает деньги, может платить дивиденды.\n"
                        "FCF < 0 → сжигает деньги — может быть нормально для растущих компаний."),
    "Dividend Yield": ("Dividend Yield — дивидендная доходность",
                        "Годовые дивиденды как % от текущей цены акции.\n"
                        "🟢 >3% — хорошая доходность   ⚪ 1-3% — умеренная   ⚫ 0% — дивидендов нет"),
}

# ══════════════════════════════════════════════════════════════════════════════
# 4. КЭШИ
# ══════════════════════════════════════════════════════════════════════════════
_YF_CACHE:   dict = {}
_PEER_CACHE: dict = {}

def _yf_info(sym: str, ttl: int = 300) -> dict:
    e = _YF_CACHE.get(f"i_{sym}")
    if e and time.time()-e[1] < ttl: return e[0]
    try:    d = yf.Ticker(sym).info or {}
    except: d = {}
    _YF_CACHE[f"i_{sym}"] = (d, time.time())
    return d

def _yf_hist(sym: str, period: str = "5mo") -> pd.DataFrame:
    e = _YF_CACHE.get(f"h_{sym}_{period}")
    if e and time.time()-e[1] < 300: return e[0]
    try:    d = yf.Ticker(sym).history(period=period, interval="1d")
    except: d = pd.DataFrame()
    _YF_CACHE[f"h_{sym}_{period}"] = (d, time.time())
    return d

# ══════════════════════════════════════════════════════════════════════════════
# 5. ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ
# ══════════════════════════════════════════════════════════════════════════════
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _macd(close: pd.Series):
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal

def _bollinger(close: pd.Series, period: int = 20):
    ma  = close.rolling(period).mean()
    std = close.rolling(period).std()
    return ma + 2*std, ma, ma - 2*std

def _tech_signals(close: pd.Series) -> list[dict]:
    """Возвращает список торговых сигналов для новичка."""
    sigs = []
    if len(close) < 30:
        return sigs

    rsi = _rsi(close)
    rsi_now = rsi.iloc[-1]
    rsi_prev = rsi.iloc[-2] if len(rsi) > 1 else rsi_now

    if not pd.isna(rsi_now):
        if rsi_now < 30:
            sigs.append({"type":"BUY","icon":"🟢","label":f"RSI {rsi_now:.0f} — Перепродан",
                         "detail":"RSI ниже 30: акция возможно избыточно распродана. Технически — сигнал на отскок."})
        elif rsi_now > 70:
            sigs.append({"type":"SELL","icon":"🔴","label":f"RSI {rsi_now:.0f} — Перекуплен",
                         "detail":"RSI выше 70: акция возможно перегрета. Технически — сигнал на коррекцию."})
        elif 40 <= rsi_now <= 60:
            sigs.append({"type":"NEUTRAL","icon":"⚪","label":f"RSI {rsi_now:.0f} — Нейтральный",
                         "detail":"RSI в нейтральной зоне (40-60). Нет явного сигнала перекупленности/перепроданности."})

    # MA crossover
    if len(close) >= 50:
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        if not pd.isna(ma20.iloc[-1]) and not pd.isna(ma50.iloc[-1]):
            if ma20.iloc[-1] > ma50.iloc[-1] and ma20.iloc[-2] <= ma50.iloc[-2]:
                sigs.append({"type":"BUY","icon":"🟢","label":"MA20 пересекла MA50 снизу (золотой крест)",
                             "detail":"Краткосрочная MA20 перешла выше долгосрочной MA50 — классический бычий сигнал."})
            elif ma20.iloc[-1] < ma50.iloc[-1] and ma20.iloc[-2] >= ma50.iloc[-2]:
                sigs.append({"type":"SELL","icon":"🔴","label":"MA20 пересекла MA50 сверху (мёртвый крест)",
                             "detail":"MA20 упала ниже MA50 — классический медвежий сигнал смены тренда."})
            elif ma20.iloc[-1] > ma50.iloc[-1]:
                sigs.append({"type":"BUY","icon":"🟡","label":"MA20 > MA50 — восходящий тренд",
                             "detail":"Краткосрочная скользящая выше долгосрочной — тренд восходящий."})
            else:
                sigs.append({"type":"SELL","icon":"🟡","label":"MA20 < MA50 — нисходящий тренд",
                             "detail":"Краткосрочная скользящая ниже долгосрочной — тренд нисходящий."})

    # MACD
    macd, signal, _ = _macd(close)
    if not pd.isna(macd.iloc[-1]) and not pd.isna(signal.iloc[-1]):
        if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            sigs.append({"type":"BUY","icon":"🟢","label":"MACD пересёк сигнальную линию снизу",
                         "detail":"MACD > Signal: ускорение роста, импульс меняется на бычий."})
        elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            sigs.append({"type":"SELL","icon":"🔴","label":"MACD пересёк сигнальную линию сверху",
                         "detail":"MACD < Signal: замедление роста, импульс меняется на медвежий."})

    # Bollinger bands
    if len(close) >= 20:
        bb_up, bb_mid, bb_low = _bollinger(close)
        c_now = close.iloc[-1]
        if not pd.isna(bb_up.iloc[-1]):
            if c_now > bb_up.iloc[-1]:
                sigs.append({"type":"SELL","icon":"🔴","label":"Цена выше верхней полосы Боллинджера",
                             "detail":"Цена вышла за 2σ вверх — статистически высокая вероятность возврата к среднему."})
            elif c_now < bb_low.iloc[-1]:
                sigs.append({"type":"BUY","icon":"🟢","label":"Цена ниже нижней полосы Боллинджера",
                             "detail":"Цена вышла за 2σ вниз — статистически возможен отскок к среднему."})

    return sigs

# ══════════════════════════════════════════════════════════════════════════════
# 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════════════
def fmt(val, pct=False, suffix="", d=2, pfx="$"):
    if val is None or (isinstance(val,float) and pd.isna(val)): return "N/A"
    if pct: return f"{val*100:.1f}%"
    if isinstance(val,(int,float)):
        p = pfx
        if   abs(val)>=1e12: return f"{p}{val/1e12:.2f}T{suffix}"
        elif abs(val)>=1e9:  return f"{p}{val/1e9:.1f}B{suffix}"
        elif abs(val)>=1e6:  return f"{p}{val/1e6:.1f}M{suffix}"
        return f"{val:.{d}f}{suffix}"
    return str(val)

def clr(v, ga=None, ba=None, gl=None, bl=None):
    if v is None or (isinstance(v,float) and pd.isna(v)): return TEXT2
    if ga is not None and v >= ga: return GREEN
    if ba is not None and v >= ba: return RED
    if gl is not None and v <= gl: return GREEN
    if bl is not None and v <= bl: return RED
    return TEXT

def get_rf() -> float:
    try:
        h = yf.Ticker("^TNX").history(period="5d")
        if not h.empty: return h["Close"].iloc[-1]/100
    except: pass
    return 0.043

def calc_wacc(info: dict, rf: float) -> dict | None:
    b = info.get("beta"); mc = info.get("marketCap")
    if not b or not mc: return None
    re_ = rf + b*(0.10-rf)
    debt = info.get("totalDebt") or 0
    if debt > 0:
        interest = abs(info.get("interestExpense") or 0)
        rd = interest/debt if interest else 0.05
        tax = info.get("effectiveTaxRate") or 0.21
        v = mc+debt
        return {"wacc":(mc/v)*re_+(debt/v)*rd*(1-tax),"re":re_,"rd":rd,"tax":tax,"ew":mc/v,"dw":debt/v}
    return {"wacc":re_,"re":re_,"rd":None,"tax":None,"ew":1.0,"dw":0.0}

def _med(lst):
    lst = [x for x in lst if x and not (isinstance(x,float) and pd.isna(x))]
    return sorted(lst)[len(lst)//2] if lst else None

# ══════════════════════════════════════════════════════════════════════════════
# 7. ДВИЖОК РЕКОМЕНДАЦИЙ
# ══════════════════════════════════════════════════════════════════════════════
def news_sentiment(news):
    score, signals = 0, []
    for item in news[:10]:
        ct = item.get("content",{}) if isinstance(item,dict) else {}
        title = (ct.get("title") or item.get("title","")).lower()
        raw   = ct.get("title") or item.get("title","")
        pos = sum(1 for k in POS_KW if k in title)
        neg = sum(1 for k in NEG_KW if k in title)
        if pos>neg:  score+=1; signals.append(("🟢", raw))
        elif neg>pos:score-=1; signals.append(("🔴", raw))
    return score, signals[:4]

def build_recommendation(info: dict, news: list, ticker: str, is_ru: bool = False) -> dict:
    total = 0; blocks = []
    sector = TICKER_SECTOR.get(ticker,"")
    bench  = SECTOR_PE_BENCH.get(sector,20.0)
    price  = info.get("currentPrice") or info.get("regularMarketPrice")
    low52  = info.get("fiftyTwoWeekLow")
    high52 = info.get("fiftyTwoWeekHigh")
    beta   = info.get("beta")
    rf     = get_rf()

    # Оценка
    vi=[]; vs=0
    pe_t=info.get("trailingPE"); pe_f=info.get("forwardPE")
    if pe_t:
        r=pe_t/bench
        if   r<0.65: d,ic=+2,"🟢"; tx=f"P/E {pe_t:.1f}x — дисконт {(1-r)*100:.0f}% к сектору ({bench:.0f}x). Недооценена."
        elif r<0.90: d,ic=+1,"🟢"; tx=f"P/E {pe_t:.1f}x — чуть ниже среднего по сектору ({bench:.0f}x)."
        elif r<1.20: d,ic= 0,"⚪"; tx=f"P/E {pe_t:.1f}x — соответствует сектору ({bench:.0f}x)."
        elif r<1.60: d,ic=-1,"🟡"; tx=f"P/E {pe_t:.1f}x — на {(r-1)*100:.0f}% выше сектора ({bench:.0f}x)."
        else:         d,ic=-2,"🔴"; tx=f"P/E {pe_t:.1f}x — значительная премия к сектору ({bench:.0f}x)."
        vs+=d; vi.append({"ic":ic,"txt":tx,"d":d})
    if pe_f and pe_t:
        if pe_f<pe_t*0.82: vs+=1; vi.append({"ic":"🟢","txt":f"Forward P/E {pe_f:.1f}x < trailing — ожидается рост прибыли.","d":+1})
        elif pe_f>pe_t*1.12: vs-=1; vi.append({"ic":"🔴","txt":f"Forward P/E {pe_f:.1f}x > trailing — прибыль может снизиться.","d":-1})
    pb=info.get("priceToBook")
    if pb:
        if pb<1.5: vs+=1; vi.append({"ic":"🟢","txt":f"P/B {pb:.1f}x — близко к балансовой стоимости.","d":+1})
        elif pb>8: vs-=1; vi.append({"ic":"🔴","txt":f"P/B {pb:.1f}x — высокая премия к активам.","d":-1})
        else:      vi.append({"ic":"⚪","txt":f"P/B {pb:.1f}x — умеренная оценка.","d":0})
    ev=info.get("enterpriseToEbitda")
    if ev:
        if ev<8:  vs+=1; vi.append({"ic":"🟢","txt":f"EV/EBITDA {ev:.1f}x — привлекательный мультипликатор.","d":+1})
        elif ev>22:vs-=1; vi.append({"ic":"🔴","txt":f"EV/EBITDA {ev:.1f}x — дорогая оценка.","d":-1})
        else:      vi.append({"ic":"⚪","txt":f"EV/EBITDA {ev:.1f}x — в норме.","d":0})
    if vi: blocks.append({"title":"📊 Оценка (Valuation)","items":vi,"score":vs}); total+=vs

    # Рост
    gi=[]; gs=0
    for val,name,good,bad in [
        (info.get("revenueGrowth"),"Выручка",0.07,-0.05),
        (info.get("earningsGrowth"),"EPS",0.10,-0.10),
    ]:
        if val is None: continue
        if val>0.20: d,ic=+2,"🟢"; tx=f"{name} +{val*100:.1f}% г/г — сильный рост."
        elif val>good:d,ic=+1,"🟢"; tx=f"{name} +{val*100:.1f}% г/г."
        elif val>0:   d,ic= 0,"⚪"; tx=f"{name} +{val*100:.1f}% г/г — слабый рост."
        elif val>bad: d,ic=-1,"🟡"; tx=f"{name} {val*100:.1f}% г/г — снижение."
        else:         d,ic=-2,"🔴"; tx=f"{name} {val*100:.1f}% г/г — существенное падение."
        gs+=d; gi.append({"ic":ic,"txt":tx,"d":d})
    gm=info.get("grossMargins")
    if gm:
        if gm>0.55: gs+=1; gi.append({"ic":"🟢","txt":f"Валовая маржа {gm*100:.1f}% — высокая ценовая власть.","d":+1})
        elif gm<0.15:gs-=1;gi.append({"ic":"🔴","txt":f"Валовая маржа {gm*100:.1f}% — слабая маржинальность.","d":-1})
        else:        gi.append({"ic":"⚪","txt":f"Валовая маржа {gm*100:.1f}%.","d":0})
    if gi: blocks.append({"title":"📈 Рост и рентабельность","items":gi,"score":gs}); total+=gs

    # Здоровье
    fi=[]; fs=0
    roe=info.get("returnOnEquity")
    if roe is not None:
        if roe>0.25: fs+=2; fi.append({"ic":"🟢","txt":f"ROE {roe*100:.1f}% — отличная отдача на капитал.","d":+2})
        elif roe>0.12:fs+=1;fi.append({"ic":"🟢","txt":f"ROE {roe*100:.1f}% — приемлемо.","d":+1})
        elif roe<0:  fs-=2; fi.append({"ic":"🔴","txt":f"ROE {roe*100:.1f}% — разрушение стоимости.","d":-2})
        else:        fi.append({"ic":"⚪","txt":f"ROE {roe*100:.1f}% — ниже нормы.","d":0})
    de=info.get("debtToEquity")
    if de is not None:
        if de<30:  fs+=1; fi.append({"ic":"🟢","txt":f"Долг/Капитал {de:.0f}% — финансово устойчива.","d":+1})
        elif de<100:fi.append({"ic":"⚪","txt":f"Долг/Капитал {de:.0f}% — умеренная задолженность.","d":0})
        elif de<200:fs-=1; fi.append({"ic":"🟡","txt":f"Долг/Капитал {de:.0f}% — повышенный долг.","d":-1})
        else:       fs-=2; fi.append({"ic":"🔴","txt":f"Долг/Капитал {de:.0f}% — высокий долг, риск дефолта.","d":-2})
    ebitda=info.get("ebitda"); tdebt=info.get("totalDebt")
    if ebitda and tdebt and ebitda>0:
        nd=tdebt/ebitda
        if nd<1.5: fs+=1; fi.append({"ic":"🟢","txt":f"Долг/EBITDA {nd:.1f}x — низкая нагрузка.","d":+1})
        elif nd<3: fi.append({"ic":"⚪","txt":f"Долг/EBITDA {nd:.1f}x — норма (<3x).","d":0})
        elif nd<5: fs-=1; fi.append({"ic":"🟡","txt":f"Долг/EBITDA {nd:.1f}x — повышенная нагрузка.","d":-1})
        else:      fs-=2; fi.append({"ic":"🔴","txt":f"Долг/EBITDA {nd:.1f}x — критически высокий долг.","d":-2})
    fcf=info.get("freeCashflow")
    if fcf is not None:
        if fcf>0: fs+=1; fi.append({"ic":"🟢","txt":f"FCF {fmt(fcf)} — положительный свободный денежный поток.","d":+1})
        else:     fs-=1; fi.append({"ic":"🔴","txt":f"FCF {fmt(fcf)} — отрицательный (сжигает деньги).","d":-1})
    if fi: blocks.append({"title":"🏛 Финансовое здоровье","items":fi,"score":fs}); total+=fs

    # Риск
    ri=[]; rs_=0
    if beta is not None:
        if beta<0.6:  rs_+=1; ri.append({"ic":"🟢","txt":f"Beta {beta:.2f} — очень стабильная, защитная акция.","d":+1})
        elif beta<1.0:rs_+=1; ri.append({"ic":"🟢","txt":f"Beta {beta:.2f} — менее волатильна, чем рынок.","d":+1})
        elif beta<1.4:ri.append({"ic":"⚪","txt":f"Beta {beta:.2f} — близко к рыночному риску.","d":0})
        elif beta<1.8:rs_-=1; ri.append({"ic":"🟡","txt":f"Beta {beta:.2f} — выше рыночного риска.","d":-1})
        else:         rs_-=2; ri.append({"ic":"🔴","txt":f"Beta {beta:.2f} — высокая волатильность.","d":-2})
        capm=rf+beta*(0.10-rf)
        ri.append({"ic":"📐","txt":f"CAPM: ожид. доходность {capm*100:.1f}% (Rf={rf*100:.1f}%, β={beta:.2f}, Rm=10%).","d":0})
    tgt=info.get("targetMeanPrice")
    if tgt and price:
        up=(tgt-price)/price*100
        ic="🟢" if up>15 else ("🔴" if up<-10 else "⚪")
        if up>25: rs_+=2; d_=+2
        elif up>10:rs_+=1;d_=+1
        elif up<-15:rs_-=2;d_=-2
        elif up<-5:rs_-=1;d_=-1
        else: d_=0
        ri.append({"ic":ic,"txt":f"Таргет аналитиков ${tgt:.1f} — апсайд {up:+.0f}%.","d":d_})
        rs_+=d_
    rk=info.get("recommendationKey","").lower()
    if rk in ("strong_buy","buy"):   rs_+=1; ri.append({"ic":"🟢","txt":f"Консенсус аналитиков: {rk.replace('_',' ').upper()}.","d":+1})
    elif rk in ("sell","strong_sell"):rs_-=1;ri.append({"ic":"🔴","txt":f"Консенсус аналитиков: {rk.replace('_',' ').upper()}.","d":-1})
    if low52 and high52 and price:
        pos=(price-low52)/(high52-low52) if high52>low52 else 0.5
        if pos<0.20:   rs_+=2; ri.append({"ic":"🟢","txt":f"Цена у 52-нед. минимума ({pos*100:.0f}% от дна) — возможная точка входа.","d":+2})
        elif pos<0.40: rs_+=1; ri.append({"ic":"🟢","txt":f"Цена в нижней части диапазона ({pos*100:.0f}% от дна).","d":+1})
        elif pos>0.92: rs_-=1; ri.append({"ic":"🟡","txt":f"Цена у 52-нед. максимума — ограниченный апсайд.","d":-1})
        else:          ri.append({"ic":"⚪","txt":f"Цена в середине 52-нед. диапазона ({pos*100:.0f}% от дна).","d":0})
    if is_ru:
        rs_-=1; ri.append({"ic":"⚠️","txt":"Страновой риск: санкции, ограничения для нерезидентов, геополитика.","d":-1})
    if ri: blocks.append({"title":"⚡ Риск и моментум","items":ri,"score":rs_}); total+=rs_

    # Новостной фон
    ns,nsigs=news_sentiment(news)
    if nsigs:
        nd=min(ns,2) if ns>0 else max(ns,-2)
        total+=nd
        blocks.append({"title":"📰 Новостной фон",
                        "items":[{"ic":ic,"txt":t,"d":1 if ic=="🟢" else -1} for ic,t in nsigs],
                        "score":ns})

    # Итог
    if total>=6:   lbl,col="ПОКУПАТЬ",GREEN; summ=f"Сильный фундаментал и позитивный фон. Убедительный кейс. Счёт: {total:+d}."
    elif total>=2: lbl,col="ПОКУПАТЬ",GREEN; summ=f"Большинство факторов позитивны. Рекомендован набор позиции. Счёт: {total:+d}."
    elif total>=-1:lbl,col="ДЕРЖАТЬ",YELLOW; summ=f"Смешанная картина. Держать, новым — дождаться лучшей точки. Счёт: {total:+d}."
    elif total>=-4:lbl,col="ПРОДАВАТЬ",RED;  summ=f"Перевес негативных факторов. Рассмотреть сокращение позиции. Счёт: {total:+d}."
    else:          lbl,col="ПРОДАВАТЬ",RED;  summ=f"Множество красных флагов. Высокий риск. Пересмотрите позицию. Счёт: {total:+d}."

    return {"label":lbl,"color":col,"score":total,"blocks":blocks,"summary":summ}

# ══════════════════════════════════════════════════════════════════════════════
# 8. ДАННЫЕ ДЛЯ СРАВНЕНИЯ US↔RU
# ══════════════════════════════════════════════════════════════════════════════
def _peer(ticker: str, is_ru: bool) -> dict:
    ck = f"peer_{ticker}"
    e  = _PEER_CACHE.get(ck)
    if e and time.time()-e[1]<600: return e[0]

    info: dict = {}
    name = (ALL_RU if is_ru else ALL_US).get(ticker, ticker)
    if is_ru:
        info = _yf_info(ticker+".ME", ttl=600)
        q    = moex.quote(ticker)
        price= q.get("LAST") or q.get("WAPRICE") or info.get("currentPrice")
        prev = q.get("PREVLEGALCLOSEPRICE") or q.get("PREVWAPRICE")
        mc_r = q.get("ISSUECAPITALIZATION")
        usd  = moex.usdrub() or 90.0
        mc   = (mc_r/usd) if mc_r else info.get("marketCap")
    else:
        info = _yf_info(ticker, ttl=600)
        price= info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose")
        mc   = info.get("marketCap")

    chg = ((price-prev)/prev*100) if price and prev and float(prev)>0 else None
    d = {"ticker":ticker,"name":name,"is_ru":is_ru,"price":price,"chg":chg,
         "pe":info.get("trailingPE"),"pb":info.get("priceToBook"),
         "ev":info.get("enterpriseToEbitda"),"roe":info.get("returnOnEquity"),
         "div":info.get("dividendYield"),"rev":info.get("revenueGrowth"),
         "de":info.get("debtToEquity"),"beta":info.get("beta"),"mc":mc}
    _PEER_CACHE[ck]=(d,time.time())
    return d

def gen_insights(label: str, us: list, ru: list) -> list[str]:
    ins = []
    us_pe=_med([d.get("pe") for d in us]); ru_pe=_med([d.get("pe") for d in ru])
    if us_pe and ru_pe and us_pe>0 and ru_pe>0:
        disc=(1-ru_pe/us_pe)*100
        if disc>20:
            ins.append(f"💡 Российские компании торгуются с **дисконтом {disc:.0f}%** к американским по P/E ({ru_pe:.1f}x vs {us_pe:.1f}x). "
                       f"Дисконт отражает страновой риск и санкции — но именно он создаёт потенциал при нормализации.")
        elif disc<-15:
            ins.append(f"⚡ Необычно: российские компании торгуются с **премией** к американским по P/E ({ru_pe:.1f}x vs {us_pe:.1f}x).")

    us_div=_med([d.get("div") for d in us]); ru_div=_med([d.get("div") for d in ru])
    if us_div and ru_div and us_div>0:
        r=ru_div/us_div
        if r>1.5:
            ins.append(f"💰 Дивидендная доходность РФ ({ru_div*100:.1f}%) в **{r:.1f}× выше** США ({us_div*100:.1f}%). "
                       f"Высокие выплаты — компенсация за риск и политика максимизации стоимости для акционеров.")

    us_roe=_med([d.get("roe") for d in us]); ru_roe=_med([d.get("roe") for d in ru])
    if us_roe and ru_roe:
        if ru_roe>us_roe*1.1:
            ins.append(f"📈 ROE российских компаний ({ru_roe*100:.1f}%) **выше** американских ({us_roe*100:.1f}%) — "
                       f"высокая отдача на капитал при низкой оценке: потенциально выгодный асимметричный кейс.")
        elif us_roe>ru_roe*1.1:
            ins.append(f"📊 ROE американских компаний ({us_roe*100:.1f}%) выше российских ({ru_roe*100:.1f}%) — "
                       f"более высокая операционная эффективность и развитый рынок капитала.")

    # Секторные инсайты
    if "Нефть" in label:
        ins += [
            "🛢️ Российские нефтяники работают под ценовым потолком ($60/барр. для Urals) и санкциями. "
            "Дисконт Urals к Brent (~$10–15/барр.) снижает прибыль vs ExxonMobil/Chevron, продающих по мировым ценам.",
            "🔄 Лукойл — один из лучших плательщиков дивидендов в секторе (>50% прибыли). "
            "Газпром в 2022–23 прекратил выплаты из-за мегапроектов — доверие восстанавливается медленно.",
            "🌍 ExxonMobil/Chevron имеют глобальную диверсификацию и доступ к дешёвым западным кредитам. "
            "Российские компании переориентировались на Азию с более сложной логистикой и скидками.",
        ]
    elif "Банки" in label:
        ins += [
            "🏦 Сбербанк — ~40% рынка РФ, аналог JPMorgan. Торгуется по P/B ~1×, JPM ~2×. "
            "При нормализации геополитики и снятии санкций потенциал переоценки огромен.",
            "💳 Т-Банк (Тинькофф) — лидер цифрового банкинга РФ, ROE стабильно >30%. "
            "Visa/Mastercard выигрывают от глобальных сетевых эффектов — в РФ их место заняла СБП и Мир.",
            "📉 Ключевая ставка ЦБ РФ 21% давит на качество кредитного портфеля. "
            "США: Fed снижает ставки — это улучшает NIM для американских банков. Разная стадия цикла.",
        ]
    elif "Технолог" in label:
        ins += [
            "🤖 US tech лидирует в AI-гонке: NVDA ($2T+ капа) больше всего российского рынка вместе взятого (~$600B). "
            "Это наглядно показывает масштабный разрыв в оценке технологических активов.",
            "🔄 Яндекс прошёл реструктуризацию 2023–24: международные активы отделены. "
            "Российская часть (поиск, маркетплейс, такси) — чистый local-play с сильными позициями.",
        ]
    elif "Ритейл" in label:
        ins += [
            "🛒 X5 и Магнит контролируют >25% рынка ритейла РФ — сопоставимо с Walmart в США. "
            "Инфляция 8-10% в РФ одновременно угрожает марже и раздувает выручку в номинале.",
        ]
    elif "Металл" in label:
        ins += [
            "⚙️ Норникель — мировой лидер по палладию и никелю. Незаменимое сырьё для EV и электроники. "
            "Торгуется с дисконтом к западным аналогам несмотря на сравнимые операционные показатели.",
            "🥇 Полюс — крупнейший золотодобытчик РФ и один из крупнейших в мире по запасам. "
            "Санкционный дисконт здесь особенно велик относительно Barrick/Newmont.",
        ]
    return ins

# ══════════════════════════════════════════════════════════════════════════════
# 9. UI-ХЕЛПЕРЫ
# ══════════════════════════════════════════════════════════════════════════════
def _tag(txt, col=ACCENT, bg=None):
    return html.Span(txt, style={"fontSize":"10px","fontWeight":"700","letterSpacing":"0.05em",
                                  "color":col,"backgroundColor":bg or f"{col}18",
                                  "padding":"2px 6px","borderRadius":"3px",
                                  "border":f"1px solid {col}33"})

def _sec_hdr(txt):
    return html.Div(txt, style={"fontSize":"10px","fontWeight":"700","color":TEXT3,
                                 "letterSpacing":"0.08em","textTransform":"uppercase",
                                 "padding":"9px 8px 3px","fontFamily":MONO})

def _ticker_btn(sym: str, name: str, is_ru: bool = False):
    col = "#ff6b35" if is_ru else ACCENT
    return html.Div(
        id={"type":"ticker-btn","index":sym}, n_clicks=0,
        children=[
            html.Span(sym, style={"fontWeight":"700","color":col,"fontSize":"12px",
                                   "fontFamily":MONO,"flexShrink":"0"}),
            html.Span(f" {name}", style={"fontSize":"11px","color":TEXT2,"overflow":"hidden",
                                          "textOverflow":"ellipsis","whiteSpace":"nowrap"}),
        ],
        style={"padding":"5px 8px","marginBottom":"2px","borderRadius":"4px","cursor":"pointer",
               "border":"1px solid transparent","display":"flex","alignItems":"center","gap":"0"},
    )

def _build_sidebar_list(custom: dict) -> list:
    ch = []
    ch.append(html.Div("🇺🇸  NYSE / NASDAQ", style={"padding":"6px 8px 2px","fontSize":"10px",
                        "fontWeight":"700","color":ACCENT,"letterSpacing":"0.1em","fontFamily":MONO,
                        "borderBottom":f"1px solid {BORDER}","marginBottom":"2px"}))
    for sec,stk in US_SECTORS.items():
        ch.append(_sec_hdr(sec))
        for sym,nm in stk.items(): ch.append(_ticker_btn(sym,nm,False))

    ch.append(html.Div("🇷🇺  МОСКОВСКАЯ БИРЖА", style={"padding":"8px 8px 2px","fontSize":"10px",
                        "fontWeight":"700","color":"#ff6b35","letterSpacing":"0.1em","fontFamily":MONO,
                        "borderTop":f"1px solid {BORDER}","marginTop":"6px",
                        "borderBottom":f"1px solid {BORDER}","marginBottom":"2px"}))
    for sec,stk in RU_SECTORS.items():
        ch.append(_sec_hdr(sec))
        for sym,nm in stk.items(): ch.append(_ticker_btn(sym,nm,True))

    if custom:
        ch.append(html.Div("🔍  ПОИСК", style={"padding":"8px 8px 2px","fontSize":"10px",
                            "fontWeight":"700","color":YELLOW,"letterSpacing":"0.1em","fontFamily":MONO,
                            "borderTop":f"1px solid {BORDER}","marginTop":"6px"}))
        for sym,nm in custom.items():
            ch.append(_ticker_btn(sym, nm, sym in ALL_RU))
    return ch

def _block_card(block: dict):
    sc=block["score"]; sc_col=GREEN if sc>0 else (RED if sc<0 else TEXT2)
    rows=[]
    for it in block["items"]:
        d=it.get("d",0); dc=GREEN if d>0 else (RED if d<0 else TEXT3)
        rows.append(html.Div(style={"display":"flex","gap":"7px","marginBottom":"4px","alignItems":"flex-start"},children=[
            html.Span(it["ic"],style={"fontSize":"13px","flexShrink":"0","marginTop":"1px"}),
            html.Span(it["txt"],style={"fontSize":"11.5px","color":TEXT,"flex":"1","lineHeight":"1.5"}),
            html.Span(f"{d:+d}" if d!=0 else "",style={"color":dc,"fontWeight":"700","fontSize":"11px",
                                                         "minWidth":"18px","textAlign":"right","fontFamily":MONO}),
        ]))
    return html.Div(style={"backgroundColor":PANEL2,"borderRadius":"6px","padding":"9px 11px",
                            "marginBottom":"8px","border":f"1px solid {BORDER}"},children=[
        html.Div(style={"display":"flex","justifyContent":"space-between","marginBottom":"6px"},children=[
            html.Span(block["title"],style={"fontWeight":"700","fontSize":"12px","color":TEXT}),
            html.Span(f"{sc:+d}",style={"color":sc_col,"fontWeight":"700","fontSize":"12px","fontFamily":MONO}),
        ]),
        *rows,
    ])

# ══════════════════════════════════════════════════════════════════════════════
# 10. ПОСТРОЕНИЕ ГРАФИКА
# ══════════════════════════════════════════════════════════════════════════════
def _build_chart(ticker, is_ru, df_price, info, currency):
    """Свечи + MA + Боллинджер + RSI + MACD."""
    row_h = [0.52, 0.16, 0.16, 0.16]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                        row_heights=row_h, vertical_spacing=0.01,
                        subplot_titles=("", "Объём", "RSI (14)", "MACD"))

    if df_price is None or df_price.empty:
        fig.update_layout(template="plotly_dark",paper_bgcolor=BG,plot_bgcolor=BG,
                          margin={"l":55,"r":10,"t":10,"b":10})
        return fig

    # Унифицируем колонки
    if is_ru:
        x  = df_price["TRADEDATE"]
        op = df_price.get("OPEN",   df_price.get("WAPRICE"))
        hi = df_price.get("HIGH",   df_price.get("WAPRICE"))
        lo = df_price.get("LOW",    df_price.get("WAPRICE"))
        cl = df_price.get("CLOSE",  df_price.get("LEGALCLOSEPRICE", df_price.get("WAPRICE")))
        vo = df_price.get("VOLUME", pd.Series(dtype=float))
    else:
        x  = df_price.index
        op,hi,lo,cl = df_price["Open"],df_price["High"],df_price["Low"],df_price["Close"]
        vo = df_price["Volume"]

    cl_s  = pd.Series(cl.values if hasattr(cl,"values") else list(cl), dtype=float)
    op_s  = pd.Series(op.values if hasattr(op,"values") else list(op), dtype=float)
    x_l   = list(x)

    # Свечи
    fig.add_trace(go.Candlestick(x=x_l,open=op_s,high=list(hi),low=list(lo),close=cl_s,
                                  name="Цена",increasing_line_color=GREEN,decreasing_line_color=RED,
                                  increasing_fillcolor=GREEN,decreasing_fillcolor=RED,
                                  showlegend=False), row=1,col=1)

    # Боллинджер
    if len(cl_s)>=20:
        bb_up,bb_mid,bb_lo=_bollinger(cl_s)
        for y,n,c in [(list(bb_up),"BB+",BORDER2),(list(bb_mid),"MA20",YELLOW),(list(bb_lo),"BB-",BORDER2)]:
            if n=="MA20":
                fig.add_trace(go.Scatter(x=x_l,y=y,name=n,line={"color":YELLOW,"width":1.4,"dash":"dot"},
                                          hovertemplate=f"{n}: %{{y:.2f}}<extra></extra>",showlegend=True),row=1,col=1)
            else:
                fig.add_trace(go.Scatter(x=x_l,y=y,name=n,line={"color":BORDER2,"width":0.8},
                                          fill=None if n=="BB+" else "tonexty",
                                          fillcolor="rgba(29,155,240,0.04)",showlegend=False),row=1,col=1)

    # MA50
    if len(cl_s)>=50:
        ma50=cl_s.rolling(50).mean()
        fig.add_trace(go.Scatter(x=x_l,y=list(ma50),name="MA50",
                                  line={"color":ORANGE,"width":1.3,"dash":"dot"},
                                  hovertemplate="MA50: %{y:.2f}<extra></extra>",showlegend=True),row=1,col=1)

    # Таргет аналитиков
    tgt=info.get("targetMeanPrice")
    if tgt and not is_ru:
        fig.add_hline(y=tgt,line_dash="dash",line_color=ACCENT,opacity=0.5,row=1,col=1,
                      annotation_text=f"  Target ${tgt:.0f}",annotation_font_color=ACCENT,
                      annotation_font_size=10)

    # Объём
    if vo is not None and len(vo)>0:
        vc=[GREEN if c>=o else RED for c,o in zip(list(cl_s),list(op_s))]
        fig.add_trace(go.Bar(x=x_l,y=list(vo),name="Объём",marker_color=vc,
                              opacity=0.6,showlegend=False),row=2,col=1)

    # RSI
    rsi=_rsi(cl_s)
    if not rsi.isna().all():
        fig.add_trace(go.Scatter(x=x_l,y=list(rsi),name="RSI",
                                  line={"color":PURPLE,"width":1.4},showlegend=False,
                                  hovertemplate="RSI: %{y:.1f}<extra></extra>"),row=3,col=1)
        fig.add_hline(y=70,line_dash="dot",line_color=RED,  opacity=0.5,row=3,col=1)
        fig.add_hline(y=30,line_dash="dot",line_color=GREEN,opacity=0.5,row=3,col=1)
        fig.add_hrect(y0=70,y1=100,fillcolor=RED,  opacity=0.04,row=3,col=1,line_width=0)
        fig.add_hrect(y0=0, y1=30, fillcolor=GREEN,opacity=0.04,row=3,col=1,line_width=0)

    # MACD
    macd,signal,hist=_macd(cl_s)
    if not macd.isna().all():
        fig.add_trace(go.Scatter(x=x_l,y=list(macd),  name="MACD",  line={"color":ACCENT,"width":1.3},showlegend=False),row=4,col=1)
        fig.add_trace(go.Scatter(x=x_l,y=list(signal),name="Signal",line={"color":ORANGE,"width":1.3},showlegend=False),row=4,col=1)
        hist_col=[GREEN if v>=0 else RED for v in hist.fillna(0)]
        fig.add_trace(go.Bar(x=x_l,y=list(hist),name="MACD Hist",
                              marker_color=hist_col,opacity=0.6,showlegend=False),row=4,col=1)

    pfx="₽" if currency=="RUB" else "$"
    axis_common={"gridcolor":BORDER,"tickfont":{"color":TEXT2,"family":MONO,"size":10},"zeroline":False}
    fig.update_layout(
        template="plotly_dark",paper_bgcolor=BG,plot_bgcolor=BG,
        margin={"l":55,"r":10,"t":18,"b":10},
        legend={"orientation":"h","y":1.04,"x":0,"font":{"color":TEXT2,"size":10},"bgcolor":"rgba(0,0,0,0)"},
        xaxis_rangeslider_visible=False,
        yaxis =dict(**axis_common, tickprefix=pfx),
        yaxis2=dict(**axis_common, tickformat=".2s"),
        yaxis3=dict(**axis_common, range=[0,100]),
        yaxis4=dict(**axis_common),
        xaxis4=dict(**axis_common),
        font={"color":TEXT,"family":SANS},
        hovermode="x unified",
    )
    for ax in ["xaxis","xaxis2","xaxis3","xaxis4"]:
        fig.update_layout(**{ax:dict(showgrid=True,gridcolor=BORDER,zeroline=False,
                                     tickfont={"color":TEXT2,"family":MONO,"size":10})})
    # Подписи subplot
    for i,lbl in enumerate(["","Объём","RSI","MACD"],1):
        if lbl:
            fig.update_layout(**{f"annotations":[
                *(fig.layout.annotations or []),
                {"text":lbl,"xref":"paper","yref":f"y{i} domain" if i>1 else "y domain",
                 "x":0,"y":1.0,"showarrow":False,"font":{"size":9,"color":TEXT3},
                 "xanchor":"left","yanchor":"top"}
            ]})

    return fig

# ══════════════════════════════════════════════════════════════════════════════
# 11. РЕНДЕР ВКЛАДОК
# ══════════════════════════════════════════════════════════════════════════════
def _tab_analysis(rec: dict):
    if not rec["blocks"]: return html.P("Нет данных.", style={"color":TEXT2})
    return html.Div([_block_card(b) for b in rec["blocks"]])

def _tab_metrics(info: dict, ticker: str, currency: str, is_ru: bool):
    beta=info.get("beta"); rf=get_rf()
    capm=f"{(rf+beta*(0.10-rf))*100:.2f}%" if beta else "N/A"
    wd=calc_wacc(info,rf)
    wstr=f"{wd['wacc']*100:.2f}%" if wd else "N/A"
    td=info.get("totalDebt"); eb=info.get("ebitda")
    de_str=f"{td/eb:.2f}x" if td and eb and eb>0 else "N/A"; de_raw=td/eb if td and eb and eb>0 else None
    pfx="₽" if currency=="RUB" else "$"
    p=info.get("currentPrice") or info.get("regularMarketPrice")
    tg=info.get("targetMeanPrice"); up=((tg-p)/p*100) if tg and p else None

    def row(lbl,val,raw=None,ga=None,ba=None,gl=None,bl=None):
        c=clr(raw,ga,ba,gl,bl) if raw is not None else TEXT
        return html.Tr([
            html.Td(lbl,style={"color":TEXT2,"padding":"4px 0","borderBottom":f"1px solid {BORDER}",
                                "width":"56%","fontSize":"12px"}),
            html.Td(val,style={"color":c, "padding":"4px 0","borderBottom":f"1px solid {BORDER}",
                                "fontWeight":"600","textAlign":"right","fontSize":"12px","fontFamily":MONO}),
        ])

    groups=[
        ("💰 Оценка",[
            row("Текущая цена",f"{pfx}{float(p):.2f}" if p else "N/A"),
            row("Таргет аналитиков",f"${tg:.1f}" if tg else "N/A",raw=up,ga=15,bl=-10),
            row("Апсайд до таргета",f"{up:.1f}%" if up else "N/A",raw=up,ga=15,bl=-5),
            row("P/E (trailing)",fmt(info.get("trailingPE")),raw=info.get("trailingPE"),gl=15,ba=40),
            row("P/E (forward)", fmt(info.get("forwardPE")), raw=info.get("forwardPE"), gl=15,ba=40),
            row("P/B",           fmt(info.get("priceToBook")),raw=info.get("priceToBook"),gl=2,ba=10),
            row("EV/EBITDA",     fmt(info.get("enterpriseToEbitda")),raw=info.get("enterpriseToEbitda"),gl=8,ba=25),
            row("Рын. капитализация",fmt(info.get("marketCap"))),
        ]),
        ("📈 Рост и маржа",[
            row("Рост выручки (YoY)", fmt(info.get("revenueGrowth"),pct=True),raw=info.get("revenueGrowth"),ga=0.10,bl=0),
            row("Рост прибыли (YoY)",fmt(info.get("earningsGrowth"),pct=True),raw=info.get("earningsGrowth"),ga=0.10,bl=0),
            row("Валовая маржа",  fmt(info.get("grossMargins"),pct=True), raw=info.get("grossMargins"),ga=0.50,bl=0.15),
            row("Операц. маржа",  fmt(info.get("operatingMargins"),pct=True),raw=info.get("operatingMargins"),ga=0.20,bl=0),
            row("Чистая маржа",   fmt(info.get("profitMargins"),pct=True), raw=info.get("profitMargins"),ga=0.15,bl=0),
        ]),
        ("🏛 Финансовое здоровье",[
            row("ROE",          fmt(info.get("returnOnEquity"),pct=True),raw=info.get("returnOnEquity"),ga=0.20,bl=0),
            row("ROA",          fmt(info.get("returnOnAssets"),pct=True),raw=info.get("returnOnAssets"),ga=0.08,bl=0),
            row("Долг/Капитал", fmt(info.get("debtToEquity"),suffix="%"),raw=info.get("debtToEquity"),gl=30,ba=200),
            row("Долг/EBITDA",  de_str,raw=de_raw,gl=1.5,ba=5.0),
            row("Current Ratio",fmt(info.get("currentRatio")),raw=info.get("currentRatio"),ga=1.5,bl=1.0),
            row("Free Cash Flow",fmt(info.get("freeCashflow")),raw=info.get("freeCashflow"),ga=0,bl=0),
            row("EBITDA",       fmt(info.get("ebitda"))),
            row("Дивид. доходность",fmt(info.get("dividendYield"),pct=True)),
        ]),
        ("🔑 CAPM & WACC",[
            row("Beta (52 нед.)",     f"{beta:.2f}" if beta else "N/A",raw=beta,gl=0.8,ba=1.8),
            row("CAPM (ожид. доходн.)",capm),
            row("WACC",               wstr),
            row("  Re (стоим. капит.)",f"{wd['re']*100:.2f}%" if wd else "N/A"),
            row("  Rd (стоим. долга)",f"{wd['rd']*100:.2f}%" if wd and wd.get("rd") else "—"),
            row("  E/V (вес капитала)",f"{wd['ew']*100:.1f}%" if wd else "N/A"),
            row("  D/V (вес долга)",  f"{wd['dw']*100:.1f}%" if wd else "N/A"),
        ]),
        ("⚡ Риск",[
            row("52 нед. макс.",  fmt(info.get("fiftyTwoWeekHigh"))),
            row("52 нед. мин.",   fmt(info.get("fiftyTwoWeekLow"))),
            row("Short % Float",  fmt(info.get("shortPercentOfFloat"),pct=True),
                raw=info.get("shortPercentOfFloat"),ba=0.15),
            row("Num Analysts",   str(info.get("numberOfAnalystOpinions") or "N/A")),
        ]),
    ]

    ch=[]
    for title,rows in groups:
        ch.append(html.Div([
            html.Div(title,style={"fontWeight":"700","color":ACCENT,"fontSize":"11px","marginBottom":"3px","marginTop":"10px"}),
            html.Table(style={"width":"100%","borderCollapse":"collapse"},children=[html.Tbody(rows)]),
        ]))
    ch.append(html.P(f"CAPM = Rf {rf*100:.2f}% + β·(Rm 10%−Rf)  |  WACC = (E/V)·Re + (D/V)·Rd·(1−T)",
                      style={"fontSize":"10px","color":TEXT3,"marginTop":"10px","fontFamily":MONO}))
    return html.Div(ch)

def _tab_news(news: list):
    if not news: return html.P("Нет новостей",style={"color":TEXT2})
    items=[]
    for n in news[:12]:
        ct=n.get("content",{}) if isinstance(n,dict) else {}
        title=ct.get("title") or n.get("title","Без заголовка")
        url=((ct.get("canonicalUrl") or {}).get("url") or
             (ct.get("clickThroughUrl") or {}).get("url") or n.get("link","#"))
        pub=n.get("providerPublishTime") or ct.get("pubDate","")
        if isinstance(pub,(int,float)): pub=datetime.fromtimestamp(pub).strftime("%d %b %Y %H:%M")
        elif isinstance(pub,str) and pub: pub=pub[:16]
        else: pub=""
        src=(ct.get("provider") or {}).get("displayName") or n.get("publisher","")
        tl=title.lower()
        has_p=any(k in tl for k in POS_KW); has_n=any(k in tl for k in NEG_KW)
        dot_col=GREEN if (has_p and not has_n) else (RED if (has_n and not has_p) else TEXT3)
        items.append(html.Div(style={"marginBottom":"10px","paddingBottom":"10px","borderBottom":f"1px solid {BORDER}"},children=[
            html.Div(style={"display":"flex","gap":"7px","alignItems":"flex-start"},children=[
                html.Span("●",style={"color":dot_col,"fontSize":"12px","flexShrink":"0","marginTop":"2px"}),
                html.A(title,href=url,target="_blank",style={"color":ACCENT,"textDecoration":"none",
                       "fontSize":"12px","fontWeight":"600","lineHeight":"1.45","display":"block"}),
            ]),
            html.Span(f"{src}  ·  {pub}",style={"color":TEXT3,"fontSize":"10px","marginLeft":"19px","fontFamily":MONO}),
        ]))
    return html.Div(items)

def _tab_beginner(rec: dict, info: dict, close_series: pd.Series | None, ticker: str, is_ru: bool):
    """Вкладка 'Для новичка' — упрощённый разбор для начинающих."""

    # ── Рейтинг риска (1-5) ───────────────────────────────────────────────────
    score = rec["score"]
    beta  = info.get("beta") or 1.0
    de    = info.get("debtToEquity") or 0

    risk_pts = 0
    if beta > 1.5: risk_pts += 2
    elif beta > 1.0: risk_pts += 1
    if de > 150: risk_pts += 2
    elif de > 80: risk_pts += 1
    if is_ru: risk_pts += 2
    if info.get("earningsGrowth") is not None and info["earningsGrowth"] < -0.1: risk_pts += 1

    risk_level = min(max(risk_pts, 1), 5)
    risk_colors = {1:GREEN, 2:"#7ecf2f", 3:YELLOW, 4:ORANGE, 5:RED}
    risk_labels = {1:"Низкий","2":"Умеренно-низкий",3:"Умеренный",4:"Повышенный",5:"Высокий"}
    risk_descs  = {
        1: "Стабильная, защитная акция. Подходит для консервативного портфеля.",
        2: "Небольшой риск, подходит для начинающих.",
        3: "Средний риск. Требует понимания компании и диверсификации.",
        4: "Повышенный риск. Для инвесторов с опытом и готовностью к потерям.",
        5: "Высокий риск. Для опытных трейдеров с чётким планом управления позицией.",
    }

    # ── Технические сигналы ────────────────────────────────────────────────────
    tech_sigs = []
    if close_series is not None and len(close_series) >= 20:
        tech_sigs = _tech_signals(close_series)

    rsi_now = None
    if close_series is not None and len(close_series) >= 14:
        r = _rsi(close_series)
        if not r.isna().all():
            rsi_now = r.iloc[-1]

    # ── Стоп-лосс рекомендация ────────────────────────────────────────────────
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    stop_loss_pct = 0.08 if risk_level <= 2 else (0.12 if risk_level == 3 else 0.15)
    stop_loss_str = "N/A"
    if price:
        sl = float(price) * (1 - stop_loss_pct)
        pfx = "₽" if is_ru else "$"
        stop_loss_str = f"{pfx}{sl:.2f} (−{stop_loss_pct*100:.0f}% от текущей цены)"

    # ── Топ-3 причины решения ─────────────────────────────────────────────────
    all_items = [it for b in rec["blocks"] for it in b["items"]]
    pos_reasons = sorted([i for i in all_items if i.get("d",0)>0], key=lambda x:-x["d"])[:3]
    neg_reasons = sorted([i for i in all_items if i.get("d",0)<0], key=lambda x: x["d"])[:3]

    def _reason_row(items, is_positive):
        if not items:
            return html.P("—", style={"color":TEXT2,"fontSize":"12px"})
        return html.Div([
            html.Div(style={"display":"flex","gap":"6px","marginBottom":"4px","alignItems":"flex-start"},children=[
                html.Span(it["ic"],style={"fontSize":"12px","flexShrink":"0"}),
                html.Span(it["txt"],style={"fontSize":"12px","color":TEXT,"lineHeight":"1.45"}),
            ]) for it in items
        ])

    # ── Период удержания ──────────────────────────────────────────────────────
    rev_gr = info.get("revenueGrowth") or 0
    if score >= 4 and rev_gr > 0.10:
        horizon = ("📅 Долгосрочный (6–18 месяцев)", GREEN,
                   "Сильный фундаментал + рост — лучше держать долго и не паниковать на коррекциях.")
    elif score >= 0:
        horizon = ("📅 Среднесрочный (3–6 месяцев)", YELLOW,
                   "Умеренный потенциал. Следите за квартальной отчётностью и пересматривайте позицию.")
    else:
        horizon = ("📅 Краткосрочный / выход", RED,
                   "Фундаментал слабый. Если держите — поставьте стоп-лосс и контролируйте риск.")

    # ── Глоссарий ─────────────────────────────────────────────────────────────
    glossary_items = []
    for term, (title, desc) in list(GLOSSARY.items())[:5]:
        glossary_items.append(html.Details(style={"marginBottom":"6px"},children=[
            html.Summary(title, style={"cursor":"pointer","color":ACCENT,"fontSize":"12px",
                                        "fontWeight":"600","padding":"4px 0","listStyle":"none"}),
            html.Div(desc, style={"color":TEXT2,"fontSize":"11.5px","lineHeight":"1.6",
                                   "padding":"4px 0 4px 12px","whiteSpace":"pre-line"}),
        ]))

    rclr = risk_colors.get(risk_level, YELLOW)
    stars = "★"*risk_level + "☆"*(5-risk_level)

    return html.Div([

        # Рейтинг риска
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"12px 14px",
                        "marginBottom":"10px","border":f"1px solid {rclr}33"},children=[
            html.Div(style={"display":"flex","alignItems":"center","gap":"10px","marginBottom":"4px"},children=[
                html.Span("⚠️ Уровень риска:", style={"color":TEXT2,"fontSize":"12px"}),
                html.Span(stars, style={"color":rclr,"fontSize":"16px","letterSpacing":"2px"}),
                html.Span(risk_labels.get(risk_level,"—"), style={"color":rclr,"fontWeight":"700","fontSize":"13px"}),
            ]),
            html.P(risk_descs.get(risk_level,""), style={"color":TEXT2,"fontSize":"12px","margin":"0","lineHeight":"1.5"}),
        ]),

        # Горизонт инвестирования
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"10px 14px",
                        "marginBottom":"10px","border":f"1px solid {BORDER}"},children=[
            html.Div(style={"display":"flex","gap":"8px","alignItems":"center","marginBottom":"4px"},children=[
                html.Span(horizon[0], style={"color":horizon[1],"fontWeight":"700","fontSize":"12px"}),
            ]),
            html.P(horizon[2], style={"color":TEXT2,"fontSize":"12px","margin":"0","lineHeight":"1.5"}),
        ]),

        # Стоп-лосс
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"10px 14px",
                        "marginBottom":"10px","border":f"1px solid {BORDER}"},children=[
            html.Div("🛑 Рекомендуемый стоп-лосс",
                     style={"color":RED,"fontWeight":"700","fontSize":"12px","marginBottom":"4px"}),
            html.P(stop_loss_str, style={"color":TEXT,"fontSize":"13px","fontFamily":MONO,"margin":"0"}),
            html.P("Стоп-лосс — цена, при достижении которой стоит зафиксировать убыток, "
                   "чтобы не потерять ещё больше. Дисциплина важнее прогнозов.",
                   style={"color":TEXT2,"fontSize":"11px","margin":"4px 0 0","lineHeight":"1.5"}),
        ]),

        # Технические сигналы
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"10px 14px",
                        "marginBottom":"10px","border":f"1px solid {BORDER}"},children=[
            html.Div("📡 Технические сигналы",
                     style={"color":TEXT,"fontWeight":"700","fontSize":"12px","marginBottom":"6px"}),
            html.Div([
                html.Div(style={"display":"flex","gap":"8px","alignItems":"flex-start","marginBottom":"5px"},children=[
                    html.Span(s["icon"],style={"fontSize":"14px","flexShrink":"0"}),
                    html.Div([
                        html.Span(s["label"],style={"color":TEXT,"fontSize":"12px","fontWeight":"600"}),
                        html.P(s["detail"],style={"color":TEXT2,"fontSize":"11px","margin":"1px 0 0","lineHeight":"1.4"}),
                    ]),
                ]) for s in tech_sigs
            ]) if tech_sigs else html.P("Недостаточно данных для технического анализа.",
                                         style={"color":TEXT2,"fontSize":"12px"}),
            html.P(f"RSI текущий: {rsi_now:.1f}" if rsi_now else "",
                   style={"color":PURPLE,"fontSize":"11px","fontFamily":MONO,"marginTop":"4px"}),
        ]),

        # Причины BUY/SELL
        html.Div(style={"display":"flex","gap":"8px","marginBottom":"10px"},children=[
            html.Div(style={"flex":"1","backgroundColor":f"{GREEN}0d","borderRadius":"8px",
                            "padding":"10px 12px","border":f"1px solid {GREEN}30"},children=[
                html.Div("✅ За покупку",style={"color":GREEN,"fontWeight":"700","fontSize":"12px","marginBottom":"6px"}),
                _reason_row(pos_reasons, True),
            ]),
            html.Div(style={"flex":"1","backgroundColor":f"{RED}0d","borderRadius":"8px",
                            "padding":"10px 12px","border":f"1px solid {RED}30"},children=[
                html.Div("❌ Против покупки",style={"color":RED,"fontWeight":"700","fontSize":"12px","marginBottom":"6px"}),
                _reason_row(neg_reasons, False),
            ]),
        ]),

        # Правило 3 вопросов
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"10px 14px",
                        "marginBottom":"10px","border":f"1px solid {ACCENT}33"},children=[
            html.Div("❓ 3 вопроса перед покупкой",
                     style={"color":ACCENT,"fontWeight":"700","fontSize":"12px","marginBottom":"6px"}),
            *[html.P(q, style={"color":TEXT2,"fontSize":"11.5px","margin":"0 0 5px","lineHeight":"1.5"}) for q in [
                "1. Понимаю ли я, на чём компания зарабатывает деньги?",
                "2. Могу ли я потерять эту сумму без критических последствий?",
                "3. Есть ли у меня план выхода (таргет и стоп-лосс)?",
            ]],
        ]),

        # Глоссарий
        html.Div(style={"backgroundColor":PANEL2,"borderRadius":"8px","padding":"10px 14px",
                        "border":f"1px solid {BORDER}"},children=[
            html.Div("📚 Глоссарий терминов",
                     style={"color":TEXT,"fontWeight":"700","fontSize":"12px","marginBottom":"8px"}),
            *glossary_items,
        ]),

    ])

def _tab_comparison(ticker: str, is_ru: bool):
    sector_lbl = COMP_LABELS[0]
    for s in COMPARISON_SECTORS:
        if ticker in s["us"] or ticker in s["ru"]:
            sector_lbl = s["label"]; break

    return html.Div([
        html.Div(style={"marginBottom":"10px","display":"flex","alignItems":"center","gap":"8px"},children=[
            html.Span("Сектор:", style={"color":TEXT2,"fontSize":"12px","flexShrink":"0"}),
            dcc.Dropdown(id="comp-dd",
                options=[{"label":s["label"],"value":s["label"]} for s in COMPARISON_SECTORS],
                value=sector_lbl, clearable=False,
                style={"flex":"1","fontSize":"12px","backgroundColor":PANEL2},
            ),
        ]),
        html.Div(id="comp-content",
                 children=html.Span("Загрузка…",style={"color":TEXT2,"fontSize":"12px"})),
    ])

# ══════════════════════════════════════════════════════════════════════════════
# 12. DASH APP + LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, title="Bloomberg Terminal",
                meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])
app.config.suppress_callback_exceptions = True

app.layout = html.Div(
    style={"display":"flex","flexDirection":"column","height":"100vh",
           "backgroundColor":BG,"fontFamily":SANS,"color":TEXT,"overflow":"hidden"},
    children=[

        # ── РЫНОЧНАЯ ПОЛОСА ───────────────────────────────────────────────────
        html.Div(id="market-strip",
                 style={"height":"34px","backgroundColor":"#040b10",
                        "borderBottom":f"1px solid {BORDER}",
                        "display":"flex","alignItems":"center","padding":"0 10px",
                        "overflowX":"auto","flexShrink":"0","fontFamily":MONO,
                        "scrollbarWidth":"none"},
                 children=[html.Span("Загрузка рынков…",style={"color":TEXT3,"fontSize":"11px"})]),

        # ── ОСНОВНОЙ КОНТЕНТ ──────────────────────────────────────────────────
        html.Div(style={"flex":"1","display":"flex","overflow":"hidden"},children=[

            # САЙДБАР
            html.Div(
                style={"width":"190px","minWidth":"190px","backgroundColor":PANEL,
                       "borderRight":f"1px solid {BORDER}","display":"flex",
                       "flexDirection":"column","overflow":"hidden"},
                children=[
                    html.Div(
                        style={"padding":"9px 12px","borderBottom":f"1px solid {BORDER}",
                               "display":"flex","alignItems":"center","gap":"8px"},
                        children=[
                            html.Span("▣",style={"color":ACCENT,"fontSize":"18px"}),
                            html.Div([
                                html.Div("TERMINAL",style={"fontSize":"11px","fontWeight":"900",
                                                            "color":ACCENT,"letterSpacing":"0.15em","fontFamily":MONO}),
                                html.Div("NYSE · MOEX · ISS",style={"fontSize":"9px","color":TEXT3,"fontFamily":MONO}),
                            ]),
                        ],
                    ),
                    # Поиск
                    html.Div(style={"padding":"7px 8px 5px","borderBottom":f"1px solid {BORDER}"},children=[
                        html.Div(style={"display":"flex","gap":"4px"},children=[
                            dcc.Input(id="ticker-search",type="text",placeholder="Тикер…",
                                      debounce=False,maxLength=12,
                                      style={"flex":"1","backgroundColor":PANEL2,"color":TEXT,
                                             "border":f"1px solid {BORDER2}","borderRadius":"4px",
                                             "padding":"5px 7px","fontSize":"12px","outline":"none",
                                             "fontFamily":MONO}),
                            html.Button("GO",id="ticker-search-btn",n_clicks=0,
                                        style={"backgroundColor":ACCENT,"color":"#fff","border":"none",
                                               "borderRadius":"4px","padding":"5px 8px","cursor":"pointer",
                                               "fontWeight":"700","fontSize":"11px","fontFamily":MONO,"flexShrink":"0"}),
                        ]),
                        html.Div(id="search-error",style={"color":RED,"fontSize":"10px","marginTop":"3px","fontFamily":MONO}),
                    ]),
                    # Список
                    html.Div(id="sidebar-list",style={"flex":"1","overflowY":"auto","padding":"0 4px 8px"},
                             children=_build_sidebar_list({})),
                    # Stores
                    dcc.Store(id="selected-ticker",data="JPM"),
                    dcc.Store(id="custom-tickers",data={}),
                ],
            ),

            # ГЛАВНАЯ ОБЛАСТЬ
            html.Div(style={"flex":"1","display":"flex","flexDirection":"column","overflow":"hidden"},children=[

                # Хедер
                html.Div(
                    style={"backgroundColor":PANEL,"borderBottom":f"1px solid {BORDER}",
                           "padding":"8px 16px","display":"flex","alignItems":"center",
                           "gap":"10px","flexWrap":"wrap","flexShrink":"0"},
                    children=[
                        html.Div(id="hdr-ticker",style={"fontSize":"20px","fontWeight":"900",
                                                          "color":ACCENT,"fontFamily":MONO}),
                        html.Div(id="hdr-name",  style={"fontSize":"13px","color":TEXT2}),
                        html.Div(id="hdr-price", style={"fontSize":"20px","fontWeight":"700",
                                                          "fontFamily":MONO,"marginLeft":"6px"}),
                        html.Div(id="hdr-change",style={"fontSize":"13px","fontFamily":MONO}),
                        html.Div(id="hdr-badges",style={"marginLeft":"auto","display":"flex",
                                                          "gap":"5px","alignItems":"center","flexWrap":"wrap"}),
                    ],
                ),

                # Тело
                html.Div(style={"flex":"1","display":"flex","overflow":"hidden"},children=[

                    # График
                    html.Div(style={"flex":"11","display":"flex","flexDirection":"column",
                                    "padding":"8px","overflow":"hidden"},children=[
                        dcc.Graph(id="price-chart",style={"flex":"1"},
                                  config={"displayModeBar":True,"scrollZoom":True,
                                          "modeBarButtonsToRemove":["lasso2d","select2d"]}),
                    ]),

                    # Правая панель
                    html.Div(style={"flex":"8","minWidth":"330px","borderLeft":f"1px solid {BORDER}",
                                    "display":"flex","flexDirection":"column","overflow":"hidden"},children=[
                        # Рекомендация
                        html.Div(id="rec-box",style={"padding":"8px 12px",
                                                       "borderBottom":f"1px solid {BORDER}","flexShrink":"0"}),
                        # Вкладки
                        dcc.Tabs(id="right-tabs",value="beginner",
                                 style={"borderBottom":f"1px solid {BORDER}","flexShrink":"0"},
                                 colors={"background":PANEL,"primary":ACCENT,"border":BORDER},
                                 children=[
                                     dcc.Tab(label="🎓 Новичку", value="beginner", style=TAB_S,selected_style=TAB_AS),
                                     dcc.Tab(label="Анализ",    value="analysis", style=TAB_S,selected_style=TAB_AS),
                                     dcc.Tab(label="Метрики",   value="metrics",  style=TAB_S,selected_style=TAB_AS),
                                     dcc.Tab(label="Новости",   value="news",     style=TAB_S,selected_style=TAB_AS),
                                     dcc.Tab(label="🇷🇺↔🇺🇸",   value="compare",  style=TAB_S,selected_style=TAB_AS),
                                 ]),
                        html.Div(id="tab-content",style={"flex":"1","overflowY":"auto","padding":"10px 12px"}),
                    ]),
                ]),
            ]),
        ]),

        dcc.Interval(id="mkt-interval",interval=300_000,n_intervals=0),
        dcc.Loading(type="dot",color=ACCENT,
                    style={"position":"fixed","bottom":"8px","right":"8px"},
                    children=html.Div(id="loading-trigger")),
    ],
)

# ══════════════════════════════════════════════════════════════════════════════
# 13. CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

# ── Рыночная полоса ───────────────────────────────────────────────────────────
@app.callback(Output("market-strip","children"), Input("mkt-interval","n_intervals"))
def update_strip(_):
    items=[]
    sep=html.Span("│",style={"color":BORDER2,"margin":"0 8px","fontSize":"14px"})
    for code,name in [("IMOEX","IMOEX"),("RTSI","RTS")]:
        try:
            q=moex.index_quote(code)
            val=q.get("CURRENTVALUE") or q.get("LAST") or q.get("MARKETPRICE")
            prev=q.get("LASTVALUE") or q.get("PREVVALUE") or q.get("PREVLEGALCLOSEPRICE")
            if val and prev and float(prev)>0:
                chg=(float(val)-float(prev))/float(prev)*100
                col=GREEN if chg>=0 else RED
                items.append(html.Span([
                    html.Span(name,style={"color":TEXT3,"fontSize":"10px","marginRight":"4px"}),
                    html.Span(f"{float(val):,.0f}",style={"color":TEXT,"fontSize":"11px","fontWeight":"600"}),
                    html.Span(f" {'▲' if chg>=0 else '▼'}{abs(chg):.1f}%",style={"color":col,"fontSize":"10px"}),
                ]))
                items.append(sep)
        except: pass
    try:
        r=moex.usdrub()
        if r:
            items.append(html.Span([
                html.Span("USD/RUB",style={"color":TEXT3,"fontSize":"10px","marginRight":"4px"}),
                html.Span(f"{r:.2f}",style={"color":YELLOW,"fontSize":"11px","fontWeight":"600"}),
            ]))
            items.append(sep)
    except: pass
    for name,sym in MARKET_STRIP_YF:
        try:
            h=yf.Ticker(sym).history(period="2d",interval="1d")
            if len(h)>=2:
                last=h["Close"].iloc[-1]; prev=h["Close"].iloc[-2]
                chg=(last-prev)/prev*100; col=GREEN if chg>=0 else RED
                ps=f"{last:,.0f}" if last>1000 else (f"{last:,.1f}" if last>10 else f"{last:.4f}")
                items.append(html.Span([
                    html.Span(name,style={"color":TEXT3,"fontSize":"10px","marginRight":"4px"}),
                    html.Span(ps,style={"color":TEXT,"fontSize":"11px","fontWeight":"600"}),
                    html.Span(f" {'▲' if chg>=0 else '▼'}{abs(chg):.1f}%",style={"color":col,"fontSize":"10px"}),
                ]))
                items.append(sep)
        except: pass
    return items or [html.Span("Нет данных",style={"color":TEXT3,"fontSize":"11px"})]

# ── Поиск тикера ─────────────────────────────────────────────────────────────
@app.callback(
    Output("selected-ticker","data",allow_duplicate=True),
    Output("custom-tickers","data"),
    Output("search-error","children"),
    Output("sidebar-list","children"),
    Input("ticker-search-btn","n_clicks"),
    Input("ticker-search","n_submit"),
    State("ticker-search","value"),
    State("custom-tickers","data"),
    prevent_initial_call=True,
)
def search_ticker(_,__,raw,custom):
    if not raw: return dash.no_update,dash.no_update,"",dash.no_update
    sym=raw.strip().upper(); custom=custom or {}
    info=_yf_info(sym,ttl=60)
    if not info.get("currentPrice") and not info.get("regularMarketPrice"):
        q=moex.quote(sym)
        if q.get("LAST") or q.get("WAPRICE"):
            custom[sym]=str(q.get("SHORTNAME") or sym)[:22]
            return sym,custom,"",_build_sidebar_list(custom)
        return dash.no_update,dash.no_update,f"✗ {sym} не найден",dash.no_update
    custom[sym]=(info.get("shortName") or sym)[:22]
    return sym,custom,"",_build_sidebar_list(custom)

# ── Выбор тикера ─────────────────────────────────────────────────────────────
@app.callback(
    Output("selected-ticker","data"),
    Input({"type":"ticker-btn","index":ALL},"n_clicks"),
    State("selected-ticker","data"),
    prevent_initial_call=True,
)
def select_ticker(_,cur):
    ctx=callback_context
    if not ctx.triggered: return cur
    try:    return json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]
    except: return cur

# ── Главный дашборд ───────────────────────────────────────────────────────────
@app.callback(
    Output("hdr-ticker","children"),
    Output("hdr-name","children"),
    Output("hdr-price","children"),
    Output("hdr-change","children"),
    Output("hdr-badges","children"),
    Output("price-chart","figure"),
    Output("rec-box","children"),
    Output("tab-content","children"),
    Output("right-tabs","value"),
    Output("loading-trigger","children"),
    Input("selected-ticker","data"),
    Input("right-tabs","value"),
    State("custom-tickers","data"),
)
def update_dashboard(ticker, tab, custom):
    custom = custom or {}
    is_ru  = ticker in ALL_RU or (ticker not in ALL_US and bool(moex.quote(ticker).get("LAST")))

    # Данные
    if is_ru:
        df_price = moex.history(ticker)
        info     = _yf_info(ticker+".ME", ttl=300)
        q        = moex.quote(ticker)
        price    = q.get("LAST") or q.get("WAPRICE") or info.get("currentPrice")
        prev     = q.get("PREVLEGALCLOSEPRICE") or q.get("PREVWAPRICE")
        currency = "RUB"
        name     = ALL_RU.get(ticker) or custom.get(ticker) or q.get("SHORTNAME") or info.get("shortName") or ticker
        try:    news = yf.Ticker(ticker+".ME").news or []
        except: news = []
    else:
        info     = _yf_info(ticker, ttl=300)
        df_price = _yf_hist(ticker)
        price    = info.get("currentPrice") or info.get("regularMarketPrice")
        prev     = info.get("previousClose")
        currency = "USD"
        name     = ALL_US.get(ticker) or custom.get(ticker) or info.get("shortName") or ticker
        try:    news = yf.Ticker(ticker).news or []
        except: news = []

    # Изменение
    if price and prev and float(prev)>0:
        chg=float(price)-float(prev); pct=chg/float(prev)*100
        chg_str=f"{'▲' if chg>=0 else '▼'} {abs(chg):.2f}  ({abs(pct):.2f}%)"
        chg_col=GREEN if chg>=0 else RED
    else: chg_str,chg_col="—",TEXT2

    pfx="₽" if currency=="RUB" else "$"
    price_str=f"{pfx}{float(price):.2f}" if price else "—"

    # Хедер
    sector=TICKER_SECTOR.get(ticker,info.get("sector",""))
    badges=[_tag("🇷🇺" if is_ru else "🇺🇸"),
            _tag(sector,TEXT2,PANEL2) if sector else None,
            _tag(currency,YELLOW if currency=="RUB" else ACCENT)]
    badges=[b for b in badges if b]

    # График
    if is_ru:
        close_s = pd.Series(list(df_price["CLOSE"]) if not df_price.empty and "CLOSE" in df_price.columns else [],dtype=float)
    else:
        close_s = pd.Series(list(df_price["Close"]) if not df_price.empty else [], dtype=float)

    fig = _build_chart(ticker, is_ru, df_price, info, currency)

    # Рекомендация
    rec=build_recommendation(info,news,ticker,is_ru)
    lbl,col,sc=rec["label"],rec["color"],rec["score"]
    bar_w=min(abs(sc)/14*100,100)
    rec_box=html.Div([
        html.Div(style={"display":"flex","alignItems":"center","gap":"10px"},children=[
            html.Span(lbl,style={"color":col,"fontWeight":"900","fontSize":"19px","fontFamily":MONO,
                                  "padding":"2px 10px","borderRadius":"4px",
                                  "border":f"2px solid {col}","backgroundColor":f"{col}15"}),
            html.Span(f"{sc:+d} pts",style={"color":TEXT2,"fontSize":"12px","fontFamily":MONO}),
            html.Span("⚠ СТРАНОВОЙ РИСК",style={"color":"#ff6b35","fontSize":"10px","fontWeight":"700",
                                                   "fontFamily":MONO,"padding":"1px 6px",
                                                   "border":"1px solid #ff6b35","borderRadius":"3px"}) if is_ru else None,
        ]),
        html.Div(style={"height":"3px","backgroundColor":BORDER,"borderRadius":"2px","marginTop":"6px"},
                 children=[html.Div(style={"height":"100%","width":f"{bar_w}%",
                                           "backgroundColor":col,"borderRadius":"2px"})]),
        html.P(rec["summary"],style={"color":TEXT2,"fontSize":"11px","margin":"5px 0 0","lineHeight":"1.55"}),
    ])

    # Вкладки
    if   tab=="beginner":  content=_tab_beginner(rec,info,close_s if len(close_s)>0 else None,ticker,is_ru)
    elif tab=="analysis":  content=_tab_analysis(rec)
    elif tab=="metrics":   content=_tab_metrics(info,ticker,currency,is_ru)
    elif tab=="news":      content=_tab_news(news)
    elif tab=="compare":   content=_tab_comparison(ticker,is_ru)
    else:                  content=html.Div()

    return (ticker, name, price_str,
            html.Span(chg_str,style={"color":chg_col}),
            badges, fig, rec_box, content, tab, "")

# ── Вкладка сравнения ────────────────────────────────────────────────────────
@app.callback(Output("comp-content","children"), Input("comp-dd","value"),
              prevent_initial_call=False)
def update_comparison(lbl):
    if not lbl: return html.P("Выберите сектор",style={"color":TEXT2})
    cfg=next((s for s in COMPARISON_SECTORS if s["label"]==lbl),None)
    if not cfg: return html.P("Нет данных",style={"color":TEXT2})

    us_d=[_peer(t,False) for t in cfg["us"]]
    ru_d=[_peer(t,True)  for t in cfg["ru"]]

    th={"color":TEXT3,"fontSize":"10px","fontWeight":"700","padding":"4px 4px","textAlign":"right",
        "fontFamily":MONO,"letterSpacing":"0.04em"}
    thl={**th,"textAlign":"left"}

    def _v(v,pct=False):
        if v is None or (isinstance(v,float) and pd.isna(v)):
            return html.Td("—",style={"color":TEXT3,"fontSize":"11px","padding":"4px 4px","textAlign":"right","fontFamily":MONO})
        s=f"{v*100:.1f}%" if pct else f"{v:.1f}x"
        return html.Td(s,style={"color":TEXT,"fontSize":"11px","padding":"4px 4px","textAlign":"right",
                                 "fontFamily":MONO,"fontWeight":"600"})

    def _row(d,is_r):
        fl="🇷🇺" if is_r else "🇺🇸"; col="#ff6b35" if is_r else ACCENT
        chg=d.get("chg"); cc=GREEN if chg and chg>=0 else RED
        cs=f"{'▲' if chg and chg>=0 else '▼'}{abs(chg):.1f}%" if chg else "—"
        return html.Tr(style={"backgroundColor":PANEL2 if is_r else PANEL},children=[
            html.Td(f"{fl} {d['ticker']}",style={"color":col,"fontWeight":"700","fontFamily":MONO,
                                                   "fontSize":"11px","padding":"4px 6px"}),
            html.Td(d["name"][:13],style={"color":TEXT2,"fontSize":"11px","padding":"4px 4px"}),
            _v(d.get("pe")), _v(d.get("pb")), _v(d.get("ev")), _v(d.get("roe"),True),
            _v(d.get("div"),True), _v(d.get("rev"),True),
            html.Td(cs,style={"color":cc,"fontSize":"11px","padding":"4px 6px","textAlign":"right","fontFamily":MONO}),
        ])

    def _grp(label, color):
        return html.Tr([html.Td(label,colSpan=9,style={"backgroundColor":"#0a1520","color":color,
                                                         "fontSize":"10px","fontWeight":"700",
                                                         "padding":"4px 6px","letterSpacing":"0.08em","fontFamily":MONO})])

    table=html.Table(style={"width":"100%","borderCollapse":"collapse","marginBottom":"12px"},children=[
        html.Thead(html.Tr([html.Th("Тикер",style=thl),html.Th("Название",style=thl),
                             html.Th("P/E",style=th),html.Th("P/B",style=th),html.Th("EV/EBI",style=th),
                             html.Th("ROE",style=th),html.Th("Дивид.",style=th),html.Th("Rev.Gr.",style=th),
                             html.Th("1d%",style=th)])),
        html.Tbody([_grp("🇺🇸 США",ACCENT),*[_row(d,False) for d in us_d],
                    _grp("🇷🇺 РОССИЯ","#ff6b35"),*[_row(d,True) for d in ru_d]]),
    ])

    # Bubble: P/E vs ROE
    bfig=go.Figure()
    for rows,col_b,fl,nm in [(us_d,ACCENT,"🇺🇸","США"),(ru_d,"#ff6b35","🇷🇺","РФ")]:
        xs=[d["pe"] for d in rows if d.get("pe") and d.get("roe")]
        ys=[d["roe"]*100 for d in rows if d.get("pe") and d.get("roe")]
        sz=[max((d.get("mc") or 1e10)**0.33/5e2,10) for d in rows if d.get("pe") and d.get("roe")]
        lb=[d["ticker"] for d in rows if d.get("pe") and d.get("roe")]
        if xs:
            bfig.add_trace(go.Scatter(x=xs,y=ys,mode="markers+text",text=lb,
                                       textposition="top center",textfont={"size":9,"color":TEXT2},
                                       marker={"size":sz,"color":col_b,"opacity":0.75},
                                       name=f"{fl} {nm}",
                                       hovertemplate=f"{fl} %{{text}}<br>P/E:%{{x:.1f}}x ROE:%{{y:.1f}}%<extra></extra>"))
    bfig.update_layout(template="plotly_dark",paper_bgcolor=PANEL2,plot_bgcolor=PANEL2,
                        margin={"l":40,"r":10,"t":28,"b":36},height=200,
                        xaxis={"title":"P/E","gridcolor":BORDER,"titlefont":{"size":10},
                               "tickfont":{"size":9,"family":MONO}},
                        yaxis={"title":"ROE %","gridcolor":BORDER,"titlefont":{"size":10},
                               "tickfont":{"size":9,"family":MONO}},
                        legend={"font":{"size":9},"bgcolor":"rgba(0,0,0,0)"},
                        title={"text":"P/E vs ROE  (размер = капитализация)","font":{"size":10,"color":TEXT2},"x":0.5})

    # Bar: дивиденды
    dfig=go.Figure()
    for rows,col_b,fl in [(us_d,ACCENT,"🇺🇸"),(ru_d,"#ff6b35","🇷🇺")]:
        tks=[f"{fl} {d['ticker']}" for d in rows if d.get("div")]
        dvs=[d["div"]*100 for d in rows if d.get("div")]
        if tks: dfig.add_trace(go.Bar(x=tks,y=dvs,marker_color=col_b,opacity=0.85,name=fl,
                                       hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
    dfig.update_layout(template="plotly_dark",paper_bgcolor=PANEL2,plot_bgcolor=PANEL2,
                        margin={"l":35,"r":10,"t":28,"b":36},height=170,barmode="group",
                        yaxis={"title":"Дивид. %","gridcolor":BORDER,"titlefont":{"size":10},
                               "tickfont":{"size":9,"family":MONO}},
                        xaxis={"tickfont":{"size":9,"family":MONO}},
                        legend={"font":{"size":9},"bgcolor":"rgba(0,0,0,0)"},
                        title={"text":"Дивидендная доходность, %","font":{"size":10,"color":TEXT2},"x":0.5})

    # Инсайты
    raw_ins=gen_insights(lbl,us_d,ru_d)
    ins_els=[]
    for ins in raw_ins:
        parts=re.split(r"\*\*(.+?)\*\*",ins)
        rnd=[html.Strong(p,style={"color":TEXT}) if i%2==1 else p for i,p in enumerate(parts)]
        ins_els.append(html.Div(rnd,style={"marginBottom":"9px","paddingBottom":"9px",
                                            "borderBottom":f"1px solid {BORDER}","fontSize":"12px",
                                            "color":TEXT2,"lineHeight":"1.6"}))

    return html.Div([
        table,
        html.Div(style={"display":"flex","gap":"10px","marginBottom":"10px"},children=[
            html.Div(dcc.Graph(figure=bfig,config={"displayModeBar":False}),style={"flex":"1"}),
            html.Div(dcc.Graph(figure=dfig,config={"displayModeBar":False}),style={"flex":"1"}),
        ]),
        html.Div([
            html.Div("💡 ИНСАЙТЫ И АНАЛИТИКА",style={"fontSize":"10px","fontWeight":"900","color":ACCENT,
                                                       "fontFamily":MONO,"letterSpacing":"0.1em",
                                                       "marginBottom":"8px","paddingBottom":"4px",
                                                       "borderBottom":f"1px solid {BORDER}"}),
            *ins_els,
        ]),
    ])

# ══════════════════════════════════════════════════════════════════════════════
# 14. ГЛОБАЛЬНЫЙ CSS
# ══════════════════════════════════════════════════════════════════════════════
app.index_string = f'''<!DOCTYPE html>
<html><head>{{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{BG};overflow:hidden}}
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-track{{background:{PANEL}}}
::-webkit-scrollbar-thumb{{background:{BORDER2};border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:{TEXT3}}}
#market-strip{{scrollbar-width:none}}
#market-strip::-webkit-scrollbar{{display:none}}
#sidebar-list>div>div:hover{{background-color:{PANEL2}!important;border-color:{BORDER2}!important}}
.tab--selected{{font-weight:700!important}}
.modebar{{background:transparent!important}}
.modebar-btn path{{fill:{TEXT3}!important}}
.modebar-btn:hover path{{fill:{ACCENT}!important}}
details summary::-webkit-details-marker{{display:none}}
details summary::marker{{display:none}}
.Select-control,.Select-menu-outer{{background-color:{PANEL2}!important;border-color:{BORDER}!important;color:{TEXT}!important}}
.Select-option{{background-color:{PANEL2}!important;color:{TEXT}!important}}
.Select-option:hover,.Select-option.is-focused{{background-color:{BORDER}!important}}
.Select-value-label{{color:{TEXT}!important}}
.Select-arrow{{border-top-color:{TEXT2}!important}}
</style>
</head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=False, port=8050)
