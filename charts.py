"""
charts.py
成員損益折線圖（PNG），由 main.py 的 /chart/trend.png 提供給 LINE 圖片訊息使用。

X 軸為月份，Y 軸為年度「累計」輸贏；只畫 members 名單內的成員。
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

def render_trend_png(year: int, monthly_pnl: dict, last_month: int, preview: bool = False) -> bytes:
    """
    monthly_pnl = {name: [12 個月輸贏]}
    last_month  = 畫到幾月（今年畫到本月，過去年份畫到 12 月）
    """
    months = list(range(1, last_month + 1))
    # 依年度累計高到低排序，圖例順序與排名一致
    series = []
    for name, vals in monthly_pnl.items():
        vals = vals[:last_month]
        if not any(vals):
            continue
        cum, run = [], 0
        for v in vals:
            run += v
            cum.append(run)
        series.append((name, cum))
    series.sort(key=lambda x: x[1][-1], reverse=True)

    w, h = (8, 5) if preview else (12, 7.5)
    fig, ax = plt.subplots(figsize=(w, h), dpi=100 if preview else 150)
    fig.patch.set_facecolor("white")

    if not series:
        ax.text(0.5, 0.5, f"{year} 年尚無成員戰績", ha="center", va="center", fontsize=18,
                transform=ax.transAxes, color="#718096")
        ax.set_axis_off()
    else:
        for idx, (name, cum) in enumerate(series):
            color = PALETTE[idx % len(PALETTE)]
            label = f"{short_name(name)}  {cum[-1]:+,}"
            ax.plot(months, cum, marker="o", markersize=4, linewidth=2.2, color=color, label=label)

        ax.axhline(0, color="#A0AEC0", linewidth=1, zorder=0)
        ax.set_xticks(months)
        ax.set_xticklabels([f"{m}月" for m in months], fontsize=11)
        ax.set_xlim(0.7, last_month + 0.3)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:+,.0f}" if v else "0"))
        ax.tick_params(axis="y", labelsize=11)
        ax.grid(axis="y", color="#EDF2F7", linewidth=1)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=11,
                  title="年度累計", title_fontsize=11)

    title = f"{year} 年成員累計損益" if len(series) != 1 else f"{short_name(series[0][0])} {year} 年累計損益"
    ax.set_title(title, fontsize=17, pad=14, loc="left", color="#1A365D")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    return buf.getvalue()
