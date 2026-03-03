import asyncio
from app.core.database import get_db_context
from sqlalchemy import text

async def check():
    async with get_db_context() as s:
        r = await s.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ('registry_transactions','guideline_values','locality_metadata','web_collected_prices') "
            "ORDER BY table_name"
        ))
        tables = [row[0] for row in r.fetchall()]
        print(f"RAG tables found: {tables}")
        if not tables:
            print("TABLES NOT CREATED YET - run 001_rag_foundation.sql in Supabase first!")
        return len(tables) > 0

asyncio.run(check())
