import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM empresa_equivalencias_tecnicas WHERE empresa_id = 1 ORDER BY id")).mappings()
    for r in result:
        print(dict(r))