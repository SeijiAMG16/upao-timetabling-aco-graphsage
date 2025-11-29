from app.database import get_db
from sqlalchemy import text

db = next(get_db())

backup_table = "proposed_schedule_assignments_backup_20251026_183608"

count = db.execute(text(f"SELECT COUNT(*) FROM {backup_table}")).scalar()
print(f"Registros en backup: {count}")

if count > 0:
    print("\n=== PRIMEROS 10 REGISTROS DEL BACKUP ===")
    rows = db.execute(text(f"SELECT * FROM {backup_table} LIMIT 10")).fetchall()
    for r in rows:
        print(f"ID={r[0]}, prof={r[1]}, course={r[2]}, nrc={r[4]}, session={r[8]}")
    
    print("\n=== ESTRUCTURA DE LA TABLA BACKUP ===")
    desc = db.execute(text(f"DESCRIBE {backup_table}")).fetchall()
    for col in desc:
        print(f"{col[0]:30} {col[1]:20} NULL={col[2]:5} Default={col[4]}")
