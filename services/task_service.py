from sqlalchemy import select  # 查詢資料庫的工具
from sqlalchemy.ext.asyncio import AsyncSession  # 跟資料庫對話的工具（這裡只用來標示型別）

import models  # 資料表定義（Task、User）
from errors import AppError  # 自訂錯誤類別

from schemas import SortField, TaskCreate  # 排序欄位選項、建立任務的資料格式


async def get_own_task(db: AsyncSession, task_id: int, user: models.User) -> models.Task:  # 取出屬於這位使用者的任務
    result = await db.execute(select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user.id))  # 編號對、主人也對
    task = result.scalars().first()  # 找不到、或是別人的任務，都會是 None
    if task is None:  # 規則：找不到就是 404，由廚房統一判斷
        raise AppError(404, "TASK_NOT_FOUND", "找不到這筆任務")  # 以後不用在三個端點各寫一次
    return task  # 能走到這裡，保證是自己的任務


SORT_COLUMNS = {SortField.id: models.Task.id, SortField.title: models.Task.title, SortField.done: models.Task.done}  # 對照表：使用者選的字 → 對應的欄位


async def list_tasks(db: AsyncSession, user: models.User, limit: int, offset: int, done: bool | None, sort_by: SortField) -> list[models.Task]:  # 列出這位使用者的任務（一頁）
    query = select(models.Task).where(models.Task.user_id == user.id)  # 規則：只查自己的任務
    if done is not None:  # 有傳 done 才篩選；沒傳就跳過
        query = query.where(models.Task.done == done)  # 多加一條：done 等於傳進來的值
    query = query.order_by(SORT_COLUMNS[sort_by], models.Task.id).limit(limit).offset(offset)  # 依選的欄位排序，相同再依 id，最後切一頁
    result = await db.execute(query)  # 執行查詢
    return list(result.scalars().all())  # 轉成一般的 list 回傳


async def create_task(db: AsyncSession, user: models.User, data: TaskCreate) -> models.Task:  # 幫這位使用者新增一筆任務
    task = models.Task(**data.model_dump(), user_id=user.id)  # 規則：主人一律是目前的使用者，不能由請求內容指定
    db.add(task)  # 放進待存清單
    await db.commit()  # 真正寫進資料庫
    await db.refresh(task)  # 重新讀回來，拿到資料庫產生的 id 和時間戳記
    return task  # 回傳新建好的任務


