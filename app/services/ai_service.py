"""
AI Service - Wrapper around CropDoctor model
Global singleton instance for the FastAPI app
"""

from typing import Dict, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """
    AI Service wrapper for Qwen2.5-Omni Crop Doctor
    Singleton pattern - one model instance for the entire app
    """

    def __init__(self):
        self.doctor = None
        self.model_loaded = False

    def load_model(self):
        """Load AI model on startup"""
        if self.model_loaded:
            logger.info("Model already loaded, skipping...")
            return

        # Import here to avoid loading torch/CUDA on startup
        from crop_doctor import CropDoctor

        logger.info("Initializing CropDoctor AI...")
        logger.info(f"Model: {settings.model_name}")
        logger.info(f"Device: {settings.model_device}")
        logger.info(f"4-bit quantization: {settings.use_4bit_quantization}")
        logger.info(f"Audio output: {settings.enable_audio_output}")

        self.doctor = CropDoctor(
            model_name=settings.model_name,
            device=settings.model_device,
            use_4bit=settings.use_4bit_quantization,
            enable_audio_output=settings.enable_audio_output,
            flash_attention=False
        )

        self.doctor.load_model()
        self.model_loaded = True
        logger.info("✓ AI model loaded successfully!")

    async def diagnose(
        self,
        image_path: str,
        question: Optional[str] = None,
        audio_path: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Run diagnosis with the AI model

        Args:
            image_path: Path to uploaded image
            question: Farmer's question (text)
            audio_path: Path to audio file (optional)
            context: Environmental context (province, temperature, humidity, etc.)

        Returns:
            AI response text
        """
        if not self.model_loaded or self.doctor is None:
            raise RuntimeError("AI model not loaded! Call load_model() first.")

        # Build context string from dict
        context_str = None
        if context:
            parts = []
            if context.get('province'):
                location = context['province']
                if context.get('district'):
                    location += f", {context['district']}"
                parts.append(f"Vị trí: {location}")

            if context.get('temperature'):
                parts.append(f"Nhiệt độ: {context['temperature']}°C")

            if context.get('humidity'):
                parts.append(f"Độ ẩm: {context['humidity']}%")

            if context.get('weather_conditions'):
                parts.append(f"Thời tiết: {context['weather_conditions']}")

            if parts:
                context_str = ". ".join(parts) + "."

        # Run inference
        logger.info(f"Running diagnosis - Image: {image_path}, Question: {question is not None}, Audio: {audio_path is not None}")

        try:
            result = self.doctor.diagnose(
                image=image_path,
                question=question,
                audio=audio_path,
                context=context_str,
                temperature=0.3
            )

            logger.info("Diagnosis completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error during diagnosis: {e}")
            raise

    async def chat(
        self,
        message: str,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Chat with the AI model (conversational mode)

        Args:
            message: User's text message
            image_path: Optional image attachment
            audio_path: Optional audio attachment
            context: Environmental context (province, temperature, humidity, etc.)

        Returns:
            AI response text
        """
        if not self.model_loaded or self.doctor is None:
            raise RuntimeError("AI model not loaded! Call load_model() first.")

        # Build context string from dict
        context_str = None
        if context:
            parts = []
            if context.get('province'):
                location = context['province']
                if context.get('district'):
                    location += f", {context['district']}"
                parts.append(f"Vị trí: {location}")

            if context.get('temperature'):
                parts.append(f"Nhiệt độ: {context['temperature']}°C")

            if context.get('humidity'):
                parts.append(f"Độ ẩm: {context['humidity']}%")

            if context.get('weather_conditions'):
                parts.append(f"Thời tiết: {context['weather_conditions']}")

            if parts:
                context_str = ". ".join(parts) + "."

        # Log the chat request
        logger.info(f"Chat request - Message length: {len(message)}, Image: {image_path is not None}, Audio: {audio_path is not None}")

        try:
            # Use the same diagnose method but with chat-style prompt
            # If user sends image + text, it's multimodal chat
            # If text only, it's pure conversation
            result = self.doctor.diagnose(
                image=image_path,
                question=message,
                audio=audio_path,
                context=context_str,
                temperature=0.7  # Higher temperature for more natural conversation
            )

            logger.info("Chat response generated successfully")
            return result

        except Exception as e:
            logger.error(f"Error during chat: {e}")
            raise


# Global AI service instance
ai_service = AIService()
