Flask Super Calendar (全方位個人管理系統)
這是一個基於 Python Flask 開發的多功能個人管理儀表板。整合了行事曆、飲食追蹤、重訓紀錄、日記撰寫以及課表管理功能。支援多使用者系統，並整合 Google 與 LINE 第三方登入。

✨ 主要功能 (Features)
🔐 多元身分驗證：

支援 Google 與 LINE 快速登入 (OAuth 2.0)。

帳號關聯 (Account Linking)：透過 Email 自動辨識並連結不同登入方式的帳號。

完整的權限隔離，每位使用者僅能存取自己的資料。

📅 行事曆系統：

月檢視、週檢視、日檢視。

支援多種事項類型（工作、提醒、活動）。

🍱 飲食追蹤：

紀錄每日餐點（熱量、蛋白質、脂肪、碳水）。

智慧建議：輸入時自動跳出歷史輸入過的食物與營養素。

每日營養目標進度條視覺化。

💪 重訓日誌：

紀錄訓練部位、動作、重量與次數。

自動計算總訓練量，並追蹤該動作的 歷史最大重量 (PR)。

📝 生活日記：

整合 Trix Editor，支援富文本 (Rich Text) 編輯。

支援日記的新增、編輯與刪除。

⏳ 重要事項：

追蹤重要日期的倒數天數（如考試、報告截止日）。

🎓 課表系統：

支援節次合併顯示 (Rowspan)。

🛠️ 技術棧 (Tech Stack)
後端：Python 3.10+, Flask

資料庫：SQLite, SQLAlchemy (ORM)

前端：HTML5, Jinja2 Templates, JavaScript

UI 框架：Pico.css (簡約、支援深色模式)

編輯器：Trix Editor

認證套件：Flask-Login, Authlib

部署：Docker, Gunicorn

🚀 快速開始 (Quick Start)
1. 環境設定
請確保已安裝 Python 3.10 以上版本。

Bash

# 1. 複製專案
git clone https://github.com/your-username/super-calendar.git
cd super-calendar

# 2. 建立虛擬環境 (建議)
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 安裝依賴套件
pip install -r requirements.txt
2. 設定環境變數 (.env)
在專案根目錄建立一個 .env 檔案，填入你的 API 金鑰：

Ini, TOML

# .env 檔案內容

# Flask 安全金鑰 (請設為隨機亂碼)
SECRET_KEY=your-super-secret-key

# Google Login 設定 (至 GCP Console 申請)
GOOGLE_CLIENT_ID=你的Google_Client_ID
GOOGLE_CLIENT_SECRET=你的Google_Client_Secret

# LINE Login 設定 (至 LINE Developers 申請)
LINE_CLIENT_ID=你的Channel_ID
LINE_CLIENT_SECRET=你的Channel_Secret

# 開發環境設定 (本地開發時設為 1，正式上線 HTTPS 環境請移除)
OAUTHLIB_INSECURE_TRANSPORT=1
注意：Callback URL 請在 Google/LINE 後台設定為：

Google: http://127.0.0.1:5000/auth/google/callback

LINE: http://127.0.0.1:5000/auth/line/callback

3. 初始化資料庫與啟動
Bash

# 啟動應用程式 (首次啟動會自動建立 calendar.db)
python app.py
打開瀏覽器訪問：http://127.0.0.1:5000

🐳 Docker 部署 (推薦)
本專案已容器化，支援使用 Docker 快速部署。

1. 建置映像檔 (Build)
Bash

docker build -t super-calendar .
2. 執行容器 (Run)
請確保 .env 檔案已建立，或在指令中加入 -e 參數。此指令會掛載 instance 資料夾以保存資料庫。

Bash

docker run -d \
  --name my-calendar \
  --restart always \
  -p 5000:5000 \
  -v $(pwd)/instance:/app/instance \
  --env-file .env \
  super-calendar
📝 開發筆記與常見問題
LINE Login 錯誤 (UnsupportedAlgorithmError)
LINE 使用 ES256 演算法，若 Authlib 報錯，請確保已安裝 cryptography 套件，或使用本專案已實作的 requests 手動驗證方案。

Callback URL 設定
若使用 Cloudflare Tunnel 或 Microsoft Dev Tunnels 進行外部測試：

請務必將公開網址 (如 https://xxx.trycloudflare.com/auth/...) 加入 Google/LINE 後台的白名單。

程式已包含 ProxyFix 設定，可正確處理 HTTPS 代理。

📜 授權 (License)
MIT License. 僅供學術交流與個人使用。