import asyncpg

DATABASE_URL = "postgresql://myuser:mypassword@localhost/mydatabase"

async def get_db_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally: 
        await conn.close()

