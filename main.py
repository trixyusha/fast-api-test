from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Annotated
from database.models import datetime, Base, User, Task, Permission
from database.connection import engine, localsession
from sqlalchemy.orm import Session
from sqlalchemy import select, update, union_all
import hashlib

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()
Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserBase(BaseModel):
    name: str | None = None
    login: str
    admin: bool

class TaskBase(BaseModel):
    name: str
    description: str | None = None
    create_date: datetime
    update_date: datetime | None = None
    author: int | None = None

class PermissionBase(BaseModel):
    read: bool = False
    update: bool = False
    task: int
    user: int

def get_database():
    db = localsession()
    try:
        yield db
    finally:
        db.close()

db_depend = Annotated[Session, Depends(get_database)]

def password_hash(password: str) -> str:
    passwordhash = hashlib.sha256(password.encode()).hexdigest()
    return passwordhash

def check_pass(hash: str, passwd: str) -> bool:
    return hash == hashlib.sha256(passwd.encode()).hexdigest()

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: db_depend) -> User:
    user = db.scalar(select(User).where(User.login == token))
    if not user:
        raise HTTPException(status_code=401, detail='Неверные учетные данные', headers={"WWW-Authenticate": "Bearer"},)
    return user

def get_current_user_tasks(current_user: Annotated[User, Depends(get_current_user)], db: db_depend) -> list:
    tasks = db.scalars(select(Task.ID).where(Task.Author == current_user.ID))
    if not tasks:
        raise HTTPException(status_code=400, detail='Задач не найдено')
    return list(tasks)

def tasks_can_update(current_user: Annotated[User, Depends(get_current_user)], db: db_depend) -> list:
    query1 = select(Task).where(Task.Author == current_user.ID)
    query2 = (
        select(Task)
        .join(Permission, Task.ID == Permission.task)
        .where(Permission.user == current_user.ID)
        .where(Permission.update == True)
    )
    customquery = query1.union_all(query2)
    task_ids = db.execute(customquery).scalars().all()
    if not task_ids:
        raise HTTPException(status_code=400, detail='Задач не найдено')
    return task_ids

def tasks_can_read(current_user: Annotated[User, Depends(get_current_user)], db: db_depend) -> list:
    query1 = select(Task).where(Task.Author == current_user.ID)
    query2 = (
        select(Task)
        .join(Permission, Task.ID == Permission.task)
        .where(Permission.user == current_user.ID)
        .where(Permission.read == True)
    )
    customquery = query1.union_all(query2)
    task_ids = db.execute(customquery).scalars().all()
    if not task_ids:
        raise HTTPException(status_code=400, detail='Задач не найдено')
    return task_ids


@app.get('/token/')
async def get_token(token: Annotated[str, Depends(oauth2_scheme)]):
    return {'token': token}

@app.get('/users/')
async def get_users(current_user: Annotated[User, Depends(get_current_user)], db: db_depend):
    if current_user.admin:
        result = db.query(User).all()
        if not result:
            raise HTTPException(status_code=404, detail='В БД нет записей')
        return list(result)
    else: raise HTTPException(status_code=400, detail='Не хватает полномочий')

@app.get('/users/{user_id}')
async def get_user(user_id: int, current_user: Annotated[User, Depends(get_current_user)], db: db_depend):
    if current_user.admin:
        result = db.query(User).where(User.ID == user_id)
        if not result:
            raise HTTPException(status_code=404, detail='В БД нет записей')
        return result
    else: raise HTTPException(status_code=400, detail='Не хватает полномочий')

@app.get("/users/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@app.post('/token/')
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_depend):
    user_db = db.scalar(select(User).where(User.login == form_data.username))
    if not user_db:
        db_user = User(UserName=None, login=form_data.username, password=password_hash(form_data.password))
        db.add(db_user)
        user_db = db_user
        db.commit()
    elif not check_pass(user_db.password,form_data.password):
        raise HTTPException(status_code=400, detail="Неверный пароль")
    return {"access_token": user_db.login, "token_type": "bearer"}


@app.get('/tasks/')
async def get_tasks(current_user: Annotated[User, Depends(get_current_user)], 
                    task_ids: Annotated[list, Depends(tasks_can_read)],  db: db_depend):
    result = None
    if current_user.admin:
        result = db.query(Task).all()
    else:
        result = db.query(Task).filter(Task.ID.in_(task_ids)).all()
    if not result:
        raise HTTPException(status_code=404, detail='В бд нет записей/не хватает полномочий на просмотр')
    return result

@app.post('/tasks/')
async def create_task(current_user: Annotated[User, Depends(get_current_user)], task: TaskBase, db: db_depend):
    db_task = Task(TaskName=task.name, TaskDescription=task.description, CreateDate=datetime.now(), Author=current_user.ID)
    db.add(db_task)
    db.commit()
    return {'update': f'Задача добавлена'}

@app.put('/tasks/{task_id}')
async def update_task(task_id: int, current_user: Annotated[User, Depends(get_current_user)], 
                    task_ids: Annotated[list, Depends(tasks_can_update)],  db: db_depend, task_name: str = None, 
                    task_description: str = None):
    task_db = db.scalar(select(Task).where(Task.ID == task_id))
    if not task_db:
        raise HTTPException(status_code=400, detail='Задача не найдена')
    elif task_db.ID in task_ids:
        if task_name:
            task_db.TaskName = task_name
        if task_description:
            task_db.TaskDescription = task_description
        task_db.UpdateDate = datetime.now()
        db.commit()
        return {'update': f'Задача {task_id} обновлена'}
    else:
        raise HTTPException(status_code=400, detail='Не хватает прав на редактирование')

@app.delete('/tasks/{task_id}')
async def delete_task(task_id: int, tasks_id: Annotated[list, Depends(get_current_user_tasks)], db: db_depend):
    if tasks_id not in tasks_id:
        raise HTTPException(status_code=400, detail=f'Нет прав на удаление этой ({task_id}) задачи')
    task_db = db.scalar(select(Task).where(Task.ID == task_id))
    if not task_db:
        raise HTTPException(status_code=400, detail='Задача не найдена')
    db.delete(task_db)
    db.commit()
    return {'delete': f'Задача {task_id} удалена'}

@app.post('/permissions/{user_id}')
async def add_permission(permission: PermissionBase, tasks_id: Annotated[list, Depends(get_current_user_tasks)], db: db_depend):
    if permission.task in tasks_id:
        db_permission = Permission(read=permission.read, update=permission.update, task=permission.task, user=permission.user)
        db.add(db_permission)
        db.commit()
        return {'post': f'Правило добавлено'}

@app.put('/permissions/{permission_id}')
async def update_permission(permission_id: int, tasks_id: Annotated[list, Depends(get_current_user_tasks)], db: db_depend,
                        read: bool = False, update: bool = False):
    task_id = db.scalar(select(Permission.task).where(Permission.ID == permission_id))
    if not task_id:
        raise HTTPException(status_code=400, detail=f'Правила с таким id ({permission_id}) не существует')
    if task_id in tasks_id:
        db_permission = db.query(Permission).where(Permission.ID == permission_id).first()
        db_permission.read = read
        db_permission.update = update
        db.commit()
        return {'put': f'Правило {permission_id} обновлено'}

@app.delete('/permissions/{permission_id}')
async def delete_permission(permission_id: int, tasks_id: Annotated[list, Depends(get_current_user_tasks)], db: db_depend):
    task_id = db.scalar(select(Permission.task).where(Permission.ID == permission_id))
    if not task_id:
        raise HTTPException(status_code=400, detail=f'Правила с таким id ({permission_id}) не существует')
    if task_id in tasks_id:
        db_permission = db.query(Permission).where(Permission.ID == permission_id).first()
        db.delete(db_permission)
        db.commit()
        return {'delete': f'Правило {permission_id} удалено'}