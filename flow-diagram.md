# 程式流程與元件架構

## 程式流程圖

```mermaid
flowchart TD
    A["啟動 main.py"] --> B["建立下載器並載入設定"]
    B --> C["建立 Telegram 使用者端"]
    C --> D["登入或讀取既有 Telegram 工作階段"]
    D --> E{"是否已設定機器人？"}
    E -- 是 --> F["啟動 Telegram 機器人"]
    E -- 否 --> G["略過機器人功能"]
    F --> H["啟動網頁面板"]
    G --> I["讀取設定連結或連結檔案"]
    H --> I

    I --> J{"是否有有效連結？"}
    J -- 否，且未設定機器人 --> X["提示沒有有效連結並結束"]
    J -- 否，但已設定機器人 --> K["等待機器人任務"]
    J -- 是 --> L["解析連結並取得 Telegram 訊息"]
    K --> M["接收機器人指令或監聽任務"]
    M --> L

    L --> N["建立記憶體中的下載任務"]
    N --> O["排程器依並行數限制派發訊息"]
    O --> P["從 Telegram 串流取得媒體"]
    P --> Q["寫入暫存 .temp 檔案"]
    Q --> R{"下載完整且驗證通過？"}
    R -- 否 --> S["保留或清除暫存檔；重試或標記失敗"]
    S --> O
    R -- 是 --> T["移至設定的下載目錄"]
    T --> U{"是否要求上傳且機器人可用？"}
    U -- 是 --> V["上傳至 Telegram；以 JSON 儲存分塊續傳資訊"]
    U -- 否 --> W["略過上傳"]
    V --> Y["更新記憶體中的任務與統計狀態"]
    W --> Y
    Y --> Z{"是否還有待處理任務，或機器人仍在執行？"}
    Z -- 是 --> O
    Z -- 否 --> AA["顯示結果；視設定匯出 CSV"]
    AA --> AB["停止排程器、Telegram 用戶端與網頁服務"]

    H -. "查詢進度、管理監聽" .-> AC["網頁面板"]
    AC -. "讀取執行狀態" .-> N
    AC -. "讀取下載進度" .-> O
```

## 元件圖

```mermaid
flowchart LR
    user["使用者／命令列"]
    telegram["Telegram 服務"]
    remote["遠端設定服務"]

    subgraph app["TRMD 應用程式"]
        entry["程式入口<br/>main.py"]
        config["設定管理<br/>使用者與全域設定"]
        orchestrator["下載器<br/>流程協調與任務排程"]
        tasks["任務狀態<br/>下載佇列與執行統計"]
        client["Telegram 使用者端<br/>Kurigram／Pyrogram"]
        bot["Telegram 機器人<br/>選用"]
        web["網頁面板<br/>進度與監聽管理"]
        uploader["上傳器<br/>選用"]
        report["統計與報表"]
    end

    subgraph storage["本機檔案儲存"]
        yaml["YAML 設定檔"]
        session[".session 工作階段檔<br/>SQLite，由用戶端管理"]
        temp["暫存媒體<br/>.temp"]
        media["已下載媒體檔"]
        upload_json["上傳續傳資料<br/>JSON"]
        local_meta["日誌、網頁工作階段<br/>遠端設定快取"]
        csv["匯出的 CSV 報表"]
    end

    user --> entry
    entry --> config
    config <--> yaml
    entry --> orchestrator
    config --> client
    client <--> session
    client <--> telegram
    orchestrator <--> tasks
    orchestrator --> client
    orchestrator <--> bot
    bot <--> telegram
    orchestrator --> temp
    temp --> media
    orchestrator -. "有啟用上傳時" .-> uploader
    uploader --> bot
    uploader <--> upload_json
    user <--> web
    web <--> orchestrator
    tasks --> report
    report --> csv
    remote --> local_meta
    entry --> local_meta
```

## 資料儲存概覽

| 資料 | 儲存位置／方式 | 用途 |
| --- | --- | --- |
| Telegram 使用者與機器人工作階段 | 工作階段目錄中的 `.session` 檔案；由 Kurigram／Pyrogram 用戶端管理，採 SQLite 格式 | 保存 Telegram 登入工作階段，以供後續重用 |
| 使用者與全域設定 | YAML 檔案 | 保存 API 參數、下載目錄、並行數、機器人及其他設定 |
| 下載任務與執行統計 | 記憶體 | 維護目前佇列、任務狀態、進度與統計；不會持久化為應用程式資料庫 |
| 下載內容 | 設定的下載目錄 | 保存已完成的媒體檔案 |
| 未完成的下載 | 暫存目錄中的 `.temp` 檔案 | 保存部分下載內容，以供續傳處理 |
| 上傳續傳狀態 | 暫存目錄中的 `<檔案 SHA-256>.json` 檔案 | 記錄上傳分塊資訊，以供上傳續傳 |
| 日誌、網頁工作階段權杖與遠端設定快取 | 本機檔案 | 記錄執行日誌、網頁工作階段狀態與遠端設定快取 |
| 統計報表 | 可選的 CSV 檔案 | 匯出下載、連結或上傳統計 |

**資料庫結論：**應用程式本身沒有用於下載任務、使用者或統計資訊的業務資料庫。SQLite 用於 Telegram 用戶端的工作階段儲存；應用程式的任務狀態主要保存在記憶體中，部分續傳狀態與設定則儲存在一般檔案中。
