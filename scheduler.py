"""
scheduler.py
每月 1 號 12:00（台灣時間）自動推播「上個月」的月結報告與頒獎至所有設定的群組。
LINE_GROUP_ID 支援逗號分隔多個群組。

觸發來源有兩個（互為備援）：
  1. 本程式內的 APScheduler（服務醒著才會跑）
  2. GitHub Actions 每月 1 號呼叫 POST /cron/monthly（會先把 Render 叫醒）
每個群組推播成功後會在 Google Sheets 的 meta 工作表記下月份，同一個月不會重複推播。
"""

import logging
import threading
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi
from linebot.models import FlexSendMessage, TextSendMessage

from awards import calculate_monthly_awards
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_GROUP_ID
from flex_messages import awards_flex, leaderboard_flex
from sheets_client import get_meta, get_player_monthly_stats, set_meta

log = logging.getLogger(__name__)
TW_TZ = pytz.timezone("Asia/Taipei")
_lock = threading.Lock()


def _push_monthly_summary_for_group(api: LineBotApi, group_id: str, year: int, month: int) -> None:
    api.push_message(group_id, TextSendMessage(text=f"🀄 {year}年{month}月戰績結算＆頒獎！以下是上個月完整回顧 👇"))

    stats = get_player_monthly_stats(year, month, group_id)
    if not stats:
        api.push_message(group_id, TextSendMessage(text=f"📊 {month} 月無任何場次記錄。"))
        return

    api.push_message(group_id, FlexSendMessage(
        alt_text=f"{month}月戰績排行",
        contents=leaderboard_flex(stats, year, month),
    ))

    awards = calculate_monthly_awards(year, month, group_id)
    if awards:
        api.push_message(group_id, FlexSendMessage(
            alt_text=f"{month}月英雄榜",
            contents=awards_flex(awards, year, month),
        ))
    else:
        api.push_message(group_id, TextSendMessage(text=f"🎖 {month} 月資料不足，無法頒獎。"))


def send_monthly_summary() -> dict:
    """推播上個月月結；已推播過的群組會跳過。回傳 {group_id: 狀態}。"""
    group_ids = [g.strip() for g in LINE_GROUP_ID.split(",") if g.strip()]
    if not group_ids:
        log.warning("LINE_GROUP_ID 未設定，跳過月結推播。")
        return {}

    api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    # 1 號執行 → 結算上個月
    now = datetime.now(TW_TZ)
    year, month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
    period = f"{year}-{month:02d}"
    result = {}
    with _lock:
        for gid in group_ids:
            key = f"awarded:{gid}"
            try:
                if get_meta(key) == period:
                    result[gid] = "already_sent"
                    continue
                _push_monthly_summary_for_group(api, gid, year, month)
                set_meta(key, period)
                result[gid] = "sent"
                log.info(f"月結推播完成：{gid} {period}")
            except Exception as e:
                result[gid] = "error"
                log.error(f"推播失敗 {gid}: {e}")
    return result


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TW_TZ)
    scheduler.add_job(
        send_monthly_summary,
        trigger="cron",
        day=1,
        hour=12,
        minute=0,
        id="monthly_summary",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler 啟動：每月 1 號 12:00 自動推播上月月結＆頒獎（支援多群組）。")
    return scheduler
