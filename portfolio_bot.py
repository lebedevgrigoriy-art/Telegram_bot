"""
Бот портфеля ИИС (Т-Инвестиции).

Что делает:
  • понедельник 10:00 — сверка портфеля: количество, средняя цена покупки, текущая цена,
    изменение за неделю, прибыль/убыток;
  • каждые 15 минут во время торгов — алерт, если бумага ушла больше чем на 5% от вчерашнего закрытия;
  • 1-го числа 10:00 — календарь купонов и погашений на месяц с суммами;
  • 1-го числа сразу после календаря — разбор эмитентов: новости, отчёты, Смартлаб, риск дефолта.

Источники: T-Invest API (токен только для чтения), Мосбиржа (купоны и погашения),
Смартлаб (страница облигации и форум эмитента), Gemini с поиском Google (новости и анализ).

Переменные окружения: PORTFOLIO_BOT_TOKEN, TINVEST_TOKEN, MY_CHAT_ID, GEMINI_API_KEY,
необязательно TINVEST_ACCOUNT_ID (если ИИС не определился сам).
"""
import asyncio
import html
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, time as dtime

import certifi
import pytz
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Bangkok")
MOSCOW = pytz.timezone("Europe/Moscow")

PORTFOLIO_BOT_TOKEN = os.environ.get("PORTFOLIO_BOT_TOKEN")
TINVEST_TOKEN = os.environ.get("TINVEST_TOKEN")
TINVEST_ACCOUNT_ID = os.environ.get("TINVEST_ACCOUNT_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID") or 0)

ALERT_THRESHOLD = 5.0          # % движения цены для алерта
BUY_TARGET = 50                # набираем бумагу до 50 шт, потом переходим к следующей
TINVEST_URL = "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1."
UA = {"User-Agent": "Mozilla/5.0 (portfolio-bot)"}

# Т-Банк (и часть российских сайтов) используют сертификат российского УЦ Минцифры,
# которого нет в стандартном наборе Python. Добавляем его к обычным корневым сертификатам:
# проверка HTTPS остаётся включённой, просто Python начинает доверять ещё одному корню.
# Источник: gu-st.ru, SHA-256 D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31
RUSSIAN_TRUSTED_ROOT_CA = """-----BEGIN CERTIFICATE-----
MIIFwjCCA6qgAwIBAgICEAAwDQYJKoZIhvcNAQELBQAwcDELMAkGA1UEBhMCUlUx
PzA9BgNVBAoMNlRoZSBNaW5pc3RyeSBvZiBEaWdpdGFsIERldmVsb3BtZW50IGFu
ZCBDb21tdW5pY2F0aW9uczEgMB4GA1UEAwwXUnVzc2lhbiBUcnVzdGVkIFJvb3Qg
Q0EwHhcNMjIwMzAxMjEwNDE1WhcNMzIwMjI3MjEwNDE1WjBwMQswCQYDVQQGEwJS
VTE/MD0GA1UECgw2VGhlIE1pbmlzdHJ5IG9mIERpZ2l0YWwgRGV2ZWxvcG1lbnQg
YW5kIENvbW11bmljYXRpb25zMSAwHgYDVQQDDBdSdXNzaWFuIFRydXN0ZWQgUm9v
dCBDQTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAMfFOZ8pUAL3+r2n
qqE0Zp52selXsKGFYoG0GM5bwz1bSFtCt+AZQMhkWQheI3poZAToYJu69pHLKS6Q
XBiwBC1cvzYmUYKMYZC7jE5YhEU2bSL0mX7NaMxMDmH2/NwuOVRj8OImVa5s1F4U
zn4Kv3PFlDBjjSjXKVY9kmjUBsXQrIHeaqmUIsPIlNWUnimXS0I0abExqkbdrXbX
YwCOXhOO2pDUx3ckmJlCMUGacUTnylyQW2VsJIyIGA8V0xzdaeUXg0VZ6ZmNUr5Y
Ber/EAOLPb8NYpsAhJe2mXjMB/J9HNsoFMBFJ0lLOT/+dQvjbdRZoOT8eqJpWnVD
U+QL/qEZnz57N88OWM3rabJkRNdU/Z7x5SFIM9FrqtN8xewsiBWBI0K6XFuOBOTD
4V08o4TzJ8+Ccq5XlCUW2L48pZNCYuBDfBh7FxkB7qDgGDiaftEkZZfApRg2E+M9
G8wkNKTPLDc4wH0FDTijhgxR3Y4PiS1HL2Zhw7bD3CbslmEGgfnnZojNkJtcLeBH
BLa52/dSwNU4WWLubaYSiAmA9IUMX1/RpfpxOxd4Ykmhz97oFbUaDJFipIggx5sX
ePAlkTdWnv+RWBxlJwMQ25oEHmRguNYf4Zr/Rxr9cS93Y+mdXIZaBEE0KS2iLRqa
OiWBki9IMQU4phqPOBAaG7A+eP8PAgMBAAGjZjBkMB0GA1UdDgQWBBTh0YHlzlpf
BKrS6badZrHF+qwshzAfBgNVHSMEGDAWgBTh0YHlzlpfBKrS6badZrHF+qwshzAS
BgNVHRMBAf8ECDAGAQH/AgEEMA4GA1UdDwEB/wQEAwIBhjANBgkqhkiG9w0BAQsF
AAOCAgEAALIY1wkilt/urfEVM5vKzr6utOeDWCUczmWX/RX4ljpRdgF+5fAIS4vH
tmXkqpSCOVeWUrJV9QvZn6L227ZwuE15cWi8DCDal3Ue90WgAJJZMfTshN4OI8cq
W9E4EG9wglbEtMnObHlms8F3CHmrw3k6KmUkWGoa+/ENmcVl68u/cMRl1JbW2bM+
/3A+SAg2c6iPDlehczKx2oa95QW0SkPPWGuNA/CE8CpyANIhu9XFrj3RQ3EqeRcS
AQQod1RNuHpfETLU/A2gMmvn/w/sx7TB3W5BPs6rprOA37tutPq9u6FTZOcG1Oqj
C/B7yTqgI7rbyvox7DEXoX7rIiEqyNNUguTk/u3SZ4VXE2kmxdmSh3TQvybfbnXV
4JbCZVaqiZraqc7oZMnRoWrXRG3ztbnbes/9qhRGI7PqXqeKJBztxRTEVj8ONs1d
WN5szTwaPIvhkhO3CO5ErU2rVdUr89wKpNXbBODFKRtgxUT70YpmJ46VVaqdAhOZ
D9EUUn4YaeLaS8AjSF/h7UkjOibNc4qVDiPP+rkehFWM66PVnP1Msh93tc+taIfC
EYVMxjh8zNbFuoc7fzvvrFILLe7ifvEIUqSVIC/AzplM/Jxw7buXFeGP1qVCBEHq
391d/9RAfaZ12zkwFsl+IKwE/OZxW8AHa9i1p4GO0YSNuczzEm4=
-----END CERTIFICATE-----"""


def _build_ca_bundle() -> str:
    path = os.path.join(tempfile.gettempdir(), "ca_bundle_with_russian_root.pem")
    with open(certifi.where(), encoding="utf-8") as f:
        default = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(default + "\n" + RUSSIAN_TRUSTED_ROOT_CA + "\n")
    return path


CA_BUNDLE = _build_ca_bundle()
MONTHS = ["", "январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]

_alerted = {}          # uid -> дата последнего алерта (не чаще раза в день по бумаге)
_instrument_cache = {}  # uid -> {name, isin, type}
_account_id = None


# =====================
# ФОРМАТИРОВАНИЕ
# =====================

def _q(v) -> float:
    """Quotation / MoneyValue из API -> float."""
    if not v:
        return 0.0
    return int(v.get("units", 0) or 0) + int(v.get("nano", 0) or 0) / 1e9


def rub(x: float) -> str:
    sign = "−" if x < 0 else ""
    return f"{sign}{abs(x):,.0f} ₽".replace(",", " ")


def price(x: float) -> str:
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return s.rstrip("0").rstrip(",") + " ₽" if "," in s else s + " ₽"


def pct(x: float) -> str:
    sign = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{sign}{abs(x):.1f}%".replace(".", ",")


def dot(x: float) -> str:
    return "🟢" if x > 0.05 else ("🔴" if x < -0.05 else "⚪")


def esc(s) -> str:
    return html.escape(str(s or ""))


# =====================
# T-INVEST API
# =====================

def tapi(method: str, body: dict) -> dict:
    """Вызов T-Invest API (REST). method вида 'OperationsService/GetPortfolio'."""
    resp = requests.post(
        TINVEST_URL + method,
        headers={"Authorization": f"Bearer {TINVEST_TOKEN}", "Content-Type": "application/json"},
        json=body,
        timeout=20,
        verify=CA_BUNDLE,
    )
    if not resp.ok:
        raise RuntimeError(f"T-Invest {method}: {resp.status_code} {resp.text[:300]}")
    return resp.json()


ACCOUNT_TYPES = {
    "ACCOUNT_TYPE_TINKOFF": "брокерский счёт",
    "ACCOUNT_TYPE_TINKOFF_IIS": "ИИС",
    "ACCOUNT_TYPE_INVEST_BOX": "инвесткопилка",
}


def get_accounts() -> list:
    return tapi("UsersService/GetAccounts", {}).get("accounts", [])


def get_account_id() -> str:
    """ИИС определяется сам; TINVEST_ACCOUNT_ID нужен только если счетов несколько и ИИС не нашёлся."""
    global _account_id
    if TINVEST_ACCOUNT_ID:
        return TINVEST_ACCOUNT_ID
    if _account_id:
        return _account_id
    accounts = [a for a in get_accounts() if a.get("status") != "ACCOUNT_STATUS_CLOSED"]
    iis = [a for a in accounts if a.get("type") == "ACCOUNT_TYPE_TINKOFF_IIS"]
    if iis:
        _account_id = iis[0]["id"]
    elif len(accounts) == 1:
        _account_id = accounts[0]["id"]
    if _account_id:
        return _account_id
    raise RuntimeError("ИИС не найден среди счетов. Проверь /accounts")


def instrument_info(uid: str) -> dict:
    if uid in _instrument_cache:
        return _instrument_cache[uid]
    info = {"name": "", "isin": "", "type": ""}
    try:
        ins = tapi("InstrumentsService/GetInstrumentBy",
                   {"idType": "INSTRUMENT_ID_TYPE_UID", "id": uid}).get("instrument", {})
        info = {"name": ins.get("name", ""), "isin": ins.get("isin", ""), "type": ins.get("instrumentType", "")}
    except Exception as e:
        logger.error(f"instrument_info {uid}: {e}")
    _instrument_cache[uid] = info
    return info


def get_positions() -> tuple[list, float]:
    """Бумаги портфеля и свободные рубли."""
    data = tapi("OperationsService/GetPortfolio", {"accountId": get_account_id(), "currency": "RUB"})
    positions, cash = [], 0.0
    for p in data.get("positions", []):
        qty = _q(p.get("quantity"))
        if qty <= 0:
            continue
        if p.get("instrumentType") == "currency":
            if (p.get("ticker") or "").upper().startswith("RUB"):
                cash += qty
            continue
        uid = p.get("instrumentUid")
        info = instrument_info(uid)
        positions.append({
            "uid": uid,
            "figi": p.get("figi", ""),
            "ticker": p.get("ticker", ""),
            "type": p.get("instrumentType", ""),
            "name": info["name"] or p.get("ticker", ""),
            "isin": info["isin"],
            "qty": qty,
            "avg": _q(p.get("averagePositionPrice")),
            "cur": _q(p.get("currentPrice")),
            "nkd": _q(p.get("currentNkd")),
            "pnl": _q(p.get("expectedYield")),
        })
    positions.sort(key=lambda x: x["qty"] * x["cur"], reverse=True)
    return positions, cash


def week_change(uid: str) -> float | None:
    """Изменение цены за неделю в % по дневным свечам."""
    now = datetime.utcnow()
    try:
        candles = tapi("MarketDataService/GetCandles", {
            "instrumentId": uid,
            "from": (now - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "interval": "CANDLE_INTERVAL_DAY",
        }).get("candles", [])
    except Exception as e:
        logger.error(f"week_change {uid}: {e}")
        return None
    if len(candles) < 2:
        return None
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    old = [c for c in candles if c.get("time", "")[:10] <= week_ago]
    base = _q((old[-1] if old else candles[0]).get("close"))
    last = _q(candles[-1].get("close"))
    return (last / base - 1) * 100 if base else None


# =====================
# 1. ЕЖЕНЕДЕЛЬНАЯ СВЕРКА
# =====================

def coupon_rate(ticker: str) -> float | None:
    """Годовой купон на одну облигацию, ₽: ближайший известный купон × число выплат в год."""
    try:
        coupons, _ = moex_bondization(ticker)
    except Exception as e:
        logger.error(f"coupon_rate {ticker}: {e}")
        return None
    dated = sorted((d, v) for d, v in coupons if d)
    if len(dated) < 2:
        return None
    today = datetime.now(MOSCOW).strftime("%Y-%m-%d")
    future_known = [v for d, v in dated if d >= today and v]
    past_known = [v for d, v in dated if d < today and v]
    value = (future_known or past_known[-1:] or [None])[0]
    if not value:
        return None
    days = [(datetime.strptime(b, "%Y-%m-%d") - datetime.strptime(a, "%Y-%m-%d")).days
            for (a, _), (b, _) in zip(dated, dated[1:])]
    period = sorted(days)[len(days) // 2] or 182   # медиана купонного периода в днях
    return value * 365 / period


def redemption_info(ticker: str) -> tuple[float, float] | None:
    """Сколько вернут при погашении на одну облигацию (оставшийся номинал) и через сколько лет."""
    try:
        _, amorts = moex_bondization(ticker)
    except Exception:
        return None
    today = datetime.now(MOSCOW).strftime("%Y-%m-%d")
    future = [(d, v) for d, v in amorts if d and d >= today and v]
    if not future:
        return None
    face = sum(v for _, v in future)
    # средневзвешенный срок возврата номинала (для амортизации учитывает частичные погашения)
    years = sum(v * (datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(today, "%Y-%m-%d")).days
                for d, v in future) / face / 365.25
    # меньше года не растягиваем: иначе разница с номиналом за пару недель даёт абсурдные сотни процентов
    return face, max(years, 1.0)


DEPOSIT_TYPES = {"OPERATION_TYPE_INPUT", "OPERATION_TYPE_INPUT_SWIFT", "OPERATION_TYPE_INPUT_ACQUIRING",
                 "OPERATION_TYPE_INP_MULTI"}
WITHDRAW_TYPES = {"OPERATION_TYPE_OUTPUT", "OPERATION_TYPE_OUTPUT_SWIFT", "OPERATION_TYPE_OUTPUT_ACQUIRING",
                  "OPERATION_TYPE_OUT_MULTI"}


def money_flows() -> list[tuple[datetime, float]]:
    """Все пополнения (минус) и выводы (плюс) ИИС за всю историю счёта."""
    acc_id = get_account_id()
    opened = next((a.get("openedDate") for a in get_accounts() if a.get("id") == acc_id), None)
    start = (opened or "2015-01-01T00:00:00Z")[:10]
    ops = tapi("OperationsService/GetOperations", {
        "accountId": acc_id,
        "from": f"{start}T00:00:00Z",
        "to": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": "OPERATION_STATE_EXECUTED",
    }).get("operations", [])
    flows = []
    for o in ops:
        t = o.get("operationType")
        if t in DEPOSIT_TYPES or t in WITHDRAW_TYPES:
            amount = abs(_q(o.get("payment")))
            when = datetime.strptime(o.get("date", "")[:10], "%Y-%m-%d")
            flows.append((when, -amount if t in DEPOSIT_TYPES else amount))
    return sorted(flows)


def xirr(flows: list[tuple[datetime, float]]) -> float | None:
    """Годовая доходность с учётом дат взносов (как XIRR в Excel), в %."""
    if len(flows) < 2:
        return None
    t0 = flows[0][0]

    def npv(rate):
        return sum(a / (1 + rate) ** ((d - t0).days / 365.25) for d, a in flows)

    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2 * 100


def fact_result(value_now: float) -> tuple[float, float, float | None] | None:
    """(внесено чистыми, результат ₽, % годовых) по всей истории пополнений ИИС."""
    try:
        flows = money_flows()
    except Exception as e:
        logger.error(f"money_flows: {e}")
        return None
    net = -sum(a for _, a in flows)          # пополнения минус выводы
    if net <= 0:
        return None
    today = datetime.strptime(datetime.now(MOSCOW).strftime("%Y-%m-%d"), "%Y-%m-%d")
    return net, value_now - net, xirr(flows + [(today, value_now)])


def num(x: float) -> str:
    """18.43 -> '18,4' (знак минус только у отрицательных)."""
    return pct(x).lstrip("+").rstrip("%")


def build_weekly_report() -> str:
    positions, cash = get_positions()
    if not positions:
        return "💼 В портфеле пока нет бумаг."
    year_income = bonds_value = bonds_cost = year_full = 0.0

    lines = []
    for p in positions:
        value = p["qty"] * p["cur"]
        yields = maturity = ""
        if p["type"] == "bond":
            annual = coupon_rate(p["ticker"])
            if annual and p["avg"] and p["cur"]:
                year_income += annual * p["qty"]
                bonds_value += value
                bonds_cost += p["avg"] * p["qty"]
                red = redemption_info(p["ticker"])
                try:
                    dates = [d for d, v in moex_bondization(p["ticker"])[1] if d]
                    if dates:
                        maturity = " · погашение " + datetime.strptime(max(dates), "%Y-%m-%d").strftime("%m.%Y")
                except Exception:
                    pass
                # с погашением: купоны + разница между номиналом и ценой покупки, растянутая на годы до погашения
                full = annual + ((red[0] - p["avg"]) / red[1] if red else 0)
                year_full += full * p["qty"]
                yields = (f" · к цене {num(annual / p['cur'] * 100)}% · к вложенным {num(annual / p['avg'] * 100)}%"
                          + (f" · с погаш. {num(full / p['avg'] * 100)}%" if red else ""))
        lines.append(
            f"<b>{esc(p['name'])}</b> · {p['qty']:g} шт{maturity}\n"
            f"{price(p['avg'])} → {price(p['cur'])}{yields}"
        )

    # стоимость счёта целиком: бумаги + НКД + свободные деньги
    value_now = sum(p["qty"] * (p["cur"] + p["nkd"]) for p in positions) + cash
    text = f"💼 <b>Сверка ИИС, {datetime.now(TIMEZONE).strftime('%d.%m.%Y')}</b>\n\n"

    fr = fact_result(value_now)
    if fr:
        net, result, yearly = fr
        text += (f"💰 <b>Результат: {'+' if result >= 0 else ''}{rub(result)} ({pct(result / net * 100)})"
                 + (f" · {num(yearly)}% годовых" if yearly is not None else "") + "</b>\n"
                 f"Внёс {rub(net)} → сейчас {rub(value_now)}\n")
    else:
        text += f"💰 <b>Сейчас на счёте: {rub(value_now)}</b>\n"
    if cash >= 1000:
        text += f"Свободные деньги {rub(cash)}: можно вложить\n"

    if bonds_cost:
        y_cost = year_income / bonds_cost * 100
        text += (
            "\n🎟 <b>Доходность, % годовых</b>\n"
            f"К цене: {num(year_income / bonds_value * 100)} · купоны к вложенным: <b>{num(y_cost)}</b> "
            f"{'✅' if y_cost >= 20 else '⏳'} цель 20 · с погашением: {num(year_full / bonds_cost * 100)}\n"
            f"Купоны ≈ {rub(year_income / 12)} в месяц\n"
        )
    return text + "\n" + "\n\n".join(lines)


# =====================
# 2. АЛЕРТЫ
# =====================

def check_moves(force: bool = False) -> list[str]:
    """Бумаги, ушедшие больше чем на ALERT_THRESHOLD% от закрытия прошлой сессии."""
    positions, _ = get_positions()
    if not positions:
        return []
    uids = [p["uid"] for p in positions]
    last = {x["instrumentUid"]: _q(x.get("price"))
            for x in tapi("MarketDataService/GetLastPrices", {"instrumentId": uids}).get("lastPrices", [])}
    close = {x["instrumentUid"]: _q(x.get("price"))
             for x in tapi("MarketDataService/GetClosePrices",
                           {"instruments": [{"instrumentId": u} for u in uids]}).get("closePrices", [])}
    today = datetime.now(MOSCOW).date()
    alerts = []
    for p in positions:
        lp, cp = last.get(p["uid"]), close.get(p["uid"])
        if not lp or not cp:
            continue
        move = (lp / cp - 1) * 100
        if abs(move) < ALERT_THRESHOLD:
            continue
        if not force and _alerted.get(p["uid"]) == today:
            continue
        _alerted[p["uid"]] = today
        unit = "% от номинала" if p["type"] == "bond" else " ₽"
        fmt = lambda v: f"{v:.2f}".replace(".", ",") + unit
        word = "выросла" if move > 0 else "упала"
        delta = p["qty"] * p["cur"] * move / (100 + move)   # изменение стоимости позиции за день
        alerts.append(
            f"{'🚀' if move > 0 else '⚠️'} <b>{esc(p['name'])}</b> {word} на {pct(abs(move))[1:]} "
            f"к вчерашнему закрытию\n{fmt(cp)} → {fmt(lp)}\n"
            f"У тебя {p['qty']:g} шт: {rub(delta)} за день"
        )
    return alerts


# =====================
# 3. КУПОНЫ И ПОГАШЕНИЯ
# =====================

_moex_cache = {}


def moex_bondization(secid: str) -> tuple[list, list]:
    """Купоны и погашения с Мосбиржи: [(date, value_rub|None)], [(date, value_rub|None)]. Кэш на день."""
    key = (secid, datetime.now(MOSCOW).strftime("%Y-%m-%d"))
    if key not in _moex_cache:
        if len(_moex_cache) > 200:
            _moex_cache.clear()
        _moex_cache[key] = _moex_bondization(secid)
    return _moex_cache[key]


def _moex_bondization(secid: str) -> tuple[list, list]:
    resp = requests.get(
        f"https://iss.moex.com/iss/securities/{secid}/bondization.json",
        params={"iss.meta": "off", "iss.only": "coupons,amortizations", "limit": "unlimited"},
        headers=UA, timeout=20, verify=CA_BUNDLE,
    )
    resp.raise_for_status()
    data = resp.json()

    def rows(table, date_col):
        t = data.get(table, {})
        cols = t.get("columns", [])
        out = []
        for r in t.get("data", []):
            row = dict(zip(cols, r))
            out.append((row.get(date_col), row.get("value_rub")))
        return out

    return rows("coupons", "coupondate"), rows("amortizations", "amortdate")


def tapi_coupons(uid: str, start: datetime, end: datetime) -> list:
    """Запасной источник купонов: T-Invest API."""
    events = tapi("InstrumentsService/GetBondCoupons", {
        "instrumentId": uid,
        "from": start.strftime("%Y-%m-%dT00:00:00Z"),
        "to": end.strftime("%Y-%m-%dT23:59:59Z"),
    }).get("events", [])
    return [(e.get("couponDate", "")[:10], _q(e.get("payOneBond")) or None) for e in events]


def collect_payments(d_from: str, d_to: str) -> tuple[list, list, list]:
    """Купоны и погашения по облигациям портфеля в интервале дат (YYYY-MM-DD, по Москве).
    Возвращает (events, unknown, failed): events = [(дата, значок, бумага, сумма, пояснение)]."""
    positions, _ = get_positions()
    bonds = [p for p in positions if p["type"] == "bond"]
    events, unknown, failed = [], [], []
    for b in bonds:
        try:
            coupons, amorts = moex_bondization(b["ticker"])
            all_amorts = [d for d, _ in amorts if d]
            maturity = max(all_amorts) if all_amorts else None
        except Exception as e:
            logger.warning(f"MOEX {b['ticker']}: {e}, беру купоны из T-Invest")
            try:
                coupons = tapi_coupons(b["uid"], datetime.strptime(d_from, "%Y-%m-%d"),
                                       datetime.strptime(d_to, "%Y-%m-%d"))
                bond = tapi("InstrumentsService/BondBy",
                            {"idType": "INSTRUMENT_ID_TYPE_UID", "id": b["uid"]}).get("instrument", {})
                maturity = (bond.get("maturityDate") or "")[:10] or None
                amorts = [(maturity, _q(bond.get("nominal")))] if maturity else []
            except Exception as e2:
                logger.error(f"coupons {b['ticker']}: {e2}")
                failed.append(b["name"])
                continue
        for d, v in coupons:
            if d and d_from <= d <= d_to:
                if v is None:
                    unknown.append((d, b["name"]))
                else:
                    events.append((d, "💰", b["name"], v * b["qty"], f"купон {price(v)} × {b['qty']:g}"))
        for d, v in amorts:
            if d and d_from <= d <= d_to and v:
                icon, kind = ("🏁", "погашение") if d == maturity else ("🧩", "амортизация")
                events.append((d, icon, b["name"], v * b["qty"], f"{kind} {price(v)} × {b['qty']:g}"))
    events.sort()
    unknown.sort()
    return events, unknown, failed


def _dm(d: str) -> str:
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m")


def _event_lines(events: list, with_date: bool = True) -> str:
    return "\n".join(
        (f"{_dm(d)} " if with_date else "") + f"{icon} <b>{esc(n)}</b>: {rub(s)}\n      {esc(note)}"
        for d, icon, n, s, note in events)


def build_coupon_calendar(month_shift: int = 0) -> str:
    today = datetime.now(MOSCOW)
    first = today.replace(day=1)
    for _ in range(month_shift):
        first = (first + timedelta(days=32)).replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    events, unknown, failed = collect_payments(first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d"))

    title = f"📅 <b>Купоны и погашения: {MONTHS[first.month]} {first.year}</b>\n"
    if not events and not unknown:
        text = title + "\nВ этом месяце выплат нет."
    else:
        total = sum(e[3] for e in events)
        text = title + "\n" + _event_lines(events) + f"\n\n<b>Всего придёт: {rub(total)}</b>"
        if unknown:
            text += "\n\nРазмер купона ещё не объявлен:\n" + "\n".join(
                f"• {_dm(d)} {esc(n)}" for d, n in unknown)
    if failed:
        text += "\n\n⚠️ Не удалось получить данные: " + esc(", ".join(failed))
    text += "\n\n<i>Суммы по текущему количеству бумаг, до налога, если он удерживается.</i>"
    return text


def build_payday_message(force: bool = False) -> str | None:
    """В день выплаты: что пришло сегодня, что ещё придёт, покупать сейчас или подождать.
    Правило Григория: если в ближайшую неделю выплат больше нет, покупать сразу;
    если следующая выплата в пределах недели, подождать и купить на всю сумму."""
    now = datetime.now(MOSCOW)
    today = now.strftime("%Y-%m-%d")
    month_end = ((now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1))
    week_end = now + timedelta(days=7)
    horizon = max(month_end, week_end).strftime("%Y-%m-%d")

    events, unknown, failed = collect_payments(today, horizon)
    todays = [e for e in events if e[0] == today]
    if not todays and not force:
        return None

    later = [e for e in events if e[0] > today]
    later_unknown = [u for u in unknown if u[0] > today]
    week_str = week_end.strftime("%Y-%m-%d")
    month_str = month_end.strftime("%Y-%m-%d")
    today_sum = sum(e[3] for e in todays)

    if todays:
        text = (f"💸 <b>Сегодня выплаты, {now.strftime('%d.%m')}</b>\n\n" + _event_lines(todays, with_date=False)
                + f"\n\n<b>Сегодня придёт: {rub(today_sum)}</b>")
    else:
        text = f"💸 Сегодня, {now.strftime('%d.%m')}, выплат нет."

    in_month = [e for e in later if e[0] <= month_str]
    after_month = [e for e in later if month_str < e[0] <= week_str]
    if in_month:
        text += f"\n\n📅 <b>Ещё в этом месяце: {rub(sum(e[3] for e in in_month))}</b>\n" + _event_lines(in_month)
    else:
        text += "\n\n📅 В этом месяце больше выплат нет."
    if after_month:
        text += "\n\n🗓 <b>В начале следующего месяца (в пределах недели):</b>\n" + _event_lines(after_month)
    if later_unknown:
        text += "\n\nРазмер купона ещё не объявлен:\n" + "\n".join(
            f"• {_dm(d)} {esc(n)}" for d, n in later_unknown)

    # Покупать сейчас или подождать неделю
    week = [e for e in later if e[0] <= week_str]
    week_unknown = [u for u in later_unknown if u[0] <= week_str]
    if todays:
        if week or week_unknown:
            last_day = max([e[0] for e in week] + [u[0] for u in week_unknown])
            week_sum = sum(e[3] for e in week)
            parts = []
            if week_sum:
                parts.append(rub(week_sum))
            if week_unknown:
                parts.append("купон, сумма которого ещё не объявлена")
            text += (f"\n\n⏳ <b>Можно подождать до {_dm(last_day)}</b>: в ближайшую неделю придёт ещё "
                     + " и ".join(parts) + f". Тогда купишь сразу на {rub(today_sum + week_sum)}"
                     + (" и больше" if week_unknown else "") + ".")
            buy_amount = today_sum + week_sum
        else:
            text += f"\n\n🛒 <b>В ближайшую неделю выплат больше нет: можно покупать сразу на {rub(today_sum)}.</b>"
            buy_amount = today_sum
        try:
            text += "\n\n" + build_buy_hint(buy_amount)
        except Exception as e:
            logger.error(f"buy hint: {e}")
    if failed:
        text += "\n\n⚠️ Не удалось получить данные: " + esc(", ".join(failed))
    text += "\n\n<i>Деньги приходят на ИИС в течение дня. Суммы до налога, если он удерживается.</i>"
    return text


# ---------- Что сейчас набираем ----------

def moex_bond_price(secid: str) -> float | None:
    """Цена одной облигации в рублях с НКД: (последняя цена или вчерашнее закрытие) × номинал + НКД."""
    try:
        resp = requests.get(
            f"https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{secid}.json",
            params={"iss.meta": "off", "iss.only": "securities,marketdata",
                    "securities.columns": "BOARDID,FACEVALUE,ACCRUEDINT,PREVPRICE",
                    "marketdata.columns": "BOARDID,LAST"},
            headers=UA, timeout=20, verify=CA_BUNDLE)
        data = resp.json()
        sec = [dict(zip(data["securities"]["columns"], r)) for r in data["securities"]["data"]]
        md = {r[0]: r[1] for r in data["marketdata"]["data"]}
        for row in sec:
            pr = md.get(row["BOARDID"]) or row.get("PREVPRICE")
            if pr and row.get("FACEVALUE"):
                return pr / 100 * row["FACEVALUE"] + (row.get("ACCRUEDINT") or 0)
    except Exception as e:
        logger.error(f"moex_bond_price {secid}: {e}")
    return None


def recent_buys() -> list[str]:
    """FIGI купленных бумаг за 4 месяца, от последней покупки к ранней."""
    now = datetime.utcnow()
    try:
        ops = tapi("OperationsService/GetOperations", {
            "accountId": get_account_id(),
            "from": (now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state": "OPERATION_STATE_EXECUTED",
        }).get("operations", [])
    except Exception as e:
        logger.error(f"recent_buys: {e}")
        return []
    buys = sorted((o for o in ops if o.get("operationType") == "OPERATION_TYPE_BUY"),
                  key=lambda o: o.get("date", ""), reverse=True)
    return [o.get("figi") for o in buys]


def current_target(positions: list) -> tuple[dict | None, list]:
    """Какую бумагу сейчас набираем: ту, что меньше 50 шт и покупалась последней.
    Возвращает (текущая, остальные недобранные)."""
    bonds = [p for p in positions if p["type"] == "bond"]
    unfinished = [b for b in bonds if b["qty"] < BUY_TARGET]
    if not unfinished:
        return None, []
    by_figi = {b["figi"]: b for b in unfinished}
    cur = next((by_figi[f] for f in recent_buys() if f in by_figi), None)
    if cur is None:
        cur = max(unfinished, key=lambda b: b["qty"])   # покупок не нашли: берём самую набранную
    return cur, [b for b in unfinished if b is not cur]


def build_buy_hint(amount: float | None, positions: list | None = None) -> str:
    """Что сейчас покупать по правилу: одна бумага до 50 шт, потом следующая."""
    if positions is None:
        positions, _ = get_positions()
    cur, others = current_target(positions)
    if cur is None:
        return (f"✅ Все облигации в портфеле набраны до {BUY_TARGET} шт. Выбери следующую бумагу "
                "и купи первую штуку: бот сам подхватит её как текущую.")
    need = BUY_TARGET - cur["qty"]
    one = moex_bond_price(cur["ticker"])
    lines = [f"🛒 <b>Сейчас набираешь: {esc(cur['name'])}</b>",
             f"У тебя {cur['qty']:g} из {BUY_TARGET} шт, осталось {need:g} шт"
             + (f" ≈ {rub(need * one)}" if one else "")]
    if one and amount:
        lines.append(f"На {rub(amount)} хватит на <b>{int(amount // one)} шт</b> (одна ≈ {price(one)} с НКД)")
    elif not one:
        lines.append("Цену сейчас получить не удалось")
    return "\n".join(lines)


# ---------- Купоны на год вперёд ----------

def build_income_forecast() -> str:
    """Купоны по месяцам на 12 месяцев вперёд. Необъявленные купоны считаем по последнему известному."""
    now = datetime.now(MOSCOW)
    d_from, d_to = now.strftime("%Y-%m-%d"), (now + timedelta(days=365)).strftime("%Y-%m-%d")
    positions, _ = get_positions()
    bonds = [p for p in positions if p["type"] == "bond"]
    months, redemptions, estimated, failed = {}, 0.0, False, []
    for b in bonds:
        try:
            coupons, amorts = moex_bondization(b["ticker"])
        except Exception:
            failed.append(b["name"])
            continue
        last_known = None
        for d, v in sorted((d, v) for d, v in coupons if d):
            if v:
                last_known = v
            if d_from <= d <= d_to:
                val = v or last_known
                if not v and last_known:
                    estimated = True
                if val:
                    months[d[:7]] = months.get(d[:7], 0) + val * b["qty"]
        redemptions += sum(v * b["qty"] for d, v in amorts if d and d_from <= d <= d_to and v)

    keys = []
    y, m = now.year, now.month
    for _ in range(12):
        keys.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    top = max([months.get(k, 0) for k in keys] + [1])
    short = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    rows = []
    for k in keys:
        v = months.get(k, 0)
        filled = round(v / top * 8)
        rows.append(f"<code>{short[int(k[5:])]} {k[2:4]} {'▓' * filled}{'░' * (8 - filled)}</code> {rub(v)}")
    total = sum(months.get(k, 0) for k in keys)
    text = ("📈 <b>Купоны на 12 месяцев вперёд</b>\n\n" + "\n".join(rows)
            + f"\n\n<b>Всего за год: {rub(total)} · в среднем {rub(total / 12)} в месяц</b>")
    if redemptions:
        text += f"\nПлюс вернётся при погашениях: {rub(redemptions)}"
    if estimated:
        text += "\n\n<i>Купоны, размер которых ещё не объявлен, посчитаны по последнему известному.</i>"
    if failed:
        text += "\n⚠️ Нет данных: " + esc(", ".join(failed))
    text += "\n<i>По текущему количеству бумаг: каждая докупка увеличит эти цифры.</i>"
    return text


def build_queue_text() -> str:
    positions, cash = get_positions()
    bonds = sorted([p for p in positions if p["type"] == "bond"], key=lambda b: -b["qty"])
    cur, _ = current_target(positions)
    rows = []
    for b in bonds:
        mark = "✅" if b["qty"] >= BUY_TARGET else ("👉" if cur and b is cur else "⏳")
        rows.append(f"{mark} {esc(b['name'])}: {b['qty']:g} / {BUY_TARGET}")
    text = "🛒 <b>Набор бумаг до 50 шт</b>\n\n" + "\n".join(rows) + "\n\n"
    text += build_buy_hint(cash if cash >= 1 else None, positions)
    if cash >= 1:
        text += f"\n\nСвободные деньги на счёте: {rub(cash)}"
    return text


def build_maturity_message(days_ahead: int = 14) -> str | None:
    """За 2 недели до погашения: сколько вернётся."""
    day = (datetime.now(MOSCOW) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    events, _, _ = collect_payments(day, day)
    redemptions = [e for e in events if e[1] == "🏁"]
    if not redemptions:
        return None
    parts = []
    for d, _, name, total, note in redemptions:
        coupon = sum(e[3] for e in events if e[1] == "💰" and e[2] == name)
        parts.append(
            f"🎉🥳 <b>{esc(name)}</b> погашается {_dm(d)}!\n"
            f"💵 Вернётся номинал: <b>{rub(total)}</b> ({esc(note.replace('погашение ', ''))})"
            + (f"\n🎁 И последний купон: {rub(coupon)}" if coupon else "")
        )
    grand = sum(e[3] for e in events)
    return ("🍾 <b>Через 2 недели погашение!</b>\n\n" + "\n\n".join(parts)
            + f"\n\n💰 Всего придёт {rub(grand)}. Самое время присмотреть, куда вложить 🚀")


SCREENING_DAYS = ((4, 12), (10, 12))   # первый скрининг был 12.10.2026, дальше каждые полгода


def build_screening_reminder() -> str | None:
    now = datetime.now(MOSCOW)
    if (now.month, now.day) not in SCREENING_DAYS:
        return None
    return ("📋 <b>Пора обновить топ-5 облигаций на полугодие</b>\n\n"
            "Полгода прошло: время нового скрининга. После него все взносы и купоны "
            "следующие 6 месяцев идут в новые 5 бумаг.")


# =====================
# 4. РАЗБОР ЭМИТЕНТОВ
# =====================

def _html_to_text(s: str) -> str:
    s = re.sub(r"<blockquote.*?</blockquote>", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def smartlab_bond(isin_or_secid: str) -> dict:
    """Страница облигации на Смартлабе: ключевые цифры и ссылка на форум эмитента."""
    out = {"facts": "", "forum_url": "", "issuer": ""}
    try:
        resp = requests.get(f"https://smart-lab.ru/q/bonds/{isin_or_secid}/", headers=UA, timeout=20, verify=CA_BUNDLE)
        if not resp.ok:
            return out
        page = resp.text
        m = re.search(r'href="([^"]*?/bonds/[a-zA-Z0-9_\-]+)"[^>]*>\s*Обсудить на форуме\s*([^<]+)<', page)
        if m:
            url = m.group(1)
            out["forum_url"] = url if url.startswith("http") else "https://smart-lab.ru" + url
            out["issuer"] = m.group(2).strip()
        text = _html_to_text(page)
        start = text.find("стоит сейчас")
        end = text.find("Календарь выплаты")
        if start != -1:
            line_start = text.rfind("\n", 0, start) + 1   # с начала фразы «Облигация ... стоит сейчас»
            out["facts"] = text[line_start: end if end > start else start + 1500][:1500]
    except Exception as e:
        logger.error(f"smartlab_bond {isin_or_secid}: {e}")
    return out


def smartlab_forum(url: str, limit: int = 20) -> str:
    """Последние сообщения форума эмитента на Смартлабе."""
    try:
        resp = requests.get(url, headers=UA, timeout=20, verify=CA_BUNDLE)
        if not resp.ok:
            return ""
        posts = re.findall(
            r'<time datetime="([^"]+)">.*?<div class="text">(.*?)</div><div class="cm_ftr">',
            resp.text, flags=re.S)
        lines = []
        for when, body in posts[:limit]:
            txt = _html_to_text(body)[:400]
            if txt:
                lines.append(f"[{when[:10]}] {txt}")
        return "\n".join(lines)[:4000]
    except Exception as e:
        logger.error(f"smartlab_forum {url}: {e}")
        return ""


def ask_gemini_grounded(prompt: str) -> str:
    """Gemini 2.5 Flash с поиском Google: свежие новости и отчёты."""
    if not GEMINI_API_KEY:
        return ""
    for attempt in range(2):
        try:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                params={"key": GEMINI_API_KEY},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "tools": [{"google_search": {}}],
                    "generationConfig": {"maxOutputTokens": 12000, "temperature": 0.2,
                                         "thinkingConfig": {"thinkingBudget": 2048}},
                },
                timeout=120,
            )
            cands = resp.json().get("candidates", [])
            if cands:
                text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
                if text.strip():
                    return text.strip()
            logger.error(f"Gemini empty (attempt {attempt + 1}): {resp.text[:300]}")
        except Exception as e:
            logger.error(f"Gemini error (attempt {attempt + 1}): {e}")
    return ""


def group_issuers(bonds: list) -> list[dict]:
    """Группируем облигации по эмитенту (по форуму Смартлаба). ОФЗ отдельно."""
    groups = {}
    for b in bonds:
        is_ofz = b["ticker"].startswith("SU") and "RMFS" in b["ticker"]
        sl = {"facts": "", "forum_url": "", "issuer": "Минфин РФ"} if is_ofz else smartlab_bond(b["ticker"])
        key = "ofz" if is_ofz else (sl["forum_url"] or b["name"].split()[0])
        g = groups.setdefault(key, {"issuer": sl["issuer"] or b["name"].split()[0],
                                    "forum_url": sl["forum_url"], "ofz": is_ofz, "bonds": []})
        g["bonds"].append({**b, "facts": sl["facts"]})
    return list(groups.values())


RISK_RE = re.compile(r"РИСК ДЕФОЛТА:\s*(низкий|средний|высокий)", re.I)
RISK_ICON = {"низкий": "🟢", "средний": "🟡", "высокий": "🔴"}


def analyze_issuer(g: dict) -> tuple[str, str]:
    """Разбор одного эмитента. Возвращает (текст, уровень риска)."""
    today = datetime.now(TIMEZONE)
    bonds_txt = "\n".join(
        f"- {b['name']} (ISIN {b['isin'] or b['ticker']}): {b['qty']:g} шт, "
        f"цена {price(b['cur'])}, средняя покупки {price(b['avg'])}\n  Смартлаб: {b['facts'] or 'нет данных'}"
        for b in g["bonds"])
    forum = smartlab_forum(g["forum_url"]) if g["forum_url"] else ""
    prompt = (
        f"Сегодня {today.strftime('%d.%m.%Y')}. Ты аналитик долгового рынка РФ. "
        f"Сделай ежемесячный разбор эмитента «{g['issuer']}» для частного инвестора, "
        "который держит его облигации на ИИС до погашения.\n\n"
        f"Облигации в портфеле:\n{bonds_txt}\n\n"
        + (f"Последние сообщения с форума эмитента на Смартлабе ({g['forum_url']}):\n{forum}\n\n" if forum else "")
        + "Найди в интернете свежую информацию за последний месяц: новости компании, последние отчёты "
        "(МСФО/РСБУ: выручка, EBITDA, долг, чистый долг/EBITDA, покрытие процентов), изменения "
        "кредитных рейтингов, новые выпуски, оферты, судебные иски, проблемы с выплатами, мнения аналитиков.\n\n"
        "Ответь простым текстом без Markdown (без звёздочек и решёток), коротко и по делу, в таком порядке:\n"
        "РИСК ДЕФОЛТА: низкий / средний / высокий\n"
        "📰 Новости за месяц: 2-4 пункта с датами\n"
        "📊 Отчётность и долг: последние цифры и их динамика\n"
        "⭐ Рейтинг: текущий рейтинг и изменения\n"
        "💬 Смартлаб: о чём спорят и какие опасения у инвесторов\n"
        "⚠️ Опасения: главные риски\n"
        "🛡 Риск дефолта: почему именно такой уровень, что может его повысить, за чем следить\n"
        "Не выдумывай цифры: если данных нет, так и напиши."
    )
    text = ask_gemini_grounded(prompt)
    if not text:
        return f"🏢 {g['issuer']}\nНе удалось получить разбор, попробую в следующий раз.", ""
    text = text.replace("**", "").replace("##", "")
    m = RISK_RE.search(text)
    risk = m.group(1).lower() if m else ""
    return f"🏢 {g['issuer'].upper()} {RISK_ICON.get(risk, '')}\n\n{text}", risk


async def send_long(bot, chat_id, text: str, parse_mode=None):
    """Telegram ограничивает сообщение 4096 символами: режем по абзацам."""
    while text:
        if len(text) <= 4000:
            chunk, text = text, ""
        else:
            cut = text.rfind("\n", 0, 4000)
            cut = cut if cut > 1000 else 4000
            chunk, text = text[:cut], text[cut:].lstrip()
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode,
                               disable_web_page_preview=True)


async def send_issuer_report(bot, chat_id):
    positions, _ = await asyncio.to_thread(get_positions)
    bonds = [p for p in positions if p["type"] == "bond"]
    if not bonds:
        await bot.send_message(chat_id=chat_id, text="🏢 В портфеле нет облигаций для разбора.")
        return
    await bot.send_message(chat_id=chat_id, text="🏢 Разбор эмитентов за месяц. Собираю новости, отчёты и Смартлаб, "
                                                 "это займёт несколько минут…")
    groups = await asyncio.to_thread(group_issuers, bonds)
    summary = []
    for g in groups:
        if g["ofz"]:
            summary.append("🟢 ОФЗ (Минфин РФ): государственный долг, риск дефолта минимальный")
            continue
        text, risk = await asyncio.to_thread(analyze_issuer, g)
        await send_long(bot, chat_id, text)
        summary.append(f"{RISK_ICON.get(risk, '⚪')} {g['issuer']}: риск {risk or 'не определён'}")
        await asyncio.sleep(1)
    order = {"🔴": 0, "🟡": 1, "⚪": 2, "🟢": 3}
    summary.sort(key=lambda s: order.get(s[:1], 2))
    await bot.send_message(chat_id=chat_id, text="🛡 Итог по риску дефолта\n\n" + "\n".join(summary))


# =====================
# КОМАНДЫ
# =====================

def _mine(update: Update) -> bool:
    """Данные портфеля показываем только владельцу."""
    return update.effective_chat and update.effective_chat.id == MY_CHAT_ID


async def _run(update: Update, title: str, func, *args):
    if not _mine(update):
        return
    msg = await update.message.reply_text(f"{title}…")
    try:
        text = await asyncio.to_thread(func, *args)
        await msg.delete()
        await send_long(update.get_bot(), update.effective_chat.id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"{title}: {e}")
        await msg.edit_text(f"⚠️ Не получилось: {e}"[:1000])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _mine(update):
        return
    await update.message.reply_text(
        "💼 Бот портфеля ИИС\n\n"
        "Сам присылаю:\n"
        "• по понедельникам в 10:00 — сверку портфеля\n"
        f"• во время торгов — алерт, если бумага ушла больше чем на {ALERT_THRESHOLD:g}% за день\n"
        "• в день купона или погашения — сколько пришло и покупать сразу или подождать неделю\n"
        "• за 2 недели до погашения — сколько вернётся\n"
        "• 12 апреля и 12 октября — напоминание обновить топ-5\n"
        "• 1-го числа — календарь купонов, купоны на год вперёд и разбор эмитентов\n\n"
        "Команды:\n"
        "/accounts — какие счета видит бот\n"
        "/portfolio — сверка портфеля сейчас\n"
        "/coupons — выплаты в этом месяце\n"
        "/coupons_next — выплаты в следующем месяце\n"
        "/check — проверить резкие движения сейчас\n"
        "/payday — выплаты сегодня и до конца месяца\n"
        "/income — купоны на 12 месяцев вперёд\n"
        "/queue — что сейчас набираешь до 50 шт\n"
        "/issuers — разбор эмитентов сейчас (несколько минут)"
    )


def build_accounts_text() -> str:
    accounts = get_accounts()
    if not accounts:
        return "Токен работает, но счетов не видно. Проверь, что при создании токена выбран ИИС."
    try:
        used = get_account_id()
    except Exception:
        used = ""
    lines = []
    for a in accounts:
        kind = ACCOUNT_TYPES.get(a.get("type"), a.get("type", ""))
        mark = " ✅ использую этот" if a.get("id") == used else ""
        closed = " (закрыт)" if a.get("status") == "ACCOUNT_STATUS_CLOSED" else ""
        lines.append(f"• {esc(a.get('name') or kind)}: {kind}{closed}{mark}\n  id: <code>{a.get('id')}</code>")
    text = "🔑 <b>Счета, которые видит бот</b>\n\n" + "\n".join(lines)
    if not used:
        text += ("\n\n⚠️ ИИС не определился сам. Скопируй id нужного счёта в Railway "
                 "в переменную TINVEST_ACCOUNT_ID.")
    return text


async def accounts_command(update, context):
    await _run(update, "🔑 Смотрю счета", build_accounts_text)


async def portfolio_command(update, context):
    await _run(update, "💼 Собираю сверку", build_weekly_report)


async def coupons_command(update, context):
    await _run(update, "📅 Считаю выплаты", build_coupon_calendar, 0)


async def coupons_next_command(update, context):
    await _run(update, "📅 Считаю выплаты", build_coupon_calendar, 1)


async def income_command(update, context):
    await _run(update, "📈 Считаю купоны на год", build_income_forecast)


async def queue_command(update, context):
    await _run(update, "🛒 Смотрю очередь", build_queue_text)


async def payday_command(update, context):
    await _run(update, "💸 Смотрю выплаты", build_payday_message, True)


async def check_command(update, context):
    if not _mine(update):
        return
    try:
        alerts = await asyncio.to_thread(check_moves, True)
        if alerts:
            for a in alerts:
                await update.message.reply_text(a, parse_mode="HTML")
        else:
            await update.message.reply_text(f"✅ Резких движений нет: все бумаги в пределах ±{ALERT_THRESHOLD:g}% "
                                            "от вчерашнего закрытия.")
    except Exception as e:
        logger.error(f"check: {e}")
        await update.message.reply_text(f"⚠️ Не получилось: {e}"[:1000])


async def issuers_command(update, context):
    if not _mine(update):
        return
    try:
        await send_issuer_report(update.get_bot(), update.effective_chat.id)
    except Exception as e:
        logger.error(f"issuers: {e}")
        await update.message.reply_text(f"⚠️ Не получилось: {e}"[:1000])


# =====================
# РАСПИСАНИЕ
# =====================

async def weekly_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = await asyncio.to_thread(build_weekly_report)
        await send_long(context.bot, MY_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"weekly_job: {e}")
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=f"⚠️ Сверка портфеля не собралась: {e}"[:1000])


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    """Каждый день в 10:05: выплаты сегодня, погашения через 2 недели, напоминание о скрининге.
    Если ничего нет, бот молчит."""
    for name, func in (("payday", build_payday_message), ("maturity", build_maturity_message),
                       ("screening", build_screening_reminder)):
        try:
            text = await asyncio.to_thread(func)
            if text:
                await send_long(context.bot, MY_CHAT_ID, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"daily_job {name}: {e}")


async def alert_job(context: ContextTypes.DEFAULT_TYPE):
    """Каждые 15 минут, но работает только в торговые часы Мосбиржи (будни 10:00–23:50 МСК)."""
    now = datetime.now(MOSCOW)
    if now.weekday() >= 5 or not (dtime(10, 5) <= now.time() <= dtime(23, 50)):
        return
    try:
        for a in await asyncio.to_thread(check_moves):
            await context.bot.send_message(chat_id=MY_CHAT_ID, text=a, parse_mode="HTML")
    except Exception as e:
        logger.error(f"alert_job: {e}")


async def monthly_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = await asyncio.to_thread(build_coupon_calendar, 0)
        await send_long(context.bot, MY_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"monthly coupons: {e}")
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=f"⚠️ Календарь купонов не собрался: {e}"[:1000])
    try:
        text = await asyncio.to_thread(build_income_forecast)
        await send_long(context.bot, MY_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"monthly income: {e}")
    try:
        await send_issuer_report(context.bot, MY_CHAT_ID)
    except Exception as e:
        logger.error(f"monthly issuers: {e}")
        await context.bot.send_message(chat_id=MY_CHAT_ID, text=f"⚠️ Разбор эмитентов не собрался: {e}"[:1000])


async def main() -> list:
    if not PORTFOLIO_BOT_TOKEN or not TINVEST_TOKEN:
        logger.warning("Портфельный бот выключен: нет PORTFOLIO_BOT_TOKEN или TINVEST_TOKEN")
        return []
    app = Application.builder().token(PORTFOLIO_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("accounts", accounts_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("coupons", coupons_command))
    app.add_handler(CommandHandler("coupons_next", coupons_next_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("payday", payday_command))
    app.add_handler(CommandHandler("income", income_command))
    app.add_handler(CommandHandler("queue", queue_command))
    app.add_handler(CommandHandler("issuers", issuers_command))

    jq = app.job_queue
    # run_daily: 0 = воскресенье, 1 = понедельник
    jq.run_daily(weekly_job, time=dtime(hour=10, minute=0, tzinfo=TIMEZONE), days=(1,))
    jq.run_daily(daily_job, time=dtime(hour=10, minute=5, tzinfo=TIMEZONE))
    jq.run_repeating(alert_job, interval=900, first=120)
    jq.run_monthly(monthly_job, when=dtime(hour=10, minute=0, tzinfo=TIMEZONE), day=1)
    return [app]
