"""
main.py
FastAPI 應用程式入口。
啟動指令（本機）：uvicorn main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from linebot.exceptions import InvalidSignatureError

from line_handler import handler
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="🀄 麻將戰績 Bot")

# 啟動排程器
_scheduler = start_scheduler()


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
