"""
Demo script for AI Crop Doctor with Qwen2.5-Omni
TRUE multimodal support: Image + Text/Audio input
"""

from crop_doctor import CropDoctor
import sys

def main():
    print("="*60)
    print("🌾 AI CROP DOCTOR - QWEN2.5-OMNI DEMO")
    print("="*60)

    # Initialize
    print("\n1️⃣ Initializing Crop Doctor AI...")
    print("\n⚙️  Configuration:")
    print("   - Model: Qwen2.5-Omni-7B")
    print("   - Quantization: 4-bit (saves VRAM)")
    print("   - Audio output: Disabled (saves ~2GB VRAM)")
    print("   - Flash Attention: Disabled")

    doctor = CropDoctor(
        model_name="Qwen/Qwen2.5-Omni-7B",
        use_4bit=True,
        enable_audio_output=False,  # Set True if you want voice response
        flash_attention=False  # Set True if you have flash-attn installed
    )

    # Load model
    print("\n2️⃣ Loading Qwen2.5-Omni model...")
    print("   (First run will download ~4-7GB)")
    doctor.load_model()

    # Example diagnosis
    print("\n3️⃣ Running multimodal diagnosis...")
    print("-" * 60)

    # Get image
    image_path = input("\n📸 Enter crop image path: ").strip()
    if not image_path:
        print("⚠️  No image provided. Please provide a crop image for diagnosis.")
        sys.exit(0)

    # Ask input method
    print("\n❓ How do you want to ask the question?")
    print("   1. Text (type your question)")
    print("   2. Audio (provide audio file - WAV, MP3, etc.)")
    input_choice = input("Choose (1 or 2): ").strip()

    question = None
    audio_path = None

    if input_choice == "1":
        # Text input
        question = input("\n💬 Enter farmer question (Vietnamese): ").strip()
        if not question:
            question = "Cây lúa của tôi có vết bệnh hình thoi màu nâu, đây là bệnh gì và phải xử lý như thế nào?"
    elif input_choice == "2":
        # Audio input
        audio_path = input("\n🎤 Enter audio file path (WAV/MP3/etc.): ").strip()
        if not audio_path:
            print("⚠️  No audio provided.")
            sys.exit(0)
        print("   ℹ️  Qwen2.5-Omni will process audio automatically!")
    else:
        print("❌ Invalid choice!")
        sys.exit(0)

    # Optional context
    context = "Vị trí: Đồng Bằng Sông Cửu Long, An Giang. Thời tiết: Nhiệt độ 27°C, độ ẩm 88%, mưa nhiều."

    # Show input summary
    print("\n" + "="*60)
    print("📋 INPUT SUMMARY:")
    print("="*60)
    print(f"📸 Image: {image_path}")
    if question:
        print(f"💬 Question (text): {question}")
    if audio_path:
        print(f"🎤 Question (audio): {audio_path}")
    print(f"🌤️  Context: {context}")
    print("\n" + "="*60)
    print("🔍 DIAGNOSIS RESULT:")
    print("="*60 + "\n")

    # Get diagnosis
    try:
        result = doctor.diagnose(
            image=image_path,
            question=question,
            audio=audio_path,
            context=context,
            temperature=0.7
        )

        print(result)
        print("\n" + "="*60)
        print("✓ Demo complete!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
