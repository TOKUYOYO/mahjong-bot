"""
state_manager.py
記帳對話狀態機。

完整步驟流程（精簡版）：
  idle
    → /記帳
    → select_players（按鈕選 4 人）
    → enter_amounts（文字輸入前 3 位金額，第 4 位自動計算）
    → assign_winds（按鈕指定東南西北，選完一個 →）
    → enter_zimo_after_wind（QuickReply 問該玩家自摸，回來後繼續下一個風位）
    → 前 3 人完畢後北風自動分配 →
    → enter_last_zimo（QuickReply 問最後一人自摸）
    → confirming（確認卡）
    → 寫入 Sheets → idle
"""

from dataclasses import dataclass, field
from typing import Optional

WIND_ORDER = ["東", "南", "西", "北"]


@dataclass
class RecordState:
    user_id: str
    step: str = "select_players"
    # step 可能值：
    #   select_players | enter_visitor_name | enter_amounts
    #   | assign_winds | enter_zimo_after_wind | enter_last_zimo | confirming

    # ── 選人 ──
    selected_players: list = field(default_factory=list)

    # ── 金額 ──
    amounts: list = field(default_factory=list)
    amount_idx: int = 0   # 目前要輸入第幾位（0-based），收到 3 筆後自動算第 4

    # ── 風位 ──
    winds: dict = field(default_factory=dict)   # {player_name: "東"|"南"|"西"|"北"}
    wind_idx: int = 0                           # 已分配幾個風位（0~3）

    # ── 自摸 ──
    zimos: list = field(default_factory=lambda: [0, 0, 0, 0])  # 依 selected_players 順序
    zimo_idx: int = 0                           # 保留相容

    # ── 風位+自摸交替流程 ──
    pending_zimo_player: str = ""               # 目前待詢問自摸的玩家名字


# 全域狀態：{user_id: RecordState}
_states: dict[str, RecordState] = {}


def get_state(user_id: str) -> Optional[RecordState]:
    return _states.get(user_id)


def create_state(user_id: str) -> RecordState:
    state = RecordState(user_id=user_id)
    _states[user_id] = state
    return state


def clear_state(user_id: str) -> None:
    _states.pop(user_id, None)
