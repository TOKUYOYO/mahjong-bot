# 🀄 麻將戰績 Bot

台灣麻將群組戰績追蹤 Line Bot。

---

## 功能

| 指令 | 說明 |
|------|------|
| `/記帳` | 開始記錄本場戰績（選人 → 輸金額 → 確認） |
| `/排行` | 本月積分排行榜 |
| `/頒獎` | 本月英雄榜（🏆 月度猛將、💣 最大雷、🔥 磨人王、😢 跟你就不起） |
| `/我的戰績` | 個人本月統計 |
| `/加入 [名字]` | 加入成員清單（省略名字則用 Line 顯示名稱） |
| `/取消` | 取消目前操作 |
| `/說明` | 顯示指令列表 |

**月結自動推播**：每月最後一天 22:00（台灣時間）自動推播月結排行 + 英雄榜至群組。

---

## 部署流程

### 1. Line Developer Console 設定

1. 前往 [https://developers.line.biz](https://developers.line.biz)
2. 建立 Provider → 建立 Messaging API Channel
3. 取得：
   - **Channel Secret**（Basic settings 頁面）
   - **Channel Access Token**（Messaging API 頁面 → 最底下 Issue）
4. 在 Messaging API 頁面：
   - 開啟 **Allow bot to join group chats**
   - 關閉 **Auto-reply messages**（否則 Bot 會自動回覆所有訊息）
   - 關閉 **Greeting messages**

---

### 2. Google Cloud 設定

#### a. 建立 Service Account
1. 前往 [https://console.cloud.google.com](https://console.cloud.google.com)
2. 建立專案（或使用現有）
3. 啟用 **Google Sheets API** 和 **Google Drive API**
4. IAM & Admin → Service Accounts → 建立 Service Account
5. 下載 JSON 金鑰檔

#### b. 建立 Google 試算表
1. 新增一個空白 Google 試算表
2. 從 URL 複製試算表 ID（長串字母數字那段）
3. 在試算表的共用設定裡，將 Service Account 的 email 加入（需有**編輯**權限）

---

### 3. 取得 Line Group ID

1. 將 Bot 加入麻將群組
2. 群組裡隨便發一則訊息
3. 在 Render 的 Log 裡找到 webhook payload，其中的 `group_id` 就是 `LINE_GROUP_ID`
   - 或者暫時在 `handle_message` 裡加上 `print(event.source.group_id)` 輔助取得

---

### 4. 本機測試

```bash
# 複製並填入環境變數
cp .env.example .env
# 編輯 .env 填入所有值

# 安裝套件
pip install -r requirements.txt

# 初始化 Google Sheets
python setup_sheets.py

# 啟動
uvicorn main:app --reload --port 8000
```

本機測試 Webhook 需搭配 [ngrok](https://ngrok.com)：
```bash
ngrok http 8000
# 將 https://xxxx.ngrok.io/webhook 填入 Line Developer Console 的 Webhook URL
```

---

### 5. Render.com 部署

1. 推送到 GitHub
2. [https://dashboard.render.com](https://dashboard.render.com) → New Web Service
3. 連結 GitHub repo
4. 設定：
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**：Free instance type
5. 在 Environment Variables 新增：
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `SPREADSHEET_ID`
   - `GOOGLE_CREDENTIALS_JSON`（將整個 JSON 貼成一行）
   - `LINE_GROUP_ID`
6. Deploy 完成後，將 Render 給的 URL + `/webhook` 填入 Line Developer Console

> **注意**：Render 免費方案 15 分鐘沒流量會 spin down（冷啟動約 30-60 秒）。
> 可設定 UptimeRobot 每 10 分鐘打一次 `/ping` 保持活躍。

---

## 資料結構

### members 工作表
| name | line_user_id | joined_date |
|------|--------------|-------------|
| 小明 | Uxxxxxxxx | 2025-01-01 |

### sessions 工作表
| session_id | date | p1_name | p1_amount | p2_name | p2_amount | p3_name | p3_amount | p4_name | p4_amount | recorded_by | created_at |
|------------|------|---------|-----------|---------|-----------|---------|-----------|---------|-----------|-------------|------------|
| A1B2C3D4 | 2025-06-13 | 小明 | 500 | 小花 | -200 | 大頭 | 300 | 阿杰 | -600 | 小明 | 2025-06-13 22:00:00 |

---

## 未來預留功能

- **指上神罷（最多自摸）**：sessions 工作表可新增 `p1_zimo` ~ `p4_zimo` 欄位
- **風位記錄**：可新增 `p1_wind` ~ `p4_wind` 欄位（東南西北）
- 目前 config.py 的 `AWARDS_META` 已預留 `指上神罷` 定義，待資料收集後啟用

---

## 檔案結構

```
mahjong_bot/
├── main.py            # FastAPI 入口
├── config.py          # 環境變數 / 常數
├── line_handler.py    # Line 事件處理（核心）
├── state_manager.py   # 對話狀態機
├── sheets_client.py   # Google Sheets 讀寫
├── awards.py          # 月度頒獎計算
├── flex_messages.py   # Flex Message 建構
├── scheduler.py       # APScheduler 月結推播
├── setup_sheets.py    # 一次性初始化腳本
├── requirements.txt
└── .env.example
```
