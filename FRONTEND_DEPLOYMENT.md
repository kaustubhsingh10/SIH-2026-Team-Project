# CrimeGraph AI — Frontend Deployment & Operational Guide

This document provides complete instructions for deploying, configuring, and operating the CrimeGraph AI frontend application for **SIH 2026**.

---

## 1. System Requirements

- **Client Browser**: Modern Browser with ES6 JavaScript support (Chrome 90+, Edge 90+, Firefox 88+, Safari 14+).
- **Backend API**: Python 3.10+ with FastAPI and Uvicorn (`run_server.py`).
- **Dependencies**: No Node.js build step is strictly required for production — the application uses native ES6 modules, Tailwind CDN, and standalone Vis.js network libraries.

---

## 2. Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/kaustubhsingh10/SIH-2026-Team-Project.git
   cd SIH-2026-Team-Project
   ```

2. **Backend Dependencies Installation**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

### Supported Configuration Keys:

| Environment Variable | Default Value | Description |
|----------------------|---------------|-------------|
| `CRIMEGRAPH_API_URL` | `http://127.0.0.1:8000` | Target FastAPI backend URL for client requests |
| `HOST` | `127.0.0.1` | Local IP address for Uvicorn server binding |
| `PORT` | `8000` | Port for REST API server |
| `NODE_ENV` | `production` | Deployment environment mode |

> [!IMPORTANT]
> Frontend client code runs in the user's browser. Never store private API secrets, database credentials, or model private keys in `.env` or client JS files.

---

## 4. Centralized API Configuration

Centralized frontend configuration is managed in `config.js` (`window.CRIMEGRAPH_CONFIG`):

```javascript
window.CRIMEGRAPH_CONFIG = {
    API_BASE_URL: window.location.origin.startsWith("http")
        ? window.location.origin
        : "http://127.0.0.1:8000",
    APP_NAME: "CrimeGraph AI",
    VERSION: "1.0.0"
};
```

To configure a custom backend endpoint in production without rebuilding, set `window.CRIMEGRAPH_CONFIG.API_BASE_URL` prior to loading `service.js`.

---

## 5. Running the Application

### Option A: Integrated FastAPI Server (Recommended for Production & SIH Demo)

Start the combined REST backend and static web host:

```powershell
python run_server.py --host 127.0.0.1 --port 8000
```

Access Points:
- **Web Frontend**: `http://127.0.0.1:8000/web/index.html` (or `http://127.0.0.1:8000/web/`)
- **API Health**: `http://127.0.0.1:8000/api/health`
- **Interactive OpenAPI Docs**: `http://127.0.0.1:8000/docs`

### Option B: Standalone Web Server / Static Hosting (Nginx / Vercel / Netlify / Live Server)

Serve root directory static files:

```powershell
python -m http.server 3000
```

Access at `http://127.0.0.1:3000`. The frontend service layer (`CrimeGraphDataService`) will auto-detect the live FastAPI backend at `http://127.0.0.1:8000`.

---

## 6. Architecture & Data Flow

```text
UI Views (Dashboard / Case Explorer / Graph Workspace / AI Investigator)
   ↓
window.dataService (CrimeGraphDataService Facade)
   ↓
HttpCrimeGraphAdapter (Auto-detects live FastAPI at /api/*)
   ↓ [Fallback if Offline: MockCrimeGraphAdapter]
FastAPI REST Backend (src/crimegraph/api/app.py)
   ↓
Aditya AI Intelligence Layer & KnowledgeGraphStore
```

---

## 7. Troubleshooting & Diagnostics

1. **Backend Offline Badge ("Backend Offline — Demo Mode")**:
   - Verify server status by navigating to `http://127.0.0.1:8000/api/health`.
   - Click the status badge in the header bar (`#adapter-status-badge`) to trigger connection recheck.

2. **CORS Errors**:
   - Ensure `app.py` has `CORSMiddleware` active with `allow_origins=["*"]`.

3. **Graph Not Rendering**:
   - Check browser console (`F12`) to verify Vis.js standalone script loaded from CDN.

4. **Direct Route Deep Linking**:
   - Hash routes are supported natively: `#dashboard`, `#cases`, `#graph`, `#ai-investigator`, `#timeline`, `#evidence`, `#reports`, `#CASE_101`, `#CASE_204`.
