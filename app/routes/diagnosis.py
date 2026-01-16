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


def extract_causes_from_response(full_response: str) -> Optional[str]:
    """Extract disease causes from AI full response"""
    if not full_response:
        return None

    # Look for "Nguyên nhân:" section
    if "Nguyên nhân:" in full_response or "**Nguyên nhân:**" in full_response:
        lines = full_response.split('\n')
        causes_lines = []
        in_causes = False

        for line in lines:
            if "Nguyên nhân:" in line or "**Nguyên nhân:**" in line:
                in_causes = True
                continue
            if in_causes:
                # Stop at next section
                if line.strip().startswith('**') and ':' in line:
                    break
                if line.strip() and not line.strip().startswith('#'):
                    cleaned = line.strip().replace('**', '').replace('- ', '')
                    if cleaned:
                        causes_lines.append(cleaned)

        return "\n".join(causes_lines) if causes_lines else None

    return None


def convert_list_to_string(items: Optional[list], join_str: str = "\n") -> Optional[str]:
    """Convert list of items to string for Android compatibility"""
    if not items:
        return None
    if isinstance(items, list):
        # Handle list of TreatmentInfo objects
        if items and hasattr(items[0], '__dict__'):
            return join_str.join([
                f"{t.name}: {t.dosage or ''} {t.method or ''}".strip()
                for t in items
            ])
        # Handle list of strings
        return join_str.join(str(item) for item in items)
    return str(items)


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
    image: Optional[UploadFile] = File(None, description="Crop image (JPG, PNG) - optional for text/voice chat"),
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
    **UC-01: Cognitive Diagnosis / Chatbot**

    Upload crop image and/or question (text or audio) to get AI diagnosis

    - **image**: Optional - Image of crop disease
    - **question**: Optional - Farmer's question as text
    - **audio**: Optional - Farmer's question as audio file
    - **farmer_id**: Optional - Farmer identifier
    - **latitude, longitude**: Optional - GPS coordinates
    - **province, district**: Optional - Location info
    - **temperature, humidity**: Optional - Weather conditions

    At least one of image, question, or audio must be provided.
    Returns detailed diagnosis with disease name, confidence, treatments, and prevention tips.
    """
    try:
        # Validate input - at least one must be provided
        if not question and not audio and not image:
            raise HTTPException(
                status_code=400,
                detail="At least one of 'image', 'question' (text), or 'audio' must be provided"
            )

        # Save uploaded image if provided
        image_path = None
        if image:
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

        # Build response - UPDATED to include all fields for Android compatibility
        return DiagnosisResponse(
            diagnosis_id=diagnosis.id,
            farmer_id=diagnosis.farmer_id,
            image_path=diagnosis.image_path,
            audio_path=diagnosis.audio_path,
            question=diagnosis.question,
            latitude=diagnosis.latitude,
            longitude=diagnosis.longitude,
            province=diagnosis.province,
            district=diagnosis.district,
            temperature=diagnosis.temperature,
            humidity=diagnosis.humidity,
            weather_conditions=diagnosis.weather_conditions,
            disease_detected=parsed["disease_detected"],
            disease_name_en=None,
            confidence=parsed["confidence"],
            severity=parsed["severity"],
            symptoms=convert_list_to_string(parsed.get("symptoms")),
            treatment_suggestions=convert_list_to_string(parsed.get("treatments")),
            prevention_tips=convert_list_to_string(parsed.get("prevention_tips")),
            causes=extract_causes_from_response(full_response),
            full_response=full_response,
            status=diagnosis.status,
            expert_reviewed=diagnosis.expert_reviewed,
            expert_comment=diagnosis.expert_comment,
            created_at=diagnosis.created_at,
            updated_at=diagnosis.updated_at
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
        farmer_id=diagnosis.farmer_id,
        image_path=diagnosis.image_path,
        audio_path=diagnosis.audio_path,
        question=diagnosis.question,
        latitude=diagnosis.latitude,
        longitude=diagnosis.longitude,
        province=diagnosis.province,
        district=diagnosis.district,
        temperature=diagnosis.temperature,
        humidity=diagnosis.humidity,
        weather_conditions=diagnosis.weather_conditions,
        disease_detected=diagnosis.disease_detected or parsed["disease_detected"],
        disease_name_en=None,
        confidence=diagnosis.confidence or parsed["confidence"],
        severity=diagnosis.severity or parsed["severity"],
        symptoms=convert_list_to_string(parsed.get("symptoms")),
        treatment_suggestions=convert_list_to_string(parsed.get("treatments")),
        prevention_tips=convert_list_to_string(parsed.get("prevention_tips")),
        causes=extract_causes_from_response(diagnosis.full_response),
        full_response=diagnosis.full_response,
        status=diagnosis.status,
        expert_reviewed=diagnosis.expert_reviewed,
        expert_comment=diagnosis.expert_comment,
        created_at=diagnosis.created_at,
        updated_at=diagnosis.updated_at
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

    # Convert to response models - UPDATED for Android compatibility
    diagnosis_responses = []
    for diag in diagnoses:
        parsed = parse_ai_response(diag.full_response)
        diagnosis_responses.append(
            DiagnosisResponse(
                diagnosis_id=diag.id,
                farmer_id=diag.farmer_id,
                image_path=diag.image_path,
                audio_path=diag.audio_path,
                question=diag.question,
                latitude=diag.latitude,
                longitude=diag.longitude,
                province=diag.province,
                district=diag.district,
                temperature=diag.temperature,
                humidity=diag.humidity,
                weather_conditions=diag.weather_conditions,
                disease_detected=diag.disease_detected or parsed["disease_detected"],
                disease_name_en=None,
                confidence=diag.confidence or parsed["confidence"],
                severity=diag.severity or parsed["severity"],
                symptoms=convert_list_to_string(parsed.get("symptoms")),
                treatment_suggestions=convert_list_to_string(parsed.get("treatments")),
                prevention_tips=convert_list_to_string(parsed.get("prevention_tips")),
                causes=extract_causes_from_response(diag.full_response),
                full_response=diag.full_response,
                status=diag.status,
                expert_reviewed=diag.expert_reviewed,
                expert_comment=diag.expert_comment,
                created_at=diag.created_at,
                updated_at=diag.updated_at
            )
        )

    return DiagnosisHistoryResponse(
        farmer_id=farmer_id,
        total=total,
        diagnoses=diagnosis_responses
    )
