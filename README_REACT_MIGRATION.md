## React + Python Website

This project now has:

- `backend_api.py` (FastAPI): keeps the Python simulation/business logic.
- `frontend/` (React + Vite): modern UI for cards and dashboard.

### 1) Start backend

```bash
pip install -r requirements.txt
uvicorn backend_api:app --reload --port 8000
```

### 2) Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open the React site at `http://localhost:5173`.

### Preserved features

- Add/remove postes with Excel upload.
- Home page monitoring cards with color status (green/red/gray).
- Poste dashboard with:
  - pause/resume
  - restart simulation
  - speed controls (value + unit)
  - jump to target time / finish
  - totals, shift stats, splice breakdown, recent history
