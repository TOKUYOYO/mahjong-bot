"""
sheets_client.py
Google Sheets 讀寫封裝。

sessions 工作表欄位（22 欄）：
  session_id | date | group_id |
  p1_name | p1_amount | p1_wind | p1_zimo |
  p2_name | p2_amount | p2_wind | p2_zimo |
  p3_name | p3_amount | p3_wind | p3_zimo |
  p4_name | p4_amount | p4_wind | p4_zimo |
  recorded_by | created_at

members 工作表欄位（3 欄）：
  name | line_user_id | joined_date
"""

import json
import time
import uuid
import logging
from datetime import datetime

import gspread
import pytz
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_JSON, SPREADSHEET_ID, SHEET_MEMBERS, SHEET_SESSIONS

log = logging.getLogger(__name__)
TW_TZ = pytz.timezone("Asia/Taipei")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── 快取 ──
_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 300


def _get_cache(key: str):
    if key in _cache and time.time() - _cache_ts.get(key, 0) < CACHE_TTL:
        return _cache[key]
    return None


def _set_cache(key: str, value):
    _cache[key] = value
    _cache_ts[key] = time.time()


def _bust_cache(key: str):
    _cache.pop(key, None)
    _cache_ts.pop(key, None)


# ── 連線 ──

def _get_client():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet(sheet_name: str):
    client = _get_client()
    return client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)


# ── Members ──

def get_all_members() -> list[str]:
    cached = _get_cache("members")
    if cached is not None:
        return cached
    sheet = _get_sheet(SHEET_MEMBERS)
    records = sheet.get_all_records()
    names = [r["name"] for r in records if r.get("name")]
    _set_cache("members", names)
    return names


def get_member_name_by_user_id(user_id: str) -> str | None:
    cached = _get_cache("members_full")
    if cached is None:
        sheet = _get_sheet(SHEET_MEMBERS)
        cached = sheet.get_all_records()
        _set_cache("members_full", cached)
    for r in cached:
        if r.get("line_user_id") == user_id:
            return r.get("name")
    return None


def get_member_avatar(name: str) -> str:
    """取得某成員的 avatar_url，沒有則回傳空字串。"""
    cached = _get_cache("members_full")
    if cached is None:
        sheet = _get_sheet(SHEET_MEMBERS)
        cached = sheet.get_all_records()
        _set_cache("members_full", cached)
    for r in cached:
        if str(r.get("name", "")).strip() == name:
            return str(r.get("avatar_url", "")).strip()
    return ""


def register_member(name: str, line_user_id: str) -> bool:
    sheet = _get_sheet(SHEET_MEMBERS)
    records = sheet.get_all_records()
    name = name.strip()
    if not name:
        return False
    for r in records:
        if r.get("name") == name:
            return False
    today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    sheet.append_row([name, line_user_id, today])
    _bust_cache("members")
    _bust_cache("members_full")
    return True


# ── Sessions：寫入 ──

def add_session(players: list[dict], recorded_by: str, group_id: str = "") -> str:
    """
    players = [
        {"name": "小明", "amount": 500, "wind": "東", "zimo": 0},
        {"name": "小花", "amount": -200, "wind": "南", "zimo": 1},
        {"name": "大頭", "amount": 300, "wind": "西", "zimo": 0},
        {"name": "阿杰", "amount": -600, "wind": "北", "zimo": 2},
    ]
    """
    sheet = _get_sheet(SHEET_SESSIONS)
    session_id = str(uuid.uuid4())[:8].upper()
    date = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    created_at = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")

    row = [session_id, date, group_id]
    for p in players:
        row += [
            p["name"],
            p["amount"],
            p.get("wind", ""),
            p.get("zimo", 0),
        ]
    row += [recorded_by, created_at]

    sheet.append_row(row)
    _bust_cache("sessions")
    log.info(f"Session {session_id} recorded by {recorded_by} in group {group_id}")
    return session_id


# ── Sessions：讀取 ──

def _get_all_sessions() -> list[dict]:
    cached = _get_cache("sessions")
    if cached is not None:
        return cached
    sheet = _get_sheet(SHEET_SESSIONS)
    records = sheet.get_all_records()
    _set_cache("sessions", records)
    return records


def get_monthly_sessions(year: int, month: int, group_id: str = "") -> list[dict]:
    all_sessions = _get_all_sessions()
    prefix = f"{year:04d}-{month:02d}"
    result = [s for s in all_sessions if str(s.get("date", "")).startswith(prefix)]
    if group_id:
        result = [s for s in result if str(s.get("group_id", "")) == group_id]
    return result


def get_player_monthly_stats(year: int, month: int, group_id: str = "") -> dict:
    """
    回傳：
    {name: {"total": int, "sessions": int, "wins": int, "losses": int, "zimo": int}}
    """
    sessions = get_monthly_sessions(year, month, group_id)
    stats: dict = {}
    for s in sessions:
        for i in range(1, 5):
            name = str(s.get(f"p{i}_name", "")).strip()
            if not name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except (ValueError, TypeError):
                amount = 0
            try:
                zimo = int(s.get(f"p{i}_zimo", 0) or 0)
            except (ValueError, TypeError):
                zimo = 0

            stats.setdefault(name, {"total": 0, "sessions": 0, "wins": 0, "losses": 0, "zimo": 0})
            stats[name]["total"] += amount
            stats[name]["sessions"] += 1
            stats[name]["zimo"] += zimo
            if amount > 0:
                stats[name]["wins"] += 1
            elif amount < 0:
                stats[name]["losses"] += 1
    return stats


def get_yearly_stats(player_name: str, group_id: str, year: int) -> dict:
    """年度累計統計"""
    all_sessions = _get_all_sessions()
    prefix = f"{year:04d}-"
    stats = {"total": 0, "sessions": 0, "wins": 0, "losses": 0, "zimo": 0}
    for s in all_sessions:
        if not str(s.get("date", "")).startswith(prefix):
            continue
        if group_id and str(s.get("group_id", "")) != group_id:
            continue
        for i in range(1, 5):
            if str(s.get(f"p{i}_name", "")).strip() != player_name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except:
                amount = 0
            try:
                zimo = int(s.get(f"p{i}_zimo", 0) or 0)
            except:
                zimo = 0
            stats["total"] += amount
            stats["sessions"] += 1
            stats["zimo"] += zimo
            if amount > 0:
                stats["wins"] += 1
            elif amount < 0:
                stats["losses"] += 1
    return stats


def get_last_n_sessions(player_name: str, group_id: str, n: int = 5) -> list[dict]:
    """最近 N 場（依日期倒序）"""
    all_sessions = _get_all_sessions()
    player_sessions = []
    for s in all_sessions:
        if group_id and str(s.get("group_id", "")) != group_id:
            continue
        for i in range(1, 5):
            if str(s.get(f"p{i}_name", "")).strip() != player_name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except:
                amount = 0
            try:
                zimo = int(s.get(f"p{i}_zimo", 0) or 0)
            except:
                zimo = 0
            player_sessions.append({
                "date": s.get("date", ""),
                "amount": amount,
                "wind": str(s.get(f"p{i}_wind", "")).strip(),
                "zimo": zimo,
                "session_id": s.get("session_id", ""),
            })
    player_sessions.sort(key=lambda x: x["date"], reverse=True)
    return player_sessions[:n]


def get_matchup_stats(player_name: str, group_id: str, recent_n: int = 50) -> dict:
    """
    比例分攤法估算「你與每位對手的淨輸贏」，每位對手僅取最近同桌 recent_n 場。

    每場把輸家的錢，按各贏家贏額比例分攤給贏家，
    估出該場「某對手付給你」或「你付給某對手」的金額；
    再對每位對手，依日期取最近 recent_n 場同桌紀錄加總。

    回傳：{co_player: {"sessions": N, "net": float}}
      sessions = 取用的最近同桌場數（最多 recent_n）
      net > 0 → 對手淨付錢給你（你贏他）→ 贊助商方向
      net < 0 → 你淨付錢給對手（你輸他）→ 我有欠你嗎方向

    門檻：同桌 10 場以上才納入計算（在 line_handler.py 過濾）。
    註：此為依淨輸贏的估算，非實際金流（未記放炮/自摸明細）。
    """
    all_sessions = _get_all_sessions()
    # 每位對手收集 (date, 單場淨額貢獻) 清單
    per_co: dict = {}

    for s in all_sessions:
        if group_id and str(s.get("group_id", "")) != group_id:
            continue

        players_in_session: dict = {}
        for i in range(1, 5):
            name = str(s.get(f"p{i}_name", "")).strip()
            if not name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except (ValueError, TypeError):
                amount = 0
            players_in_session[name] = amount

        if player_name not in players_in_session:
            continue

        date = str(s.get("date", ""))
        a_amount = players_in_session[player_name]
        winners = {n: v for n, v in players_in_session.items() if v > 0}
        losers = {n: v for n, v in players_in_session.items() if v < 0}
        total_win = sum(winners.values())

        # 該場每位對手的淨額貢獻（預設 0）
        contrib: dict = {co: 0.0 for co in players_in_session if co != player_name}

        if total_win > 0:
            if a_amount > 0:
                for ln, la in losers.items():
                    contrib[ln] = (-la) * (a_amount / total_win)
            elif a_amount < 0:
                for wn, wa in winners.items():
                    contrib[wn] = -((-a_amount) * (wa / total_win))

        for co, val in contrib.items():
            per_co.setdefault(co, []).append((date, val))

    # 對每位對手取最近 recent_n 場加總
    matchups: dict = {}
    for co, recs in per_co.items():
        recs.sort(key=lambda x: x[0])      # 依日期升冪
        recent = recs[-recent_n:]          # 取最近 recent_n 場
        net = sum(v for _, v in recent)
        matchups[co] = {"sessions": len(recent), "net": round(net, 0)}

    return matchups

def get_player_wind_stats(player_name: str, group_id: str) -> dict:
    """
    各風位下的平均 P&L。
    回傳：{"東": {"sessions": N, "total": int, "avg": float}, ...}
    """
    all_sessions = _get_all_sessions()
    wind_stats: dict = {}
    for s in all_sessions:
        if group_id and str(s.get("group_id", "")) != group_id:
            continue
        for i in range(1, 5):
            if str(s.get(f"p{i}_name", "")).strip() != player_name:
                continue
            wind = str(s.get(f"p{i}_wind", "")).strip()
            if not wind:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except:
                amount = 0
            wind_stats.setdefault(wind, {"sessions": 0, "total": 0})
            wind_stats[wind]["sessions"] += 1
            wind_stats[wind]["total"] += amount

    for w in wind_stats:
        n = wind_stats[w]["sessions"]
        wind_stats[w]["avg"] = round(wind_stats[w]["total"] / n, 0) if n > 0 else 0.0

    return wind_stats


def get_best_single_session(player_name: str, group_id: str) -> dict | None:
    """
    生涯最佳單場（贏最多的那一場）。
    回傳：{"date": str, "amount": int, "wind": str, "session_id": str} 或 None
    """
    all_sessions = _get_all_sessions()
    best = None
    for s in all_sessions:
        if group_id and str(s.get("group_id", "")) != group_id:
            continue
        for i in range(1, 5):
            if str(s.get(f"p{i}_name", "")).strip() != player_name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except:
                amount = 0
            if best is None or amount > best["amount"]:
                best = {
                    "date": str(s.get("date", "")),
                    "amount": amount,
                    "wind": str(s.get(f"p{i}_wind", "")).strip(),
                    "session_id": str(s.get("session_id", "")),
                }
    return best


def get_yearly_leaderboard(year: int, group_id: str = "") -> dict:
    """
    年度排行榜：該年所有場次的累計輸贏。
    回傳：{name: {"total": int, "sessions": int, "wins": int, "losses": int, "zimo": int}}
    """
    all_sessions = _get_all_sessions()
    prefix = f"{year:04d}-"
    stats: dict = {}
    for s in all_sessions:
        if not str(s.get("date", "")).startswith(prefix):
            continue
        if group_id and str(s.get("group_id", "")) != group_id:
            continue
        for i in range(1, 5):
            name = str(s.get(f"p{i}_name", "")).strip()
            if not name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except (ValueError, TypeError):
                amount = 0
            try:
                zimo = int(s.get(f"p{i}_zimo", 0) or 0)
            except (ValueError, TypeError):
                zimo = 0
            stats.setdefault(name, {"total": 0, "sessions": 0, "wins": 0, "losses": 0, "zimo": 0})
            stats[name]["total"] += amount
            stats[name]["sessions"] += 1
            stats[name]["zimo"] += zimo
            if amount > 0:
                stats[name]["wins"] += 1
            elif amount < 0:
                stats[name]["losses"] += 1
    return stats


def get_player_monthly_breakdown(player_name: str, group_id: str, year: int) -> list[dict]:
    """
    個人逐月明細（供個人頁面用）。
    回傳：[{"month": int, "total": int, "sessions": int}, ...]，只含有資料的月份。
    """
    result = []
    for m in range(1, 13):
        stats = get_player_monthly_stats(year, m, group_id)
        data = stats.get(player_name)
        if data:
            result.append({"month": m, "total": data["total"], "sessions": data["sessions"]})
    return result
