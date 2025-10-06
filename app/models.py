import re
from pydantic import BaseModel, EmailStr, Field, field_validator, conint

# Базовый класс для моделей пользователя - содержит общие поля
class UserBase(BaseModel):
    username: str
    email: str

# Модель для получения данных от клиента (валидация ввода)
# Наследует все поля от UserBase и может быть расширена дополнительными полями
# Пример: на входе мы можем запросить пароль, который не будем возвращать в ответе
class UserCreate(UserBase):
    """
    Входная модель для создания пользователя. 
    В реальных проектах обычно содержит больше полей, чем выходная модель,
    например, пароль, подтверждение пароля или другие чувствительные данные.
    """
    pass  # В текущей реализации поля совпадают с базовой моделью

# Модель для возврата данных клиенту (сериализация вывода)
# Наследует общие поля и добавляет технические данные из БД
# Важно: выходная модель часто содержит меньше полей, чем входная
class UserReturn(UserBase):
    """
    Выходная модель пользователя. Демонстрирует:
    - Добавление служебных полей (id из БД)
    - Исключение чувствительных данных (если бы они были)
    - Формат данных, безопасный для возврата клиенту
    """
    id: int  # ID всегда присутствует после сохранения в БД

# Пример расширения моделей для учебных целей:
# class UserCreateWithPassword(UserCreate):
#     password: str
#     password_confirm: str

# class UserPrivateInfo(UserReturn):
#     created_at: datetime
#     last_login: datetime

class Todo(BaseModel):
    title: str
    description: str
    is_complited: bool = False

class TodoReturn(Todo):
    id: int

class Item(BaseModel):
    name: str

class User(BaseModel):
    id: int
    username: str
    age: int

'''
class UserCreate(BaseModel):
    name: str 
    email: EmailStr
    age: int = conint(gt=0, lt=120) 
    is_subscribed: bool | None = Field(default=False)
'''
class Contact(BaseModel):
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r'^\d{7,15}$')

class Feedback(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    message: str = Field(min_length=10, max_length=500)
    contact: Contact

    @field_validator('message', mode='after')
    @classmethod
    def validate_message(cls, data : str):
        pattern = r'(?i)редиск[а-я]|бяк[а-я]|козявк[а-я]'
        if re.findall(pattern, data):
            raise ValueError("Использование недопустимых слов")
        return data
