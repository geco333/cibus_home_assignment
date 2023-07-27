from pydantic import BaseModel


class RequestUser(BaseModel):
    username: str
    password: str


class DbUser(RequestUser):
    id: int
    hashed_password: str
    is_active: bool

    class Config:
        orm_mode = True
