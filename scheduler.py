"""
scheduler.py
每月最後一天 22:00（台灣時間）自動推播月結報告至所有設定的群組。
LINE_GROUP_ID 支援逗號分隔多個群組。
"""

import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi
from linebot.models import FlexSendMessage, TextSendMessage

from awards import calculate_monthly_awards
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_GROUP_ID
from flex_messages import awards_flex, leaderboard_flex
from sheets_client import get_player_monthly_stats

log = logging.getLogger(__name__)
TW_TZ = pytz.timezone("Asia/Taipei")


def _push_monthly_summary_for_group(api: LineBotApi, group_id: str, year: int, month: int) -> None:
    api.push_message(group_id, TextSendMessage(text=f"🀄 {month} 月戰績結算！以下是本月完整回顧 👇"))

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


def send_monthly_summary() -> None:
    group_ids = [g.strip() for g in LINE_GROUP_ID.split(",") if g.strip()]
    if not group_ids:
        log.warning("LINE_GROUP_ID 未設定，跳過月結推播。")
        return

    api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    now = datetime.now(TW_TZ)
    for gid in group_ids:
        try:
            _push_monthly_summary_for_group(api, gid, now.year, now.month)
            log.info(f"月結推播完成：{gid}")
        except Exception as e:
            log.error(f"推播失敗 {gid}: {e}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TW_TZ)
    scheduler.add_job(
        send_monthly_summary,
        trigger="cron",
        day="last",
        hour=22,
        minute=0,
        id="monthly_summary",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler 啟動：每月末 22:00 自動推播（支援多群組）。")
    return scheduler
