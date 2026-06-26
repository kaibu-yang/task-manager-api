FROM python:3.11-slim
# FROM（從）= 以 python:3.11-slim 這個基底映像檔開始
# python:3.11-slim = 官方提供的精簡版 Python 環境
# slim（精簡）= 比完整版小很多，適合部署用

WORKDIR /app
# WORKDIR（工作目錄）= 設定容器裡的工作資料夾為 /app
# 之後所有指令都在 /app 這個資料夾裡執行

COPY requirements.txt .
# COPY（複製）= 把 requirements.txt 複製進容器的 /app 資料夾

RUN pip install -r requirements.txt
# RUN（執行）= 在容器裡執行這個指令
# pip install -r requirements.txt = 安裝所有套件

COPY . .
# COPY . . = 把整個專案複製進容器

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD（指令）= 容器啟動時執行的指令
# --host 0.0.0.0 = 讓外部可以連進來（不只是本機）
# --port 8000 = 用 8000 號埠