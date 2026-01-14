"""
AI Crop Doctor - Core Model Loader & Inference
Using Qwen2.5-Omni (TRUE multimodal model with audio support)
"""

import torch
import soundfile as sf
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
from qwen_omni_utils import process_mm_info
from typing import Optional, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CropDoctor:
    """
    Qwen2.5-Omni loader for crop disease diagnosis with TRUE multimodal support
    (Image + Audio/Text + Video)
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-Omni-7B",
        device: str = "auto",
        use_4bit: bool = True,
        enable_audio_output: bool = False,
        flash_attention: bool = False
    ):
        """
        Initialize Crop Doctor AI with Qwen2.5-Omni

        Args:
            model_name: Hugging Face model name
            device: "auto", "cuda", or "cpu"
            use_4bit: Use 4-bit quantization to save memory
            enable_audio_output: Enable audio response (Talker module)
            flash_attention: Use flash attention 2 for speedup
        """
        self.model_name = model_name
        self.device = device
        self.use_4bit = use_4bit
        self.enable_audio_output = enable_audio_output
        self.flash_attention = flash_attention
        self.model = None
        self.processor = None
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self, prompt_path: str = "system_prompt.txt") -> str:
        """Load system prompt from file"""
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {prompt_path}, using default")
            return "Bạn là AI Crop Doctor, chuyên gia chẩn đoán bệnh cây trồng."

    def load_model(self):
        """
        Load Qwen2.5-Omni model with optional quantization
        """
        logger.info(f"Loading model: {self.model_name}")
        logger.info(f"4-bit quantization: {self.use_4bit}")
        logger.info(f"Audio output enabled: {self.enable_audio_output}")
        logger.info(f"Flash Attention 2: {self.flash_attention}")

        # Quantization config
        load_kwargs = {
            "device_map": self.device,
            "torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        }

        if self.use_4bit:
            from transformers import BitsAndBytesConfig
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            logger.info("Using 4-bit quantization (saves ~10GB VRAM)")

        if self.flash_attention:
            load_kwargs["attn_implementation"] = "flash_attention_2"
            logger.info("Using Flash Attention 2 for speedup")

        # Load model
        logger.info("Loading Qwen2.5-Omni model (this may take a few minutes)...")
        self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            self.model_name,
            **load_kwargs
        )

        # Disable audio output if not needed (saves ~2GB VRAM)
        if not self.enable_audio_output:
            self.model.disable_talker()
            logger.info("Talker disabled - only text output (saves ~2GB VRAM)")

        self.model.eval()

        # Load processor
        logger.info("Loading processor...")
        self.processor = Qwen2_5OmniProcessor.from_pretrained(self.model_name)

        logger.info("✓ Model loaded successfully!")
        return self

    def diagnose(
        self,
        image: str,
        question: Optional[str] = None,
        audio: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        save_audio_path: Optional[str] = None
    ) -> Union[str, tuple]:
        """
        Diagnose crop disease from image and question (text or audio)

        Args:
            image: Path to image file
            question: Farmer's question as text (Vietnamese) - optional if audio provided
            audio: Path to audio file (farmer's voice question) - optional
            context: Optional environmental context (location, weather)
            temperature: Sampling temperature (0.1-1.0)
            max_tokens: Maximum response length
            save_audio_path: Path to save audio output (if enabled)

        Returns:
            - If audio output disabled: text response (str)
            - If audio output enabled: (text_response, audio_data) tuple
        """
        if self.model is None:
            raise RuntimeError("Model not loaded! Call load_model() first.")

        # Build conversation in Qwen2.5-Omni format
        conversation = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": self.system_prompt}
                ],
            },
            {
                "role": "user",
                "content": []
            }
        ]

        # Add image (always required)
        conversation[1]["content"].append({"type": "image", "image": image})

        # Add audio if provided (Qwen2.5-Omni will process it automatically)
        if audio:
            conversation[1]["content"].append({"type": "audio", "audio": audio})

        # Build text prompt
        if audio:
            user_prompt = "Nông dân hỏi qua giọng nói. "
            if context:
                user_prompt = f"Thông tin môi trường: {context}\n\n" + user_prompt
        else:
            if not question:
                raise ValueError("Either 'question' (text) or 'audio' must be provided!")
            user_prompt = question
            if context:
                user_prompt = f"Thông tin môi trường: {context}\n\nCâu hỏi: {question}"

        # Add text prompt
        conversation[1]["content"].append({"type": "text", "text": user_prompt})

        # Process conversation with Qwen2.5-Omni utilities
        logger.info("Processing multimodal inputs...")
        text = self.processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=False
        )

        # Use process_mm_info to handle audio/image/video automatically
        audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)

        # Process inputs
        inputs = self.processor(
            text=text,
            audio=audios,
            images=images,
            videos=videos,
            return_tensors="pt",
            padding=True
        )
        inputs = inputs.to(self.model.device)

        # Generate response
        logger.info("Generating diagnosis...")
        with torch.no_grad():
            if self.enable_audio_output:
                # Generate both text and audio
                text_ids, audio_output = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    return_audio=True,
                    speaker="Chelsie"  # Female voice
                )
            else:
                # Generate only text
                text_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    return_audio=False
                )

        # Decode text output
        response_text = self.processor.batch_decode(
            text_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        # Extract only the assistant's response (remove system prompt and user message)
        # The response format is: system\n[prompt]\nuser\n[message]\nassistant\n[response]
        if "assistant" in response_text:
            # Split by "assistant" and take the last part
            parts = response_text.split("assistant")
            if len(parts) > 1:
                response_text = parts[-1].strip()
        
        logger.info("✓ Diagnosis complete!")

        # Handle audio output if enabled
        if self.enable_audio_output:
            if save_audio_path:
                # Save audio to file
                sf.write(
                    save_audio_path,
                    audio_output.reshape(-1).detach().cpu().numpy(),
                    samplerate=24000,
                )
                logger.info(f"Audio saved to: {save_audio_path}")

            return response_text, audio_output
        else:
            return response_text
