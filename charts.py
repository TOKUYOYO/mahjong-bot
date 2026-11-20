"""
charts.py
成員損益折線圖（PNG），由 main.py 的 /chart/trend.png 提供給 LINE 圖片訊息使用。

/走勢       → 排名賽跑圖：每月月底依年度累計輸贏排名（members）
/走勢 名字  → 半月K線：每月分上半(1–15日)/下半(16日～月底)；開=期初累計、收=期末累計、高低=期內每場後的最高/最低累計，下方為場數
圖片網址帶 HMAC 簽章，避免外人任意查詢群組資料。
"""

import hashlib
import hmac
import io
import os
import re
import time
from urllib.parse import urlencode

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager, ticker  # noqa: E402

from config import LINE_CHANNEL_SECRET, PUBLIC_BASE_URL  # noqa: E402

_FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansTC-Medium.ttf")
font_manager.fontManager.addfont(_FONT_PATH)
_FONT_NAME = font_manager.FontProperties(fname=_FONT_PATH).get_name()
plt.rcParams["font.family"] = _FONT_NAME
plt.rcParams["axes.unicode_minus"] = False

# 11+ 位成員也分得開的色盤
PALETTE = [
    "#2B6CB0", "#C53030", "#2F855A", "#B7791F", "#6B46C1", "#D53F8C",
    "#319795", "#DD6B20", "#4A5568", "#9C4221", "#1A202C", "#805AD5",
    "#E53E3E", "#3182CE",
]


def short_name(name: str) -> str:
    """閻芝霖（北區） → 閻芝霖"""
    return re.sub(r"[（(].*?[）)]", "", name).strip() or name


# ── 簽章網址 ──

def _sign(year: int, gid: str, name: str) -> str:
    msg = f"{year}|{gid}|{name}".encode()
    return hmac.new(LINE_CHANNEL_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:20]


def verify(year: int, gid: str, name: str, sig: str) -> bool:
    return hmac.compare_digest(_sign(year, gid, name), sig or "")


def trend_chart_url(year: int, gid: str, name: str = "", preview: bool = False) -> str:
    params = {
        "year": year, "gid": gid, "name": name,
        "sig": _sign(year, gid, name),
        "v": int(time.time() // 60),   # LINE 會快取圖片，每分鐘換網址
    }
    if preview:
        params["preview"] = 1
    return f"{PUBLIC_BASE_URL.rstrip('/')}/chart/trend.png?{urlencode(params)}"


# ── 繪圖 ──

# 台股慣例：紅漲綠跌
UP = "#D62828"
DOWN = "#1B8A3A"
FLAT = "#A0AEC0"
MA_COLOR = "#D69E2E"
INK = "#1A365D"


def _fig(preview: bool, w: float, h: float, **kw):
    scale = 0.68 if preview else 1
    fig = plt.figure(figsize=(w * scale, h * scale), dpi=100 if preview else 150, **kw)
    fig.patch.set_facecolor("white")
    return fig


def _to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _empty_png(text: str, preview: bool) -> bytes:
    fig = _fig(preview, 10, 5)
    ax = fig.add_subplot()
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=18, transform=ax.transAxes, color="#718096")
    ax.set_axis_off()
    return _to_png(fig)


def _clean(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")


# ── /走勢：排名賽跑圖（bump chart）──

def render_rank_png(year: int, monthly_pnl: dict, last_month: int, preview: bool = False) -> bytes:
    """
    每月月底依「年度累計」排名，線條交叉＝超車。
    monthly_pnl = {name: [12 個月輸贏]}；只畫今年有上桌的人。
    """
    months = list(range(1, last_month + 1))
    cum = {}
    for name, vals in monthly_pnl.items():
        vals = vals[:last_month]
        if not any(vals):
            continue
        run, c = 0, []
        for v in vals:
            run += v
            c.append(run)
        cum[name] = c
    if not cum:
        return _empty_png(f"{year} 年尚無成員戰績", preview)

    names = list(cum)
    ranks = {n: [] for n in names}
    for mi in range(len(months)):
        order = sorted(names, key=lambda n: (-cum[n][mi], n))
        for r, n in enumerate(order, start=1):
            ranks[n].append(r)
    final_order = sorted(names, key=lambda n: ranks[n][-1])
    n_players = len(names)

    fig = _fig(preview, 13, 0.55 * n_players + 3)
    ax = fig.add_subplot()
    for idx, n in enumerate(final_order):
        color = PALETTE[idx % len(PALETTE)]
        ax.plot(months, ranks[n], color=color, linewidth=4, alpha=0.9, solid_capstyle="round", zorder=2)
        ax.scatter(months, ranks[n], s=110, color=color, edgecolor="white", linewidth=2, zorder=3)
        # 左側：1 月時的名字
        ax.text(months[0] - 0.25, ranks[n][0], short_name(n), ha="right", va="center", fontsize=12, color=color)
        # 右側：目前名次、名字、累計、與上月相比
        delta = ranks[n][-2] - ranks[n][-1] if len(months) > 1 else 0
        arrow = f"▲{delta}" if delta > 0 else (f"▼{-delta}" if delta < 0 else "—")
        arrow_color = UP if delta > 0 else (DOWN if delta < 0 else FLAT)
        ax.text(months[-1] + 0.25, ranks[n][-1], f"{short_name(n)}  {cum[n][-1]:+,}",
                ha="left", va="center", fontsize=12, color=color, fontweight="bold")
        ax.text(months[-1] + 2.05, ranks[n][-1], arrow, ha="left", va="center", fontsize=11, color=arrow_color)

    ax.set_ylim(n_players + 0.6, 0.4)
    ax.set_yticks(range(1, n_players + 1))
    ax.set_yticklabels([str(r) for r in range(1, n_players + 1)], fontsize=11, color="#718096")
    ax.set_xticks(months)
    ax.set_xticklabels([f"{m}月" for m in months], fontsize=12)
    ax.set_xlim(months[0] - 1.6, months[-1] + 2.6)
    ax.tick_params(length=0)
    for x in months:
        ax.axvline(x, color="#EDF2F7", linewidth=1, zorder=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(f"{year} 年排名賽跑", fontsize=19, pad=28, loc="left", color=INK, fontweight="bold")
    ax.text(0, 1.02, "每月月底依年度累計輸贏排名　·　線交叉＝超車　·　▲▼ 與上月比",
            transform=ax.transAxes, fontsize=11, color="#718096")
    fig.tight_layout()
    return _to_png(fig)


# ── /走勢 名字：半月K線 ──
# 每月切兩期：上半月 1–15 日、下半月 16 日～月底（31 天的月份即 15 + 16 天）

def half_month_index(month: int, day: int) -> int:
    """1 月上半 = 1、1 月下半 = 2、…、12 月下半 = 24"""
    return (month - 1) * 2 + (1 if day <= 15 else 2)


def period_label(p: int) -> str:
    return f"{(p + 1) // 2}月{'上' if p % 2 else '下'}"


def _half_month_candles(games: list[dict], last_period: int) -> list[dict | None]:
    """依每場累計算出每半月 開/高/低/收 與場數；沒打的期間為 None。"""
    by_period: dict = {}
    for g in games:
        p = half_month_index(int(g["date"][5:7]), int(g["date"][8:10]))
        by_period.setdefault(p, []).append(g["amount"])
    candles, run = [], 0
    for p in range(1, last_period + 1):
        amounts = by_period.get(p)
        if not amounts:
            candles.append(None)
            continue
        o, path = run, [run]
        for a in amounts:
            run += a
            path.append(run)
        candles.append({"open": o, "close": run, "high": max(path), "low": min(path), "games": len(amounts)})
    return candles


def render_kline_png(name: str, year: int, games: list[dict], last_period: int, preview: bool = False) -> bytes:
    candles = _half_month_candles(games, last_period)
    if not any(candles):
        return _empty_png(f"{short_name(name)} {year} 年尚無戰績", preview)
    periods = list(range(1, last_period + 1))
    last_month = (last_period + 1) // 2

    fig = _fig(preview, 13, 8)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.2, 1], hspace=0.08)
    ax = fig.add_subplot(gs[0])
    axv = fig.add_subplot(gs[1], sharex=ax)

    # 月份分隔線（上下半月之間不畫）
    for m in range(1, last_month):
        for a in (ax, axv):
            a.axvline(2 * m + 0.5, color="#E2E8F0", linewidth=1, zorder=0)

    closes, level = [], 0
    for p, c in zip(periods, candles):
        if c is None:
            ax.hlines(level, p - 0.3, p + 0.3, color=FLAT, linewidth=1.5, linestyles=(0, (2, 2)))
            closes.append(level)
            continue
        level = c["close"]
        closes.append(level)
        color = UP if c["close"] > c["open"] else (DOWN if c["close"] < c["open"] else FLAT)
        ax.vlines(p, c["low"], c["high"], color=color, linewidth=1.5, zorder=2)
        body_h = c["close"] - c["open"]
        ax.bar(p, body_h if body_h else 1, bottom=c["open"], width=0.62, color=color,
               edgecolor=color, linewidth=1.2, zorder=3)
        axv.bar(p, c["games"], width=0.62, color=color, alpha=0.75)
        axv.text(p, c["games"], str(c["games"]), ha="center", va="bottom", fontsize=8, color="#718096")

    # 6 期均線（約 3 個月）
    ma = [sum(closes[i - 5:i + 1]) / 6 if i >= 5 else None for i in range(len(closes))]
    ma_x = [p for p, v in zip(periods, ma) if v is not None]
    if ma_x:
        ax.plot(ma_x, [v for v in ma if v is not None], color=MA_COLOR, linewidth=2,
                label="MA6（6期≈3個月均線）", zorder=4)
        ax.legend(loc="upper left", frameon=False, fontsize=10)

    ax.axhline(0, color="#A0AEC0", linewidth=1, linestyle="--", zorder=1)

    # 標註年度最高 / 最低點
    real = [(p, c) for p, c in zip(periods, candles) if c]
    hp, hc = max(real, key=lambda x: x[1]["high"])
    lp, lc = min(real, key=lambda x: x[1]["low"])
    span = max(hc["high"] - lc["low"], 1)
    ax.annotate(f"最高 {hc['high']:+,}", (hp, hc["high"]), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=10, color=UP)
    ax.annotate(f"最低 {lc['low']:+,}", (lp, lc["low"]), xytext=(0, -16), textcoords="offset points",
                ha="center", fontsize=10, color=DOWN)
    ax.set_ylim(lc["low"] - span * 0.12, hc["high"] + span * 0.12)

    # 最新收盤
    last_close = closes[-1]
    ax.annotate(f"{last_close:+,}", (periods[-1] + 0.6, last_close), ha="left", va="center", fontsize=11,
                color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc=UP if last_close >= 0 else DOWN, ec="none"))

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:+,.0f}" if v else "0"))
    ax.grid(axis="y", color="#EDF2F7", linewidth=1)
    ax.tick_params(axis="x", labelbottom=False, length=0)
    _clean(ax)
    # X 軸：每根 K 棒標「上/下」，月份標在兩根中間
    axv.set_xticks(periods)
    axv.set_xticklabels(["上" if p % 2 else "下" for p in periods], fontsize=8, color="#A0AEC0")
    axv.tick_params(axis="x", length=0, pad=2)
    for m in range(1, last_month + 1):
        axv.text(2 * m - 0.5, -0.22, f"{m}月", transform=axv.get_xaxis_transform(),
                 ha="center", va="top", fontsize=11)
    axv.set_xlim(0.3, last_period + 1.6)
    axv.set_ylabel("場數", fontsize=10, color="#718096")
    axv.yaxis.set_major_locator(ticker.MaxNLocator(3, integer=True))
    axv.set_ylim(0, max(c["games"] for _, c in real) * 1.35)
    _clean(axv)

    up_n = sum(1 for _, c in real if c["close"] > c["open"])
    down_n = sum(1 for _, c in real if c["close"] < c["open"])
    best = max(real, key=lambda x: x[1]["close"] - x[1]["open"])
    ax.set_title(f"{short_name(name)}　{year} 年 半月K線", fontsize=19, pad=30, loc="left", color=INK, fontweight="bold")
    ax.text(0, 1.03, f"年度 {last_close:+,}　·　收紅 {up_n} 期 / 收綠 {down_n} 期　·　"
                     f"最強 {period_label(best[0])}半月 {best[1]['close'] - best[1]['open']:+,}　·　"
                     f"上半月 1–15 日、下半月 16 日～月底",
            transform=ax.transAxes, fontsize=11, color="#718096")
    fig.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.1)
    return _to_png(fig)
