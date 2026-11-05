#!/bin/sh
set -e

echo "🏥 Initializing hospital operations forecasting backend..."

# Run automated bootstrap: checks datasets, models, and initial database rows
python scripts/init_system.py

echo "🚀 Starting FastAPI server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

