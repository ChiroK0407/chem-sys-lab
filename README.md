# ChemsysLab

A local development setup for the ChemsysLab process engineering web app with a FastAPI backend and Vite/React frontend.

## Prerequisites

- Python 3.11+ (or compatible)
- Node.js 18+ / npm
- Git (optional)

## Setup

### 1. Backend

From the repo root:

```bash
cd d:\Code\chemsyslab
python -m venv venv
Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Frontend

From the repo root:

```bash
cd frontend
npm install
```

## Run locally

Yes — start two terminals:

### Terminal 1: Backend

```bash
cd d:\Code\chemsyslab
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at:
- `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Terminal 2: Frontend

```bash
cd d:\Code\chemsyslab\frontend
npm run dev
```

The frontend app will typically be available at:
- `http://localhost:5173`

## Notes

- The backend uses CORS middleware to allow the frontend to access the API.
- If the frontend uses a different port, update the API base URL accordingly in client.js.

## Testing

From the repo root:

```bash
.\venv\Scripts\Activate.ps1
pytest
```

## Useful commands

- Backend install: `pip install -r requirements.txt`
- Backend run: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend install: `cd frontend && npm install`
- Frontend run: `cd frontend && npm run dev`

```

> Start one terminal for the backend and another for the frontend so both services run concurrently.> Start one terminal for the backend and another for the frontend so both services run concurrently.