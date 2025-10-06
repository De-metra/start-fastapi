import asyncpg
import asyncio

DATABASE_URL = "postgresql://myuser:mypassword@localhost/mydatabase"

async def create_table():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    await conn.close()

#asyncio.run(create_table())
