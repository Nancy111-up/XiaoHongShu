from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str | None = None
