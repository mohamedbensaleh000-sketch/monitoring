# Leoni Schunk Monitoring System

A unified monitoring system with a FastAPI backend and a React (Vite) frontend.

## Features
- Real-time machine monitoring.
- Production data analysis from Excel files.
- Maintenance alert system with claim/fix workflow.
- Historical data export.

---

## 🚀 Hosting on Render (Recommended)

This project is configured for **Unified Deployment** using Docker. This means the frontend and backend are hosted together as a single service.

### Steps to Deploy:
1. **Create a New Web Service**: In your [Render Dashboard](https://dashboard.render.com/), click **New +** > **Web Service**.
2. **Connect GitHub**: Connect this repository (`monitoring`).
3. **Environment**: Select **Docker**. Render will automatically detect the `Dockerfile` in the root.
4. **Instance Type**: You can use the **Free** tier.
5. **Deploy**: Click **Deploy Web Service**.

Once finished, Render will provide a single URL. The backend API is at `/api`, and the frontend is served at the root `/`.

---

## 🛠️ Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+

### 1. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start the backend server
# It will run on http://127.0.0.1:8000
uvicorn backend_api:app --reload
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
# It will run on http://127.0.0.1:5173
npm run dev
```

*Note: The frontend is configured to proxy requests to `http://127.0.0.1:8000` automatically during local development.*

---

## 🏗️ Manual Deployment (Without Docker)

If you prefer not to use Docker, you can host them as two separate services on Render:

### Backend (Web Service)
- **Runtime**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend_api:app`

### Frontend (Static Site)
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `frontend/dist`
- **Environment Variable**: You must set `VITE_API_URL` to your Backend URL.

---

## 📂 Project Structure
- `backend_api.py`: FastAPI server logic.
- `frontend/`: React application source code.
- `Dockerfile`: Configuration for unified containerized deployment.
- `requirements.txt`: Python dependencies.
