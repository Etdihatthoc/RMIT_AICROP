"""
UC-03: Expert Validation API Routes
Authentication and expert review endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
import logging

from app.database.connection import get_db
from app.database.models import Diagnosis
from app.models.request_models import ExpertReviewRequest
from app.models.response_models import (
    ExpertLoginResponse,
    ExpertPendingResponse,
    PendingDiagnosisInfo,
    ExpertReviewResponse,
    ExpertStatsResponse,
    DiagnosisResponse,
    ErrorResponse
)
from app.services.expert_service import (
    authenticate_expert,
    get_pending_diagnoses,
    review_diagnosis,
    get_expert_stats,
    get_expert_by_id
)
from app.utils.auth import create_access_token, get_current_expert_id
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/auth/expert/login",
    response_model=ExpertLoginResponse,
    responses={401: {"model": ErrorResponse}}
)
async def expert_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    **UC-03: Expert Login**

    Authenticate expert user and receive JWT access token.

    **Credentials:**
    - **username**: Expert username
    - **password**: Expert password

    **Returns:**
    - JWT access token (use in Authorization header: `Bearer <token>`)
    - Token type (bearer)
    - Expert ID and name

    **Usage:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/expert/login \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=expert_01&password=password123"
    ```

    **Android Integration:**
    ```kotlin
    // Store token in SharedPreferences
    val token = response.access_token
    sharedPrefs.edit().putString("expert_token", token).apply()

    // Use in subsequent requests
    val authHeader = "Bearer $token"
    ```
    """
    # Authenticate expert
    expert = authenticate_expert(db, form_data.username, form_data.password)

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(expert.id)},
        expires_delta=access_token_expires
    )

    logger.info(f"Expert {expert.username} logged in successfully")

    return ExpertLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expert_id=expert.id,
        full_name=expert.full_name
    )


@router.get(
    "/expert/pending",
    response_model=ExpertPendingResponse,
    responses={401: {"model": ErrorResponse}}
)
async def get_pending_for_review(
    confidence_threshold: Optional[float] = None,
    limit: int = 50,
    expert_id: int = Depends(get_current_expert_id),
    db: Session = Depends(get_db)
):
    """
    **UC-03: Get Pending Diagnoses**

    Get list of diagnoses that need expert review.

    **Authentication Required:** Include JWT token in Authorization header

    **Query Parameters:**
    - **confidence_threshold**: Only show diagnoses below this confidence (default: 0.7)
    - **limit**: Maximum number of results (default: 50)

    **Returns:**
    - Count of pending cases
    - List of diagnoses with:
      - Diagnosis ID
      - Image URL
      - Farmer's question
      - AI diagnosis result
      - Confidence score
      - Creation date

    **Criteria for Expert Review:**
    - AI confidence < 70% (configurable)
    - Status = "expert_review"
    - Not yet reviewed by expert

    **Use Cases:**
    - Expert dashboard showing pending cases
    - Quality control workflow
    - Training data collection for model improvement
    """
    logger.info(f"Expert {expert_id} requesting pending diagnoses")

    pending = get_pending_diagnoses(
        db=db,
        confidence_threshold=confidence_threshold,
        limit=limit
    )

    # Convert to response model
    pending_info = []
    for diagnosis in pending:
        pending_info.append(
            PendingDiagnosisInfo(
                diagnosis_id=diagnosis.id,
                image_url=f"/uploads/images/{diagnosis.image_path.split('/')[-1]}" if diagnosis.image_path else "",
                farmer_question=diagnosis.question,
                ai_diagnosis=diagnosis.disease_detected,
                confidence=diagnosis.confidence,
                created_at=diagnosis.created_at
            )
        )

    return ExpertPendingResponse(
        pending_count=len(pending_info),
        diagnoses=pending_info
    )


@router.post(
    "/expert/review/{diagnosis_id}",
    response_model=ExpertReviewResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def review_diagnosis_by_expert(
    diagnosis_id: int,
    review: ExpertReviewRequest,
    expert_id: int = Depends(get_current_expert_id),
    db: Session = Depends(get_db)
):
    """
    **UC-03: Expert Review Diagnosis**

    Expert validates, corrects, or rejects an AI diagnosis.

    **Authentication Required:** Include JWT token in Authorization header

    **Path Parameters:**
    - **diagnosis_id**: ID of diagnosis to review

    **Request Body:**
    - **action**: Action to take
      - `"confirm"`: AI diagnosis is correct
      - `"correct"`: AI diagnosis is wrong, provide correction
      - `"reject"`: Diagnosis is invalid/unusable
    - **corrected_disease**: Required if action is "correct"
    - **expert_comment**: Optional comment explaining the decision
    - **confidence_adjustment**: Optional adjusted confidence score (0.0-1.0)

    **Returns:**
    - Diagnosis ID
    - Updated status
    - Expert reviewed flag
    - Update timestamp

    **Examples:**

    **Confirm:**
    ```json
    {
      "action": "confirm",
      "expert_comment": "Xác nhận chính xác, triệu chứng rõ ràng"
    }
    ```

    **Correct:**
    ```json
    {
      "action": "correct",
      "corrected_disease": "Đốm nâu lúa",
      "expert_comment": "AI nhầm, đây là đốm nâu chứ không phải đạo ôn",
      "confidence_adjustment": 0.95
    }
    ```

    **Reject:**
    ```json
    {
      "action": "reject",
      "expert_comment": "Hình ảnh không rõ ràng, cần chụp lại"
    }
    ```

    **Impact:**
    - Confirmed/corrected diagnoses update database
    - Expert feedback can be used to retrain/fine-tune AI model
    - Improves overall system accuracy
    """
    logger.info(f"Expert {expert_id} reviewing diagnosis {diagnosis_id}")

    try:
        updated_diagnosis = review_diagnosis(
            db=db,
            diagnosis_id=diagnosis_id,
            expert_id=expert_id,
            action=review.action,
            corrected_disease=review.corrected_disease,
            expert_comment=review.expert_comment,
            confidence_adjustment=review.confidence_adjustment
        )

        return ExpertReviewResponse(
            diagnosis_id=updated_diagnosis.id,
            status=updated_diagnosis.status,
            expert_reviewed=updated_diagnosis.expert_reviewed,
            updated_at=updated_diagnosis.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during expert review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@router.get(
    "/expert/stats",
    response_model=ExpertStatsResponse,
    responses={401: {"model": ErrorResponse}}
)
async def get_expert_statistics(
    expert_id: int = Depends(get_current_expert_id),
    db: Session = Depends(get_db)
):
    """
    **UC-03: Expert Dashboard Statistics**

    Get statistics about expert reviews and system accuracy.

    **Authentication Required:** Include JWT token in Authorization header

    **Returns:**
    - **total_reviewed**: Total cases reviewed by this expert
    - **confirmed**: Cases where AI was correct
    - **corrected**: Cases where AI was wrong and corrected
    - **rejected**: Cases that were rejected
    - **pending**: Current number of cases awaiting review
    - **accuracy_improvement**: Percentage improvement from expert feedback

    **Use Cases:**
    - Expert dashboard/overview
    - Track expert activity
    - Measure AI accuracy and improvement
    - Quality control metrics
    """
    logger.info(f"Expert {expert_id} requesting statistics")

    stats = get_expert_stats(db=db, expert_id=expert_id)

    return ExpertStatsResponse(
        total_reviewed=stats["total_reviewed"],
        confirmed=stats["confirmed"],
        corrected=stats["corrected"],
        rejected=stats["rejected"],
        pending=stats["pending"],
        accuracy_improvement=stats["accuracy_improvement"]
    )


@router.get(
    "/expert/profile",
    responses={401: {"model": ErrorResponse}}
)
async def get_expert_profile(
    expert_id: int = Depends(get_current_expert_id),
    db: Session = Depends(get_db)
):
    """
    **Get Expert Profile**

    Get current expert's profile information.

    **Authentication Required:** Include JWT token in Authorization header

    **Returns:**
    - Expert ID
    - Username
    - Full name
    - Email
    - Specialization
    - Account creation date
    """
    expert = get_expert_by_id(db, expert_id)

    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    return {
        "expert_id": expert.id,
        "username": expert.username,
        "full_name": expert.full_name,
        "email": expert.email,
        "phone": expert.phone,
        "specialization": expert.specialization,
        "created_at": expert.created_at
    }
