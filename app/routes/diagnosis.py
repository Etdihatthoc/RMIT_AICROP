"""
UC-01: Diagnosis API Routes
Endpoints for crop disease diagnosis
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
import json
from datetime import datetime

from app.database.connection import get_db
from app.database.models import Diagnosis
from app.models.response_models import (
    DiagnosisResponse,
    DiagnosisHistoryResponse,
    ErrorResponse
)
from app.services.ai_service import ai_service
from app.utils.file_handler import save_uploaded_file
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_ai_response(full_response: str) -> dict:
    """
    Parse AI response to extract structured data
    This is a simple parser - in production, use more sophisticated NLP

    Returns dict with: disease_detected, confidence, severity, symptoms, treatments, etc.
    """
    # For MVP, we'll do basic parsing
    # In production, you might want to fine-tune the model to output JSON

    result = {
        "disease_detected": None,
        "confidence": None,
        "severity": None,
        "symptoms": [],
        "treatments": [],
        "prevention_tips": []
    }

    # Try to extract disease name (simple heuristic)
    if "Bệnh phát hiện:" in full_response or "**Bệnh phát hiện:**" in full_response:
        # Extract disease name
        lines = full_response.split('\n')
        for i, line in enumerate(lines):
            if "Bệnh phát hiện:" in line or "**Bệnh phát hiện:**" in line:
                # Get next line or extract from this line
                disease_line = line.split('Bệnh phát hiện:')[-1].strip()
                disease_line = disease_line.replace('**', '').strip()
                if disease_line:
                    result["disease_detected"] = disease_line
                elif i + 1 < len(lines):
                    result["disease_detected"] = lines[i + 1].strip().replace('**', '')
                break

    # Try to extract confidence
    if "Độ tin cậy:" in full_response or "**Độ tin cậy:**" in full_response:
        import re
        confidence_match = re.search(r'Độ tin cậy:.*?(\d+)%', full_response)
        if confidence_match:
            result["confidence"] = float(confidence_match.group(1)) / 100.0

    # Try to extract severity
    if "Mức độ nghiêm trọng:" in full_response:
        if "Nặng" in full_response:
            result["severity"] = "high"
        elif "Trung bình" in full_response:
            result["severity"] = "medium"
        elif "Nhẹ" in full_response:
            result["severity"] = "low"

    # If formal diagnosis format not found, default values
    if result["disease_detected"] is None:
        result["disease_detected"] = "Cần thêm thông tin"
        result["confidence"] = 0.5
        result["severity"] = "unknown"

    return result


@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_diagnosis(
    image: UploadFile = File(..., description="Crop image (JPG, PNG)"),
    question: Optional[str] = Form(None, description="Farmer's question (text)"),
    audio: Optional[UploadFile] = File(None, description="Farmer's question (audio file)"),
    farmer_id: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    province: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    humidity: Optional[float] = Form(None),
    weather_conditions: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    **UC-01: Cognitive Diagnosis**

    Upload crop image and question (text or audio) to get AI diagnosis

    - **image**: Required - Image of crop disease
    - **question**: Optional - Farmer's question as text (if no audio)
    - **audio**: Optional - Farmer's question as audio file
    - **farmer_id**: Optional - Farmer identifier
    - **latitude, longitude**: Optional - GPS coordinates
    - **province, district**: Optional - Location info
    - **temperature, humidity**: Optional - Weather conditions

    Returns detailed diagnosis with disease name, confidence, treatments, and prevention tips.
    """
    try:
        # Validate input
        if not question and not audio:
            raise HTTPException(
                status_code=400,
                detail="Either 'question' (text) or 'audio' must be provided"
            )

        # Save uploaded image
        logger.info(f"Saving uploaded image: {image.filename}")
        image_path = await save_uploaded_file(
            image,
            f"{settings.upload_dir}/images",
            allowed_extensions={'.jpg', '.jpeg', '.png', '.webp'}
        )

        # Save audio if provided
        audio_path = None
        if audio:
            logger.info(f"Saving uploaded audio: {audio.filename}")
            audio_path = await save_uploaded_file(
                audio,
                f"{settings.upload_dir}/audio",
                allowed_extensions={'.wav', '.mp3', '.m4a', '.ogg'}
            )

        # Build context
        context = {}
        if province:
            context['province'] = province
        if district:
            context['district'] = district
        if temperature:
            context['temperature'] = temperature
        if humidity:
            context['humidity'] = humidity
        if weather_conditions:
            context['weather_conditions'] = weather_conditions

        # Run AI diagnosis
        logger.info("Running AI diagnosis...")
        full_response = await ai_service.diagnose(
            image_path=image_path,
            question=question,
            audio_path=audio_path,
            context=context if context else None
        )

        # Parse AI response
        parsed = parse_ai_response(full_response)

        # Create diagnosis record in database
        diagnosis = Diagnosis(
            farmer_id=farmer_id,
            image_path=image_path,
            audio_path=audio_path,
            question=question,
            latitude=latitude,
            longitude=longitude,
            province=province,
            district=district,
            temperature=temperature,
            humidity=humidity,
            weather_conditions=weather_conditions,
            disease_detected=parsed["disease_detected"],
            confidence=parsed["confidence"],
            severity=parsed["severity"],
            full_response=full_response,
            status="pending"
        )

        db.add(diagnosis)
        db.commit()
        db.refresh(diagnosis)

        logger.info(f"Diagnosis saved with ID: {diagnosis.id}")

        # Check for epidemic clusters (UC-02)
        from app.services.epidemic_service import check_epidemic_clusters
        try:
            alerts = check_epidemic_clusters(diagnosis, db)
            if alerts:
                logger.info(f"Created/updated {len(alerts)} epidemic alerts")
        except Exception as e:
            logger.warning(f"Epidemic check failed (non-critical): {e}")

        # Check if needs expert review (UC-03)
        if parsed["confidence"] and parsed["confidence"] < settings.auto_review_threshold:
            diagnosis.status = "expert_review"
            db.commit()
            logger.info(f"Diagnosis {diagnosis.id} flagged for expert review (confidence: {parsed['confidence']})")

        # Build response
        return DiagnosisResponse(
            diagnosis_id=diagnosis.id,
            disease_detected=parsed["disease_detected"],
            disease_name_en=None,  # Could add translation
            confidence=parsed["confidence"],
            severity=parsed["severity"],
            symptoms=parsed["symptoms"],
            treatments=parsed["treatments"],
            prevention_tips=parsed["prevention_tips"],
            full_response=full_response,
            status=diagnosis.status,
            expert_reviewed=diagnosis.expert_reviewed,
            expert_comment=diagnosis.expert_comment,
            created_at=diagnosis.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


@router.get(
    "/diagnose/{diagnosis_id}",
    response_model=DiagnosisResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db)
):
    """
    Get diagnosis details by ID

    Returns complete diagnosis information including AI response and status.
    """
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()

    if not diagnosis:
        raise HTTPException(status_code=404, detail=f"Diagnosis {diagnosis_id} not found")

    # Parse for structured response (or retrieve from cache if stored)
    parsed = parse_ai_response(diagnosis.full_response)

    return DiagnosisResponse(
        diagnosis_id=diagnosis.id,
        disease_detected=diagnosis.disease_detected or parsed["disease_detected"],
        disease_name_en=None,
        confidence=diagnosis.confidence or parsed["confidence"],
        severity=diagnosis.severity or parsed["severity"],
        symptoms=parsed["symptoms"],
        treatments=parsed["treatments"],
        prevention_tips=parsed["prevention_tips"],
        full_response=diagnosis.full_response,
        status=diagnosis.status,
        expert_reviewed=diagnosis.expert_reviewed,
        expert_comment=diagnosis.expert_comment,
        created_at=diagnosis.created_at
    )


@router.get(
    "/diagnose/history",
    response_model=DiagnosisHistoryResponse
)
async def get_diagnosis_history(
    farmer_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get diagnosis history

    - **farmer_id**: Optional - Filter by farmer ID
    - **limit**: Maximum number of results (default: 10, max: 100)
    - **offset**: Pagination offset (default: 0)

    Returns list of diagnoses ordered by creation date (newest first).
    """
    query = db.query(Diagnosis)

    if farmer_id:
        query = query.filter(Diagnosis.farmer_id == farmer_id)

    # Get total count
    total = query.count()

    # Get paginated results
    diagnoses = query.order_by(Diagnosis.created_at.desc()).limit(min(limit, 100)).offset(offset).all()

    # Convert to response models
    diagnosis_responses = []
    for diag in diagnoses:
        parsed = parse_ai_response(diag.full_response)
        diagnosis_responses.append(
            DiagnosisResponse(
                diagnosis_id=diag.id,
                disease_detected=diag.disease_detected or parsed["disease_detected"],
                disease_name_en=None,
                confidence=diag.confidence or parsed["confidence"],
                severity=diag.severity or parsed["severity"],
                symptoms=parsed["symptoms"],
                treatments=parsed["treatments"],
                prevention_tips=parsed["prevention_tips"],
                full_response=diag.full_response,
                status=diag.status,
                expert_reviewed=diag.expert_reviewed,
                expert_comment=diag.expert_comment,
                created_at=diag.created_at
            )
        )

    return DiagnosisHistoryResponse(
        farmer_id=farmer_id,
        total=total,
        diagnoses=diagnosis_responses
    )
