# 麻將 Bot Debug 指南

## 專案基本資訊

- **部署平台**：Render.com（免費方案，閒置會休眠）
- **Bot URL**：`https://mahjong-bot-uila.onrender.com/webhook`
- **GitHub**：`https://github.com/TOKUYOYO/mahjong-bot`（帳號：TOKUYOYO）
- **語言/框架**：Python 3.11 + FastAPI + LINE Bot SDK v2
- **資料庫**：Google Sheets（gspread）
- **Keep-alive**：UptimeRobot 定時 ping `/ping`

---

## 檔案結構

```
mahjong_bot/
├── main.py              # FastAPI 入口，/webhook POST/GET，/ping
├── line_handler.py      # 所有指令與狀態機邏輯
├── flex_messages.py     # 所有 Flex Message 建構
├── sheets_client.py     # Google Sheets 讀寫（含 5 分鐘快取）
├── state_manager.py     # 記帳狀態機（RecordState dataclass）
├── awards.py            # 月度頒獎計算
├── scheduler.py         # APScheduler 每月自動廣播
├── config.py            # 環境變數讀取
├── requirements.txt
└── .python-version      # 內容：3.11.9（Render 用）
```

---

## Sheets 工作表結構

**members 工作表（4 欄）**
| A: name | B: line_user_id | C: joined_date | D: avatar_url |
|---------|----------------|----------------|---------------|

**sessions 工作表（22 欄）**
`session_id | date | group_id | p1_name | p1_amount | p1_wind | p1_zimo | p2_... | p3_... | p4_... | recorded_by | created_at`

---

## Bot 指令一覽

| 指令 | 功能 |
|------|------|
| `/記帳` | 開始記帳流程 |
| `/排行` | 本月排行 |
| `/年排行` | 年度排行（場次 < 5 不列入） |
| `/逐月 名字` | 個人逐月戰績 |
| `/查 名字` | 個人頁面（含頭像、生涯最佳、逐月） |
| `/我的戰績` | 本月個人統計 |
| `/頒獎` | 本月英雄榜 |
| `/加入 名字` | 加入成員清單 |
| `/取消` | 取消記帳 |
| `/說明` | 顯示說明 |

---

## 記帳狀態機流程

```
/記帳
 → select_players（選 4 人）
 → enter_amounts（前 3 人輸金額，第 4 人自動計算）
 → assign_winds（選東風是誰）
   → enter_zimo_after_wind（問該玩家自摸，用 push_message）
   → assign_winds（選南風）→ enter_zimo_after_wind
   → assign_winds（選西風）→ enter_zimo_after_wind
   → 自動分配北風 → enter_last_zimo（問北風自摸，用 push_message）
 → confirming（確認卡）
 → 儲存 → 完成
```

**重要**：自摸提示用 `push_message`（非 reply），因為 reply_token 在 postback 後已消耗。自摸支援快速回覆按鈕（0–5 次）或直接輸入數字。

---

## Render 環境變數（需在 Render Dashboard 設定）

| 變數名 | 說明 |
|--------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Channel Access Token |
| `LINE_CHANNEL_SECRET` | LINE Bot Channel Secret |
| `GOOGLE_CREDENTIALS_JSON` | Google Service Account JSON（整個貼上） |
| `SPREADSHEET_ID` | Google Sheets 的 ID（URL 中間那段） |

---

## 常見問題與解法

### Bot 沒有回應
1. 確認 Render 有在運行（UptimeRobot 是否正常）
2. 看 Render Logs 有無 error
3. 確認 LINE Webhook URL 是 `https://mahjong-bot-uila.onrender.com/webhook`

### 推 GitHub 失敗（Authentication failed）
GitHub 不支援密碼，需用 Personal Access Token：
```bash
git remote set-url origin https://TOKUYOYO:YOUR_TOKEN@github.com/TOKUYOYO/mahjong-bot.git
git push
```
Token 建立：GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → 勾 `repo`

### git lock 錯誤
```bash
rm -f ~/mahjong_bot/.git/HEAD.lock
rm -f ~/mahjong_bot/.git/index.lock
```

### 頭像不顯示
- D 欄網址必須是直連圖片：`https://i.imgur.com/xxxxx.jpg`
- 在 Imgur 右鍵圖片 → **複製圖片網址** 可直接取得正確格式

### Render 部署失敗（Python 版本問題）
確認 `~/.python-version` 內容是 `3.11.9`

---

## 推版流程

```bash
cd ~/mahjong_bot
git add 修改的檔案
git commit -m "說明"
git push
# Render 收到後自動部署，約 1–2 分鐘
```

---

## Debug 時提供給 Claude 的資訊

1. **問題描述**：什麼指令、什麼步驟出錯
2. **Render Logs**：出錯當下的 log 截圖
3. **LINE 畫面**：Bot 回傳的內容截圖（或「完全沒回應」）
4. 告知：是新功能問題還是原本可以現在壞了

---

## 本專案用到的 LINE Flex Message 注意事項

- `box` 元件**不支援 `cornerRadius`**（只有 bubble 支援）
- `box` 元件**不支援 `justifyContent` / `alignItems`**（用 `gravity` 代替）
- 每個 reply_token **只能用一次**，postback 後若要再送訊息要用 `push_message`
- 圖片網址必須是 HTTPS 直連
