#!/bin/bash

echo "================================"
echo "AI Crop Doctor - Starting Server"
echo "================================"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found, using defaults"
fi

# Check if database exists, if not initialize it
if [ ! -f "./database/crop_doctor.db" ]; then
    echo ""
    echo "Database not found. Initializing..."
    python -m app.database.init_db
    echo ""
fi

# Start FastAPI server
echo "Starting FastAPI server..."
echo "Server will be available at: http://${HOST}:${PORT}"
echo "API Documentation at: http://${HOST}:${PORT}/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

uvicorn app.main:app --host ${HOST} --port ${PORT} --reload
