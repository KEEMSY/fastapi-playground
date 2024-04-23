from typing import Optional


class PLException(Exception):
    def __init__(self, detail: Optional[str], status_code: int = 400, code: str = "D0000"):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class BLException(Exception):
    def __init__(self, detail: Optional[str], status_code: int = 400, code: str = "D0000"):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class DLException(Exception):
    def __init__(self, detail: Optional[str], status_code: int = 500, code: str = "D0000"):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)
