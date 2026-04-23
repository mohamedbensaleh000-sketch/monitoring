from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def process_excel_data(file_obj: Any) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_obj)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")

    if "Date" not in df.columns or "Time" not in df.columns:
        # Try to guess or use default columns if common names exist
        if "date" in df.columns: df = df.rename(columns={"date": "Date"})
        if "time" in df.columns: df = df.rename(columns={"time": "Time"})
        
        if "Date" not in df.columns or "Time" not in df.columns:
            raise HTTPException(status_code=400, detail="Excel file must contain 'Date' and 'Time' columns")

    df["Date"] = df["Date"].astype(str)
    df["Time"] = df["Time"].astype(str)
    df["Timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce")
    
    # Drop rows where timestamp couldn't be parsed
    df = df.dropna(subset=["Timestamp"])
    
    if df.empty:
        raise HTTPException(status_code=400, detail="No valid date/time data found in Excel file")
        
    return df.sort_values("Timestamp").reset_index(drop=True)


def process_excel_files(files: list[UploadFile]) -> pd.DataFrame:
    frames = [process_excel_data(f.file) for f in files]
    if not frames:
        raise HTTPException(status_code=400, detail="No valid Excel file provided")
    merged = pd.concat(frames, ignore_index=True)
    return merged.sort_values("Timestamp").reset_index(drop=True)


def get_time_jump_delta(poste: "Poste") -> pd.Timedelta:
    if poste.time_jump_unit == "Sec":
        return pd.Timedelta(seconds=poste.time_jump_value)
    if poste.time_jump_unit == "Min":
        return pd.Timedelta(minutes=poste.time_jump_value)
    return pd.Timedelta(hours=poste.time_jump_value)


def compute_poste_status(poste: "Poste") -> tuple[str, str, pd.DataFrame, dict[str, Any] | None, pd.Timestamp]:
    color = "green"
    status = "Machine en Production"

    sim_time = poste.current_sim_time
    # Handle timezone mismatch between simulation time and data
    if not poste.data.empty:
        data_tz = poste.data["Timestamp"].dt.tz
        if data_tz is None and sim_time.tz is not None:
            sim_time = sim_time.tz_localize(None)
        elif data_tz is not None and sim_time.tz is None:
            sim_time = sim_time.tz_localize(data_tz)

    df_sim = poste.data[poste.data["Timestamp"] <= sim_time]
    last_row = df_sim.iloc[-1].to_dict() if not df_sim.empty else None

    if last_row:
        last_activity = pd.Timestamp(last_row["Timestamp"])
        # Ensure last_activity is naive if sim_time is naive for duration calculation
        if sim_time.tz is None and last_activity.tz is not None:
            last_activity = last_activity.tz_localize(None)
        
        has_error = pd.notna(last_row.get("Error-Text")) and str(last_row.get("Error-Text")).strip() != ""
        if has_error:
            color = "red"
            status = f"ERREUR : {last_row.get('Error-Text')}"
    else:
        last_activity = poste.last_activity_time
        if sim_time.tz is None and last_activity.tz is not None:
            last_activity = last_activity.tz_localize(None)
        color = "gray"
        status = "Machine en Repos (> 5 min)"

    idle_duration = (sim_time - last_activity).total_seconds() / 60
    if idle_duration >= 40:
        color = "gray"
        status = "La machine cessé de fonctionelle"
    elif idle_duration >= 20:
        color = "gray"
        status = "L'employeur est perdue"
    elif idle_duration > 5 and color == "green":
        color = "gray"
        status = "Machine en Repos (> 5 min)"

    return color, status, df_sim, last_row, last_activity


@dataclass
class Poste:
    id: str
    name: str
    data: pd.DataFrame
    current_sim_time: pd.Timestamp
    last_activity_time: pd.Timestamp
    is_paused: bool = False
    time_jump_value: int = 1
    time_jump_unit: str = "Sec"
    sim_delay: float = 1.0
    filter_start: datetime | None = None
    filter_end: datetime | None = None

    def base_payload(self) -> dict[str, Any]:
        color, status, _, _, _ = compute_poste_status(self)
        return {
            "id": self.id,
            "name": self.name,
            "statusColor": color,
            "statusText": status,
            "isPaused": self.is_paused,
            "currentSimTime": self.current_sim_time.isoformat(),
        }


class SettingsIn(BaseModel):
    simDelay: float
    timeJumpValue: int
    timeJumpUnit: str


class JumpIn(BaseModel):
    target: datetime | None = None
    finish: bool = False


class FilterIn(BaseModel):
    start: datetime
    end: datetime


class User(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    email: str
    token: str


class Alert(BaseModel):
    id: str
    poste_id: str
    poste_name: str
    error_text: str
    start_time: datetime
    status: str  # "pending", "claimed", "fixed"
    claimed_by: str | None = None


class MaintenanceAction(BaseModel):
    alert_id: str
    user_email: str


class Store:
    postes: dict[str, Poste] = field(default_factory=dict)
    users: dict[str, str] = field(default_factory=dict)  # email -> password
    alerts: dict[str, Alert] = field(default_factory=dict)

    def __init__(self) -> None:
        self.postes = {}
        self.users = {}
        self.alerts = {}


store = Store()
app = FastAPI(title="Leoni Schunk Monitoring API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_poste(poste_id: str) -> Poste:
    poste = store.postes.get(poste_id)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste not found")
    return poste


@app.get("/api/postes")
def list_postes() -> list[dict[str, Any]]:
    return [p.base_payload() for p in store.postes.values()]


# --- Authentication ---

@app.post("/api/auth/register")
def register(user: User):
    if user.email in store.users:
        raise HTTPException(status_code=400, detail="User already exists")
    store.users[user.email] = user.password
    return {"email": user.email, "token": "mock-token-" + str(uuid4())}


@app.post("/api/auth/login")
def login(user: User):
    if store.users.get(user.email) != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"email": user.email, "token": "mock-token-" + str(uuid4())}


@app.post("/api/auth/forgot-password")
def forgot_password(payload: dict):
    email = payload.get("email")
    if email not in store.users:
        raise HTTPException(status_code=404, detail="Email not found")
    # In a real app, send a reset link. Here we just return a success message.
    return {"message": "Password reset instructions sent to " + email}


# --- Maintenance ---

@app.get("/api/maintenance/alerts")
def get_alerts():
    return list(store.alerts.values())


@app.post("/api/maintenance/claim")
def claim_alert(action: MaintenanceAction):
    alert = store.alerts.get(action.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "pending":
        raise HTTPException(status_code=400, detail="Alert already claimed or fixed")
    
    alert.status = "claimed"
    alert.claimed_by = action.user_email
    print(f"MAINTENANCE LOG: User {action.user_email} claimed alert for {alert.poste_name}")
    return alert


@app.post("/api/maintenance/fix")
def fix_alert(action: MaintenanceAction):
    alert = store.alerts.get(action.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "fixed"
    
    # Update machine status to "gris" (simulated by setting a flag or jumping time)
    poste = store.postes.get(alert.poste_id)
    if poste:
        # In this simulation, we'll mark the machine as paused and "fixed" 
        # which will be reflected in compute_poste_status as gray if we handle it there.
        # For now, let's just force its current simulation time forward if needed or mark it.
        poste.is_paused = True 
        print(f"MAINTENANCE LOG: Machine {poste.name} marked as FIXED and PAUSED (Gris)")
    
    print(f"PROFESSIONAL MAIL: To Group Maintenance - Machine {alert.poste_name} has been fixed by {action.user_email}.")
    return alert


@app.post("/api/postes")
def create_poste(name: str = Form(...), files: list[UploadFile] = File(...)) -> dict[str, Any]:
    data = process_excel_files(files)
    start = data["Timestamp"].min()
    poste = Poste(
        id=str(uuid4()),
        name=name,
        data=data,
        current_sim_time=start,
        last_activity_time=start,
        filter_start=start.to_pydatetime(),
        filter_end=data["Timestamp"].max().to_pydatetime(),
    )
    store.postes[poste.id] = poste
    return poste.base_payload()


@app.put("/api/postes/{poste_id}")
def update_poste(poste_id: str, name: str = Form(...), files: list[UploadFile] | None = File(default=None)) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    poste.name = name
    if files:
        data = process_excel_files(files)
        poste.data = data
        poste.current_sim_time = data["Timestamp"].min()
        poste.last_activity_time = data["Timestamp"].min()
        poste.filter_start = data["Timestamp"].min().to_pydatetime()
        poste.filter_end = data["Timestamp"].max().to_pydatetime()
    return poste.base_payload()


@app.post("/api/postes/{poste_id}/append")
def append_to_poste(poste_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    new_data = process_excel_files(files)
    poste.data = pd.concat([poste.data, new_data], ignore_index=True).sort_values("Timestamp").reset_index(drop=True)
    poste.filter_start = poste.data["Timestamp"].min().to_pydatetime()
    poste.filter_end = poste.data["Timestamp"].max().to_pydatetime()
    return poste.base_payload()


@app.delete("/api/postes/{poste_id}")
def delete_poste(poste_id: str) -> dict[str, bool]:
    _get_poste(poste_id)
    del store.postes[poste_id]
    return {"ok": True}


@app.post("/api/postes/{poste_id}/toggle")
def toggle_pause(poste_id: str) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    poste.is_paused = not poste.is_paused
    return poste.base_payload()


@app.post("/api/postes/{poste_id}/restart")
def restart(poste_id: str) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    poste.current_sim_time = poste.data["Timestamp"].min()
    poste.last_activity_time = poste.data["Timestamp"].min()
    return poste.base_payload()


@app.post("/api/postes/{poste_id}/settings")
def update_settings(poste_id: str, payload: SettingsIn) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    poste.sim_delay = min(3.0, max(0.1, payload.simDelay))
    poste.time_jump_value = min(60, max(1, payload.timeJumpValue))
    poste.time_jump_unit = payload.timeJumpUnit if payload.timeJumpUnit in {"Sec", "Min", "Hrs"} else "Sec"
    return poste.base_payload()


@app.post("/api/postes/{poste_id}/jump")
def jump(poste_id: str, payload: JumpIn) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    if payload.finish:
        poste.current_sim_time = poste.data["Timestamp"].max()
        print(f"JUMP LOG: Machine {poste.name} jumped to FINISH: {poste.current_sim_time}")
    elif payload.target:
        # Ensure target is converted to naive timestamp if data is naive, or match timezone
        target_ts = pd.Timestamp(payload.target)
        if poste.data["Timestamp"].dt.tz is None and target_ts.tz is not None:
            target_ts = target_ts.tz_localize(None)
        poste.current_sim_time = target_ts
        print(f"JUMP LOG: Machine {poste.name} jumped to {poste.current_sim_time}")
    return poste.base_payload()


@app.post("/api/postes/{poste_id}/filter")
def update_filter(poste_id: str, payload: FilterIn) -> dict[str, bool]:
    poste = _get_poste(poste_id)
    start = payload.start
    end = payload.end
    if end < start:
        end = start
    poste.filter_start = start
    poste.filter_end = end
    return {"ok": True}


@app.post("/api/postes/jump-all")
def jump_all(payload: JumpIn) -> dict[str, bool]:
    for poste in store.postes.values():
        if payload.finish:
            poste.current_sim_time = poste.data["Timestamp"].max()
        elif payload.target:
            target_ts = pd.Timestamp(payload.target)
            if poste.data["Timestamp"].dt.tz is None and target_ts.tz is not None:
                target_ts = target_ts.tz_localize(None)
            poste.current_sim_time = target_ts
    return {"ok": True}


@app.post("/api/tick")
def tick_all() -> dict[str, bool]:
    for poste in store.postes.values():
        if not poste.is_paused and not poste.data.empty:
            poste.current_sim_time += get_time_jump_delta(poste)
            
            # Check for errors and handle 3-minute alert logic
            color, status, _, last_row, _ = compute_poste_status(poste)
            if color == "red" and last_row:
                error_start = pd.Timestamp(last_row["Timestamp"])
                
                # Ensure same timezone for subtraction
                sim_time = poste.current_sim_time
                if sim_time.tz is not None and error_start.tz is None:
                    error_start = error_start.tz_localize(sim_time.tz)
                elif sim_time.tz is None and error_start.tz is not None:
                    error_start = error_start.tz_localize(None)
                
                duration_mins = (sim_time - error_start).total_seconds() / 60
                
                if duration_mins >= 3:
                    # Check if an alert already exists for this error on this machine
                    alert_exists = any(a.poste_id == poste.id and a.status != "fixed" for a in store.alerts.values())
                    if not alert_exists:
                        alert_id = str(uuid4())
                        store.alerts[alert_id] = Alert(
                            id=alert_id,
                            poste_id=poste.id,
                            poste_name=poste.name,
                            error_text=last_row.get('Error-Text', 'Unknown error'),
                            start_time=poste.current_sim_time,
                            status="pending"
                        )
                        print(f"PROFESSIONAL MAIL: To Group Maintenance - Machine {poste.name} has a Technical failure: {last_row.get('Error-Text')}. Duration: {duration_mins:.1f} min.")
    
    return {"ok": True}


from fastapi.responses import FileResponse, StreamingResponse
import io

@app.get("/api/postes/{poste_id}/export")
def export_history(poste_id: str, start: str, end: str):
    poste = _get_poste(poste_id)
    
    # Convert dates and handle timezones
    fs = pd.Timestamp(start)
    fe = pd.Timestamp(end)
    
    data_tz = poste.data["Timestamp"].dt.tz
    if data_tz is None:
        if fs.tz is not None: fs = fs.tz_localize(None)
        if fe.tz is not None: fe = fe.tz_localize(None)
    else:
        if fs.tz is None: fs = fs.tz_localize(data_tz)
        if fe.tz is None: fe = fe.tz_localize(data_tz)

    # Filter data
    df_filtered = poste.data[(poste.data["Timestamp"] >= fs) & (poste.data["Timestamp"] <= fe)]
    
    if df_filtered.empty:
        raise HTTPException(status_code=404, detail="No data found for this time range")

    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtered.to_excel(writer, index=False, sheet_name='Historique')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="historique_{poste.name}_{start[:10]}.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.get("/api/postes/{poste_id}")
def poste_detail(poste_id: str) -> dict[str, Any]:
    poste = _get_poste(poste_id)
    color, status, df_sim, last_row, last_activity = compute_poste_status(poste)
    poste.last_activity_time = last_activity

    min_ts = poste.data["Timestamp"].min()
    max_ts = poste.data["Timestamp"].max()
    filter_start = poste.filter_start or min_ts.to_pydatetime()
    filter_end = poste.filter_end or max_ts.to_pydatetime()
    
    # Convert to pandas Timestamps and handle timezones
    fs = pd.Timestamp(filter_start)
    fe = pd.Timestamp(filter_end)
    
    data_tz = poste.data["Timestamp"].dt.tz
    if data_tz is None:
        if fs.tz is not None: fs = fs.tz_localize(None)
        if fe.tz is not None: fe = fe.tz_localize(None)
    else:
        if fs.tz is None: fs = fs.tz_localize(data_tz)
        if fe.tz is None: fe = fe.tz_localize(data_tz)

    df_filtered = df_sim[(df_sim["Timestamp"] >= fs) & (df_sim["Timestamp"] <= fe)] if not df_sim.empty else pd.DataFrame()
    total_filtered = int(len(df_filtered))

    current_day = poste.current_sim_time.date()
    df_today = df_sim[df_sim["Timestamp"].dt.date == current_day] if not df_sim.empty else pd.DataFrame()
    total_today = int(len(df_today))

    if not df_today.empty:
        minutes = df_today["Timestamp"].dt.hour * 60 + df_today["Timestamp"].dt.minute
        shift_1 = int(((minutes >= 360) & (minutes < 870)).sum())
        shift_2 = int(((minutes >= 870) & (minutes < 1320)).sum())
        shift_3 = int(((minutes >= 1320) | (minutes < 360)).sum())
    else:
        shift_1 = 0
        shift_2 = 0
        shift_3 = 0

    now_time = poste.current_sim_time.time()
    shift_start_1 = pd.Timestamp(current_day).replace(hour=6, minute=0)
    shift_end_1 = pd.Timestamp(current_day).replace(hour=14, minute=30)
    shift_start_2 = pd.Timestamp(current_day).replace(hour=14, minute=30)
    shift_end_2 = pd.Timestamp(current_day).replace(hour=22, minute=0)
    shift_start_3 = pd.Timestamp(current_day).replace(hour=22, minute=0)
    # Shift 3 spans midnight, so we check for both parts
    if shift_start_1.time() <= now_time < shift_end_1.time():
        df_shift = df_today[(df_today["Timestamp"] >= shift_start_1) & (df_today["Timestamp"] < shift_end_1)]
    elif shift_start_2.time() <= now_time < shift_end_2.time():
        df_shift = df_today[(df_today["Timestamp"] >= shift_start_2) & (df_today["Timestamp"] < shift_end_2)]
    elif now_time >= shift_start_3.time() or now_time < shift_start_1.time():
        # This handles the spanning midnight logic
        df_shift = df_today[(df_today["Timestamp"] >= shift_start_3) | (df_today["Timestamp"] < shift_start_1)]
    else:
        df_shift = pd.DataFrame()

    # breakdown logic fix
    if not df_sim.empty and "Splice" in df_sim.columns:
        counts = df_sim["Splice"].value_counts().reset_index()
        # Handle different pandas versions for value_counts().reset_index()
        # In newer versions it might have columns ['Splice', 'count']
        # In older versions it might have columns ['index', 'Splice']
        if "index" in counts.columns:
            counts = counts.rename(columns={"index": "name", "Splice": "qty"})
        elif "count" in counts.columns:
            counts = counts.rename(columns={"Splice": "name", "count": "qty"})
        else:
            # Fallback for other potential structures
            counts.columns = ["name", "qty"]
        breakdown = counts.to_dict("records")
    else:
        breakdown = []
    history = (
        df_sim[["Date", "Time", "Splice", "Error-Text"]].tail(10).fillna("").to_dict("records")
        if not df_sim.empty
        else []
    )

    # Calculate shift history per day from start to current sim time
    shift_history = []
    if not df_sim.empty:
        # Sort days to ensure chronological order
        unique_days = sorted(df_sim["Timestamp"].dt.date.unique())
        for d in unique_days:
            df_day = df_sim[df_sim["Timestamp"].dt.date == d]
            minutes = df_day["Timestamp"].dt.hour * 60 + df_day["Timestamp"].dt.minute
            s1 = int(((minutes >= 360) & (minutes < 870)).sum())
            s2 = int(((minutes >= 870) & (minutes < 1320)).sum())
            s3 = int(((minutes >= 1320) | (minutes < 360)).sum())
            shift_history.append({
                "date": str(d),
                "shift1": s1,
                "shift2": s2,
                "shift3": s3
            })

    return {
        "id": poste.id,
        "name": poste.name,
        "statusColor": color,
        "statusText": status,
        "currentSimTime": poste.current_sim_time.isoformat(),
        "lastActivity": f"{last_row['Date']} {last_row['Time']}" if last_row else None,
        "totalFiltered": total_filtered,
        "totalToday": total_today,
        "totalShift": int(len(df_shift)),
        "spliceCurrent": str(last_row.get("Splice", "---")) if last_row else "---",
        "isPaused": poste.is_paused,
        "simDelay": poste.sim_delay,
        "timeJumpValue": poste.time_jump_value,
        "timeJumpUnit": poste.time_jump_unit,
        "filterStart": filter_start.isoformat(),
        "filterEnd": filter_end.isoformat(),
        "shiftDay": {
            "shift1": shift_1,
            "shift2": shift_2,
            "shift3": shift_3,
            "total": total_today,
            "date": str(current_day),
        },
        "shiftFilter": {
            "shift1": int(((df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute >= 360) & (df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute < 870)).sum()) if not df_filtered.empty else 0,
            "shift2": int(((df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute >= 870) & (df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute < 1320)).sum()) if not df_filtered.empty else 0,
            "shift3": int(((df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute >= 1320) | (df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute < 360)).sum()) if not df_filtered.empty else 0,
            "total": total_filtered,
        },
        "breakdown": breakdown,
        "history": history,
        "shiftHistory": shift_history,
    }
