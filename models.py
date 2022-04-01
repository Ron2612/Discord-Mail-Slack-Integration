import datetime

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base



class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String)
    password = Column(String)

    logs = relationship("Logs", back_populates="editor")


class Logs(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, ForeignKey("users.username"))
    date_time = Column(String)
    action_performed = Column(String)

    editor = relationship("User", back_populates="logs")
