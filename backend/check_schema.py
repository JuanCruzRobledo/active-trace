import asyncio, asyncpg

async def main():
    conn = await asyncpg.connect(user='postgres', password='nikolan', database='trace_test', host='localhost', port=5432)
    try:
        r = await conn.fetchrow("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'public'")
        print(f"public schema exists: {r is not None}")
        r2 = await conn.fetchrow("SELECT current_schema")
        print(f"current_schema: {r2['current_schema']}")
    finally:
        await conn.close()

asyncio.run(main())
