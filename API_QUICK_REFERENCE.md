# API Quick Reference Card

Quick reference cho testing API - Copy & paste commands

---

## 🚀 Server Commands

```bash
# Start server
bash start_server.sh

# Initialize database
python -m app.database.init_db

# Create expert
python scripts/create_expert.py --username admin --password admin123 --name "Admin"
```

**Server URL:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

---

## 📋 UC-01: Diagnosis

### 1. Create Diagnosis (Text)
```bash
curl -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "question=Lúa tôi có vết hình thoi màu nâu" \
  -F "latitude=10.6889" \
  -F "longitude=105.1259" \
  -F "province=An Giang" \
  -F "district=Châu Phú"
```

### 2. Get Diagnosis
```bash
curl http://localhost:8000/api/v1/diagnose/1
```

### 3. Get History
```bash
curl "http://localhost:8000/api/v1/diagnose/history?farmer_id=farmer_001&limit=10"
```

---

## 🗺️ UC-02: Epidemic Alerts

### 1. Get All Alerts
```bash
curl http://localhost:8000/api/v1/epidemic/alerts
```

### 2. Get Alerts by Province
```bash
curl "http://localhost:8000/api/v1/epidemic/alerts?province=An%20Giang"
```

### 3. Get Heatmap Data
```bash
curl "http://localhost:8000/api/v1/epidemic/map?disease=Đạo%20ôn%20lúa&province=An%20Giang"
```

### 4. Get Statistics
```bash
curl http://localhost:8000/api/v1/epidemic/stats
```

---

## 👨‍⚕️ UC-03: Expert Validation

### 1. Expert Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/expert/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**Save token:**
```bash
export TOKEN="<paste_token_here>"
```

### 2. Get Pending Cases
```bash
curl http://localhost:8000/api/v1/expert/pending \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Confirm Diagnosis
```bash
curl -X POST http://localhost:8000/api/v1/expert/review/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"confirm","expert_comment":"Xác nhận chính xác"}'
```

### 4. Correct Diagnosis
```bash
curl -X POST http://localhost:8000/api/v1/expert/review/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action":"correct",
    "corrected_disease":"Đốm nâu lúa",
    "expert_comment":"AI nhầm",
    "confidence_adjustment":0.9
  }'
```

### 5. Get Expert Stats
```bash
curl http://localhost:8000/api/v1/expert/stats \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Get Profile
```bash
curl http://localhost:8000/api/v1/expert/profile \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔄 Complete Workflows

### Workflow 1: Farmer Diagnosis
```bash
# Step 1: Submit diagnosis
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/diagnose \
  -F "image=@sample/benh-loet-cay.jpg" \
  -F "question=Cây lúa bị bệnh gì?" \
  -F "latitude=10.69" \
  -F "longitude=105.13" \
  -F "province=An Giang")

echo $RESPONSE | jq

# Step 2: Get diagnosis ID
ID=$(echo $RESPONSE | jq -r '.diagnosis_id')
echo "Diagnosis ID: $ID"

# Step 3: Get full details
curl -s http://localhost:8000/api/v1/diagnose/$ID | jq
```

### Workflow 2: Expert Review
```bash
# Step 1: Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/expert/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Step 2: Get pending
curl -s http://localhost:8000/api/v1/expert/pending \
  -H "Authorization: Bearer $TOKEN" | jq

# Step 3: Review first case
curl -s -X POST http://localhost:8000/api/v1/expert/review/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"confirm","expert_comment":"OK"}' | jq
```

### Workflow 3: Trigger Epidemic Alert
```bash
# Create 5 diagnoses in same area
for i in {1..5}; do
  LAT=$(echo "10.6889 + $i * 0.01" | bc)
  LON=$(echo "105.1259 + $i * 0.01" | bc)

  curl -s -X POST http://localhost:8000/api/v1/diagnose \
    -F "image=@sample/benh-loet-cay.jpg" \
    -F "question=Phát hiện bệnh đạo ôn" \
    -F "latitude=$LAT" \
    -F "longitude=$LON" \
    -F "province=An Giang" | jq '.diagnosis_id'

  sleep 1
done

# Check alerts
curl -s http://localhost:8000/api/v1/epidemic/alerts | jq
```

---

## 🔍 Health Checks

```bash
# Root endpoint
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# API docs (browser)
open http://localhost:8000/docs
```

---

## 🗄️ Database Queries

```bash
# Count diagnoses
sqlite3 database/crop_doctor.db "SELECT COUNT(*) FROM diagnoses;"

# Count alerts
sqlite3 database/crop_doctor.db "SELECT COUNT(*) FROM epidemic_alerts;"

# List experts
sqlite3 database/crop_doctor.db "SELECT id, username, full_name FROM experts;"

# Recent diagnoses
sqlite3 database/crop_doctor.db "SELECT id, disease_detected, confidence, province FROM diagnoses ORDER BY created_at DESC LIMIT 5;"

# Active alerts
sqlite3 database/crop_doctor.db "SELECT id, disease_name, province, case_count FROM epidemic_alerts WHERE alert_status='active';"
```

---

## 🐛 Troubleshooting

### Port already in use
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database locked
```bash
# Stop server first
pkill -f uvicorn

# Restart
bash start_server.sh
```

### Reset database
```bash
rm database/crop_doctor.db
python -m app.database.init_db
```

### Check logs
```bash
# If running in background
tail -f logs/server.log
```

---

## 📊 Test Data

### Sample Locations (An Giang)
- **Châu Phú**: 10.6889, 105.1259
- **Long Xuyên**: 10.3876, 105.4352
- **Châu Đốc**: 10.7065, 105.1165

### Sample Diseases
- Đạo ôn lúa (Rice Blast)
- Đốm nâu lúa (Brown Spot)
- Bạc lá lúa (Bacterial Leaf Blight)
- Khảo lá lúa (Sheath Blight)

### Test Expert Accounts
Create with:
```bash
python scripts/create_expert.py \
  --username test_expert \
  --password test123 \
  --name "Test Expert" \
  --specialization rice_diseases
```

---

## 💡 Pro Tips

1. **Use jq for pretty JSON:**
   ```bash
   curl ... | jq
   ```

2. **Save token as variable:**
   ```bash
   export TOKEN=$(curl ... | jq -r '.access_token')
   ```

3. **Test in browser:**
   - Open http://localhost:8000/docs
   - Click "Try it out" on any endpoint
   - Much easier than curl!

4. **Parallel requests:**
   ```bash
   for i in {1..5}; do
     curl ... &
   done
   wait
   ```

5. **Check response time:**
   ```bash
   time curl ...
   ```

---

**Quick Ref Version:** 1.0
**Last Updated:** 2024-01-13
