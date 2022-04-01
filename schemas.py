import datetime
from typing import List

from pydantic import BaseModel


class Log(BaseModel):
    log_id: int
    name: str
    time: datetime.datetime


class User(BaseModel):
    user_id: int
    name: str
    email: str
    password: str

