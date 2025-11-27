# 1. 基底映像檔：使用官方 Python 3.10 輕量版 (基於 Debian Linux)
FROM python:3.10-slim

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 設定環境變數
# 讓 Python 的 log 直接輸出到終端機 (方便除錯)
ENV PYTHONUNBUFFERED=1
# 告訴 Flask 這是生產環境
ENV FLASK_ENV=production

# 4. 安裝系統依賴 (有些 Python 套件需要編譯工具)
# 如果你的 requirements.txt 安裝時報錯，可能需要這行，通常 slim 版需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. 複製食材清單並安裝
# (先複製清單是為了利用 Docker 的快取機制，加速之後的 build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 複製剩下的所有程式碼
COPY . .

# 7. 宣告這個容器會使用 5000 port
EXPOSE 5000

# 8. 啟動指令 (使用 Gunicorn)
# -w 4 : 開啟 4 個工作程序 (Workers) 處理請求
# -b 0.0.0.0:5000 : 綁定所有 IP 的 5000 port
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]