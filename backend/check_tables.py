from app.database import get_db
from sqlalchemy import text

db = next(get_db())

print("=== TABLAS CON 'assignment' ===")
tables = db.execute(text("SHOW TABLES LIKE '%assignment%'")).fetchall()
for t in tables:
    print(f"- {t[0]}")

print("\n=== BACKUP DE LA TABLA ===")
backups = db.execute(text("SHOW TABLES LIKE '%backup%'")).fetchall()
for t in backups:
    print(f"- {t[0]}")
    # Ver estructura
    desc = db.execute(text(f"DESCRIBE {t[0]}")).fetchall()
    print(f"  Columnas: {', '.join([c[0] for c in desc])}")
