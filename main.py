"""
main.py
FastAPI 應用程式入口。
啟動指令（本機）：uvicorn main:app --reload --port 8000
"""

import logging
import time
from datetime import datetime

import pytz
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from linebot.exceptions import InvalidSignatureError

from charts import render_trend_png, verify
from line_handler import handler
from sheets_client import get_all_members, get_members_monthly_pnl
from scheduler import send_monthly_summary, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="🀄 麻將戰績 Bot")

# 啟動排程器
_scheduler = start_scheduler()


@app.get("/webhook")
async def webhook_verify():
    """LINE Verify 用的 GET endpoint"""
    return PlainTextResponse("OK")


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        log.error(f"Webhook 處理錯誤: {e}", exc_info=True)
        # 回 200 避免 Line 重送
    return PlainTextResponse("OK")


@app.get("/")
def root():
    return {"status": "running", "service": "麻將戰績 Bot 🀄"}


@app.get("/ping")
def ping():
    """Render.com keep-alive 或健康檢查"""
    return "pong"


@app.post("/cron/monthly")
def cron_monthly():
    """GitHub Actions 每月 1 號呼叫：推播上個月月結＆頒獎（已推過的月份會自動跳過）"""
    return send_monthly_summary()


_chart_cache: dict = {}
CHART_CACHE_TTL = 300


@app.get("/chart/trend.png")
def chart_trend(year: int, gid: str = "", name: str = "", sig: str = "", preview: int = 0):
    """成員累計損益折線圖（網址需帶 line_handler 產生的簽章）"""
    if not verify(year, gid, name, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    key = (year, gid, name, bool(preview))
    hit = _chart_cache.get(key)
    if hit and time.time() - hit[0] < CHART_CACHE_TTL:
        return Response(hit[1], media_type="image/png")

    now = datetime.now(pytz.timezone("Asia/Taipei"))
    last_month = now.month if year == now.year else 12
    names = [name] if name else get_all_members()
    png = render_trend_png(year, get_members_monthly_pnl(year, gid, names), last_month, bool(preview))
    _chart_cache[key] = (time.time(), png)
    return Response(png, media_type="image/png")
