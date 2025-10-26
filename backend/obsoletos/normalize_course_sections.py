import logging

from app.database import SessionLocal
from app.services.section_normalizer import normalize_all_courses

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    session = SessionLocal()
    try:
        result = normalize_all_courses(session)
        logger.info(
            "Normalización completada: %s cursos procesados, %s cursos actualizados, %s secciones ajustadas",
            result['courses_processed'],
            result['courses_updated'],
            result['sections_updated'],
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
