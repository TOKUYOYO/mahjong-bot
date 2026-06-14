"""
line_handler.py
Line Webhook 事件處理。

記帳完整流程（精簡版）：
  /記帳 → 選人 → 輸金額 → 風位選人（選完後立即詢問該玩家自摸次數）→ 確認 → 儲存

  精簡重點：原本「風位全選完 → 再逐一詢問自摸」現改為「選完某人風位，立刻問他自摸幾次」，
  交替進行直到四人完畢，省去一整輪來回。
"""

import logging
from datetime import datetime

import pytz
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    FlexSendMessage, MessageEvent, PostbackEvent,
    QuickReply, QuickReplyButton, PostbackAction,
    TextMessage, TextSendMessage,
)

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from awards import calculate_monthly_awards
from flex_messages import (
    awards_flex, confirmation_flex, leaderboard_flex,
    monthly_trend_flex, personal_stats_flex, player_profile_flex,
    player_selection_flex, wind_selection_flex, yearly_leaderboard_flex,
)
from sheets_client import (
    add_session, get_all_members, get_matchup_stats,
    get_member_name_by_user_id, get_last_n_sessions,
    get_player_monthly_stats, get_yearly_stats,
    get_player_wind_stats, register_member, get_member_avatar,
    get_best_single_session, get_yearly_leaderboard,
    get_player_monthly_breakdown,
)
from state_manager import WIND_ORDER, RecordState, clear_state, create_state, get_state

log = logging.getLogger(__name__)
TW_TZ = pytz.timezone("Asia/Taipei")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

MIN_MATCHUP_SESSIONS = 10   # 我有欠你嗎/贊助商 最低同桌場次門檻


# ──────────────────────────────────────
# 工具
# ──────────────────────────────────────

def _get_group_id(event) -> str:
    return getattr(event.source, "group_id", "")


def _get_display_name(event) -> str:
    uid = event.source.user_id
    try:
        gid = _get_group_id(event)
        if gid:
            profile = line_bot_api.get_group_member_profile(gid, uid)
        else:
            profile = line_bot_api.get_profile(uid)
        return profile.display_name
    except Exception as e:
        log.warning(f"Cannot get display name for {uid}: {e}")
        return "玩家"


def _reply_text(reply_token: str, text: str) -> None:
    line_bot_api.reply_message(reply_token, TextSendMessage(text=text))


def _reply_flex(reply_token: str, alt_text: str, flex_dict: dict) -> None:
    line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text=alt_text, contents=flex_dict))


def _reply_zimo_prompt(reply_token: str, player_name: str, push_to: str = "") -> None:
    """詢問指定玩家自摸次數（附快速回覆）
    push_to: 若有提供 group_id 或 user_id，改用 push_message（reply_token 已被消耗時使用）
    """
    msg = TextSendMessage(
        text=f"⚡ {player_name} 這場自摸幾次？",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=PostbackAction(
                label=f"{n}次",
                data=f"action=set_zimo&count={n}",
                display_text=f"{player_name} 自摸 {n} 次",
            ))
            for n in range(6)
        ]),
    )
    if push_to:
        line_bot_api.push_message(push_to, msg)
    else:
        line_bot_api.reply_message(reply_token, msg)


# ──────────────────────────────────────
# 各指令處理
# ──────────────────────────────────────

def _start_record(event, user_id: str) -> None:
    clear_state(user_id)
    members = get_all_members()
    if not members:
        _reply_text(event.reply_token, "⚠️ 尚未有任何成員！\n請先用 /加入 <名字> 加入成員清單。")
        return
    create_state(user_id)
    _reply_flex(event.reply_token, "選擇第 1 位玩家", player_selection_flex(members, [], 1))


def _show_rank(event, year: int | None = None, month: int | None = None) -> None:
    now = datetime.now(TW_TZ)
    year = year or now.year
    month = month or now.month
    gid = _get_group_id(event)
    stats = get_player_monthly_stats(year, month, gid)
    if not stats:
        _reply_text(event.reply_token, f"📊 {year}年{month}月尚無戰績記錄！")
        return
    _reply_flex(event.reply_token, f"{year}年{month}月戰績排行", leaderboard_flex(stats, year, month))


def _show_yearly_rank(event, year: int | None = None) -> None:
    now = datetime.now(TW_TZ)
    year = year or now.year
    gid = _get_group_id(event)
    stats = get_yearly_leaderboard(year, gid)
    # 場次少於 5 場的不列入
    stats = {k: v for k, v in stats.items() if v["sessions"] >= 5}
    if not stats:
        _reply_text(event.reply_token, f"📊 {year}年尚無戰績記錄！")
        return
    _reply_flex(event.reply_token, f"{year}年度排行", yearly_leaderboard_flex(stats, year))


def _show_monthly_trend(event, query_name: str, year: int | None = None) -> None:
    now = datetime.now(TW_TZ)
    year = year or now.year
    gid = _get_group_id(event)
    monthly_data = get_player_monthly_breakdown(query_name, gid, year)
    if not monthly_data:
        _reply_text(event.reply_token, f"📊 {query_name} 在 {year} 年尚無戰績記錄！")
        return
    _reply_flex(
        event.reply_token,
        f"{query_name} {year}年逐月",
        monthly_trend_flex(query_name, year, monthly_data),
    )


def _show_awards(event) -> None:
    now = datetime.now(TW_TZ)
    gid = _get_group_id(event)
    awards = calculate_monthly_awards(now.year, now.month, gid)
    if not awards:
        _reply_text(event.reply_token, f"🎖 {now.month} 月資料還不夠，無法頒獎！")
        return
    _reply_flex(event.reply_token, f"{now.month}月英雄榜", awards_flex(awards, now.year, now.month))


def _show_personal_stats(event, user_id: str) -> None:
    now = datetime.now(TW_TZ)
    gid = _get_group_id(event)
    name = get_member_name_by_user_id(user_id)
    if not name:
        _reply_text(event.reply_token, "找不到你的記錄。\n請先用 /加入 <名字> 加入成員清單。")
        return
    stats = get_player_monthly_stats(now.year, now.month, gid)
    data = stats.get(name)
    if not data:
        _reply_text(event.reply_token, f"{name} 本月還沒有任何場次紀錄。")
        return
    _reply_flex(
        event.reply_token,
        f"{name} 本月戰績",
        personal_stats_flex(name, data, now.year, now.month),
    )


def _show_player_profile(event, query_name: str) -> None:
    now = datetime.now(TW_TZ)
    gid = _get_group_id(event)

    # 月度
    monthly_stats = get_player_monthly_stats(now.year, now.month, gid)
    monthly = monthly_stats.get(query_name, {"total": 0, "sessions": 0, "wins": 0, "losses": 0, "zimo": 0})

    # 年度
    yearly = get_yearly_stats(query_name, gid, now.year)

    # 最近 5 場
    last5 = get_last_n_sessions(query_name, gid, 5)

    # 生涯最佳單場
    best_session = get_best_single_session(query_name, gid)

    # 我有欠你嗎 / 贊助商（最近50場，同桌10場門檻，只納入 members）
    matchups = get_matchup_stats(query_name, gid)
    members_set = set(get_all_members())
    valid = {
        k: v for k, v in matchups.items()
        if v["sessions"] >= MIN_MATCHUP_SESSIONS and k in members_set
    }
    debtor = min(valid, key=lambda x: valid[x]["net"], default=None) if valid else None
    sponsor = max(valid, key=lambda x: valid[x]["net"], default=None) if valid else None

    # 擅長風位
    wind_stats = get_player_wind_stats(query_name, gid)
    valid_winds = {w: v for w, v in wind_stats.items() if v["sessions"] >= 3}
    best_wind = max(valid_winds, key=lambda w: valid_winds[w]["avg"], default=None)

    # 逐月（今年）
    monthly_breakdown = get_player_monthly_breakdown(query_name, gid, now.year)

    profile_data = {
        "name": query_name,
        "avatar_url": get_member_avatar(query_name),
        "month_total": monthly["total"],
        "year_total": yearly["total"],
        "month_sessions": monthly["sessions"],
        "month_zimo": monthly["zimo"],
        "last5": [s["amount"] for s in last5] if last5 else [],
        "best_session": best_session,
        "debtor": debtor,
        "debtor_net": valid[debtor]["net"] if debtor else 0,
        "sponsor": sponsor,
        "sponsor_net": valid[sponsor]["net"] if sponsor else 0,
        "best_wind": best_wind,
        "best_wind_avg": valid_winds[best_wind]["avg"] if best_wind else 0,
        "best_wind_sessions": valid_winds[best_wind]["sessions"] if best_wind else 0,
        "monthly_breakdown": monthly_breakdown,
    }
    _reply_flex(event.reply_token, f"{query_name} 個人頁面", player_profile_flex(profile_data))


def _join_member(event, user_id: str, name_override: str | None) -> None:
    display_name = _get_display_name(event)
    name = name_override.strip() if name_override else display_name
    if not name:
        _reply_text(event.reply_token, "請輸入名字，例如：/加入 小明")
        return
    if register_member(name, user_id):
        _reply_text(event.reply_token, f"✅ {name} 已加入麻將群！🀄")
    else:
        _reply_text(event.reply_token, f"⚠️ {name} 已在成員清單中。")


def _show_help(event) -> None:
    _reply_text(event.reply_token, (
        "🀄 麻將戰績 Bot 指令\n────────────────────\n"
        "/記帳　　　　開始記錄本場戰績\n"
        "/排行　　　　本月積分排行\n"
        "/排行 3　　　查本年3月排行\n"
        "/排行 2025 3　查指定年月排行\n"
        "/年排行　　　今年年度排行\n"
        "/年排行 2025　查指定年度排行\n"
        "/逐月 [名字]　個人逐月戰績\n"
        "/頒獎　　　　本月英雄榜\n"
        "/我的戰績　　個人本月統計\n"
        "/查 [名字]　　查詢玩家個人頁面\n"
        "/加入 [名字]　加入成員清單\n"
        "/取消　　　　取消目前操作\n"
        "/說明　　　　顯示此說明"
    ))


# ──────────────────────────────────────
# 狀態機：金額 → 風位+自摸交替
# ──────────────────────────────────────

def _handle_amount_input(event, user_id: str, text: str, state: RecordState) -> None:
    try:
        amount = int(text.replace(",", "").replace("，", "").replace(" ", ""))
    except ValueError:
        player_name = state.selected_players[state.amount_idx]
        _reply_text(event.reply_token, f"格式不對！請輸入數字，例如 +500 或 -300\n（目前輸入 {player_name} 的金額）")
        return

    state.amounts.append(amount)
    state.amount_idx += 1

    if state.amount_idx >= len(state.selected_players) - 1:
        # 自動計算第 4 位
        state.amounts.append(-sum(state.amounts))
        # 進入風位分配（wind_idx 追蹤已分配幾個風位）
        state.step = "assign_winds"
        state.winds = {}
        state.wind_idx = 0
        state.zimos = [0, 0, 0, 0]
        state.pending_zimo_player = ""
        _reply_flex(event.reply_token, "東風是誰？",
                    wind_selection_flex(state.selected_players, state.winds, 0))
    else:
        next_name = state.selected_players[state.amount_idx]
        is_last_manual = (state.amount_idx == len(state.selected_players) - 2)
        hint = "（輸入後將自動計算最後一位玩家的金額）\n" if is_last_manual else ""
        _reply_text(event.reply_token,
                    f"📝 {next_name}（第 {state.amount_idx+1} 位）的輸贏金額？\n{hint}格式：+500 或 -300")


def _handle_visitor_name(event, user_id: str, text: str, state: RecordState) -> None:
    visitor_name = text.strip()
    if not visitor_name or len(visitor_name) > 10:
        _reply_text(event.reply_token, "名字太長或為空，請重新輸入（最多 10 字）")
        return
    state.selected_players.append(visitor_name)
    if len(state.selected_players) >= 4:
        _transition_to_amounts(event, user_id, state)
    else:
        state.step = "select_players"
        members = get_all_members()
        step_num = len(state.selected_players) + 1
        _reply_flex(event.reply_token, f"選擇第 {step_num} 位玩家",
                    player_selection_flex(members, state.selected_players, step_num))


def _transition_to_amounts(event, user_id: str, state: RecordState) -> None:
    state.step = "enter_amounts"
    state.amounts = []
    state.amount_idx = 0
    first_name = state.selected_players[0]
    players_text = "、".join(state.selected_players)
    _reply_text(event.reply_token,
                f"✅ 本場玩家：{players_text}\n\n📝 {first_name}（第 1 位）的輸贏金額？\n格式：+500 或 -300")


# ──────────────────────────────────────
# Postback 處理
# ──────────────────────────────────────

def _parse_postback(data: str) -> dict:
    return {k: v for k, v in (p.split("=", 1) for p in data.split("&") if "=" in p)}


@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    params = _parse_postback(event.postback.data)
    action = params.get("action")
    state = get_state(user_id)

    # ── 選人 ──
    if action == "select_player":
        if not state:
            _reply_text(event.reply_token, "操作逾時，請重新 /記帳")
            return
        state.selected_players.append(params.get("player", ""))
        if len(state.selected_players) >= 4:
            _transition_to_amounts(event, user_id, state)
        else:
            members = get_all_members()
            step_num = len(state.selected_players) + 1
            _reply_flex(event.reply_token, f"選擇第 {step_num} 位玩家",
                        player_selection_flex(members, state.selected_players, step_num))

    elif action == "add_visitor":
        if not state:
            _reply_text(event.reply_token, "操作逾時，請重新 /記帳")
            return
        state.step = "enter_visitor_name"
        _reply_text(event.reply_token, "請輸入訪客名字（不會存入成員清單）：")

    # ── 風位分配：選完後立即詢問自摸 ──
    elif action == "assign_wind":
        if not state or state.step != "assign_winds":
            _reply_text(event.reply_token, "操作逾時，請重新 /記帳")
            return
        wind = params.get("wind", "")
        player = params.get("player", "")
        state.winds[player] = wind
        state.pending_zimo_player = player
        state.step = "enter_zimo_after_wind"
        # reply_token 已被 postback 消耗，改用 push
        push_target = _get_group_id(event) or event.source.user_id
        _reply_zimo_prompt(event.reply_token, player, push_to=push_target)

    # ── 自摸次數（每選完一個風位後立即收，最後一人亦同）──
    elif action == "set_zimo":
        if not state or state.step not in {"enter_zimo_after_wind", "enter_last_zimo"}:
            _reply_text(event.reply_token, "操作逾時，請重新 /記帳")
            return
        try:
            count = int(params.get("count", 0))
        except ValueError:
            count = 0

        # 存入對應玩家的自摸
        player = state.pending_zimo_player
        if player in state.selected_players:
            idx = state.selected_players.index(player)
            state.zimos[idx] = count

        if state.step == "enter_last_zimo":
            # 四人風位+自摸全部收齊 → 確認卡
            state.step = "confirming"
            players = [
                {
                    "name": state.selected_players[i],
                    "amount": state.amounts[i],
                    "wind": state.winds.get(state.selected_players[i], ""),
                    "zimo": state.zimos[i],
                }
                for i in range(4)
            ]
            _reply_flex(event.reply_token, "確認本場記錄", confirmation_flex(players))
        else:
            # enter_zimo_after_wind：前三人
            state.wind_idx += 1
            if state.wind_idx >= 3:
                # 自動分配最後一個風位，再問最後一人自摸
                last_player = next(p for p in state.selected_players if p not in state.winds)
                state.winds[last_player] = WIND_ORDER[3]
                state.pending_zimo_player = last_player
                state.step = "enter_last_zimo"
                push_target = _get_group_id(event) or event.source.user_id
                _reply_zimo_prompt(event.reply_token, last_player, push_to=push_target)
            else:
                # 繼續下一個風位
                state.step = "assign_winds"
                _reply_flex(event.reply_token, f"{WIND_ORDER[state.wind_idx]}風是誰？",
                            wind_selection_flex(state.selected_players, state.winds, state.wind_idx))

    # ── 確認儲存 ──
    elif action == "confirm_record":
        if not state or state.step != "confirming":
            _reply_text(event.reply_token, "操作逾時，請重新 /記帳")
            return
        players = [
            {
                "name": state.selected_players[i],
                "amount": state.amounts[i],
                "wind": state.winds.get(state.selected_players[i], ""),
                "zimo": state.zimos[i] if i < len(state.zimos) else 0,
            }
            for i in range(4)
        ]
        display_name = _get_display_name(event)
        gid = _get_group_id(event)
        session_id = add_session(players, display_name, gid)
        clear_state(user_id)

        lines = [f"✅ 本場記錄完成！ #{session_id}"]
        for p in players:
            a = p["amount"]
            e = "📈" if a > 0 else ("📉" if a < 0 else "➡️")
            s = "+" if a > 0 else ""
            lines.append(f"{e} {p['name']}：{s}{a:,}　{p['wind']}風　自摸 {p['zimo']} 次")
        _reply_text(event.reply_token, "\n".join(lines))

    elif action == "restart_record":
        clear_state(user_id)
        _start_record(event, user_id)

    elif action == "cancel":
        clear_state(user_id)
        _reply_text(event.reply_token, "❌ 已取消記帳。")


# ──────────────────────────────────────
# 訊息處理
# ──────────────────────────────────────

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if text in {"/記帳", "記帳"}:
        _start_record(event, user_id); return

    if text in {"/排行", "排行"}:
        _show_rank(event); return
    if text.startswith("/排行 ") or text.startswith("排行 "):
        parts = text.split()
        nums = [p for p in parts[1:] if p.lstrip("-").isdigit()]
        try:
            if len(nums) >= 2:
                _show_rank(event, year=int(nums[0]), month=int(nums[1]))
            elif len(nums) == 1:
                _show_rank(event, month=int(nums[0]))
            else:
                _show_rank(event)
        except (ValueError, TypeError):
            _reply_text(event.reply_token, "格式：/排行 3（本年3月）或 /排行 2025 3（2025年3月）")
        return

    if text in {"/年排行", "年排行"}:
        _show_yearly_rank(event); return
    if text.startswith("/年排行 ") or text.startswith("年排行 "):
        parts = text.split()
        nums = [p for p in parts[1:] if p.lstrip("-").isdigit()]
        try:
            _show_yearly_rank(event, year=int(nums[0]) if nums else None)
        except (ValueError, TypeError):
            _reply_text(event.reply_token, "格式：/年排行 2025")
        return

    if text.startswith("/逐月") or text.startswith("逐月 "):
        parts = text.split()
        if len(parts) < 2 or parts[1].lstrip("-").isdigit():
            _reply_text(event.reply_token, "請輸入名字，例如：/逐月 小明　或　/逐月 小明 2025")
            return
        name = parts[1].strip()
        year = None
        if len(parts) >= 3 and parts[2].lstrip("-").isdigit():
            year = int(parts[2])
        _show_monthly_trend(event, name, year); return

    if text in {"/頒獎", "頒獎"}:
        _show_awards(event); return
    if text in {"/我的戰績", "我的戰績"}:
        _show_personal_stats(event, user_id); return
    if text in {"/取消", "取消"}:
        if get_state(user_id):
            clear_state(user_id)
            _reply_text(event.reply_token, "❌ 已取消。")
        return
    if text in {"/說明", "說明", "/help"}:
        _show_help(event); return
    if text.startswith("/加入") or text.startswith("加入 ") or text == "加入":
        parts = text.split(maxsplit=1)
        _join_member(event, user_id, parts[1] if len(parts) > 1 else None); return
    if text.startswith("/查") or text.startswith("查 "):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            _show_player_profile(event, parts[1].strip())
        else:
            _reply_text(event.reply_token, "請輸入要查詢的名字，例如：/查 小明")
        return

    # 狀態機：文字輸入
    state = get_state(user_id)
    if state:
        if state.step == "enter_amounts":
            _handle_amount_input(event, user_id, text, state); return
        if state.step == "enter_visitor_name":
            _handle_visitor_name(event, user_id, text, state); return
        if state.step in {"enter_zimo_after_wind", "enter_last_zimo"}:
            try:
                count = int(text.strip())
                if count < 0:
                    raise ValueError
            except ValueError:
                _reply_text(event.reply_token, "請輸入 0–5 的數字，例如：2")
                return
            player = state.pending_zimo_player
            if player in state.selected_players:
                idx = state.selected_players.index(player)
                state.zimos[idx] = count
            if state.step == "enter_last_zimo":
                state.step = "confirming"
                players = [
                    {
                        "name": state.selected_players[i],
                        "amount": state.amounts[i],
                        "wind": state.winds.get(state.selected_players[i], ""),
                        "zimo": state.zimos[i],
                    }
                    for i in range(4)
                ]
                _reply_flex(event.reply_token, "確認本場記錄", confirmation_flex(players))
            else:
                state.wind_idx += 1
                if state.wind_idx >= 3:
                    last_player = next(p for p in state.selected_players if p not in state.winds)
                    state.winds[last_player] = WIND_ORDER[3]
                    state.pending_zimo_player = last_player
                    state.step = "enter_last_zimo"
                    _reply_zimo_prompt(event.reply_token, last_player)
                else:
                    state.step = "assign_winds"
                    _reply_flex(event.reply_token, f"{WIND_ORDER[state.wind_idx]}風是誰？",
                                wind_selection_flex(state.selected_players, state.winds, state.wind_idx))
            return
