"""
awards.py
月度頒獎計算。
"""

from sheets_client import get_monthly_sessions, get_player_monthly_stats


def _calc_monthly_wins_losses(year: int, month: int, group_id: str) -> dict:
    """計算月內每人的勝場數與敗場數（用於嘿嘿嘿/嚶嚶嚶）"""
    sessions = get_monthly_sessions(year, month, group_id)
    player_wl: dict = {}
    for s in sessions:
        for i in range(1, 5):
            name = str(s.get(f"p{i}_name", "")).strip()
            if not name:
                continue
            try:
                amount = int(s.get(f"p{i}_amount", 0))
            except:
                amount = 0
            player_wl.setdefault(name, {"wins": 0, "losses": 0})
            if amount > 0:
                player_wl[name]["wins"] += 1
            elif amount < 0:
                player_wl[name]["losses"] += 1
    return player_wl


def calculate_monthly_awards(year: int, month: int, group_id: str = "") -> dict:
    """
    計算月度所有頒獎。
    回傳：{award_name: {"emoji": str, "player": str, "label": str}}

    獎項：
      本月債主   - 贏最多（金額）
      冠名贊助   - 輸最多（金額）
      嘿嘿嘿    - 勝場最多
      嚶嚶嚶    - 敗場最多
      指上神罷   - 自摸次數最多
    """
    stats = get_player_monthly_stats(year, month, group_id)
    if not stats:
        return {}

    wl = _calc_monthly_wins_losses(year, month, group_id)
    awards: dict = {}

    # 🏆 本月債主（贏最多）
    top = max(stats.items(), key=lambda x: x[1]["total"])
    if top[1]["total"] > 0:
        awards["本月債主"] = {
            "emoji": "🏆",
            "player": top[0],
            "label": f"本月贏 +{top[1]['total']:,} 元",
        }

    # 💣 冠名贊助（輸最多）
    bottom = min(stats.items(), key=lambda x: x[1]["total"])
    if bottom[1]["total"] < 0:
        awards["冠名贊助"] = {
            "emoji": "💣",
            "player": bottom[0],
            "label": f"本月輸 {bottom[1]['total']:,} 元",
        }

    if wl:
        # 😄 嘿嘿嘿（勝場最多）
        best_wins = max(wl.items(), key=lambda x: x[1]["wins"])
        if best_wins[1]["wins"] >= 1:
            awards["嘿嘿嘿"] = {
                "emoji": "😄",
                "player": best_wins[0],
                "label": f"本月贏了 {best_wins[1]['wins']} 場",
            }

        # 😢 嚶嚶嚶（敗場最多）
        worst_losses = max(wl.items(), key=lambda x: x[1]["losses"])
        if worst_losses[1]["losses"] >= 1:
            awards["嚶嚶嚶"] = {
                "emoji": "😢",
                "player": worst_losses[0],
                "label": f"本月輸了 {worst_losses[1]['losses']} 場",
            }

    # ⚡ 指上神罷：當月自摸次數最多
    top_zimo = max(stats.items(), key=lambda x: x[1]["zimo"])
    if top_zimo[1]["zimo"] > 0:
        awards["指上神罷"] = {
            "emoji": "⚡",
            "player": top_zimo[0],
            "label": f"本月自摸 {top_zimo[1]['zimo']} 次",
        }

    return awards
