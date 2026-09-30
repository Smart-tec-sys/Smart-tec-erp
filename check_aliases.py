import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM fornecedor_aliases ORDER BY id")).mappings()
    for r in result:
        print(dict(r))