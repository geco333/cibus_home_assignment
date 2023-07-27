import enum
from enum import Enum

from pydantic import BaseModel


class Vote(Enum):
    UP = "up"
    DOWN = "down"


class MessageBase(BaseModel):
    message: str


class MessageVote(BaseModel):
    vote: Vote


class DbMessage(MessageBase):
    id: int
    author_id: int
    vote_count: int

    class Config:
        orm_mode = True
