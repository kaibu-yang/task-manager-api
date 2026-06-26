# Task Manager API

一個用 **FastAPI + PostgreSQL** 打造的任務管理系統 API，支援使用者註冊、JWT 身份驗證和完整的任務 CRUD 功能。

## 技術清單

- **FastAPI** — Python 後端 API 框架（非同步）
- **PostgreSQL** — 關聯式資料庫
- **SQLAlchemy** — ORM 資料庫工具
- **JWT** — 使用者身份驗證
- **Docker** — 容器化部署
- **pytest** — 自動化測試

## 功能

- 使用者註冊 / 登入（JWT 驗證）
- 任務新增、查詢、修改、刪除（CRUD）
- 登入保護：沒有 JWT 手環無法操作任務
- Docker 一鍵啟動

## 快速啟動（Docker）

```bash
# 複製專案
git clone https://github.com/kaibu-yang/task-manager-api.git
cd task-manager-api

# 建立 .env 檔案
cp .env.example .env
# 編輯 .env，填入你的 SECRET_KEY

# 一鍵啟動
docker compose up --build
```

啟動後打開：http://localhost:8000/docs

## API 端點

### 使用者
| 方法 | 網址 | 說明 |
|------|------|------|
| POST | /register | 註冊新使用者 |
| POST | /login | 登入，取得 JWT |

### 任務（需要登入）
| 方法 | 網址 | 說明 |
|------|------|------|
| GET | /tasks | 查詢全部任務 |
| POST | /tasks | 建立新任務 |
| GET | /tasks/{id} | 查詢單筆任務 |
| PUT | /tasks/{id} | 更新任務 |
| DELETE | /tasks/{id} | 刪除任務 |

## 執行測試

```bash
pytest test_tasks.py -v
```
