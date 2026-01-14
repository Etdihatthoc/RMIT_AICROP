"""
Database initialization script
Run this to create the database and tables

Usage: python -m app.database.init_db
"""

from app.database.connection import init_database
from app.database.models import Base, Diagnosis, Expert, EpidemicAlert
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize database and create all tables"""
    logger.info("Starting database initialization...")
    logger.info("Creating tables: Diagnosis, Expert, EpidemicAlert")

    try:
        init_database()
        logger.info("✓ Database initialized successfully!")
        logger.info(f"Tables created: {', '.join(Base.metadata.tables.keys())}")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    main()
