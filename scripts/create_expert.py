"""
Script to create expert user accounts

Usage:
    python scripts/create_expert.py --username expert_01 --password password123 --name "Dr. Nguyen Van A"
    python scripts/create_expert.py --username expert_02 --password pass456 --name "Dr. Tran Thi B" --email expert2@example.com --specialization rice_diseases
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import SessionLocal
from app.database.models import Expert
from app.utils.auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_expert(
    username: str,
    password: str,
    full_name: str,
    email: str = None,
    phone: str = None,
    specialization: str = None
):
    """
    Create a new expert user

    Args:
        username: Unique username for expert
        password: Plain text password (will be hashed)
        full_name: Expert's full name
        email: Email address (optional)
        phone: Phone number (optional)
        specialization: Area of expertise (optional)
    """
    db = SessionLocal()

    try:
        # Check if username already exists
        existing = db.query(Expert).filter(Expert.username == username).first()
        if existing:
            logger.error(f"❌ Expert with username '{username}' already exists!")
            return False

        # Hash password
        password_hash = hash_password(password)

        # Create expert
        expert = Expert(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            email=email,
            phone=phone,
            specialization=specialization
        )

        db.add(expert)
        db.commit()
        db.refresh(expert)

        logger.info("=" * 60)
        logger.info("✓ Expert user created successfully!")
        logger.info("=" * 60)
        logger.info(f"  Expert ID:      {expert.id}")
        logger.info(f"  Username:       {expert.username}")
        logger.info(f"  Full Name:      {expert.full_name}")
        logger.info(f"  Email:          {expert.email or 'N/A'}")
        logger.info(f"  Phone:          {expert.phone or 'N/A'}")
        logger.info(f"  Specialization: {expert.specialization or 'N/A'}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Login credentials:")
        logger.info(f"  Username: {username}")
        logger.info(f"  Password: {password}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Error creating expert: {e}")
        db.rollback()
        return False

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create expert user account for AI Crop Doctor"
    )

    parser.add_argument(
        "--username",
        required=True,
        help="Username for expert (must be unique)"
    )

    parser.add_argument(
        "--password",
        required=True,
        help="Password for expert (will be hashed)"
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Full name of expert"
    )

    parser.add_argument(
        "--email",
        help="Email address (optional)"
    )

    parser.add_argument(
        "--phone",
        help="Phone number (optional)"
    )

    parser.add_argument(
        "--specialization",
        help="Area of expertise, e.g., 'rice_diseases' (optional)"
    )

    args = parser.parse_args()

    # Validate password length
    if len(args.password) < 6:
        logger.error("❌ Password must be at least 6 characters long")
        sys.exit(1)

    # Create expert
    success = create_expert(
        username=args.username,
        password=args.password,
        full_name=args.name,
        email=args.email,
        phone=args.phone,
        specialization=args.specialization
    )

    if success:
        logger.info("Expert user can now login via:")
        logger.info("  POST /api/v1/auth/expert/login")
        logger.info("")
        logger.info("Test with curl:")
        logger.info(f'  curl -X POST http://localhost:8000/api/v1/auth/expert/login \\')
        logger.info(f'    -H "Content-Type: application/x-www-form-urlencoded" \\')
        logger.info(f'    -d "username={args.username}&password={args.password}"')
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
