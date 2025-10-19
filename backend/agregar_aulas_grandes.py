"""Inserta aulas de gran capacidad para cubrir secciones con muchos alumnos."""
from datetime import datetime

from app.database import SessionLocal
from app.models import Classroom


AULAS_GRANDES = [
    {
        "codigo": "AUD-A",
        "edificio": "AUD",
        "piso": "1",
        "capacidad": 180,
        "tipo": "NOLAB",
        "tiene_computadoras": False,
        "numero_computadoras": 0,
    },
    {
        "codigo": "AUD-B",
        "edificio": "AUD",
        "piso": "1",
        "capacidad": 160,
        "tipo": "NOLAB",
        "tiene_computadoras": False,
        "numero_computadoras": 0,
    },
    {
        "codigo": "AUD-C",
        "edificio": "AUD",
        "piso": "2",
        "capacidad": 140,
        "tipo": "NOLAB",
        "tiene_computadoras": False,
        "numero_computadoras": 0,
    },
]


def ensure_large_classrooms() -> None:
    session = SessionLocal()
    try:
        for data in AULAS_GRANDES:
            codigo = data["codigo"]
            existing = session.query(Classroom).filter(Classroom.codigo == codigo).one_or_none()
            if existing:
                if not existing.active:
                    existing.active = True
                    existing.capacidad = max(existing.capacidad, data["capacidad"])
                    existing.updated_at = datetime.utcnow()
                continue

            classroom = Classroom(
                codigo=codigo,
                edificio=data["edificio"],
                piso=data["piso"],
                capacidad=data["capacidad"],
                tipo=data["tipo"],
                tiene_computadoras=data["tiene_computadoras"],
                numero_computadoras=data["numero_computadoras"],
                active=True,
            )
            session.add(classroom)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    ensure_large_classrooms()
    print("Aulas de gran capacidad insertadas/activadas correctamente.")
