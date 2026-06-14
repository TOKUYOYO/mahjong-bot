"""
flex_messages.py
所有 Line Flex Message 的建構函式。
"""

WIND_ORDER = ["東", "南", "西", "北"]


# ─────────────────────────────────────
# 選人卡
# ─────────────────────────────────────

def player_selection_flex(members: list[str], selected: list[str], step: int) -> dict:
    available = [m for m in members if m not in selected]
    selected_text = "、".join(selected) if selected else "（尚未選擇）"

    buttons = [
        {
            "type": "button",
            "action": {
                "type": "postback",
                "label": name,
                "data": f"action=select_player&player={name}",
                "displayText": f"選了 {name}",
            },
            "style": "link",
            "height": "sm",
        }
        for name in available
    ]
    buttons.append({
        "type": "button",
        "action": {
            "type": "postback",
            "label": "➕ 訪客",
            "data": "action=add_visitor",
            "displayText": "加入訪客",
        },
        "style": "link",
        "height": "sm",
        "color": "#888888",
    })

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#9B2335",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"🀄 選擇第 {step} 位玩家", "weight": "bold", "size": "lg", "color": "#FFFFFF"},
                {"type": "text", "text": f"已選：{selected_text}", "size": "sm", "color": "#FFCCCC", "wrap": True, "margin": "sm"},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "spacing": "xs", "contents": buttons},
        "footer": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "button", "action": {"type": "postback", "label": "❌ 取消記帳", "data": "action=cancel", "displayText": "取消記帳"}, "style": "secondary", "height": "sm"}],
        },
    }


# ─────────────────────────────────────
# 風位選擇卡
# ─────────────────────────────────────

def wind_selection_flex(selected_players: list[str], winds: dict, wind_idx: int) -> dict:
    current_wind = WIND_ORDER[wind_idx]
    available = [p for p in selected_players if p not in winds]

    assigned_parts = []
    for w in WIND_ORDER[:wind_idx]:
        for p, pw in winds.items():
            if pw == w:
                assigned_parts.append(f"{w}：{p}")
    assigned_text = "　".join(assigned_parts) if assigned_parts else "（尚未分配）"

    buttons = [
        {
            "type": "button",
            "action": {
                "type": "postback",
                "label": player,
                "data": f"action=assign_wind&wind={current_wind}&player={player}",
                "displayText": f"{player} 是 {current_wind}風",
            },
            "style": "link",
            "height": "sm",
        }
        for player in available
    ]

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1A365D",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"⛵ {current_wind}風是誰？", "weight": "bold", "size": "lg", "color": "#FFFFFF"},
                {"type": "text", "text": assigned_text, "size": "sm", "color": "#90CDF4", "margin": "sm", "wrap": True},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "spacing": "xs", "contents": buttons},
        "footer": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "button", "action": {"type": "postback", "label": "❌ 取消記帳", "data": "action=cancel", "displayText": "取消記帳"}, "style": "secondary", "height": "sm"}],
        },
    }


# ─────────────────────────────────────
# 確認卡（含風位 + 自摸）
# ─────────────────────────────────────

def confirmation_flex(players: list[dict]) -> dict:
    rows = []
    for p in players:
        amount = p["amount"]
        color = "#0A7C59" if amount > 0 else ("#C53030" if amount < 0 else "#888888")
        sign = "+" if amount > 0 else ""

        rows.append({
            "type": "box",
            "layout": "vertical",
            "paddingTop": "8px",
            "paddingBottom": "8px",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": p["name"], "weight": "bold", "size": "md", "flex": 3},
                        {"type": "text", "text": f"{sign}{amount:,}", "weight": "bold", "size": "md", "color": color, "align": "end", "flex": 2},
                    ],
                },
                {
                    "type": "box", "layout": "horizontal", "margin": "xs",
                    "contents": [
                        {"type": "text", "text": f"⛵ {p.get('wind', '—')}風", "size": "sm", "color": "#718096", "flex": 2},
                        {"type": "text", "text": f"⚡ 自摸 {p.get('zimo', 0)} 次", "size": "sm", "color": "#718096", "align": "end", "flex": 2},
                    ],
                },
            ],
        })
        rows.append({"type": "separator", "color": "#EEEEEE"})

    if rows:
        rows.pop()

    total = sum(p["amount"] for p in players)
    balance_ok = total == 0
    balance_text = "✅ 金額平衡" if balance_ok else f"⚠️ 合計不平衡：{total:+,}"
    balance_color = "#0A7C59" if balance_ok else "#C53030"

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#2D3748", "paddingAll": "16px",
            "contents": [{"type": "text", "text": "📋 確認本場記錄", "weight": "bold", "size": "lg", "color": "#FFFFFF"}],
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "16px",
            "contents": rows + [
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": balance_text, "size": "sm", "color": balance_color, "margin": "md", "align": "center"},
            ],
        },
        "footer": {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                {"type": "button", "action": {"type": "postback", "label": "✅ 確認儲存", "data": "action=confirm_record", "displayText": "確認儲存"}, "style": "primary", "color": "#0A7C59"},
                {"type": "button", "action": {"type": "postback", "label": "🔄 重新輸入", "data": "action=restart_record", "displayText": "重新輸入"}, "style": "secondary"},
            ],
        },
    }


# ─────────────────────────────────────
# 月度排行卡
# ─────────────────────────────────────

def leaderboard_flex(stats: dict, year: int, month: int) -> dict:
    sorted_players = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    rows = []

    for i, (name, data) in enumerate(sorted_players):
        medal = medals[i] if i < 3 else f"{i+1}."
        total = data["total"]
        color = "#0A7C59" if total > 0 else ("#C53030" if total < 0 else "#888888")
        label = f"+{total:,}" if total > 0 else f"{total:,}"

        rows.append({
            "type": "box", "layout": "horizontal",
            "paddingTop": "6px", "paddingBottom": "6px",
            "contents": [
                {"type": "text", "text": medal, "size": "md", "flex": 1},
                {"type": "text", "text": name, "size": "md", "flex": 3},
                {"type": "text", "text": label, "size": "md", "color": color, "weight": "bold", "align": "end", "flex": 2},
            ],
        })
        rows.append({"type": "separator", "color": "#EEEEEE"})

    if rows:
        rows.pop()

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#1A365D", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"📊 {month}月戰績排行", "weight": "bold", "size": "lg", "color": "#FFFFFF"},
                {"type": "text", "text": f"{year}年  ·  {len(stats)} 位參戰", "size": "sm", "color": "#90CDF4", "margin": "sm"},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "paddingAll": "16px", "contents": rows},
    }


# ─────────────────────────────────────
# 年度排行卡（含視覺化橫條）
# ─────────────────────────────────────

def yearly_leaderboard_flex(stats: dict, year: int) -> dict:
    """
    年度排行榜 Flex 卡片，含橫條圖視覺化。
    stats: {name: {"total": int, "sessions": int, "wins": int, "losses": int}}
    """
    sorted_players = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    max_abs = max((abs(d["total"]) for _, d in sorted_players), default=1) or 1

    rows = []
    for i, (name, data) in enumerate(sorted_players):
        medal = medals[i] if i < 3 else f"{i+1}."
        total = data["total"]
        sessions = data["sessions"]
        wins = data["wins"]
        losses = data["losses"]

        if total > 0:
            color = "#0A7C59"
            sign = "+"
        elif total < 0:
            color = "#C53030"
            sign = ""
        else:
            color = "#888888"
            sign = ""

        # 橫條：用 ▌ 重複，最多 12 個
        bar_len = max(1, round(abs(total) / max_abs * 12))
        bar = "▌" * bar_len

        rows.append({
            "type": "box", "layout": "vertical",
            "paddingTop": "8px", "paddingBottom": "4px",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": medal, "size": "sm", "flex": 1, "gravity": "center"},
                        {"type": "text", "text": name, "size": "sm", "weight": "bold", "flex": 4,
                         "gravity": "center", "wrap": True},
                        {"type": "text", "text": f"{sign}{total:,}", "size": "sm", "weight": "bold",
                         "color": color, "align": "end", "flex": 3, "gravity": "center"},
                    ],
                },
                {
                    "type": "text", "text": bar, "size": "xxs", "color": color, "margin": "xs",
                },
                {
                    "type": "text",
                    "text": f"{sessions}場  {wins}勝{losses}敗",
                    "size": "xxs", "color": "#AAAAAA", "align": "end", "margin": "xs",
                },
            ],
        })
        rows.append({"type": "separator", "color": "#EEEEEE", "margin": "xs"})

    if rows:
        rows.pop()

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#744210", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"🏅 {year}年 年度排行", "weight": "bold", "size": "xl", "color": "#FFFFFF"},
                {"type": "text", "text": f"全年累計輸贏  ·  {len(stats)} 位參戰", "size": "sm", "color": "#FBD38D", "margin": "sm"},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "paddingAll": "12px", "spacing": "none", "contents": rows},
    }


# ─────────────────────────────────────
# 月度英雄榜卡
# ─────────────────────────────────────

def awards_flex(awards: dict, year: int, month: int) -> dict:
    cards = [
        {
            "type": "box", "layout": "vertical",
            "paddingAll": "14px", "backgroundColor": "#F7FAFC",
            "cornerRadius": "8px", "margin": "sm",
            "contents": [
                {"type": "text", "text": f"{data['emoji']} {award_name}", "weight": "bold", "size": "md", "color": "#2D3748"},
                {"type": "text", "text": data["player"], "size": "xxl", "weight": "bold", "color": "#9B2335", "margin": "sm"},
                {"type": "text", "text": data["label"], "size": "sm", "color": "#718096"},
            ],
        }
        for award_name, data in awards.items()
    ]

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#744210", "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": f"🎖 {month}月英雄榜", "weight": "bold", "size": "xl", "color": "#FFFFFF", "align": "center"},
                {"type": "text", "text": f"{year}年  ·  月度頒獎", "size": "sm", "color": "#FBD38D", "align": "center", "margin": "sm"},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "paddingAll": "12px", "spacing": "sm", "contents": cards},
    }


# ─────────────────────────────────────
# 逐月趨勢卡（/逐月 指令）
# ─────────────────────────────────────

def monthly_trend_flex(player_name: str, year: int, monthly_data: list[dict]) -> dict:
    """
    monthly_data = [{"month": int, "total": int, "sessions": int}, ...]
    """
    year_total = sum(d["total"] for d in monthly_data)
    y_sign = "+" if year_total > 0 else ""
    y_color = "#0A7C59" if year_total > 0 else ("#C53030" if year_total < 0 else "#888888")

    rows = []
    for d in monthly_data:
        t = d["total"]
        color = "#0A7C59" if t > 0 else ("#C53030" if t < 0 else "#888888")
        sign = "+" if t > 0 else ""
        rows.append({
            "type": "box", "layout": "horizontal",
            "paddingTop": "5px", "paddingBottom": "5px",
            "contents": [
                {"type": "text", "text": f"{d['month']:>2}月", "size": "sm", "color": "#555555", "flex": 2, "gravity": "center"},
                {"type": "text", "text": f"{sign}{t:,}", "size": "sm", "weight": "bold",
                 "color": color, "flex": 3, "align": "end", "gravity": "center"},
                {"type": "text", "text": f"({d['sessions']}場)", "size": "xxs",
                 "color": "#AAAAAA", "flex": 2, "align": "end", "gravity": "center"},
            ],
        })
        rows.append({"type": "separator", "color": "#EEEEEE"})

    if rows:
        rows.pop()

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#2C5282", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"📈 {player_name}", "weight": "bold", "size": "lg", "color": "#FFFFFF"},
                {"type": "text", "text": f"{year}年 逐月戰績", "size": "sm", "color": "#90CDF4", "margin": "xs"},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "14px",
            "contents": rows + [
                {"type": "separator", "margin": "md"},
                {
                    "type": "box", "layout": "horizontal", "margin": "md",
                    "contents": [
                        {"type": "text", "text": "全年合計", "size": "sm", "weight": "bold", "color": "#2D3748", "flex": 3},
                        {"type": "text", "text": f"{y_sign}{year_total:,}", "size": "sm", "weight": "bold",
                         "color": y_color, "align": "end", "flex": 3},
                    ],
                },
            ],
        },
    }


# ─────────────────────────────────────
# 個人本月戰績卡（/我的戰績）
# ─────────────────────────────────────

def personal_stats_flex(name: str, data: dict, year: int, month: int) -> dict:
    """
    data = {"total": int, "sessions": int, "wins": int, "losses": int, "zimo": int}
    """
    total = data["total"]
    color = "#0A7C59" if total > 0 else ("#C53030" if total < 0 else "#888888")
    sign = "+" if total > 0 else ""
    emoji = "📈" if total > 0 else ("📉" if total < 0 else "➡️")

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#1A365D", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": f"{emoji} {name}", "weight": "bold", "size": "lg", "color": "#FFFFFF"},
                {"type": "text", "text": f"{year}年{month}月 本月戰績", "size": "sm", "color": "#90CDF4", "margin": "xs"},
            ],
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "16px", "spacing": "sm",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "💰 總輸贏", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{sign}{total:,} 元", "size": "sm", "weight": "bold",
                         "color": color, "align": "end", "flex": 3},
                    ],
                },
                {"type": "separator"},
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🎮 上桌場次", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{data['sessions']} 場", "size": "sm", "weight": "bold",
                         "color": "#2D3748", "align": "end", "flex": 3},
                    ],
                },
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "✅ 贏", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{data['wins']} 場", "size": "sm", "weight": "bold",
                         "color": "#0A7C59", "align": "end", "flex": 3},
                    ],
                },
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "❌ 輸", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{data['losses']} 場", "size": "sm", "weight": "bold",
                         "color": "#C53030", "align": "end", "flex": 3},
                    ],
                },
                {"type": "separator"},
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "⚡ 自摸", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{data['zimo']} 次", "size": "sm", "weight": "bold",
                         "color": "#2D3748", "align": "end", "flex": 3},
                    ],
                },
            ],
        },
    }


# ─────────────────────────────────────
# 個人頁面卡（含頭像 + 生涯最佳 + 逐月）
# ─────────────────────────────────────

def player_profile_flex(data: dict) -> dict:
    """
    data = {
        "name": str,
        "avatar_url": str,
        "month_total": int,
        "year_total": int,
        "month_sessions": int,
        "month_zimo": int,
        "last5": [int, ...],
        "debtor": str|None,
        "debtor_net": float,
        "sponsor": str|None,
        "sponsor_net": float,
        "best_wind": str|None,
        "best_wind_avg": float,
        "best_wind_sessions": int,
        "best_session": {"date": str, "amount": int, "wind": str} | None,
        "monthly_breakdown": [{"month": int, "total": int, "sessions": int}, ...],
    }
    """
    name = data["name"]

    # ── 頭像 ──
    avatar_url = data.get("avatar_url", "")
    first_char = name[0] if name else "?"
    if avatar_url:
        # 有圖：用 image 元件（LINE 原生支援，aspectMode=cover 自動裁圓）
        avatar_box = {
            "type": "image",
            "url": avatar_url,
            "size": "72px",
            "aspectMode": "cover",
            "aspectRatio": "1:1",
        }
    else:
        # 無圖：用大號文字字符代替
        avatar_box = {
            "type": "text",
            "text": first_char,
            "size": "4xl",
            "weight": "bold",
            "color": "#FFFFFF",
            "gravity": "center",
            "align": "center",
            "flex": 0,
        }

    m_color = "#0A7C59" if data["month_total"] > 0 else ("#C53030" if data["month_total"] < 0 else "#888888")
    y_color = "#0A7C59" if data["year_total"] > 0 else ("#C53030" if data["year_total"] < 0 else "#888888")
    m_sign = "+" if data["month_total"] > 0 else ""
    y_sign = "+" if data["year_total"] > 0 else ""

    body_contents = [
        # 本月 / 今年
        {
            "type": "box", "layout": "horizontal", "spacing": "md",
            "contents": [
                {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                    {"type": "text", "text": "本月", "size": "xs", "color": "#888888", "align": "center"},
                    {"type": "text", "text": f"{m_sign}{data['month_total']:,}", "size": "lg", "weight": "bold", "color": m_color, "align": "center"},
                ]},
                {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                    {"type": "text", "text": "今年", "size": "xs", "color": "#888888", "align": "center"},
                    {"type": "text", "text": f"{y_sign}{data['year_total']:,}", "size": "lg", "weight": "bold", "color": y_color, "align": "center"},
                ]},
            ],
        },
        {"type": "separator", "margin": "lg"},
        {"type": "text", "text": f"🎮 本月上桌 {data['month_sessions']} 場　⚡ 自摸 {data['month_zimo']} 次",
         "size": "sm", "color": "#555555", "margin": "lg", "wrap": True},
    ]

    # 近況（最近5場）
    if data.get("last5"):
        bars = " / ".join((f"+{a:,}" if a > 0 else f"{a:,}") for a in data["last5"])
        body_contents.append({
            "type": "text", "text": f"🗂 近況：{bars}",
            "size": "sm", "color": "#555555", "margin": "md", "wrap": True,
        })

    # 生涯最佳單場
    best = data.get("best_session")
    if best and best["amount"] > 0:
        body_contents.append({"type": "separator", "margin": "lg"})
        body_contents.append({
            "type": "text",
            "text": f"🌟 生涯最佳單場：+{best['amount']:,}（{best['date']}  {best['wind']}風）",
            "size": "sm", "color": "#744210", "margin": "md", "wrap": True, "weight": "bold",
        })

    body_contents.append({"type": "separator", "margin": "lg"})

    # 我有欠你嗎 / 贊助商
    if data.get("debtor"):
        body_contents.append({
            "type": "text",
            "text": f"🔴 我有欠你嗎？：{data['debtor']}（估算淨輸 {data['debtor_net']:+,.0f}）",
            "size": "sm", "color": "#555555", "margin": "md", "wrap": True,
        })
    else:
        body_contents.append({
            "type": "text", "text": "🔴 我有欠你嗎？：（資料不足）",
            "size": "sm", "color": "#AAAAAA", "margin": "md",
        })
    if data.get("sponsor"):
        body_contents.append({
            "type": "text",
            "text": f"🟢 贊助商：{data['sponsor']}（估算淨贏 {data['sponsor_net']:+,.0f}）",
            "size": "sm", "color": "#555555", "margin": "sm", "wrap": True,
        })
    else:
        body_contents.append({
            "type": "text", "text": "🟢 贊助商：（資料不足）",
            "size": "sm", "color": "#AAAAAA", "margin": "sm",
        })

    # 擅長風位
    if data.get("best_wind"):
        bw_sign = "+" if data["best_wind_avg"] > 0 else ""
        body_contents.append({
            "type": "text",
            "text": f"🌀 擅長風位：{data['best_wind']}風（平均 {bw_sign}{data['best_wind_avg']:.0f} / {data['best_wind_sessions']}場）",
            "size": "sm", "color": "#555555", "margin": "sm", "wrap": True,
        })
    else:
        body_contents.append({
            "type": "text", "text": "🌀 擅長風位：（資料不足）",
            "size": "sm", "color": "#AAAAAA", "margin": "sm",
        })

    # ── 逐月輸贏 ──
    monthly = data.get("monthly_breakdown", [])
    if monthly:
        body_contents.append({"type": "separator", "margin": "lg"})
        body_contents.append({
            "type": "text", "text": "📅 今年逐月",
            "size": "sm", "weight": "bold", "color": "#2D3748", "margin": "lg",
        })
        for md in monthly:
            t = md["total"]
            color = "#0A7C59" if t > 0 else ("#C53030" if t < 0 else "#888888")
            sign = "+" if t > 0 else ""
            body_contents.append({
                "type": "box", "layout": "horizontal",
                "paddingTop": "3px", "paddingBottom": "3px",
                "contents": [
                    {"type": "text", "text": f"{md['month']:>2}月", "size": "xs", "color": "#555555", "flex": 2},
                    {"type": "text", "text": f"{sign}{t:,}", "size": "xs", "weight": "bold",
                     "color": color, "flex": 3, "align": "end"},
                    {"type": "text", "text": f"({md['sessions']}場)", "size": "xxs",
                     "color": "#AAAAAA", "flex": 2, "align": "end"},
                ],
            })

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "horizontal",
            "backgroundColor": "#1A365D", "paddingAll": "20px", "spacing": "md", "alignItems": "center",
            "contents": [
                avatar_box,
                {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": name, "size": "lg", "weight": "bold", "color": "#FFFFFF", "wrap": True},
                    {"type": "text", "text": "個人頁面", "size": "xs", "color": "#90CDF4", "margin": "xs"},
                ]},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "paddingAll": "16px", "contents": body_contents},
    }
