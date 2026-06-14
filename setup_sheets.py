"""
setup_sheets.py
一次性執行：建立 Google Sheets 工作表並寫入欄位標題。
"""

import json
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SESSIONS_HEADERS = [
    "session_id", "date", "group_id",
    "p1_name", "p1_amount", "p1_wind", "p1_zimo",
    "p2_name", "p2_amount", "p2_wind", "p2_zimo",
    "p3_name", "p3_amount", "p3_wind", "p3_zimo",
    "p4_name", "p4_amount", "p4_wind", "p4_zimo",
    "recorded_by", "created_at",
]

MEMBERS_HEADERS = ["name", "line_user_id", "joined_date"]


def setup():
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDENTIALS_JSON), scopes=SCOPES
    )
    ss = gspread.authorize(creds).open_by_key(SPREADSHEET_ID)

    # ── members ──
    try:
        ws = ss.worksheet("members")
        print("members 工作表已存在")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title="members", rows=200, cols=3)
        print("✅ 建立 members 工作表")
    if not ws.row_values(1):
        ws.append_row(MEMBERS_HEADERS)
        print(f"   欄位：{MEMBERS_HEADERS}")

    # ── sessions ──
    try:
        ws2 = ss.worksheet("sessions")
        print("sessions 工作表已存在")
    except gspread.WorksheetNotFound:
        ws2 = ss.add_worksheet(title="sessions", rows=2000, cols=22)
        print("✅ 建立 sessions 工作表")
    if not ws2.row_values(1):
        ws2.append_row(SESSIONS_HEADERS)
        print(f"   欄位（共 {len(SESSIONS_HEADERS)} 欄）：{SESSIONS_HEADERS}")

    print(f"\n🎉 完成！試算表 ID：{SPREADSHEET_ID}")


if __name__ == "__main__":
    setup()
