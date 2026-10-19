from fastapi import FastAPI, Request  # FastAPI：登記函式要用；Request：櫃台會收到的請求

from fastapi.responses import JSONResponse  # 組出要回傳的 JSON

from fastapi.exceptions import RequestValidationError  # FastAPI 檢查參數失敗時丟出的錯誤



class AppError(Exception):  # 自訂錯誤類別，繼承 Exception 才能被 raise
    def __init__(self, status_code: int, code: str, message: str):  # 建立錯誤時要給三個資料
        super().__init__(message)  # 先讓父類別 Exception 記住訊息，印錯誤時看得到
        self.status_code = status_code  # HTTP 狀態碼，例如 404
        self.code = code  # 英文錯誤代碼，給程式判斷用，例如 TASK_NOT_FOUND
        self.message = message  # 中文錯誤訊息，給人看，例如「找不到這筆任務」


VALIDATION_MESSAGES = {  # 翻譯對照表：Pydantic 的錯誤種類（type）→ 中文訊息
    "missing": "此欄位為必填",  # 沒填
    "int_parsing": "必須是整數",  # 例如 limit=abc
    "string_type": "必須是文字",  # 例如 title 傳了數字
    "less_than_equal": "超過允許的最大值",  # 例如 limit=101
    "greater_than_equal": "低於允許的最小值",  # 例如 limit=0
    "enum": "不是允許的選項",  # 例如 sort_by 不在白名單
    "json_invalid": "JSON 格式錯誤",  # 送來的 JSON 本身壞掉
}


async def app_error_handler(request: Request, exc: AppError):  # 櫃台：處理 AppError（從 main.py 搬來，拿掉了 @app）
    return JSONResponse(  # 回傳 JSON
        status_code=exc.status_code,  # 狀態碼用錯誤身上帶的
        content={"error": {"code": exc.code, "message": exc.message}},  # 統一格式
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):  # 櫃台：處理 422 參數錯誤
    details = [  # 把每一項錯誤翻譯成 {field, message}
        {"field": str(err["loc"][-1]), "message": VALIDATION_MESSAGES.get(err["type"], "格式不正確")}  # 取欄位名、查中文
        for err in exc.errors()  # exc.errors() = FastAPI 收集到的錯誤清單，一項一項拿出來
    ]
    return JSONResponse(  # 回傳 JSON
        status_code=422,  # 422（參數不合格）
        content={"error": {"code": "VALIDATION_ERROR", "message": "請求資料格式錯誤", "details": details}},  # 多了 details
    )



def register_exception_handlers(app: FastAPI):  # 登記函式：把所有櫃台接到 app 上
    app.add_exception_handler(AppError, app_error_handler)  # 作用等同原本的 @app.exception_handler(AppError)
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # 參數錯誤交給 422 櫃台



