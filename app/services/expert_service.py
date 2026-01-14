"""
UC-03: Expert Validation Service
Business logic for expert review and validation
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from app.database.models import Diagnosis, Expert
from app.utils.auth import verify_password
from app.config import settings

logger = logging.getLogger(__name__)


def authenticate_expert(
    db: Session,
    username: str,
    password: str
) -> Optional[Expert]:
    """
    Authenticate expert user by username and password

    Args:
        db: Database session
        username: Expert username
        password: Plain text password

    Returns:
        Expert object if authentication successful, None otherwise
    """
    expert = db.query(Expert).filter(Expert.username == username).first()

    if not expert:
        logger.warning(f"Authentication failed: Expert '{username}' not found")
        return None

    if not verify_password(password, expert.password_hash):
        logger.warning(f"Authentication failed: Invalid password for '{username}'")
        return None

    logger.info(f"Expert '{username}' authenticated successfully")
    return expert


def get_pending_diagnoses(
    db: Session,
    confidence_threshold: Optional[float] = None,
    limit: int = 50
) -> List[Diagnosis]:
    """
    Get diagnoses that need expert review

    Args:
        db: Database session
        confidence_threshold: Only get diagnoses with confidence below this (default: from settings)
        limit: Maximum number of results

    Returns:
        List of diagnoses needing review
    """
    if confidence_threshold is None:
        confidence_threshold = settings.auto_review_threshold

    # Get diagnoses that:
    # 1. Have status = "expert_review" OR
    # 2. Have low confidence (< threshold) and not yet reviewed
    pending = db.query(Diagnosis).filter(
        and_(
            Diagnosis.expert_reviewed == False,
            (
                (Diagnosis.status == "expert_review") |
                (Diagnosis.confidence < confidence_threshold)
            )
        )
    ).order_by(Diagnosis.created_at.desc()).limit(limit).all()

    logger.info(f"Found {len(pending)} diagnoses needing expert review")
    return pending


def review_diagnosis(
    db: Session,
    diagnosis_id: int,
    expert_id: int,
    action: str,
    corrected_disease: Optional[str] = None,
    expert_comment: Optional[str] = None,
    confidence_adjustment: Optional[float] = None
) -> Diagnosis:
    """
    Expert reviews and validates a diagnosis

    Args:
        db: Database session
        diagnosis_id: ID of diagnosis to review
        expert_id: ID of expert performing review
        action: Action to take - "confirm", "correct", or "reject"
        corrected_disease: Corrected disease name (if action is "correct")
        expert_comment: Expert's comment
        confidence_adjustment: Adjusted confidence score

    Returns:
        Updated diagnosis object

    Raises:
        ValueError: If diagnosis not found or invalid action
    """
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()

    if not diagnosis:
        raise ValueError(f"Diagnosis {diagnosis_id} not found")

    # Validate action
    if action not in ["confirm", "correct", "reject"]:
        raise ValueError(f"Invalid action: {action}. Must be 'confirm', 'correct', or 'reject'")

    logger.info(f"Expert {expert_id} reviewing diagnosis {diagnosis_id} - Action: {action}")

    # Update based on action
    if action == "confirm":
        diagnosis.status = "confirmed"
        diagnosis.expert_reviewed = True
        diagnosis.expert_id = str(expert_id)
        diagnosis.expert_comment = expert_comment or "Xác nhận chính xác"

        # Optionally adjust confidence
        if confidence_adjustment is not None:
            diagnosis.confidence = confidence_adjustment

    elif action == "correct":
        if not corrected_disease:
            raise ValueError("corrected_disease is required when action is 'correct'")

        diagnosis.disease_detected = corrected_disease
        diagnosis.status = "confirmed"
        diagnosis.expert_reviewed = True
        diagnosis.expert_id = str(expert_id)
        diagnosis.expert_comment = expert_comment or f"Đã sửa thành: {corrected_disease}"

        # Adjust confidence to high after expert correction
        diagnosis.confidence = confidence_adjustment or 0.95

    elif action == "reject":
        diagnosis.status = "rejected"
        diagnosis.expert_reviewed = True
        diagnosis.expert_id = str(expert_id)
        diagnosis.expert_comment = expert_comment or "Chẩn đoán không chính xác"
        diagnosis.confidence = 0.0

    diagnosis.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(diagnosis)

    logger.info(f"✓ Diagnosis {diagnosis_id} reviewed successfully - Status: {diagnosis.status}")
    return diagnosis


def get_expert_stats(
    db: Session,
    expert_id: Optional[int] = None
) -> Dict:
    """
    Get expert review statistics

    Args:
        db: Database session
        expert_id: Optional - Get stats for specific expert

    Returns:
        Dictionary with statistics
    """
    query = db.query(Diagnosis).filter(Diagnosis.expert_reviewed == True)

    if expert_id:
        query = query.filter(Diagnosis.expert_id == str(expert_id))

    reviewed = query.all()

    total_reviewed = len(reviewed)
    confirmed = sum(1 for d in reviewed if d.status == "confirmed" and "sửa" not in (d.expert_comment or "").lower())
    corrected = sum(1 for d in reviewed if "sửa" in (d.expert_comment or "").lower() or d.status == "confirmed")
    rejected = sum(1 for d in reviewed if d.status == "rejected")

    # Calculate pending
    pending_count = db.query(Diagnosis).filter(
        and_(
            Diagnosis.expert_reviewed == False,
            (
                (Diagnosis.status == "expert_review") |
                (Diagnosis.confidence < settings.auto_review_threshold)
            )
        )
    ).count()

    # Calculate accuracy improvement (simplified)
    # Compare AI confidence vs expert adjusted confidence
    ai_avg_confidence = db.query(func.avg(Diagnosis.confidence)).filter(
        Diagnosis.expert_reviewed == False
    ).scalar() or 0

    expert_avg_confidence = db.query(func.avg(Diagnosis.confidence)).filter(
        Diagnosis.expert_reviewed == True
    ).scalar() or 0

    improvement = (expert_avg_confidence - ai_avg_confidence) * 100

    return {
        "total_reviewed": total_reviewed,
        "confirmed": confirmed,
        "corrected": corrected,
        "rejected": rejected,
        "pending": pending_count,
        "accuracy_improvement": f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
    }


def get_expert_by_id(db: Session, expert_id: int) -> Optional[Expert]:
    """
    Get expert by ID

    Args:
        db: Database session
        expert_id: Expert ID

    Returns:
        Expert object or None
    """
    return db.query(Expert).filter(Expert.id == expert_id).first()
