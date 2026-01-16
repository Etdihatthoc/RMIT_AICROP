"""
Chat Routes - UC-04: Agricultural Chatbot with Multimodal Support
Endpoints for conversational AI with optional image/audio attachments
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import uuid
from datetime import datetime

from app.database.connection import get_db
from app.database.models import ChatHistory, Diagnosis
from app.models.response_models import ChatResponse, ChatHistoryResponse, ChatMessage, ErrorResponse
from app.services.ai_service import ai_service
from app.services.file_service import save_upload_file
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    message: str = Form(..., description="User's text message"),
    image: Optional[UploadFile] = File(None, description="Optional image attachment"),
    audio: Optional[UploadFile] = File(None, description="Optional audio attachment"),
    farmer_id: Optional[str] = Form(None, description="Farmer identifier"),
    session_id: Optional[str] = Form(None, description="Chat session ID"),
    latitude: Optional[float] = Form(None, description="GPS latitude"),
    longitude: Optional[float] = Form(None, description="GPS longitude"),
    province: Optional[str] = Form(None, description="Province name"),
    temperature: Optional[float] = Form(None, description="Temperature in Celsius"),
    humidity: Optional[float] = Form(None, description="Humidity percentage"),
    db: Session = Depends(get_db)
):
    """
    Send a message to the agricultural chatbot

    Supports:
    - Text-only chat
    - Image + text (multimodal diagnosis)
    - Audio + text (voice questions)
    - Combined inputs

    Returns AI response and saves to chat history
    """
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"Chat request - Session: {session_id}, Farmer: {farmer_id}, Message: {message[:50]}...")

        # Save uploaded files
        image_path = None
        audio_path = None

        if image:
            image_path = await save_upload_file(image, "images")
            logger.info(f"Saved chat image: {image_path}")

        if audio:
            audio_path = await save_upload_file(audio, "audio")
            logger.info(f"Saved chat audio: {audio_path}")

        # Save user message to database
        user_message_record = ChatHistory(
            farmer_id=farmer_id,
            session_id=session_id,
            role="user",
            message=message,
            image_path=image_path,
            audio_path=audio_path,
            latitude=latitude,
            longitude=longitude,
            province=province,
            temperature=temperature,
            humidity=humidity,
            created_at=datetime.utcnow()
        )
        db.add(user_message_record)
        db.flush()  # Get ID without committing

        # Build context for AI
        context = {}
        if province:
            context['province'] = province
        if temperature:
            context['temperature'] = temperature
        if humidity:
            context['humidity'] = humidity

        # Get AI response
        ai_response = await ai_service.chat(
            message=message,
            image_path=image_path,
            audio_path=audio_path,
            context=context if context else None
        )

        logger.info(f"AI response generated: {len(ai_response)} characters")

        # Check if this was a diagnosis request (image provided)
        diagnosis_id = None
        if image_path:
            # This is a diagnosis request, create diagnosis record
            # Parse AI response for diagnosis details (simplified)
            diagnosis_record = Diagnosis(
                farmer_id=farmer_id,
                image_path=image_path,
                audio_path=audio_path,
                question=message,
                latitude=latitude,
                longitude=longitude,
                province=province,
                temperature=temperature,
                humidity=humidity,
                full_response=ai_response,
                status="pending",
                created_at=datetime.utcnow()
            )
            db.add(diagnosis_record)
            db.flush()
            diagnosis_id = diagnosis_record.id
            logger.info(f"Created diagnosis record: {diagnosis_id}")

        # Save assistant response to database
        assistant_message_record = ChatHistory(
            farmer_id=farmer_id,
            session_id=session_id,
            role="assistant",
            message=ai_response,
            diagnosis_id=diagnosis_id,
            latitude=latitude,
            longitude=longitude,
            province=province,
            created_at=datetime.utcnow()
        )
        db.add(assistant_message_record)

        # Commit all changes
        db.commit()

        return ChatResponse(
            message_id=assistant_message_record.id,
            session_id=session_id,
            role="assistant",
            message=ai_response,
            diagnosis_id=diagnosis_id,
            created_at=assistant_message_record.created_at
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: Optional[str] = None,
    farmer_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a session or farmer

    Query by:
    - session_id: Get specific conversation
    - farmer_id: Get all conversations for farmer
    - Both: Get specific farmer's session
    """
    try:
        query = db.query(ChatHistory)

        if session_id:
            query = query.filter(ChatHistory.session_id == session_id)

        if farmer_id:
            query = query.filter(ChatHistory.farmer_id == farmer_id)

        if not session_id and not farmer_id:
            raise HTTPException(
                status_code=400,
                detail="Must provide session_id or farmer_id"
            )

        # Order by timestamp and paginate
        messages = query.order_by(ChatHistory.created_at.asc()).offset(offset).limit(limit).all()
        total = query.count()

        # Convert to response models
        message_list = [
            ChatMessage(
                id=msg.id,
                role=msg.role,
                message=msg.message,
                image_path=msg.image_path,
                audio_path=msg.audio_path,
                diagnosis_id=msg.diagnosis_id,
                created_at=msg.created_at
            )
            for msg in messages
        ]

        return ChatHistoryResponse(
            session_id=session_id or "multiple_sessions",
            farmer_id=farmer_id,
            total_messages=total,
            messages=message_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


@router.delete("/chat/session/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and all its messages
    """
    try:
        deleted = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
        db.commit()

        if deleted == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Chat session not found: {session_id}"
            )

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Deleted {deleted} messages from session {session_id}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete chat session: {str(e)}"
        )
