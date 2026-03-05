# 🌾 AgriSmart API — Zabaan-E-Kissan Backend

A production-grade **FastAPI** backend for the Zabaan-E-Kissan agricultural platform.  
It combines crop price data, AI-powered plant disease detection, an agricultural chatbot, and audio transcription into a single unified API.

---

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Server](#running-the-server)
- [API Endpoints](#-api-endpoints)
  - [General](#general)
  - [Crop Prices](#crop-prices)
  - [Disease Detection](#disease-detection)
  - [Chatbot](#chatbot)
  - [Transcription](#transcription)
- [Project Architecture](#-project-architecture)
- [Deployment](#-deployment)
- [CI/CD Pipeline](#-cicd-pipeline)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌱 **Crop Prices** | Query live crop price data from MongoDB with filtering, pagination, and city comparison |
| 🔬 **Disease Detection** | Upload a plant leaf image and get an AI diagnosis with treatment recommendations (17 classes) |
| 🤖 **Agricultural Chatbot** | Real-time WebSocket chatbot powered by LangGraph for farming advice in Urdu/English |
| 🎙️ **Audio Transcription** | Convert voice messages to text using OpenAI Whisper (supports Urdu, English, Punjabi) |
| 🌍 **Remote Sensing** | Field analysis using GPS coordinates (Pakistan boundary) |

---

## 📁 Project Structure

```
Backend-Zabaan-E-Kissan/
├── main.py                          # Root entry point (uvicorn launcher)
├── requirements.txt
├── .env                             # Environment variables (not committed)
│
├── .github/
│   └── workflows/
│       └── deploy.yml               # GitHub Actions CI/CD pipeline
│
├── src/
│   └── app/
│       ├── main.py                  # FastAPI app factory + lifespan
│       ├── dependencies.py          # Depends() providers (DB, ML model)
│       ├── __init__.py
│       │
│       ├── core/
│       │   └── config.py            # All settings from environment variables
│       │
│       ├── routers/
│       │   ├── crop_prices.py       # GET  /crop/*
│       │   ├── disease.py           # POST /disease/predict, GET /disease/classes
│       │   ├── chatbot.py           # WS   /chat/{thread_id}
│       │   └── transcription.py    # POST /transcribe
│       │
│       ├── services/
│       │   ├── crop_price_service.py   # MongoDB data access layer
│       │   ├── disease_service.py      # ML model inference + image preprocessing
│       │   └── transcription_service.py # OpenAI Whisper integration
│       │
│       ├── schemas/
│       │   ├── crop_price.py        # CropPrice, APIResponse Pydantic models
│       │   ├── disease.py           # PredictionResponse Pydantic model
│       │   └── chatbot.py           # ChatRequest Pydantic model
│       │
│       ├── data/
│       │   └── disease_info.json    # Disease metadata (status, severity, treatment)
│       │
│       ├── model/
│       │   └── disease_detection_model.keras  # Trained Keras model
│       │
│       └── chatbotWorkflow.py       # LangGraph chatbot workflow
│
├── scraper/
│   └── main.py                      # Selenium-based crop price scraper
│
├── data/                            # Scraped JSON price snapshots
└── logs/
    └── scraper.log
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI ≥ 0.111 |
| ASGI Server | Uvicorn |
| Database | MongoDB (via PyMongo) |
| ML Framework | TensorFlow / Keras 3.x |
| Image Processing | Pillow, NumPy |
| Chatbot | LangChain, LangGraph, OpenAI |
| Transcription | OpenAI Whisper API |
| Scraper | Selenium, WebDriver Manager |
| Runtime | Python 3.12 |

---

## 🚀 Getting Started

### Prerequisites

- Python **3.12+**
- MongoDB instance (local or Atlas)
- OpenAI API key
- Google Cloud credentials (optional — for Google Speech-to-Text)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ABDULAHAD118/Price-Scrapping.git
cd Price-Scrapping

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Server
HOST=0.0.0.0
PORT=8000
APP_ENV=development           # set to "production" to disable auto-reload
LOG_LEVEL=INFO

# CORS (comma-separated origins, or * for all)
ALLOW_ORIGINS=*

# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
MONGODB_DB_NAME=crop_prices_db

# OpenAI (Whisper + Chatbot)
OPENAI_API_KEY=sk-...
WHISPER_MODEL=whisper-1
WHISPER_DEFAULT_LANGUAGE=ur

# Google Cloud Speech-to-Text (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Running the Server

```bash
# Option 1 — via root entry point
python main.py

# Option 2 — directly with uvicorn (development)
uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 3 — production (multi-worker)
uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Open the interactive docs at: **http://localhost:8000/docs**

---

## 📡 API Endpoints

### General

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info and full endpoint map |
| `GET` | `/health` | Health check — DB + ML model status |
| `GET` | `/ready` | Readiness probe (Kubernetes compatible) |

### Crop Prices

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/crop/cities` | List all available cities |
| `GET` | `/crop/crops` | List all crops (optional `?city=` filter) |
| `GET` | `/crop/prices` | Paginated prices (`?city=&crop=&date=&page=&limit=`) |
| `GET` | `/crop/latest` | Most recent prices (`?city=&limit=`) |
| `GET` | `/crop/compare` | Compare a crop across cities (`?crop=&cities=City1,City2`) |
| `GET` | `/crop/stats` | Database statistics |

### Disease Detection

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/disease/predict` | Upload leaf image → disease classification + treatment |
| `GET` | `/disease/classes` | List all 17 supported disease/healthy class names |

**Supported crops:** Corn, Potato, Rice, Sugarcane, Wheat  
**Supported classes:** 17 (healthy + diseased variants per crop)

**Example response from `/disease/predict`:**
```json
{
  "predicted_class": "Wheat_Yellow_Rust",
  "confidence_percent": 94.3,
  "is_healthy": false,
  "status": "🔴 Serious Disease",
  "severity_range": "High → Very High",
  "description": "Highly aggressive fungal disease - spreads rapidly in cool weather",
  "description_ur": "بہت تیزی سے پھیلنے والی پھپھوندی",
  "recommended_action": "URGENT: Apply Propiconazole 25 EC immediately.",
  "recommended_action_ur": "فوری: Propiconazole 25 EC فوراً چھڑکیں",
  "confidence_level": "High",
  "top_3_predictions": [...]
}
```

### Chatbot

| Method | Path | Description |
|--------|------|-------------|
| `WS` | `/chat/{thread_id}` | Streaming chatbot conversation |
| `GET` | `/chat/analyze-field` | Remote sensing field analysis (`?lat=&lon=`) |

**WebSocket message format:**
```json
// Client → Server
{ "query": "گندم کی کاشت کا بہترین وقت کیا ہے؟" }

// Server → Client (streamed chunks)
{ "response": "گندم کی کاشت..." }

// Server → Client (end of response)
{ "done": true }
```

### Transcription

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transcribe` | Upload audio file → transcribed text |

**Form fields:** `audio` (file), `language` (default: `ur`)  
**Supported formats:** M4A, MP3, WAV, OGG, FLAC, WebM

---

## 🏗 Project Architecture

```
Request
  │
  ▼
FastAPI App (src/app/main.py)
  │
  ├── CORSMiddleware
  │
  ├── /crop/*       →  routers/crop_prices.py   →  services/crop_price_service.py  →  MongoDB
  ├── /disease/*    →  routers/disease.py        →  services/disease_service.py     →  Keras Model
  ├── /chat/*       →  routers/chatbot.py        →  chatbotWorkflow.py              →  OpenAI/LangGraph
  └── /transcribe   →  routers/transcription.py  →  services/transcription_service.py → OpenAI Whisper
```

**Dependency injection** (`dependencies.py`):
- `get_db()` — injects the singleton `CropPriceService` (MongoDB client)
- `get_ml_model()` — injects the loaded Keras model

Both are initialised once during **app startup** via the `lifespan` context manager and injected into route handlers via `Depends()`.

---

## 🌐 Deployment

The app runs as a **systemd service** (`fastapi`) on a DigitalOcean Droplet.

```bash
# Check service status
sudo systemctl status fastapi

# Restart service
sudo systemctl restart fastapi

# View live logs
sudo journalctl -u fastapi -f
```

**Server:** `206.189.140.248`  
**Live docs:** `http://206.189.140.248:8000/docs`

---

## ⚙️ CI/CD Pipeline

Automated deployments are handled by **GitHub Actions** (`.github/workflows/deploy.yml`).

**Trigger:** Any push to the `main` branch  

**Pipeline steps:**
1. Checkout repository
2. Configure SSH access using `DROPLET_SSH_KEY` secret
3. SSH into the DigitalOcean Droplet
4. `git pull origin main`
5. Activate virtualenv & `pip install -r requirements.txt`
6. `sudo systemctl restart fastapi`

**Required GitHub Secrets:**

| Secret | Description |
|--------|-------------|
| `DROPLET_SSH_KEY` | Private SSH key for the DigitalOcean Droplet |

---

## 🌾 Data Scraper

The `scraper/` module uses **Selenium** to scrape daily crop prices and store them in MongoDB.

```bash
# Run the scraper manually
python src/scraper/main.py
```

Scraped snapshots are also saved as JSON files in `data/crop_prices_YYYY-MM-DD.json`.

---

## 📄 License

This project is proprietary software developed for the **Zabaan-E-Kissan** platform.

