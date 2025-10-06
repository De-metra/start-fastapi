import logging
import asyncio
import asyncpg
from typing import Annotated
from fastapi import FastAPI, Header, Depends, HTTPException
from contextlib import asynccontextmanager
from databases import Database
from app.logger import logger
from app.models import *
from app.database import get_db_connection


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://myuser:mypassword@localhost/mydatabase"

# Главный объект для работы с базой данных - используется во всех запросах
database = Database(DATABASE_URL)

# Управление подключением через lifespan (новый способ в FastAPI 0.95+)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления подключением к БД.
    Заменяет устаревшие @app.on_event("startup") и @app.on_event("shutdown")
    """
    # Устанавливаем соединение при старте приложения
    await database.connect()
    yield  # Здесь работает приложение
    # Корректно закрываем подключение при завершении
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    logger.info(f"Home page")
    return {"message: ": "Hello, World!"}

@app.post("/users/", response_model=UserReturn)
async def create_user(user: UserCreate):
    """
    Создание пользователя с валидацией данных.
    
    Параметры:
    - user: данные согласно модели UserCreate
    
    Возвращает:
    - UserReturn с данными созданного пользователя и ID из БД
    
    Демонстрирует:
    - Разделение входных и выходных моделей
    - Автоматическую документацию в Swagger/OpenAPI
    - Обработку ошибок базы данных
    
    Пример использования транзакции:
    async with database.transaction():
        # несколько запросов в одной транзакции
        await database.execute(...)
        
    Дополнительно сам объект Database имеет свой асинхронный контекстный менеджер, то есть можно писать:
    async with Database(DATABASE_URL) as db:
    	await db.execute(...)
    
    Примеры выше полезны, если мы устанавливаем соединение не один раз при старте приложения, 
    а подключаемся к БД на каждый запрос (используем ресурсы по мере надобности, но чуть увеличиваем накладные расходы на создание соединения)
    """

    # SQL-запрос с параметризацией (защита от SQL-инъекций)
    query = """
        INSERT INTO users (username, email)
        VALUES (:username, :email)
        RETURNING id
    """

    try:
        # Пример использования транзакции (раскомментировать при необходимости):
        # async with database.transaction():
        user_id = await database.execute(
            query=query,
            values=user.model_dump()    # Автоматическая конвертация в словарь
        )

        # Комбинируем базовые поля с полученным ID
        return UserReturn(
            id=user_id,
            **user.model_dump()  # Сериализация для ответа
        )
    except Exception as e:
        # В реальном проекте добавить логирование ошибки
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании пользователя: {str(e)}"
        )

@app.get("/users/{user_id}", response_model=UserReturn)
async def get_user(user_id: int):
    """
    Получение информации о пользователе по его ID.
    
    Параметры:
    - user_id: идентификатор пользователя в БД
    
    Возвращает:
    - Данные пользователя в формате UserReturn
    - 404 ошибку если пользователь не найден
    """
    query = """
        SELECT id, username, email 
        FROM users 
        WHERE id = :user_id
    """
    try:
        result = await database.fetch_one(
            query=query,
            values={"user_id": user_id}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка получения пользователя: {str(e)}"
        )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Пользователь с указанным ID не найден"
        )
    
    return UserReturn(
        id=result["id"],
        username=result["username"],
        email=result["email"]
    )

@app.put("/users/{user_id}", response_model=UserReturn)
async def update_user(user_id : int, user : UserCreate):
    """
    Полное обновление данных пользователя по ID (PUT-запрос).

    Параметры:
    - user_id: ID пользователя в базе данных
    - user: новые данные пользователя (все поля обязательны)

    Возвращает:
    - Обновленные данные пользователя в формате UserReturn
    - 404 ошибку если пользователь не найден
    - 500 ошибку при проблемах с базой данных

    Пример запроса:
    {
        "username": "new_username",
        "email": "new_email@example.com"
    }
    """
    # SQL-запрос с возвратом обновленных данных
    query = """
        UPDATE users
        SET username = :username, email = :email
        WHERE id = :user_id
        RETURNING id
    """

    values = {
        "user_id": user_id,
        "username": user.username,
        "email": user.email
    }

    try:
        # Выполняем запрос и получаем обновленные данные
        result = await database.execute(query=query, values=values)

        # Если запись не найдена
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Пользователь с указанным ID не найден"
            )
        
        # Преобразуем результат запроса в модель UserReturn
        return UserReturn(
            id = result,
            **user.model_dump()
        )
    
    except HTTPException as he:
        # Пробрасываем HTTPException из проверки выше
        raise he
    
    except Exception as e:
        # Обрабатываем другие ошибки базы данных
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обновления пользователя: {str(e)}"
        )

@app.delete("/users/{user_id}", response_model=dict)
async def delete_user(user_id: int):
    """
    Удаление пользователя из базы данных по ID.

    Параметры:
    - user_id: идентификатор пользователя для удаления

    Возвращает:
    - Сообщение об успешном удалении
    - 404 ошибку если пользователь не найден
    - 500 ошибку при проблемах с базой данных
    """
    query = """
        DELETE FROM users
        WHERE id = :user_id
        RETURNING id
    """
    try:
        deleted_id = await database.execute(
            query=query,
            values={"user_id": user_id}
        )

        if not deleted_id:
            raise HTTPException(
                status_code=404, 
                detail="Пользователь с указанным ID не найден"
            )
        
        return {"message": "Пользователь успешно удален"}
    
    except HTTPException as he:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления пользователя: {str(e)}"
        )


@app.post("/todos/", response_model=TodoReturn)
async def create_todo(todo: Todo):

    query = """
        INSERT INTO todos(title, description, is_complited)
        VALUES (:title, :description, :is_complited)
        RETURNING id
    """

    try:

        todo_id = await database.execute(
            query=query,
            values=todo.model_dump() 
        )

        return TodoReturn(
            id= todo_id,
            **todo.model_dump()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании задачи: {str(e)}"
        )
    
@app.get("/todos/{todo_id}", response_model=TodoReturn)
async def get_todo(todo_id: int):

    query = """
        SELECT id, title, description, is_complited
        FROM todos
        WHERE id = :todo_id
    """

    try:

        result = await database.fetch_one(
            query=query, 
            values={"todo_id": todo_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка получения задачи: {str(e)}"
        )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Задача с указанным ID не найдена"
        )
    
    return TodoReturn(
        id=result['id'],
        title=result['title'],
        description=result['description'],
        is_complited=result['is_complited']
    )

@app.put("/todos/{todo_id}", response_model=TodoReturn)
async def update_todo(todo_id : int, todo : Todo):

    query = """
        UPDATE todos
        SET title = :title, description = :description, is_complited = :is_complited
        WHERE id = :todo_id
        RETURNING id
    """

    values = {
        "todo_id": todo_id,
        "title": todo.title,
        "description": todo.description,
        "is_complited": todo.is_complited
    }

    try:

        result = await database.execute(query=query, values=values)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Задача с указанным ID не найдена"
            )
        
        return TodoReturn(
            id=result,
            **todo.model_dump()
        )
    
    except HTTPException as he:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обновления задачи: {str(e)}"
        )
    
@app.delete("/todos/{todo_id}", response_model=dict)
async def delete_todo(todo_id : int):

    query = """
        DELETE FROM todos
        WHERE id = :todo_id
        RETURNING id
    """

    try:

        deleted_todo = await database.execute(
            query=query,
            values={"todo_id": todo_id}
        )

        if not deleted_todo:
            raise HTTPException(
                status_code=404,
                detail="Задача с указанным id не найдена"
            )
        
        return {"message": "Задача успешно удалена"}

    except HTTPException as he:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления пользователя: {str(e)}"
        )

    




"""
@app.post("/items")
async def create_item(item: Item, db: asyncpg.Connection = Depends(get_db_connection)):
    await db.execute('''
                     INSERT INTO items(name) VALUES($1)
                     ''', item.name)
    return {"message" : "Item added successfully!"}


@app.get("/db")
def get_db_info():
    logger.info(f"Connecting to database: {config.db.database_url}")
    return {"database_url": config.db.database_url}


@app.get("/users/")
def read_users(username: str = None, email: str = None, limit: int = 10):
    filtered_users = fake_users

    if username:
        filtered_users = {key: user for key, user in filtered_users.items() if username.lower() in user["username"].lower()}

    if email:
        filtered_users = {key: user for key, user in filtered_users.items() if email.lower() in user["email"].lower()}

    return dict(list(filtered_users.items())[:limit])


@app.get("/items/")
async def read_items(user_agent: Annotated[str | None, Header()] = None):
    return {"User-Agent": user_agent}

"""

