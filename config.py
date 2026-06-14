import os
from dotenv import load_dotenv

load_dotenv()

# ── Line ──
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID", "")  # 月結推播用

# ── Google Sheets ──
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

# ── Sheet 名稱 ──
SHEET_MEMBERS = "members"
SHEET_SESSIONS = "sessions"

# ── 月度頒獎定義（僅供參考，實際由 awards.py 計算）──
AWARDS_META = {
    "本月債主": {"emoji": "🏆", "desc": "當月總贏最多"},
    "冠名贊助": {"emoji": "💣", "desc": "當月輸最慘"},
    "嘿嘿嘿":  {"emoji": "😄", "desc": "當月勝場最多"},
    "嚶嚶嚶":  {"emoji": "😢", "desc": "當月敗場最多"},
    "指上神罷": {"emoji": "⚡", "desc": "當月自摸最多"},
}
