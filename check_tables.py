import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (table_name LIKE '%fornec%' OR table_name LIKE '%ali%' OR table_name LIKE '%equival%')
        ORDER BY table_name
    """)).mappings()
    for r in result:
        print(dict(r))