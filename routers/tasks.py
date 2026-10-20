from enum import Enum 
# Enum（列舉）：把允許的選項先一個個列出來的清單型別

from fastapi import APIRouter, Depends, Query
# fastapi（API 框架）匯入三個工具：
# APIRouter（路由器）= 把端點分組管理的工具，等下會解釋
# Depends（依賴）= 讓端點自動取得資料庫連線
# Query（查詢參數設定工具）：設定網址 ? 後面的參數


from sqlalchemy.ext.asyncio import AsyncSession
# AsyncSession（非同步會話）= 跟資料庫對話的工具（非同步版）

from sqlalchemy import select
# select（選取）= 用來查詢資料庫的工具

from database import get_db
# 從 database.py 匯入 get_db（取得資料庫連線的函式）
from routers.auth import get_current_user
# 從 auth.py 匯入「驗票員」函式

import models
# 匯入 models.py（資料表定義）
 
from schemas import TaskCreate, TaskRead
# 從 schemas.py 匯入我們剛建立的兩個資料格式

from services import task_service
# 匯入廚房（業務規則都放在這裡）


router = APIRouter()
# router（路由器）= 用 APIRouter() 建立一個路由器物件
# 之後所有端點都掛在這個 router 上，而不是掛在 app 上

class SortField(str, Enum):  # SortField（排序欄位）：繼承 Enum，代表一張限定選項的清單
    id = "id"  # 允許用 id 排序，等號右邊是網址要傳的字
    title = "title"  # 允許用 title（標題）排序
    done = "done"  # 允許用 done（是否完成）排序


# Create（建立）：新增一筆任務
@router.post("/tasks", response_model=TaskRead)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # current_user 現在是整個 User
    task = models.Task(**payload.model_dump(), user_id=current_user.id)  # 請求內容加上主人，主人 id 來自 token
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

# Read（查全部）：列出所有任務
@router.get("/tasks", response_model=list[TaskRead])  # 網址 GET /tasks；回傳格式是 TaskRead 的清單
async def list_tasks(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), done: bool | None = None, sort_by: SortField = SortField.id, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # 新增 sort_by：只准 id、title、done，預設 id
    sort_columns = {SortField.id: models.Task.id, SortField.title: models.Task.title, SortField.done: models.Task.done}  # 對照表：使用者選的字 → 對應的欄位
    query = select(models.Task).where(models.Task.user_id == current_user.id).order_by(sort_columns[sort_by], models.Task.id).limit(limit).offset(offset)  # 只查自己的，依選的欄位排序，相同時再依 id 決勝負，再切一頁
    if done is not None:  # 有傳 done 才篩選；沒傳就跳過
        query = query.where(models.Task.done == done)  # 在原本的查詢上多加一條：done 等於傳進來的值
    result = await db.execute(query)  # 執行查詢
    return result.scalars().all()  # 取出這一頁的結果

# Read（查單筆）：依 id 查詢
@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = await task_service.get_own_task(db, task_id, current_user)  # 叫廚房拿任務；找不到廚房會直接回 404
    return task

# Update（更新）：改某一筆任務
@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, payload: TaskCreate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = await task_service.get_own_task(db, task_id, current_user)  # 叫廚房拿任務；找不到廚房會直接回 404
    task.title = payload.title
    task.description = payload.description
    task.done = payload.done
    await db.commit()
    await db.refresh(task)
    return task

# Delete（刪除）：刪掉某一筆任務
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = await task_service.get_own_task(db, task_id, current_user)  # 叫廚房拿任務；找不到廚房會直接回 404
    await db.delete(task)
    await db.commit()
    return {"message": f"任務 {task_id} 已刪除"}