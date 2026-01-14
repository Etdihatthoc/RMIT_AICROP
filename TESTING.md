# Testing Guide - AI Crop Doctor API

Hướng dẫn test và sử dụng API đầy đủ cho 3 use cases.

---

## Prerequisites

1. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

2. **Khởi tạo database:**
```bash
python -m app.database.init_db
```

3. **Tạo expert user:**
```bash
python scripts/create_expert.py \
  --username expert_01 \
  --password password123 \
  --name "Dr. Nguyen Van A" \
  --email "expert@example.com" \
  --specialization "rice_diseases"
```

4. **Khởi động server:**
```bash
bash start_server.sh
```

Server sẽ chạy tại: http://localhost:8000

API Documentation: http://localhost:8000/docs

---

## UC-01: Diagnosis API Testing

### Test 1: Diagnosis với Text Question

```bash
curl -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "question=Lúa tôi có vết hình thoi màu nâu, đây là bệnh gì?" \
  -F "farmer_id=farmer_001" \
  -F "latitude=10.6889" \
  -F "longitude=105.1259" \
  -F "province=An Giang" \
  -F "district=Châu Phú" \
  -F "temperature=27.5" \
  -F "humidity=88.0" \
  -F "weather_conditions=Mưa nhiều"
```

**Expected Response:**
```json
{
  "diagnosis_id": 1,
  "disease_detected": "Đạo ôn lúa",
  "confidence": 0.89,
  "severity": "high",
  "full_response": "...",
  "status": "pending",
  "expert_reviewed": false,
  "created_at": "2024-01-13T10:30:00"
}
```

### Test 2: Diagnosis với Audio Input (nếu có file audio)

```bash
curl -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "audio=@sample/farmer_question.wav" \
  -F "latitude=10.6889" \
  -F "longitude=105.1259" \
  -F "province=An Giang"
```

### Test 3: Get Diagnosis by ID

```bash
curl http://localhost:8000/api/v1/diagnose/1
```

### Test 4: Get Diagnosis History

```bash
curl "http://localhost:8000/api/v1/diagnose/history?farmer_id=farmer_001&limit=10"
```

---

## UC-02: Epidemic Alert Testing

### Test 5: Tạo Nhiều Diagnoses để Trigger Epidemic Alert

Để test epidemic detection, cần tạo ít nhất 5 diagnoses cùng loại bệnh trong cùng khu vực:

```bash
# Tạo 5 diagnoses trong vòng 5km
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/diagnose \
    -F "image=@sample/benh-loet-cay.jpg" \
    -F "question=Phát hiện bệnh đạo ôn lúa" \
    -F "latitude=$(echo "10.6889 + $i * 0.01" | bc)" \
    -F "longitude=$(echo "105.1259 + $i * 0.01" | bc)" \
    -F "province=An Giang" \
    -F "district=Châu Phú"
  sleep 2
done
```

**Note:** Epidemic alert sẽ tự động được tạo sau diagnosis thứ 5.

### Test 6: Get Active Epidemic Alerts

```bash
# Tất cả alerts
curl http://localhost:8000/api/v1/epidemic/alerts

# Filter theo tỉnh
curl "http://localhost:8000/api/v1/epidemic/alerts?province=An%20Giang"

# Filter theo bệnh
curl "http://localhost:8000/api/v1/epidemic/alerts?disease=Đạo%20ôn%20lúa"
```

**Expected Response:**
```json
{
  "alerts": [
    {
      "alert_id": 1,
      "disease_name": "Đạo ôn lúa",
      "province": "An Giang",
      "district": "Châu Phú",
      "case_count": 5,
      "radius_km": 2.3,
      "severity": "low",
      "alert_message": "⚠️ CẢNH BÁO DỊCH BỆNH: Phát hiện ổ dịch Đạo ôn lúa tại An Giang. 5 trường hợp trong bán kính 2.3km.",
      "center_lat": 10.70,
      "center_lon": 105.15,
      "alert_status": "active",
      "created_at": "2024-01-13T10:35:00"
    }
  ]
}
```

### Test 7: Get Heatmap Data

```bash
# Tất cả data points
curl http://localhost:8000/api/v1/epidemic/map

# Filter theo bệnh và tỉnh
curl "http://localhost:8000/api/v1/epidemic/map?disease=Đạo%20ôn%20lúa&province=An%20Giang&days=30"
```

### Test 8: Get Epidemic Statistics

```bash
curl http://localhost:8000/api/v1/epidemic/stats

# Filter theo tỉnh
curl "http://localhost:8000/api/v1/epidemic/stats?province=An%20Giang"
```

---

## UC-03: Expert Validation Testing

### Test 9: Expert Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/expert/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=expert_01&password=password123"
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expert_id": 1,
  "full_name": "Dr. Nguyen Van A"
}
```

**Lưu token để sử dụng cho các requests tiếp theo:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Test 10: Get Pending Diagnoses

```bash
curl http://localhost:8000/api/v1/expert/pending \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "pending_count": 3,
  "diagnoses": [
    {
      "diagnosis_id": 2,
      "image_url": "/uploads/images/abc123.jpg",
      "farmer_question": "Cây lúa có vết lạ",
      "ai_diagnosis": "Đạo ôn lúa",
      "confidence": 0.65,
      "created_at": "2024-01-13T09:00:00"
    }
  ]
}
```

### Test 11: Expert Review - Confirm

```bash
curl -X POST http://localhost:8000/api/v1/expert/review/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "confirm",
    "expert_comment": "Xác nhận chính xác, triệu chứng đạo ôn rõ ràng",
    "confidence_adjustment": 0.95
  }'
```

### Test 12: Expert Review - Correct

```bash
curl -X POST http://localhost:8000/api/v1/expert/review/3 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "correct",
    "corrected_disease": "Đốm nâu lúa",
    "expert_comment": "AI nhầm, đây là đốm nâu chứ không phải đạo ôn",
    "confidence_adjustment": 0.90
  }'
```

### Test 13: Expert Review - Reject

```bash
curl -X POST http://localhost:8000/api/v1/expert/review/4 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "reject",
    "expert_comment": "Hình ảnh không rõ ràng, cần chụp lại"
  }'
```

### Test 14: Get Expert Statistics

```bash
curl http://localhost:8000/api/v1/expert/stats \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "total_reviewed": 3,
  "confirmed": 1,
  "corrected": 1,
  "rejected": 1,
  "pending": 0,
  "accuracy_improvement": "+12.5%"
}
```

### Test 15: Get Expert Profile

```bash
curl http://localhost:8000/api/v1/expert/profile \
  -H "Authorization: Bearer $TOKEN"
```

---

## Integration Test: Complete Workflow

### Workflow 1: Farmer → AI Diagnosis → Epidemic Alert

```bash
# 1. Farmer uploads image
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "question=Lúa tôi bị bệnh gì?" \
  -F "latitude=10.69" \
  -F "longitude=105.13" \
  -F "province=An Giang")

echo "Diagnosis Response: $RESPONSE"

DIAGNOSIS_ID=$(echo $RESPONSE | jq -r '.diagnosis_id')
echo "Diagnosis ID: $DIAGNOSIS_ID"

# 2. Check if epidemic alert was created
sleep 1
curl -s "http://localhost:8000/api/v1/epidemic/alerts?province=An%20Giang" | jq
```

### Workflow 2: Low Confidence → Expert Review

```bash
# 1. Create diagnosis that will need expert review (simulate low confidence)
# (This happens automatically if AI confidence < 0.7)

# 2. Expert logs in
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/expert/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=expert_01&password=password123" | jq -r '.access_token')

echo "Expert Token: $TOKEN"

# 3. Expert gets pending cases
curl -s http://localhost:8000/api/v1/expert/pending \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Expert reviews case
curl -s -X POST http://localhost:8000/api/v1/expert/review/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm", "expert_comment": "Xác nhận chính xác"}' | jq
```

---

## Health Check & API Info

```bash
# Health check
curl http://localhost:8000/health

# API info
curl http://localhost:8000/

# Interactive API docs (mở trong browser)
open http://localhost:8000/docs
```

---

## Common Issues & Troubleshooting

### Issue 1: Database not found
```bash
# Solution: Initialize database
python -m app.database.init_db
```

### Issue 2: AI model not loading
```bash
# Check: VRAM requirements (minimum 6GB for 4-bit quantization)
# Check: Transformers version (must use Qwen2.5-Omni preview branch)
```

### Issue 3: File upload fails
```bash
# Check: upload directories exist
mkdir -p uploads/images uploads/audio

# Check: file size (max 10MB by default)
```

### Issue 4: Expert login fails
```bash
# Check: Expert user exists
python scripts/create_expert.py --username expert_01 --password password123 --name "Test Expert"
```

### Issue 5: Epidemic alert not created
```bash
# Need at least 5 diagnoses with:
# - Same disease
# - Same province
# - Within 5km radius (eps=0.05 degrees)
# - Confidence >= 0.5
# - Within last 7 days
```

---

## Performance Testing

### Load Test: Multiple Diagnoses

```bash
# Send 10 diagnoses in parallel
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/diagnose \
    -F "image=@sample/benh-loet-cay.jpg" \
    -F "question=Test $i" &
done
wait
```

### Database Check

```bash
# Check database size
ls -lh database/crop_doctor.db

# Count records
sqlite3 database/crop_doctor.db "SELECT COUNT(*) FROM diagnoses;"
sqlite3 database/crop_doctor.db "SELECT COUNT(*) FROM epidemic_alerts;"
sqlite3 database/crop_doctor.db "SELECT COUNT(*) FROM experts;"
```

---

## Android App Integration

### Authentication Flow

```kotlin
// 1. Login
val loginResponse = apiService.login(username, password)
val token = loginResponse.access_token

// 2. Store token
sharedPrefs.edit().putString("token", token).apply()

// 3. Use in requests
val authHeader = "Bearer $token"
```

### Diagnosis Flow

```kotlin
// Create multipart request
val imagePart = MultipartBody.Part.createFormData(
    "image",
    file.name,
    file.asRequestBody("image/*".toMediaTypeOrNull())
)

val questionBody = question.toRequestBody("text/plain".toMediaTypeOrNull())

// Send request
val response = apiService.diagnose(
    image = imagePart,
    question = questionBody,
    latitude = latitude.toRequestBody(),
    longitude = longitude.toRequestBody()
)
```

### Map Integration

```kotlin
// Get heatmap data
val heatmapData = apiService.getHeatmapData(disease, province)

// Display on Google Maps
val heatmapProvider = HeatmapTileProvider.Builder()
    .data(heatmapData.map { LatLng(it.latitude, it.longitude) })
    .build()

map.addTileOverlay(TileOverlayOptions().tileProvider(heatmapProvider))
```

---

## Success Criteria

✅ All 3 use cases working:
- UC-01: Diagnosis API accepts image/audio, returns AI diagnosis
- UC-02: Epidemic alerts auto-generated when 5+ cases clustered
- UC-03: Experts can login, review, confirm/correct diagnoses

✅ Database persists all data correctly

✅ API documentation accessible at /docs

✅ JWT authentication protects expert endpoints

✅ CORS enabled for Android app

✅ File uploads working for images and audio

---

## Next Steps

After testing backend is complete:

1. **Deploy to Server** - Setup on production server with proper security
2. **Android App Development** - Connect mobile app to API
3. **Model Fine-tuning** - Use expert feedback to improve AI accuracy
4. **Monitoring** - Add logging, metrics, error tracking
5. **Scaling** - Move to PostgreSQL, add Redis cache, load balancing
