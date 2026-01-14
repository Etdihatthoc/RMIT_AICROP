# AI Crop Doctor - Backend API

AI-powered crop disease diagnosis system using Qwen2.5-Omni multimodal model.

## Project Status

**✅ Step 1: AI Core (COMPLETE)**
- Qwen2.5-Omni integration
- Multimodal input (image + text/audio)
- Vietnamese language support

**✅ Step 2: FastAPI Backend (COMPLETE)**
- ✅ Phase 1: Project structure setup
- ✅ Phase 2: Core FastAPI app
- ✅ Phase 3: UC-01 - Diagnosis API (3 endpoints)
- ✅ Phase 4: UC-02 - Epidemic Alert API (4 endpoints)
- ✅ Phase 5: UC-03 - Expert Validation API (5 endpoints)
- ✅ Phase 6: Integration & Testing (documentation complete)

**⏳ Step 3: Android App (PENDING)**
- Mobile application development
- UI/UX design
- Integration with backend API

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Note: This will download ~4-7GB for the AI model on first run.

### 2. Initialize Database

```bash
python -m app.database.init_db
```

### 3. Start Server

```bash
bash start_server.sh
```

Or manually:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Create Expert User (Optional - for testing UC-03)

```bash
python scripts/create_expert.py \
  --username expert_01 \
  --password password123 \
  --name "Dr. Nguyen Van A"
```

### 5. Access API Documentation

Open browser: http://localhost:8000/docs

## API Endpoints

### UC-01: Cognitive Diagnosis (3 endpoints)

**POST /api/v1/diagnose** - Create new diagnosis
- Upload image + question (text or audio)
- Returns AI diagnosis with confidence, treatments, prevention
- Auto-triggers epidemic detection
- Auto-flags low confidence cases for expert review

**GET /api/v1/diagnose/{diagnosis_id}** - Get diagnosis by ID

**GET /api/v1/diagnose/history** - Get farmer's diagnosis history
- Query params: `farmer_id`, `limit`, `offset`

### UC-02: Geo-spatial Epidemic Alert (4 endpoints)

**GET /api/v1/epidemic/alerts** - Get active epidemic alerts
- Auto-generated when 5+ cases detected within 5km
- Query params: `province`, `district`, `disease`

**GET /api/v1/epidemic/map** - Get heatmap data for visualization
- Returns GPS coordinates of recent diagnoses
- Query params: `disease`, `province`, `days`

**GET /api/v1/epidemic/stats** - Get epidemic statistics
- Total alerts, severity breakdown, top diseases

### UC-03: Human-in-the-loop Expert Validation (5 endpoints)

**POST /api/v1/auth/expert/login** - Expert login (get JWT token)

**GET /api/v1/expert/pending** - Get diagnoses needing review
- Cases with confidence < 70%

**POST /api/v1/expert/review/{diagnosis_id}** - Review/validate diagnosis
- Actions: confirm, correct, reject

**GET /api/v1/expert/stats** - Expert dashboard statistics

**GET /api/v1/expert/profile** - Get expert profile

## Testing

See [TESTING.md](TESTING.md) for comprehensive testing guide covering all 3 use cases.

### Quick Test: Diagnosis API

```bash
curl -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "question=Lúa tôi có vết hình thoi, đây là bệnh gì?" \
  -F "latitude=10.6889" \
  -F "longitude=105.1259" \
  -F "province=An Giang"
```

Or use the interactive API docs at `/docs`

## Project Structure

```
RMIT/
├── app/
│   ├── main.py                 # FastAPI app ✅
│   ├── config.py               # Settings ✅
│   ├── routes/
│   │   ├── diagnosis.py        # UC-01: Diagnosis endpoints ✅
│   │   ├── epidemic.py         # UC-02: Epidemic endpoints ✅
│   │   └── expert.py           # UC-03: Expert endpoints ✅
│   ├── services/
│   │   ├── ai_service.py       # AI model wrapper ✅
│   │   ├── epidemic_service.py # DBSCAN clustering ✅
│   │   └── expert_service.py   # Expert validation logic ✅
│   ├── database/
│   │   ├── models.py           # SQLAlchemy ORM (3 tables) ✅
│   │   ├── connection.py       # DB connection ✅
│   │   └── init_db.py          # DB initialization ✅
│   ├── models/
│   │   ├── request_models.py   # Request schemas ✅
│   │   └── response_models.py  # Response schemas ✅
│   └── utils/
│       ├── file_handler.py     # File uploads ✅
│       ├── auth.py             # JWT authentication ✅
│       └── geo_utils.py        # Geo calculations ✅
├── scripts/
│   └── create_expert.py        # Create expert users ✅
├── crop_doctor.py              # Qwen2.5-Omni core ✅
├── system_prompt.txt           # Vietnamese prompt ✅
├── database/
│   └── crop_doctor.db          # SQLite database
├── uploads/                    # Uploaded files
│   ├── images/
│   └── audio/
├── start_server.sh             # Startup script ✅
├── README.md                   # Main documentation ✅
├── TESTING.md                  # Testing guide ✅
├── requirements.txt            # Dependencies ✅
└── .env                        # Configuration ✅
```

## Environment Variables

See `.env.example` for configuration options.

Key settings:
- `MODEL_NAME`: Qwen/Qwen2.5-Omni-7B
- `USE_4BIT_QUANTIZATION`: True (saves ~10GB VRAM)
- `DATABASE_URL`: sqlite:///./database/crop_doctor.db
- `DBSCAN_EPS`: 0.05 (~5km radius for epidemic detection)

## Features Implemented

### ✅ UC-01: Cognitive Diagnosis
- Multimodal AI (image + text/audio input)
- Vietnamese language support
- Automatic disease detection with confidence scoring
- Treatment recommendations and prevention tips
- Diagnosis history tracking
- Low confidence cases auto-flagged for expert review

### ✅ UC-02: Geo-spatial Epidemic Alert
- DBSCAN clustering for outbreak detection
- Automatic alert generation (5+ cases within 5km)
- Real-time epidemic monitoring
- Heatmap data for visualization
- Severity classification (low/medium/high)
- Province/district filtering

### ✅ UC-03: Human-in-the-loop Expert Validation
- JWT-based authentication
- Expert review workflow (confirm/correct/reject)
- Pending case management
- Expert dashboard with statistics
- Accuracy improvement tracking
- Feedback loop for model improvement

## Database Schema

- **diagnoses** table: All diagnosis records with AI results
- **epidemic_alerts** table: Auto-generated epidemic alerts
- **experts** table: Expert user accounts with credentials

## Next Steps (Step 3: Android App)

- [ ] Mobile app UI/UX design
- [ ] Camera integration for image capture
- [ ] Audio recording for voice questions
- [ ] GPS integration for automatic location
- [ ] Map view with epidemic alerts overlay
- [ ] Expert portal for review
- [ ] Push notifications for epidemic alerts

## Technology Stack

- **AI Model**: Qwen2.5-Omni-7B (multimodal)
- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite + SQLAlchemy
- **Auth**: JWT (python-jose)
- **Clustering**: scikit-learn (DBSCAN)
- **Geo**: geopy (distance calculations)
