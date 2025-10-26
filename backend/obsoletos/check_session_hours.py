import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

result = db.execute(text("""
    SELECT c.codigo, csh.session_type, csh.duration_blocks
    FROM course_session_hours csh
    JOIN courses c ON csh.course_id = c.id
    WHERE c.codigo IN ('ISIA126', 'ISIA119', 'ISIA120')
    ORDER BY c.codigo, csh.session_type
"""))

print("COURSE_SESSION_HOURS para cursos problematicos:")
print("=" * 70)
for row in result:
    print(f"  {row[0]:8s} | Tipo: {row[1]} | Bloques: {row[2]}")

db.close()
