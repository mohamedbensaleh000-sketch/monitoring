import { useEffect, useMemo, useState } from "react";

const API = "/api";

const ComputerLogo = ({ className }) => (
  <svg className={className} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* Monitor Frame */}
    <rect x="10" y="15" width="80" height="55" rx="4" fill="#2d3436" />
    {/* Screen */}
    <rect x="15" y="20" width="70" height="45" rx="2" fill="#74b9ff" />
    {/* Screen Reflection */}
    <path d="M15 20L85 65V20H15Z" fill="white" fillOpacity="0.1" />
    {/* Stand */}
    <rect x="42" y="70" width="16" height="8" fill="#b2bec3" />
    <rect x="35" y="78" width="30" height="4" fill="#636e72" />
    {/* Keyboard */}
    <rect x="20" y="84" width="60" height="12" rx="2" fill="#b2bec3" />
    <path d="M25 88H75M25 92H75M35 84V96M45 84V96M55 84V96M65 84V96" stroke="#636e72" strokeWidth="0.5" />
  </svg>
);

function statusClass(color) {
  if (color === "red") return "card red";
  if (color === "gray") return "card gray";
  return "card green";
}

function toLocalInputValue(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export default function App() {
  const [postes, setPostes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [name, setName] = useState("");
  const [files, setFiles] = useState([]);
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [globalTime, setGlobalTime] = useState("");
  const [showGraph, setShowGraph] = useState(false);
  const [jumpTime, setJumpTime] = useState("");
  const [spliceSearch, setSpliceSearch] = useState("");
  const [exportStart, setExportStart] = useState("");
  const [exportEnd, setExportEnd] = useState("");

  // New Maintenance States
  const [view, setView] = useState("monitoring"); // "monitoring", "maintenance"
  const [user, setUser] = useState(null); // { email, token }
  const [authMode, setAuthMode] = useState("login"); // "login", "register", "forgot"
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [alerts, setAlerts] = useState([]);

  async function refreshPostes() {
    const res = await fetch(`${API}/postes`);
    setPostes(await res.json());
  }

  async function refreshAlerts() {
    const res = await fetch(`${API}/maintenance/alerts`);
    setAlerts(await res.json());
  }

  async function refreshDetail(posteId) {
    const res = await fetch(`${API}/postes/${posteId}`);
    const payload = await res.json();
    setDetail(payload);
    return payload;
  }

  useEffect(() => {
    refreshPostes();
    if (view === "maintenance") refreshAlerts();
  }, [view]);

  useEffect(() => {
    const id = setInterval(async () => {
      await fetch(`${API}/tick`, { method: "POST" });
      await refreshPostes();
      if (selected) {
        await refreshDetail(selected);
      }
      if (view === "maintenance") {
        await refreshAlerts();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [selected, view]);

  // Update filters only when selected poste changes or when manually refreshed
  useEffect(() => {
    if (detail && selected) {
      // Only set if inputs are empty to avoid overwriting user typing
      if (!filterStart) setFilterStart(toLocalInputValue(detail.filterStart));
      if (!filterEnd) setFilterEnd(toLocalInputValue(detail.filterEnd));
    }
  }, [selected, !!detail]);

  // --- Auth Actions ---
  async function handleAuth(e) {
    e.preventDefault();
    let url = `${API}/auth/login`;
    if (authMode === "register") url = `${API}/auth/register`;
    if (authMode === "forgot") {
      const res = await fetch(`${API}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail })
      });
      const data = await res.json();
      alert(data.message || data.detail);
      setAuthMode("login");
      return;
    }

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await res.json();
      if (res.ok) {
        setUser(data);
        setAuthPassword("");
      } else {
        alert(data.detail || "Une erreur est survenue lors de l'authentification.");
      }
    } catch (error) {
      console.error("Auth error:", error);
      alert("Impossible de contacter le serveur. Vérifiez que l'URL API dans App.jsx est correcte.");
    }
  }

  // --- Maintenance Actions ---
  async function claimAlert(alertId) {
    await fetch(`${API}/maintenance/claim`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_id: alertId, user_email: user.email })
    });
    refreshAlerts();
  }

  async function fixAlert(alertId) {
    await fetch(`${API}/maintenance/fix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_id: alertId, user_email: user.email })
    });
    refreshAlerts();
    refreshPostes();
  }

  async function addPoste(e) {
    e.preventDefault();
    if (!name || files.length === 0) return;
    const form = new FormData();
    form.append("name", name);
    for (const f of files) form.append("files", f);
    await fetch(`${API}/postes`, { method: "POST", body: form });
    setName("");
    setFiles([]);
    setIsAdding(false);
    await refreshPostes();
  }

  async function removePoste(id) {
    await fetch(`${API}/postes/${id}`, { method: "DELETE" });
    if (selected === id) {
      setSelected(null);
      setDetail(null);
    }
    await refreshPostes();
  }

  async function appendFiles(id, selectedFiles) {
    if (!selectedFiles || selectedFiles.length === 0) return;
    const form = new FormData();
    for (const f of selectedFiles) form.append("files", f);
    await fetch(`${API}/postes/${id}/append`, { method: "POST", body: form });
    await refreshPostes();
  }

  async function jumpAll() {
    if (!globalTime) return;
    await fetch(`${API}/postes/jump-all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: globalTime })
    });
    await refreshPostes();
  }

  async function openDetail(id) {
    setJumpTime("");
    setFilterStart("");
    setFilterEnd("");
    setExportStart("");
    setExportEnd("");
    setSelected(id);
    await refreshDetail(id);
  }

  async function action(path, body = null) {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined
    });
    if (res.ok) {
      if (path.includes("/jump")) {
        setJumpTime("");
      }
    }
    if (selected) await refreshDetail(selected);
    await refreshPostes();
  }

  async function downloadHistory() {
    if (!exportStart || !exportEnd) {
      alert("Veuillez sélectionner une plage de dates.");
      return;
    }
    const url = `${API}/postes/${selected}/export?start=${exportStart}&end=${exportEnd}`;
    window.open(url, '_blank');
  }

  const shiftFilterRows = useMemo(() => {
    if (!detail) return [];
    return [
      { label: "Shift 1 (06:00-14:30)", value: detail.shiftFilter.shift1 },
      { label: "Shift 2 (14:30-22:00)", value: detail.shiftFilter.shift2 },
      { label: "Shift 3 (22:00-06:00)", value: detail.shiftFilter.shift3 }
    ];
  }, [detail]);

  if (!selected) {
    return (
      <div className="page">
        <aside className="sidebar">
          <div className="nav-tabs">
            <button 
              className={view === "monitoring" ? "active" : ""} 
              onClick={() => setView("monitoring")}
            >
              <ComputerLogo className="nav-icon" /> Monitoring
            </button>
            <button 
              className={view === "maintenance" ? "active" : ""} 
              onClick={() => setView("maintenance")}
            >
              Group Maintenance
            </button>
          </div>
          
          <hr />

          {view === "monitoring" ? (
            <>
              <h3>LOI : Couleurs de l'icone PC</h3>
              <ul>
                <li>Vert: production active sans erreur</li>
                <li>Rouge: erreur signalee dans Error-Text</li>
                <li>Gris: inactivite (5/20/40 min)</li>
              </ul>
            </>
          ) : (
            <div className="auth-status">
              {user ? (
                <>
                  <p>Connecté en tant que : <br /><strong>{user.email}</strong></p>
                  <button className="ghost" onClick={() => setUser(null)}>Déconnexion</button>
                </>
              ) : (
                <p>Veuillez vous connecter pour gérer les maintenances.</p>
              )}
            </div>
          )}
        </aside>

        <div className="global-jump">
          <input 
            type="datetime-local" 
            value={globalTime} 
            onChange={(e) => setGlobalTime(e.target.value)} 
          />
          <button className="primary" onClick={jumpAll}>Synchroniser</button>
        </div>

        <main className="content">
          {view === "monitoring" ? (
            <>
              <div className="header-row">
                <h1>Monitoring - Postes de production</h1>
              </div>

              {isAdding && (
                <div className="modal-overlay">
                  <div className="modal">
                    <h2>Nouveau poste de production</h2>
                    <form className="modal-form" onSubmit={addPoste}>
                      <div className="form-group">
                        <label>Nom du poste</label>
                        <input 
                          value={name} 
                          onChange={(e) => setName(e.target.value)} 
                          placeholder="Ex: Poste 1" 
                          required 
                        />
                      </div>
                      <div className="form-group">
                        <label>Données Excel</label>
                        <input 
                          type="file" 
                          multiple 
                          accept=".xlsx" 
                          onChange={(e) => setFiles(Array.from(e.target.files || []))} 
                          required 
                        />
                      </div>
                      <div className="modal-actions">
                        <button type="button" className="ghost" onClick={() => setIsAdding(false)}>
                          Annuler
                        </button>
                        <button type="submit" className="primary">
                          Ajouter le poste
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}

              <div className="grid">
                {postes.map((poste) => (
                  <div key={poste.id} className="poste-wrap">
                    <button className={statusClass(poste.statusColor)} onClick={() => openDetail(poste.id)}>
                      <ComputerLogo className="pc-icon" />
                    </button>
                    <div className="poste-name">{poste.name}</div>
                    <div className="poste-status">{poste.statusText}</div>
                    <div className="poste-actions">
                      <button className="danger-text" onClick={() => removePoste(poste.id)}>
                        Supprimer
                      </button>
                      <label className="ghost add-files-btn">
                        + Ajouter Excel
                        <input 
                          type="file" 
                          multiple 
                          accept=".xlsx" 
                          style={{ display: 'none' }} 
                          onChange={(e) => appendFiles(poste.id, Array.from(e.target.files || []))} 
                        />
                      </label>
                    </div>
                  </div>
                ))}
                <div className="poste-wrap">
                  <div className="add-card" onClick={() => setIsAdding(true)}>
                    <span className="add-icon">+</span>
                    <span className="add-text">Nouveau Poste</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="maintenance-view">
              {!user ? (
                <div className="auth-container">
                  <div className="auth-card">
                    <h2>
                      {authMode === "login" ? "Connexion Maintenance" : 
                       authMode === "register" ? "Créer un compte" : "Mot de passe oublié"}
                    </h2>
                    <form onSubmit={handleAuth} className="auth-form">
                      <div className="form-group">
                        <label>Email Gmail</label>
                        <input 
                          type="email" 
                          value={authEmail} 
                          onChange={(e) => setAuthEmail(e.target.value)} 
                          placeholder="votre.nom@gmail.com" 
                          required 
                        />
                      </div>
                      {authMode !== "forgot" && (
                        <div className="form-group">
                          <label>Mot de passe</label>
                          <input 
                            type="password" 
                            value={authPassword} 
                            onChange={(e) => setAuthPassword(e.target.value)} 
                            placeholder="••••••••" 
                            required 
                          />
                        </div>
                      )}
                      <button type="submit" className="primary full">
                        {authMode === "login" ? "Se connecter" : 
                         authMode === "register" ? "S'inscrire" : "Envoyer le lien"}
                      </button>
                    </form>
                    <div className="auth-links">
                      {authMode === "login" ? (
                        <>
                          <button onClick={() => setAuthMode("register")}>Créer un compte</button>
                          <button onClick={() => setAuthMode("forgot")}>Mot de passe oublié ?</button>
                        </>
                      ) : (
                        <button onClick={() => setAuthMode("login")}>Déjà un compte ? Se connecter</button>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="alerts-dashboard">
                  <h1>Tableau de bord Maintenance</h1>
                  <p>Bienvenue, {user.email}. Voici les alertes en cours.</p>
                  
                  <div className="alerts-list">
                    {alerts.length === 0 ? (
                      <div className="no-alerts">Aucune défaillance technique détectée.</div>
                    ) : (
                      alerts.map(alert => (
                        <div key={alert.id} className={`alert-card ${alert.status}`}>
                          <div className="alert-header">
                            <span className="machine-name">
                              <ComputerLogo className="alert-pc-icon" /> {alert.poste_name}
                            </span>
                            <span className={`alert-status-badge ${alert.status}`}>
                              {alert.status === "pending" ? "EN ATTENTE" : 
                               alert.status === "claimed" ? "EN COURS" : "RÉPARÉ"}
                            </span>
                          </div>
                          <div className="alert-body">
                            <p className="error-msg"><strong>Défaillance technique :</strong> {alert.error_text}</p>
                            <p className="time">Depuis : {new Date(alert.start_time).toLocaleTimeString()}</p>
                            {alert.claimed_by && <p className="claimer">Pris en charge par : {alert.claimed_by}</p>}
                          </div>
                          <div className="alert-actions">
                            {alert.status === "pending" && (
                              <button className="primary" onClick={() => claimAlert(alert.id)}>
                                Je vais le réparer
                              </button>
                            )}
                            {alert.status === "claimed" && alert.claimed_by === user.email && (
                              <button className="success-btn" onClick={() => fixAlert(alert.id)}>
                                Marquer comme réparé (Gris)
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    );
  }

  if (!detail) return null;
  return (
    <div className="page">
      <div className="global-jump">
        <input 
          type="datetime-local" 
          value={globalTime} 
          onChange={(e) => setGlobalTime(e.target.value)} 
        />
        <button className="primary" onClick={jumpAll}>Synchroniser</button>
      </div>
      <aside className="sidebar">
        <h3>Controle simulation</h3>
        <div className="control-group">
          <button className="primary" onClick={() => action(`/postes/${selected}/toggle`)}>
            {detail.isPaused ? "Reprendre" : "Pause"}
          </button>
          <button className="ghost" onClick={() => action(`/postes/${selected}/restart`)}>Restart</button>
        </div>

        <div className="control-group">
          <div className="label-row">
            <label>Vitesse</label>
            <span className="value-badge">{detail.timeJumpValue} {detail.timeJumpUnit}</span>
          </div>
          <div className="input-row">
            <input
              type="range"
              min="1"
              max="60"
              value={detail.timeJumpValue}
              onChange={(e) =>
                action(`/postes/${selected}/settings`, {
                  simDelay: detail.simDelay,
                  timeJumpValue: Number(e.target.value),
                  timeJumpUnit: detail.timeJumpUnit
                })
              }
            />
            <select
              className="unit-select"
              value={detail.timeJumpUnit}
              onChange={(e) =>
                action(`/postes/${selected}/settings`, {
                  simDelay: detail.simDelay,
                  timeJumpValue: detail.timeJumpValue,
                  timeJumpUnit: e.target.value
                })
              }
            >
              <option>Sec</option>
              <option>Min</option>
              <option>Hrs</option>
            </select>
          </div>
        </div>

        <div className="control-group">
          <div className="label-row">
            <label>Rafraîchissement</label>
            <span className="value-badge">{detail.simDelay}s</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="3"
            step="0.1"
            value={detail.simDelay}
            onChange={(e) =>
              action(`/postes/${selected}/settings`, {
                simDelay: Number(e.target.value),
                timeJumpValue: detail.timeJumpValue,
                timeJumpUnit: detail.timeJumpUnit
              })
            }
          />
        </div>

        <div className="control-group">
          <label>Sauter à un temps</label>
          <input
            className="date-input"
            type="datetime-local"
            value={jumpTime || toLocalInputValue(detail.currentSimTime)}
            onChange={(e) => setJumpTime(e.target.value)}
          />
          <button 
            className="primary full-width" 
            onClick={() => {
              const target = jumpTime || toLocalInputValue(detail.currentSimTime);
              // Send the local time string as it is in the input (YYYY-MM-DDTHH:mm)
              action(`/postes/${selected}/jump`, { target: target });
            }}
          >
            Go
          </button>
        </div>

        <div className="control-group">
          <label>Filtre de production</label>
          <div className="filter-inputs">
            <div className="date-field">
              <span>Du:</span>
              <input className="date-input" type="datetime-local" value={filterStart} onChange={(e) => setFilterStart(e.target.value)} />
            </div>
            <div className="date-field">
              <span>Au:</span>
              <input className="date-input" type="datetime-local" value={filterEnd} onChange={(e) => setFilterEnd(e.target.value)} />
            </div>
          </div>
          <button
            className="primary full-width"
            onClick={() =>
              action(`/postes/${selected}/filter`, {
                start: filterStart,
                end: filterEnd
              })
            }
          >
            Appliquer le filtre
          </button>
        </div>
      </aside>

      <main className="content">
        <button className="ghost" onClick={() => setSelected(null)}>
          Retour a l'accueil
        </button>
        <h1>Suivi - {detail.name}</h1>
        <div className="kpis">
          <div className={`big-status ${detail.statusColor}`}>
            <ComputerLogo className="pc-icon" />
          </div>
          <div className="shift-circle">
            <div>SHIFT</div>
            <strong>{detail.totalShift}</strong>
            <small>PIECES</small>
          </div>
          <div className="meta">
            <div>Statut: {detail.statusText}</div>
            <div>Temps simule: {new Date(detail.currentSimTime).toLocaleString()}</div>
            <div>Derniere activite: {detail.lastActivity || "---"}</div>
          </div>
        </div>

        <div className="metrics">
          <div className="metric">Total: {detail.totalFiltered}</div>
          <div className="metric">Aujourd'hui: {detail.totalToday}</div>
          <div className="metric">Splice actuel: {detail.spliceCurrent}</div>
        </div>

        <h3>Shifts - jour simule</h3>
        <table>
          <tbody>
            <tr><td>Shift 1 (06:00-14:30)</td><td>{detail.shiftDay.shift1}</td></tr>
            <tr><td>Shift 2 (14:30-22:00)</td><td>{detail.shiftDay.shift2}</td></tr>
            <tr><td>Shift 3 (22:00-06:00)</td><td>{detail.shiftDay.shift3}</td></tr>
            <tr><td>Total</td><td>{detail.shiftDay.total}</td></tr>
          </tbody>
        </table>

        <h3>Shifts - filtre</h3>
        <table>
          <tbody>
            {shiftFilterRows.map((row) => (
              <tr key={row.label}>
                <td>{row.label}</td>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <button className={`expand-btn ${showGraph ? 'open' : ''}`} onClick={() => setShowGraph(!showGraph)}>
          <svg viewBox="0 0 24 24" width="32" height="32" stroke="#a855f7" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>

        {showGraph && (
          <div className="shifts-chart-v">
            <div className="chart-header-v">
              <h3>📊 Analyse de Production par Shift</h3>
              <div className="chart-legend-v">
                <span className="legend-item-v"><i className="dot s1"></i> Shift 1</span>
                <span className="legend-item-v"><i className="dot s2"></i> Shift 2</span>
                <span className="legend-item-v"><i className="dot s3"></i> Shift 3</span>
              </div>
            </div>
            <div className="chart-main-v">
              <div className="y-axis-v">
                <span>100%</span>
                <span>75%</span>
                <span>50%</span>
                <span>25%</span>
                <span>0%</span>
              </div>
              <div className="chart-container-v">
                {detail.shiftHistory.map((day) => {
                  const maxVal = Math.max(...detail.shiftHistory.map(d => Math.max(d.shift1, d.shift2, d.shift3)), 1);
                  return (
                    <div key={day.date} className="chart-group-v">
                      <div className="bars-v">
                        <div className="bar-v s1" style={{ height: `${(day.shift1 / maxVal) * 100}%` }} title={`Shift 1: ${day.shift1}`}>
                          {day.shift1 > 0 && <span className="bar-val-v">{day.shift1}</span>}
                          <div className="bar-glow"></div>
                        </div>
                        <div className="bar-v s2" style={{ height: `${(day.shift2 / maxVal) * 100}%` }} title={`Shift 2: ${day.shift2}`}>
                          {day.shift2 > 0 && <span className="bar-val-v">{day.shift2}</span>}
                          <div className="bar-glow"></div>
                        </div>
                        <div className="bar-v s3" style={{ height: `${(day.shift3 / maxVal) * 100}%` }} title={`Shift 3: ${day.shift3}`}>
                          {day.shift3 > 0 && <span className="bar-val-v">{day.shift3}</span>}
                          <div className="bar-glow"></div>
                        </div>
                      </div>
                      <div className="group-label-v">
                        <span className="day-name">{new Date(day.date).toLocaleDateString('fr-FR', { weekday: 'short' })}</span>
                        <span className="day-date">{new Date(day.date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        <div className="section-header-row">
          <h3>Details par splice</h3>
          <div className="search-box">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input 
              type="text" 
              placeholder="Rechercher un splice..." 
              value={spliceSearch}
              onChange={(e) => setSpliceSearch(e.target.value)}
            />
          </div>
        </div>
        <table>
          <thead><tr><th>Nom</th><th>Quantite</th></tr></thead>
          <tbody>
            {detail.breakdown
              .filter(r => r.name.toLowerCase().includes(spliceSearch.toLowerCase()))
              .map((r, idx) => (
                <tr key={`${r.name}-${idx}`}><td>{r.name}</td><td>{r.qty}</td></tr>
              ))}
          </tbody>
        </table>

        <div className="section-header-row">
          <h3>Historique des activites</h3>
          <div className="export-controls">
            <input 
              type="datetime-local" 
              value={exportStart} 
              onChange={(e) => setExportStart(e.target.value)} 
              className="mini-date"
            />
            <span className="to-sep">à</span>
            <input 
              type="datetime-local" 
              value={exportEnd} 
              onChange={(e) => setExportEnd(e.target.value)} 
              className="mini-date"
            />
            <button className="primary download-btn" onClick={downloadHistory}>
              <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" style={{marginRight: '6px'}}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Telecharger
            </button>
          </div>
        </div>
        <table>
          <thead><tr><th>Date</th><th>Time</th><th>Splice</th><th>Error</th></tr></thead>
          <tbody>
            {detail.history.map((r, idx) => (
              <tr key={idx}>
                <td>{r.Date}</td>
                <td>{r.Time}</td>
                <td>{r.Splice}</td>
                <td>{r["Error-Text"]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </div>
  );
}
