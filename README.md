# Task Manager API

用 FastAPI + PostgreSQL 寫的任務管理 API。註冊登入後，每個人只看得到、改得到自己的任務。

這是我練後端用的基礎框架。題目故意選最簡單的任務管理，重點放在做什麼主題都會用到的東西：資料隔離、資料庫遷移、測試、CI、錯誤處理、設定管理、分層。之後要換主題，換掉資料表和業務規則就好。

## 目錄

- [技術棧](#技術棧)
- [系統架構](#系統架構)
- [主要流程](#主要流程)
- [設計決策](#設計決策)
  - [1. 資料隔離 — 只能碰自己的任務](#1-資料隔離--只能碰自己的任務)
  - [2. 三步遷移 — 先放寬，再收緊](#2-三步遷移--先放寬再收緊)
  - [3. 外鍵命名 — 讓降級跑得動](#3-外鍵命名--讓降級跑得動)
  - [4. 啟動時自動遷移 — 遷移成功才開門](#4-啟動時自動遷移--遷移成功才開門)
  - [5. CI 和 Docker — 各在乾淨環境測一次](#5-ci-和-docker--各在乾淨環境測一次)
  - [6. 統一錯誤格式 — code 給程式，message 給人](#6-統一錯誤格式--code-給程式message-給人)
  - [7. 集中設定 — 缺設定就不啟動](#7-集中設定--缺設定就不啟動)
  - [8. 分層 — router 管 HTTP，service 管規則](#8-分層--router-管-httpservice-管規則)
  - [9. JWT 錯誤處理 — 只抓 JWTError](#9-jwt-錯誤處理--只抓-jwterror)
- [資料模型](#資料模型)
- [API 端點](#api-端點)
- [目錄結構](#目錄結構)
- [本地開發](#本地開發)
- [測試與 CI](#測試與-ci)
- [實測：索引效能](#實測索引效能)
- [目前需要補足的地方](#目前需要補足的地方)
- [接下來](#接下來)

## 技術棧

| 層 | 技術 |
|---|---|
| Web 框架 | FastAPI + Uvicorn，全程 async |
| 語言 | Python 3.11（Docker、CI） |
| 資料庫 | PostgreSQL 15 + SQLAlchemy 2.0（async）+ psycopg 3 |
| 遷移 | Alembic（不用 `create_all`，所有結構變更都走遷移） |
| 認證 | JWT（python-jose，HS256，30 分鐘過期）+ bcrypt（passlib） |
| 設定 | pydantic-settings（啟動時檢查必要設定） |
| 測試 | pytest + pytest-asyncio + httpx |
| 容器 | Docker + Docker Compose，啟動時自動跑遷移 |
| CI | GitHub Actions：遷移 → `alembic check` → pytest |

## 系統架構

兩個容器：`api` 和 `db`。

### 一個請求怎麼走

```
 client
   │  POST /tasks   Authorization: Bearer <token>
   ▼
┌─ api   uvicorn app.main:app   :8000 ───────────────────────────────────┐
│  1. auth      get_current_user          no / bad token  ──▶ 401        │
│  2. validate  schemas.TaskCreate        bad input       ──▶ 422        │
│  3. router    routers/tasks.py                                         │
│  4. service   services/task_service.py  not yours       ──▶ 404        │
│  5. response  schemas.TaskRead                                         │
│                                                                        │
│  any error ──▶ errors.py ──▶ {"error": {"code", "message"}}            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  SQLAlchemy (async)
                                    ▼
┌─ db   PostgreSQL 15 ───────────────────────────────────────────────────┐
│  users  id | username (UNIQUE) | hashed_password                       │
│    │ 1 : N                                                             │
│  tasks  id | title | description | done | user_id (FK, INDEX)          │
└────────────────────────────────────────────────────────────────────────┘
```

1. **驗身分**：沒帶 token、token 壞了或過期、帳號不在了，都回 401
2. **檢查參數**：格式不對回 422。身分先驗，所以沒登入又亂送資料，回的是 401
3. **router**：只負責收和回，不碰資料庫
4. **service**：任務主人一律用 token 裡的人；不是你的任務回 404
5. **回傳**：只送 `TaskRead` 裡有的欄位，`user_id` 不會送出去

不管哪一步出錯，都由 `errors.py` 轉成同一個格式。

### 容器怎麼啟動

```
docker compose up
┌─ db ───────────────────────────────────────────────────────┐
│  pg_isready every 5s  ──▶  healthy                         │
└─────────┬──────────────────────────────────────────────────┘
          ▼
┌─ api ──────────────────────────────────────────────────────┐
│  config.Settings()       missing setting  ──▶ exit         │
│  alembic upgrade head    fails            ──▶ exit         │
│  exec uvicorn app.main:app                                 │
└────────────────────────────────────────────────────────────┘
```

資料庫準備好才啟動 api。設定缺了或遷移失敗，api 都不會開。

### CI 怎麼驗

```
PR / push to main
   ▼
┌─ GitHub Actions   empty postgres:15 ───────────────────────┐
│  alembic upgrade head  ──▶  alembic check  ──▶  pytest     │
└────────────────────────────────────────────────────────────┘
```

每個 PR 都在全新的資料庫上跑一遍，有一步失敗就不合併。

## 主要流程

一個使用者從註冊到管理任務，系統實際走的路：

1. **註冊**：`POST /register`。檢查帳號沒人用，密碼用 bcrypt 雜湊後才存，回傳 token。
2. **登入**：`POST /login`。帳號不存在或密碼錯，都回同一個錯誤，不讓人猜帳號存不存在。
3. **帶 token 操作任務**：每個 `/tasks` 請求先過 `get_current_user`：沒帶 token 回 `NOT_AUTHENTICATED`，解不開或過期回 `INVALID_TOKEN`。
4. **新增任務**：任務的主人一律從 token 拿，不看請求內容。
5. **查詢、修改、刪除**：查詢條件同時比對任務編號和主人，不是你的就跟不存在一樣，回 404。
6. **出錯時**：不管哪一層出錯，回應都是 `{"error": {"code", "message"}}`。

## 設計決策

每個決策都照同一個順序寫：遇到什麼問題、怎麼做、怎麼確認。

### 1. 資料隔離 — 只能碰自己的任務

**問題**：一開始任務沒記錄是誰的，改網址裡的編號就能讀改刪別人的任務（IDOR）。這是我功能做完後自己檢查發現的。

**做法**：
- 任務加上 `user_id`，而且**只從 token 拿**，不讓使用者自己傳
- 查一筆、改、刪都走同一個 `get_own_task`，查詢時就同時比對編號和主人
- 不是你的就回 404，不回 403。回 403 等於告訴對方「這筆存在」

**驗證**：先寫測試，A 建任務、B 去讀改刪。修之前測試失敗（`assert 200 == 404`），確定漏洞是真的；修完通過。

### 2. 三步遷移 — 先放寬，再收緊

**問題**：想把 `user_id` 改成必填，但舊任務都沒有值，直接改會失敗。

**做法**：
1. 先加可以空的 `user_id`，把舊任務補上主人
2. 程式開始寫入 `user_id`
3. 確認沒有空值，才改成必填

一次做完的話，失敗了沒有退路。拆開來每一步都能單獨退回。

**驗證**：改必填前先查空值是 0；在演習資料庫跑過升級、降級、再升級，筆數不變；`alembic check` 確認模型和資料庫一致。

### 3. 外鍵命名 — 讓降級跑得動

沒取名的外鍵，Alembic 自動產生的降級會失敗。所以我明確取名 `fk_tasks_user_id_users`。

學到的：自動產生的遷移只是草稿，要自己讀過、實際降級一次才算數。

### 4. 啟動時自動遷移 — 遷移成功才開門

啟動指令是 `alembic upgrade head && exec uvicorn app.main:app`：
- `&&`：遷移成功才啟動 API
- `exec`：讓 uvicorn 直接收到停止訊號。沒加之前關容器要等 10.4 秒，加了變 0.8 秒

**驗證**：`docker compose down -v` 清空後重新 `up --build`，確認遷移都有跑、欄位是 `not null`。

目前只有一個 API 容器。如果開多個，可能同時跑遷移打架，這個還沒處理。

### 5. CI 和 Docker — 各在乾淨環境測一次

我電腦上有舊資料、裝好的套件，結果可能剛好是對的。而且 CI 不看 Dockerfile，Docker 也不跑測試。

- **CI**：每個 PR 在全新機器上跑 `alembic upgrade head`、`alembic check`、`pytest`
- **Docker**：改到套件、設定或 Docker 檔案時，本機實際啟動一次

### 6. 統一錯誤格式 — code 給程式，message 給人

**問題**：FastAPI 預設的錯誤格式不一致，有的 `detail` 是字串、422 是清單，沒登入時還是英文 `Not authenticated`。前端很難處理。

**做法**：
- 全部改成 `{"error": {"code", "message"}}`，處理邏輯集中在 `app/errors.py`
- 「沒帶 token」和「token 無效」分開，前端才知道要叫人登入還是重新登入

**驗證**：每種錯誤都有測試比對完整回應，共 8 個。

### 7. 集中設定 — 缺設定就不啟動

**問題**：原本用 `os.getenv` 讀設定，找不到只會回 `None`，不會報錯。`.env` 忘了寫 `SECRET_KEY`，伺服器照樣啟動，等到有人登入才壞。

**做法**：
- 用 pydantic-settings 在 `app/config.py` 定義設定，啟動時檢查一次
- `SECRET_KEY` 故意不給預設值。給了假的預設值，忘記設定時就會用假密鑰上線

**驗證**：拿掉 `.env` 啟動，會直接報錯，並且一次列出缺的兩個設定。

### 8. 分層 — router 管 HTTP，service 管規則

**問題**：router 什麼都做。「找不到就 404」寫了 3 次，「用帳號查使用者」也寫了 3 次。

**做法**：
- router 只管 HTTP，規則和資料庫操作都放 service
- 程式碼搬進 `app/`，import 都用 `app.` 開頭，避免和別的套件撞名

**幾個取捨**：
- **沒加 repository 層**：SQLAlchemy 已經把資料庫細節包好了，也沒有換資料庫的打算，多一層只是多轉一手。之後真的需要再拆
- **找不到要不要報錯，看情況**：`get_own_task` 找不到一定是 404，直接報錯；`get_user_by_username` 找不到時回 `None`，因為註冊時「找不到」反而是好事
- service 直接丟 `AppError(404, ...)`，嚴格說它知道了一點 HTTP。現在這個規模，這樣最簡單

**驗證**：每搬一個端點就跑一次測試、各自 commit。搬完確認 router 不再直接碰資料庫。搬進 `app/` 後再跑 `alembic check` 和 Docker。

### 9. JWT 錯誤處理 — 只抓 JWTError

**問題**：解 token 時用 `except Exception`，什麼錯都變成 401「token 無效」。如果是系統自己壞了，使用者看到的卻是 token 無效，我也很難發現。

**做法**：改成只抓 `JWTError`，其他錯誤照常變成 500。

| 情況 | 改之前 | 改之後 |
|---|---|---|
| 亂寫的 token | 401 | 401 |
| 過期的 token | 401 | 401 |
| 系統出錯 | 401（被蓋掉） | 500 |

**驗證**：怕範圍縮太小、把「過期」也漏掉，所以改之前先補了「過期 token 要回 401」的測試，改完還是通過。

## 資料模型

| 表 | 欄位 |
|---|---|
| users | `id`、`username`（不可重複）、`hashed_password`（bcrypt，不存明文） |
| tasks | `id`、`title`、`description`（可空）、`done`（預設 false，不可空）、`user_id`（外鍵 → `users.id`，有索引，不可空） |

結構由 Alembic 管理，目前 6 個遷移。

## API 端點

互動式文件：http://localhost:8000/docs

### 使用者

| 方法 | 網址 | 說明 |
|---|---|---|
| POST | /register | 註冊，回傳 token；帳號重複回 400 |
| POST | /login | 登入（表單格式），回傳 token |

### 任務（都要登入）

| 方法 | 網址 | 說明 |
|---|---|---|
| GET | /tasks | 列出自己的任務，可用 `limit`、`offset`、`done`、`sort_by`（`id` / `title` / `done`） |
| POST | /tasks | 新增任務 |
| GET | /tasks/{id} | 查一筆（不是自己的回 404） |
| PUT | /tasks/{id} | 修改 |
| DELETE | /tasks/{id} | 刪除 |

### 錯誤格式

所有錯誤長一樣：

```json
{"error": {"code": "TASK_NOT_FOUND", "message": "找不到這筆任務"}}
```

422 會多一個 `details`，告訴你哪個欄位有問題：

```json
{"error": {"code": "VALIDATION_ERROR", "message": "請求資料格式錯誤",
           "details": [{"field": "limit", "message": "超過允許的最大值"}]}}
```

| 狀態碼 | code | 情況 |
|---|---|---|
| 400 | `USERNAME_TAKEN` | 帳號已經有人用 |
| 401 | `NOT_AUTHENTICATED` | 沒帶 token |
| 401 | `INVALID_TOKEN` | token 無效、過期，或帳號已不存在 |
| 401 | `INVALID_CREDENTIALS` | 帳號或密碼錯（不說是哪個） |
| 404 | `TASK_NOT_FOUND` | 任務不存在，或不是你的 |
| 404 | `NOT_FOUND` | 網址打錯 |
| 405 | `METHOD_NOT_ALLOWED` | 方法用錯 |
| 422 | `VALIDATION_ERROR` | 參數格式不對 |

## 目錄結構

```
app/
├── main.py              # 把所有東西組起來：建 app、登記錯誤處理、掛 router
├── config.py            # 設定，啟動時檢查
├── database.py          # 資料庫連線與 session
├── models.py            # 資料表
├── schemas.py           # 請求和回應的格式
├── errors.py            # 統一錯誤格式
├── routers/             # HTTP 層
│   ├── auth.py          #   註冊、登入、get_current_user
│   └── tasks.py         #   任務 CRUD
└── services/            # 業務規則和資料庫操作
    ├── auth_service.py  #   查使用者、密碼雜湊、簽發與解開 token
    └── task_service.py  #   只能碰自己的任務、篩選排序分頁

alembic/                 # 資料庫遷移
test_tasks.py            # 測試
.github/workflows/       # CI
```

## 本地開發

### 1. 建立 .env

```bash
cp .env.example .env
```

打開 `.env` 填入 `SECRET_KEY`，產生方式：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. 啟動

```bash
docker compose up --build
```

會起兩個容器：`api`（:8000）和 `db`（PostgreSQL）。`api` 啟動時會先跑遷移，成功才開始接請求。

### 3. 跑一遍流程

需要 `jq`（用來從回應裡取出 token）。

```bash
# 註冊
curl -X POST localhost:8000/register -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret123"}'

# 登入，拿 token
TOKEN=$(curl -s -X POST localhost:8000/login \
  -d 'username=alice&password=secret123' | jq -r .access_token)

# 新增任務
curl -X POST localhost:8000/tasks -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"買牛奶"}'

# 列出任務（只看未完成、依標題排序）
curl "localhost:8000/tasks?done=false&sort_by=title" -H "Authorization: Bearer $TOKEN"

# 不帶 token → 401 NOT_AUTHENTICATED
curl -i localhost:8000/tasks
```

## 測試與 CI

```bash
pytest -v
```

25 個測試，包含 CRUD、分頁篩選排序、存取別人的任務要回 404、每種錯誤的回應格式、過期 token。

測試連的是本機的 `testdb`，連線字串目前寫死在 `test_tasks.py`。

GitHub Actions（`.github/workflows/test.yml`）在開 PR 和推到 main 時跑：

1. 起一個全新的 PostgreSQL 15
2. `alembic upgrade head`：從空資料庫建出所有表
3. `alembic check`：確認模型和資料庫沒有差異
4. `pytest -v`

## 實測：索引效能

環境：本機 WSL2、PostgreSQL 18，`tasks` 約 10 萬筆（10 個使用者各 1 萬筆，另一個只有 3 筆）。用 `EXPLAIN ANALYZE` 量。

| `user_id = 1`（只有 3 筆）`ORDER BY id LIMIT 20` | 走法 | 讀取頁數 | 時間（3 次中位數） |
|---|---|---|---|
| 加 `user_id` 索引前 | 整張表掃一遍 | 934 | 58.96 ms |
| 加 `user_id` 索引後 | 走索引 | 3 | 0.17 ms |

| `user_id = 5`（1 萬筆）`ORDER BY id LIMIT 20` | 走法 | 讀取頁數 | 時間 |
|---|---|---|---|
| 加索引前 | 沿著 id 索引走，湊滿 20 筆就停 | 4 | 0.22 ms（3 次中位數） |
| 加索引後 | 一樣，沒用新索引 | 4 | 0.14 ms（量 1 次） |
| 拿掉重複的 id 索引後 | 改走主鍵 | 4 | 0.08 ms（量 1 次） |

資料少的使用者差很多，因為不用掃整張表；資料多的沒差，因為沿 id 走很快就湊滿 20 筆。

時間的變動很大（同一個查詢量到 7.6、64.1、59.0 ms），所以我主要看讀取頁數。

### 篩選和排序

另外把 `user_id = 5` 的前 100 筆改成 `done = true`（1%，集中在前面），`user_id = 6` 隔一筆改一筆（50%）。每個都量 3 次。

| 查詢（`LIMIT 20`） | 統計資料 | 讀取頁數 |
|---|---|---|
| `user_id = 5 AND done = true ORDER BY id` | 過時 | 948 |
| `user_id = 6 AND done = true ORDER BY id` | 過時 | 998 |
| `user_id = 5 AND done = true ORDER BY id` | 已更新 | 41 |
| `user_id = 6 AND done = true ORDER BY id` | 已更新 | 85～86 |
| `user_id = 6 ORDER BY id`（不篩選） | 已更新 | 42 |
| `user_id = 6 AND done = true ORDER BY title, id` | 已更新 | 1001 |

- 大量 `UPDATE` 之後忘了跑 `ANALYZE`，資料庫以為只有 1 筆符合，選錯了路。更新統計後就正常了。前兩列是我踩到的坑，不能拿來當結論。
- 統計正確時，篩 `done` 讀的頁數大約兩倍，還不用另外加 `done` 索引。
- 用 `title` 排序要讀 1001 頁，因為 `title` 沒索引。我還沒量加索引對寫入的影響，所以先不加。

這些數字的限制：資料是我自己灌的，分布很整齊，跟真實情況不一樣；而且只量了讀取，沒量寫入。

## 目前需要補足的地方

- 測試和 `docker-compose.yml` 裡還寫死了開發用的資料庫密碼
- 未預期的錯誤（500）還沒用統一格式
- 登入時，帳號不存在會比密碼錯誤回得快，可能被拿來猜帳號是否存在
- 本機 Python 3.14，CI 和 Docker 是 3.11
- 還沒部署上線

## 接下來

1. 部署上線
2. 測試的資料庫設定改用環境變數
3. 處理兩個人同時改同一筆任務（交易、樂觀鎖），加上結構化日誌
