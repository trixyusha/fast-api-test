from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .connection import Base

from datetime import datetime

class User(Base):
    __tablename__ = 'users'
        
    ID: Mapped[int] = mapped_column(primary_key = True)
    UserName: Mapped[str] = mapped_column(nullable = True)
    login: Mapped[str] = mapped_column(nullable = False)
    password: Mapped[str] = mapped_column(nullable = True)
    admin: Mapped[bool] = mapped_column(nullable = False, default=False)

class Task(Base):
    __tablename__ = 'tasks'
    
    ID: Mapped[int] = mapped_column(primary_key = True)
    TaskName: Mapped[str] = mapped_column(nullable = False)
    TaskDescription: Mapped[str] = mapped_column(nullable = True)
    CreateDate: Mapped[datetime] = mapped_column(nullable = False)
    UpdateDate: Mapped[datetime] = mapped_column(nullable = True)
    Author: Mapped[int] = mapped_column(ForeignKey('users.ID'))

class Permission(Base):
    __tablename__ = 'permissions'
    
    ID: Mapped[int] = mapped_column(primary_key = True)
    read: Mapped[bool] = mapped_column(nullable = False, default=False)
    update: Mapped[bool] = mapped_column(nullable = False, default=False)
    task: Mapped[int] = mapped_column(ForeignKey('tasks.ID'))
    user: Mapped[int] = mapped_column(ForeignKey('users.ID'))