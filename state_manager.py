"""
state_manager.py
記帳對話狀態機。

依風位逐一記錄，每位玩家一次問完：
  idle
    → /記帳
    → select_player（按鈕選「東風是誰」，可加訪客 → enter_visitor_name）
    → enter_amount（文字輸入該玩家輸贏金額）
    → enter_zimo（QuickReply 問該玩家自摸）
    → 南、西風同上循環
    → 北風選人後金額自動計算（四人合計為 0），只問自摸
    → confirming（確認卡）
    → 寫入 Sheets → idle
"""

from dataclasses import dataclass, field
from typing import Optional

WIND_ORDER = ["東", "南", "西", "北"]


@dataclass
class RecordState:
    user_id: str
    step: str = "select_player"
    # step 可能值：
    #   select_player | enter_visitor_name | enter_amount | enter_zimo | confirming

    # 以下三個 list 皆依風位順序（東南西北）排列
    selected_players: list = field(default_factory=list)
    amounts: list = field(default_factory=list)
    zimos: list = field(default_factory=list)

    @property
    def current_idx(self) -> int:
        """目前正在記錄的玩家（0-based），也就是 WIND_ORDER 的索引"""
        return len(self.selected_players) - 1

    @property
    def current_player(self) -> str:
        return self.selected_players[-1] if self.selected_players else ""

    @property
    def current_wind(self) -> str:
        return WIND_ORDER[self.current_idx]

    @property
    def next_wind(self) -> str:
        return WIND_ORDER[len(self.selected_players)]


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
