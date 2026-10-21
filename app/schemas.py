from enum import Enum
# Enum（列舉）：把允許的選項先一個個列出來的清單型別

from pydantic import BaseModel
# 從 pydantic（資料驗證工具）匯入 BaseModel（基礎模型）

from typing import Optional
# Optional（選擇性）= 代表這個欄位可以填，也可以不填

# 建立任務時，使用者要傳進來的資料
# （沒有 id，因為 id 由資料庫自動產生）
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False

# 回傳任務時的完整格式
# 繼承 TaskCreate，再多一個 id 欄位
class TaskRead(TaskCreate):
    id: int
    model_config = {"from_attributes": True}
# 讓 Pydantic 能從資料庫物件讀資料，沒有這行回傳時會出錯

# 註冊時，使用者要傳進來的資料
class UserCreate(BaseModel):
    username: str
    password: str
# 登入成功後，回傳給使用者的 JWT 手環
class Token(BaseModel):
    access_token: str     # 手環的字串內容
    token_type: str       # 手環的類型，固定是 "bearer"
    # bearer（持有者）= 表示「持有這個手環的人」的意思


class SortField(str, Enum):  # SortField（排序欄位）：繼承 Enum，代表一張限定選項的清單
    id = "id"  # 允許用 id 排序，等號右邊是網址要傳的字
    title = "title"  # 允許用 title（標題）排序
    done = "done"  # 允許用 done（是否完成）排序
