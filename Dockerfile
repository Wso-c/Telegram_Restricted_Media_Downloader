FROM python:3.13.2-slim

# 設定工作目錄。
WORKDIR /app

# 設定環境變量。
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    XDG_CONFIG_HOME=/app \
    TRMD_WEB_HOST=0.0.0.0 \
    TERM=xterm-256color

# 安裝系統依賴+Python依賴，編譯後清理，全部合併為一個RUN層以減小鏡像體積。
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
        libmediainfo0v5 \
        gcc \
        g++ \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
# 建立設定目錄、下載目錄、會話目錄、臨時目錄、可執行程式目錄、統計表目錄。
RUN mkdir -p /app/TRMD /app/downloads /app/sessions /app/temp /app/form

# 複製項目檔案。
COPY main.py .
COPY module/ ./module/

# 設定掛載點。
VOLUME ["/app/TRMD", "/app/downloads", "/app/sessions", "/app/temp", "/app/form"]

# 聲明網頁面板的預設連接埠。
EXPOSE 2921

# 執行應用。
# --config: 用戶設定存到掛載目錄，容器重啟不丟失。
# 網頁面板預設啟用，連接埠預設為2921，可通過--port指定。
# session_directory和temp_directory可在config.yaml中自行設定。
CMD ["python", "main.py", "--config", "/app/TRMD/config.yaml", "--port", "2921"]
