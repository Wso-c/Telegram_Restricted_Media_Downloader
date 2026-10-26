# TRMD Control Plane Architecture

本次 refactor 將 Web UI 定位為 TRMD 的主要 Control Plane，同時保留既有 Python/Kurigram 下載器、Telegram Bot 指令與 `config.yaml`。這是同一程序內的 layered/event-driven monolith，不是把下載器拆成另一個服務。

## 1. 新系統架構藍圖

```text
管理員瀏覽器
  ├─ HTML/CSS/JavaScript：module/templates、module/static
  ├─ REST + SSE（認證沿用 TRMD Web 登入）
  └─ module/web.py：HTTP transport、session 驗證、靜態資源
       └─ module/web_api.py：REST resource adapter
            └─ module/app_core.py：共享 service facade、EventHub
                 ├─ module/downloader.py：唯一下載排程及工作狀態來源
                 ├─ module/task.py：下載/上載任務和狀態
                 ├─ module/app.py、module/client.py：Kurigram client 與媒體串流
                 ├─ module/uploader.py：既有上載及分塊續傳
                 ├─ module/config.py：YAML 設定載入、驗證、儲存
                 └─ sessions/、temp/、downloads/：既有本機檔案

Telegram 使用者 ── Telegram Bot ── module/bot.py
                                  └─ module/bot_controller.py
                                       └─ 同一 downloader / AppCore 狀態
```

### 模組責任

| 模組 | 職責 |
| --- | --- |
| `module/app_core.py` | 將既有 downloader 暴露為 Web/Bot 共用非同步服務；提供任務控制、佇列順序檢查、Session 清單、資源資訊與有界日誌事件 feed。它不建立第二個 Telegram client 或第二份任務狀態。 |
| `module/web_api.py` | REST resource mapping，將管理 API 導向 `AppCore`。HTTP auth、JSON 和 SSE transport 仍由現有 `module/web.py` 處理。 |
| `module/bot_controller.py` | Bot 對下載提交、任務狀態及控制的服務 adapter。原有 handlers、管理員授權、互動式指令和通知仍保留在既有 Bot/downloader 程式碼。 |
| `module/downloader.py` / `module/task.py` | 沿用既有 asyncio 排程、暫停/取消/重試、Kurigram `stream_media`、分塊下載及 retry 邏輯；任務狀態仍是唯一真實來源。 |
| `module/web.py` | 沿用既有本機 HTTP server、登入保護、API 與靜態資源；將控制功能委派至新 service/resource adapter。 |
| `module/templates/index.html`、`module/static/js/app.js` | 提供任務控制、下載/轉發表單、設定表單、完整 YAML 編輯、佇列重排、帳號/Session 清單、資源監控及 SSE 日誌。 |

### 主要資料流

1. Web 或 Bot 請求進入同一 downloader，不複製任務佇列或 Telegram session。
2. Web HTTP thread 將 async 操作以 `asyncio.run_coroutine_threadsafe` 投遞到 downloader 主事件迴圈；媒體 I/O 仍由既有 asyncio/Kurigram client 執行。
3. `DownloadTask` 和 `UploadTask` 保持權威任務狀態；Web 進度快照讀取同一份狀態。
4. 認證後的日誌透過 bounded in-process EventHub 推送 SSE。待處理連結順序寫入同目錄的 `trmd-control.sqlite3`，但 Telegram Message 與 client 狀態不會序列化。
5. 設定更新先以 `yaml.safe_load` 解析，再呼叫既有設定驗證和原子檔案取代流程；變更即時生效欄位會同步更新既有 app/uploader instance。

## 2. Web API 與事件規範

除了登入/登出及既有進度 API，下列管理端點均要求已登入 Web session（Cookie 或 Bearer token）。JSON 成功回應使用 `{"status": true, ...}`；錯誤以非 2xx 和 `{"status": false, "e_code": "..."}` 回覆。

| Method | Endpoint | 說明 |
| --- | --- | --- |
| `GET` | `/api/progress` | 既有即時下載/上載、監聽及服務快照。 |
| `GET` | `/api/status` | 既有服務狀態快照。 |
| `GET` | `/api/settings` | 遮罩密鑰後的表單設定。 |
| `GET` | `/api/admin/config` | 完整 YAML 文字（含密鑰，僅認證後可讀）。 |
| `POST` | `/api/admin/config` | `{ "config_yaml": "..." }`；安全解析、驗證並保存。 |
| `GET` | `/api/admin/queue` | `{ "links": ["https://t.me/..."] }`，只列仍有 pending 項目的連結。 |
| `POST` | `/api/admin/download/reorder` | `{ "links": ["..."] }`；必須精確涵蓋目前 pending link，各連結不得重複。只重排尚未派發項目。 |
| `POST` | `/api/admin/download/add` | `{ "link": "https://t.me/..." }`。 |
| `POST` | `/api/admin/download/control` | `{ "link": "...", "message_id": 123, "action": "pause\|resume\|cancel\|retry" }`。 |
| `POST` | `/api/admin/forward` | `{ "origin_link": "...", "target_link": "...", "start_id": 1, "end_id": 100 }`；沿用既有媒體群組處理、下載類型過濾及轉發節流。 |
| `GET` | `/api/admin/forward/status?job_id=...` | 查詢非同步轉發工作狀態，避免長區間操作佔住 HTTP 請求或被同步 API timeout 取消。 |
| `POST` | `/api/admin/upload/control` | `{ "task_id": "...", "action": "pause\|resume\|cancel" }`。 |
| `GET` | `/api/admin/sessions` | 目前帳號連線狀態、工作階段檔名及活動 Session。 |
| `GET` | `/api/admin/system` | 平台、CPU load、程序 peak RSS、記憶體估算及下載磁碟使用量。 |
| `GET` | `/api/events` | Server-Sent Events (SSE) 日誌串流；支援 `Last-Event-ID` 續讀。 |
| `POST` | `/api/admin/service/reconnect` | 使用既有 Bot client 重新連線。 |
| `POST` | `/api/admin/service/shutdown` | 使用既有安全停止流程。 |
| `POST` | `/api/listener/remove` | 既有監聽移除 API。 |

SSE frame 使用標準格式 `id: <sequence>`、`event: log`、`data: {"level":"INFO","message":"..."}`。EventHub 緩衝區有上限；若用戶端落後超出緩衝範圍，只能收到目前保留的事件。UI 以 Fetch stream 帶入既有認證 header，避免 `EventSource` 無法帶 Bearer token 的限制。

EventHub 另會發布 `queue.reordered`（`{"links":[...]}`）及 `config.updated`（`{"restart_required":[...]}`）事件。下載/上載的逐項進度以 `/api/progress` 快照提供，Bot 操作及 Web 操作都會反映在相同任務清單。
轉發工作另外發布 `forward.started` 與 `forward.completed` 事件。

原 Bot 的 `/start`、`/download`、`/status` 及其餘既有命令/按鈕仍由 `module/bot.py` 和 downloader handlers 處理；管理員授權及通知未改成 Web 層驗證。`BotController` 是新增服務 adapter，不會取代既有 Telegram handler。

## 3. 核心程式碼與執行方式

可執行的實作位於：

- `module/app_core.py` — `AppCore`、`EventHub`
- `module/web_api.py` — `WebAPI`
- `module/bot_controller.py` — `BotController`
- `module/web.py` — API/SSE HTTP 路由及認證
- `module/templates/index.html`、`module/static/js/app.js`、`module/static/css/admin.css` — 控制面 UI

入口仍是 `main.py`，CLI 參數仍由 `module/parser.py` 處理；`--host` 預設綁定 `127.0.0.1`。部署至其他網路介面時，必須限制網路存取並設定 Web 管理認證。SSE 與完整 YAML API 共用同一認證層。

### 服務界線及目前限制

- 原 repository 使用單一使用者帳號 Kurigram client。Web 提供帳號連線狀態與 `.session` 檔案清單，但不提供瀏覽器內 OTP/2FA 登入或多帳號即時切換；新帳號授權仍使用既有啟動/登入流程，不在執行中建立第二個 client，也不提供危險的遠端 session 檔案刪除。換帳號需要依既有流程停機後操作。
- 下載工作包含 Telegram Message/client 物件，不能單靠序列化安全地跨程序恢復；目前執行中任務狀態仍在記憶體。SQLite 保存管理員指定的待處理連結順序，供現行任務排序使用，不宣稱 crash recovery 或重新啟動後自動重新抓取排隊訊息。
- Web transport 沿用 repository 現有 `ThreadingHTTPServer`，因而不需更換執行入口或引入 FastAPI/uvicorn；Telegram I/O 與共享服務操作仍回到原 asyncio loop。SSE 每個連線佔用一個 HTTP worker thread。
- 資源監控使用標準函式庫；平台不提供的記憶體指標會明確顯示為 unavailable。程序 RSS 使用 `resource.getrusage().ru_maxrss` peak 值，並非即時 working-set。

## 4. 設定檔與 Session 相容指南

- `config.yaml` 路徑仍由 `--config` 決定；既有欄位（`api_id`、`api_hash`、`bot_token`、`session_directory`、`proxy`、`links`、下載/暫存目錄、並行數、重試數及媒體類型）不改名、不搬移。
- 表單設定保留密鑰欄位；新增完整 YAML 編輯器可檢視/編輯既有所有 YAML 欄位。保存前使用 `yaml.safe_load` 和 `Web.validate_settings`/`Web.update_settings` 驗證，並以同目錄暫存檔 `os.replace` 原子更新。
- `api_hash`、`bot_token` 與 Proxy password 屬敏感值；管理 API 只在 Web 登入後提供，表單端仍以密鑰遮罩。可用表單儲存時留空代表不變；完整 YAML 編輯器則請保留需要的密鑰。
- `.session` 檔仍由 Kurigram/Pyrogram 在 `session_directory` 中管理，格式及檔案保持原樣；不複製、不轉換、不遷移，也不會由 Web 傳送 session 檔內容。
- 升級不要求資料庫 migration；`trmd-control.sqlite3` 會在第一次啟動時建立佇列順序表。既有 `config.yaml`、session、下載目錄及上載分塊 JSON 繼續使用。
