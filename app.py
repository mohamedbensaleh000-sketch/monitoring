import streamlit as st

import pandas as pd

import time

from datetime import datetime

import os
from urllib.parse import quote



# 1. Configuration de la page

st.set_page_config(page_title="Leoni Schunk Monitoring", layout="wide")

MACHINE_ICON_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'>
  <rect x='28' y='28' width='144' height='90' rx='8' fill='none' stroke='white' stroke-width='8'/>
  <rect x='40' y='40' width='120' height='66' rx='4' fill='white' opacity='0.16'/>
  <line x1='74' y1='126' x2='126' y2='126' stroke='white' stroke-width='8' stroke-linecap='round'/>
  <line x1='66' y1='140' x2='134' y2='140' stroke='white' stroke-width='8' stroke-linecap='round'/>
  <rect x='44' y='148' width='112' height='30' rx='4' fill='none' stroke='white' stroke-width='7'/>
  <line x1='64' y1='163' x2='136' y2='163' stroke='white' stroke-width='6' stroke-linecap='round'/>
</svg>
"""
MACHINE_ICON_URI = f"data:image/svg+xml;utf8,{quote(MACHINE_ICON_SVG)}"



# CSS pour le style du Logo et des cartes

st.markdown("""

    <style>

    .top-container {

        display: flex;

        justify-content: space-around;

        align-items: center;

        padding: 40px;

        margin-bottom: 20px;

    }

    .computer-box {

        width: 200px;

        height: 200px;

        border: 4px solid black;

        display: flex;

        flex-direction: column;

        align-items: center;

        justify-content: center;

        font-size: 150px;

        background-color: white;

        cursor: pointer;

    }

    .machine-circle {

        width: 160px;

        height: 160px;

        border: 6px solid #333;

        border-radius: 50%;

        display: flex;

        flex-direction: column;

        align-items: center;

        justify-content: center;

        font-size: 50px;

        font-weight: bold;

        background-color: #f8f9fa;

        box-shadow: inset 0 0 10px rgba(0,0,0,0.1);

        color: #333;

    }

    /* Couleurs de statut */

    .bg-green { background-color: #28a745 !important; color: white; }

    .bg-red { background-color: #dc3545 !important; color: white; }

    .bg-gray { background-color: #6c757d !important; color: white; }

   

    /* Style pour les cartes de poste sur la page d'accueil */

    .poste-container {

        display: flex;

        flex-direction: column;

        align-items: center;

        margin-bottom: 30px;

    }

   

    /* On va styliser le bouton Streamlit pour qu'il ressemble à la carte */

    [data-testid="stColumn"] div.stButton > button {

        border: 4px solid black !important;

        border-radius: 0px !important;

        width: 200px !important;

        height: 200px !important;

        background-color: white !important;

        color: black !important;

        font-size: 100px !important;

        display: flex !important;

        align-items: center !important;

        justify-content: center !important;

        padding: 0px !important;

        transition: transform 0.2s !important;

        position: relative !important;

        margin: 0 auto !important;

    }

   

    [data-testid="stColumn"] div.stButton > button:hover {

        transform: scale(1.05) !important;

        border-color: black !important;

        color: black !important;

    }



    [data-testid="stColumn"] div.stButton > button[key^="btn_open_"] {

        font-size: 150px !important;

        font-weight: 700 !important;

        letter-spacing: 1px !important;
        transform: none !important;

    }

    [data-testid="stColumn"] div.stButton > button[key^="btn_open_"]:hover {

        transform: none !important;

    }



    [data-testid="stColumn"] div.stButton > button[key="btn_add_new"] {

        width: 260px !important;

        height: 260px !important;

        font-size: 170px !important;

        font-weight: 700 !important;

        border-radius: 18px !important;

        box-shadow: 0 10px 26px rgba(0, 0, 0, 0.12) !important;

        transition: all 0.2s ease !important;

    }



    [data-testid="stColumn"] div.stButton > button[key="btn_add_new"]:hover {

        transform: translateY(-3px) scale(1.02) !important;

        box-shadow: 0 16px 30px rgba(0, 0, 0, 0.18) !important;

    }



    [data-testid="stColumn"] div.stButton > button[key^="btn_delete_"],
    [data-testid="stColumn"] div.stButton > button[key="btn_add_small"] {

        width: auto !important;
        height: auto !important;
        min-width: 78px !important;
        padding: 0.35rem 0.9rem !important;
        border: 1px solid #d9d9d9 !important;
        border-radius: 8px !important;
        background-color: white !important;
        color: #333 !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        box-shadow: none !important;

    }

    [data-testid="stColumn"] div.stButton > button[key^="btn_delete_"]:hover,
    [data-testid="stColumn"] div.stButton > button[key="btn_add_small"]:hover {

        transform: none !important;
        border-color: #bfbfbf !important;
        color: #111 !important;

    }

    .poste-label {

        margin-top: 10px;

        font-weight: bold;

        font-size: 18px;

        text-align: center;

    }

    .poste-status {

        margin-top: 6px;

        font-size: 13px;

        font-weight: 600;

        text-align: center;

    }

    .status-green { color: #28a745; }

    .status-red { color: #dc3545; }

    .status-gray { color: #6c757d; }

    </style>

""", unsafe_allow_html=True)



# 2. Gestion de l'état (Session State)

if 'postes' not in st.session_state:

    st.session_state.postes = []

if 'selected_poste_idx' not in st.session_state:

    st.session_state.selected_poste_idx = None

if 'show_add_form' not in st.session_state:

    st.session_state.show_add_form = False

if 'updating_poste_idx' not in st.session_state:

    st.session_state.updating_poste_idx = None



# 3. Fonction pour traiter les données Excel

def process_excel_data(file):

    try:

        df = pd.read_excel(file)

        # Nettoyage simple

        df['Date'] = df['Date'].astype(str)

        df['Time'] = df['Time'].astype(str)

        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

       

        # Ken fama ligne mafihch date, na3tiwah 15/12/2025 kima fel code original

        df['Timestamp'] = df['Timestamp'].fillna(pd.Timestamp('2025-12-15 08:00:00'))

       

        # Sort by timestamp to ensure correct simulation

        df = df.sort_values('Timestamp').reset_index(drop=True)

        return df

    except Exception as e:

        st.error(f"Erreur lors de la lecture du fichier : {e}")

        return None



def process_excel_files(files):

    valid_frames = []

    for file in files:

        df = process_excel_data(file)

        if df is not None:

            valid_frames.append(df)

    if not valid_frames:

        return None

    merged = pd.concat(valid_frames, ignore_index=True)

    merged = merged.sort_values('Timestamp').reset_index(drop=True)

    return merged


# 4. Fonctions de Navigation

def go_to_home():

    st.session_state.selected_poste_idx = None

    st.session_state.show_add_form = False

    st.session_state.updating_poste_idx = None

    st.rerun()



def open_add_form():

    st.session_state.show_add_form = True

    st.session_state.updating_poste_idx = None

    st.rerun()



def open_update_form(idx):

    st.session_state.updating_poste_idx = idx

    st.session_state.show_add_form = True

    st.rerun()



def select_poste(idx):

    st.session_state.selected_poste_idx = idx

    st.rerun()


def delete_poste(idx):

    if idx < 0 or idx >= len(st.session_state.postes):

        return

    st.session_state.postes.pop(idx)

    st.session_state.selected_poste_idx = None

    st.session_state.show_add_form = False

    st.session_state.updating_poste_idx = None

    st.rerun()



# Helpers partages pour statut/simulation
def get_time_jump_delta(poste):
    if poste['time_jump_unit'] == "Sec":
        return pd.Timedelta(seconds=poste['time_jump_value'])
    if poste['time_jump_unit'] == "Min":
        return pd.Timedelta(minutes=poste['time_jump_value'])
    return pd.Timedelta(hours=poste['time_jump_value'])


def compute_poste_status(poste):
    color_class = "bg-green"
    status_msg = "Machine en Production"

    df_full = poste['data']
    sim_time = poste['current_sim_time']
    df_sim = df_full[df_full['Timestamp'] <= sim_time]
    last_row = df_sim.iloc[-1] if not df_sim.empty else None

    if last_row is not None:
        last_activity = last_row['Timestamp']
        has_error = pd.notna(last_row['Error-Text']) and str(last_row['Error-Text']).strip() != ""
        if has_error:
            color_class = "bg-red"
            status_msg = f"ERREUR : {last_row['Error-Text']}"
    else:
        last_activity = poste.get('last_activity_time', sim_time)
        color_class = "bg-gray"
        status_msg = "Machine en Repos (> 5 min)"

    idle_duration = (sim_time - last_activity).total_seconds() / 60
    if idle_duration >= 40:
        color_class = "bg-gray"
        status_msg = "La machine cessé de fonctionelle"
    elif idle_duration >= 20:
        color_class = "bg-gray"
        status_msg = "L'employeur est perdue"
    elif idle_duration > 5 and color_class == "bg-green":
        color_class = "bg-gray"
        status_msg = "Machine en Repos (> 5 min)"

    return color_class, status_msg, df_sim, last_row, last_activity


# 5. Rendu de la page d'accueil

def render_home():

    st.title("Monitoring - Postes de production")



    with st.sidebar.expander("⚖️ LOI : Couleurs de l'icône PC", expanded=False):

        st.markdown("""

**Règles de Statut :**



🟢 **Vert (Production)**

- Machine active sans erreur.

- Délai d'activité < 5 minutes.



🔴 **Rouge (Erreur)**

- Une erreur est signalée dans le fichier Excel (Error-Text).



⚪ **Gris (Inactivité)**

- Repos : Inactif depuis plus de 5 minutes.

- Perte : Inactif depuis plus de 20 minutes (L'employeur est perdu).

- Arrêt : Inactif depuis plus de 40 minutes (La machine a cessé de fonctionner).

""")

   

    # Grid display

    cols = st.columns(4)

   

    # Display existing postes

    for i, poste in enumerate(st.session_state.postes):

        with cols[i % 4]:

            color_class, status_msg, _, _, _ = compute_poste_status(poste)



            # Poste Box as a clickable button

            color_hex = "#28a745" # default green

            if color_class == "bg-red":

                color_hex = "#dc3545"

            elif color_class == "bg-gray":

                color_hex = "#6c757d"



            # Use a container to group the styling and the button

            with st.container():

                st.markdown(f"""

                    <style>

                    div.element-container:has(.poste-style-marker-{i}) + div.element-container div.stButton > button {{

                        background-color: {color_hex} !important;
                        color: transparent !important;
                        border: 4px solid black !important;
                        border-radius: 0 !important;
                        width: 200px !important;
                        height: 200px !important;
                        font-size: 0 !important;
                        background-image: url("{MACHINE_ICON_URI}") !important;
                        background-repeat: no-repeat !important;
                        background-position: center !important;
                        background-size: 64% !important;
                        box-shadow: none !important;

                    }}

                    div.element-container:has(.poste-style-marker-{i}) + div.element-container div.stButton > button:hover {{
                        transform: scale(1.05) !important;
                        border-color: black !important;
                        color: transparent !important;
                    }}

                    </style>

                """, unsafe_allow_html=True)

                st.markdown(f'<div class="poste-style-marker-{i}"></div>', unsafe_allow_html=True)

                if st.button(" ", key=f"btn_open_{i}", use_container_width=True):

                    select_poste(i)

                st.markdown(f'<div class="poste-label">{poste["name"]}</div>', unsafe_allow_html=True)
                if st.button("Annuler", key=f"btn_delete_{i}"):
                    delete_poste(i)



    # Add button card

    with cols[len(st.session_state.postes) % 4]:

        with st.container():

            st.markdown("""

                <style>

                div.element-container:has(.nouveau-style-marker) + div.element-container div.stButton > button {

                    background-color: white !important;
                    background-image: none !important;

                    color: black !important;

                    font-size: 230px !important;
                    font-weight: 800 !important;
                    line-height: 1 !important;
                    border: 4px solid black !important;
                    border-radius: 0 !important;
                    width: 200px !important;
                    height: 200px !important;
                    box-shadow: none !important;

                }

                div.element-container:has(.nouveau-style-marker) + div.element-container div.stButton > button:hover {
                    transform: scale(1.05) !important;
                    background-image: none !important;
                    color: black !important;
                }

                </style>

            """, unsafe_allow_html=True)

            st.markdown('<div class="nouveau-style-marker"></div>', unsafe_allow_html=True)

            if st.button("＋", key="btn_add_new"):

                open_add_form()

            st.markdown('<div class="poste-label">add</div>', unsafe_allow_html=True)
            if st.button("+ add", key="btn_add_small"):
                open_add_form()



# 6. Formulaire d'ajout/mise à jour

def render_form():

    is_updating = st.session_state.updating_poste_idx is not None

    title = "Modifier le poste" if is_updating else "Ajouter un nouveau poste"

    st.header(title)

   

    with st.form("poste_form"):

        name = st.text_input("Nom du poste (ex: Poste 1, Machine X)",

                            value=st.session_state.postes[st.session_state.updating_poste_idx]['name'] if is_updating else "")

        excel_files = st.file_uploader(
            "Fichier(s) Excel (Minic III.xlsx)",
            type=["xlsx"],
            accept_multiple_files=True
        )

       

        submitted = st.form_submit_button("Enregistrer")

        if submitted:

            if not name:

                st.error("Le nom du poste est obligatoire.")

            elif (not excel_files or len(excel_files) == 0) and not is_updating:

                st.error("Veuillez sélectionner un fichier Excel.")

            else:

                data = None

                if excel_files and len(excel_files) > 0:

                    data = process_excel_files(excel_files)

               

                if data is not None or is_updating:

                    if is_updating:

                        idx = st.session_state.updating_poste_idx

                        st.session_state.postes[idx]['name'] = name

                        if data is not None:

                            st.session_state.postes[idx]['data'] = data

                            st.session_state.postes[idx]['current_sim_time'] = data['Timestamp'].min()

                            st.session_state.postes[idx]['last_activity_time'] = data['Timestamp'].min()

                    else:

                        new_poste = {

                            'name': name,

                            'data': data,

                            'current_sim_time': data['Timestamp'].min(),

                            'last_activity_time': data['Timestamp'].min(),

                            'is_paused': False,

                            'time_jump_value': 1,

                            'time_jump_unit': "Sec",

                            'sim_delay': 1.0

                        }

                        st.session_state.postes.append(new_poste)

                   

                    st.session_state.show_add_form = False

                    st.session_state.updating_poste_idx = None

                    st.rerun()



    if st.button("Annuler"):

        go_to_home()



# 7. Tableau de bord détaillé (Dashboard)

def render_dashboard():

    idx = st.session_state.selected_poste_idx

    poste = st.session_state.postes[idx]

    df_full = poste['data']

   

    if st.button("⬅️ Retour à l'accueil"):

        go_to_home()

       

    st.title(f"Suivi - {poste['name']}")

   

    with st.sidebar.expander("⚖️ LOI : Couleurs de l'icône PC", expanded=False):

        st.markdown("""

**Règles de Statut :**



🟢 **Vert (Production)**

- Machine active sans erreur.

- Délai d'activité < 5 minutes.



🔴 **Rouge (Erreur)**

- Une erreur est signalée dans le fichier Excel (Error-Text).



⚪ **Gris (Inactivité)**

- Repos : Inactif depuis plus de 5 minutes.

- Perte : Inactif depuis plus de 20 minutes (L'employeur est perdu).

- Arrêt : Inactif depuis plus de 40 minutes (La machine a cessé de fonctionner).

""")



    st.sidebar.header("⚙️ Contrôle Simulation")

    poste['sim_delay'] = st.sidebar.slider("Délai de rafraîchissement (Sec)", 0.1, 3.0, poste['sim_delay'])

   

    if st.sidebar.button("⏸️ Pause" if not poste['is_paused'] else "▶️ Reprendre"):

        poste['is_paused'] = not poste['is_paused']

        st.rerun()

       

    if st.sidebar.button("🔄 Restart Simulation"):

        poste['current_sim_time'] = df_full['Timestamp'].min()

        poste['last_activity_time'] = df_full['Timestamp'].min()

        st.rerun()

   

    if st.sidebar.button("✏️ Modifier le poste (+ add)"):

        open_update_form(idx)



    # Time Jump Logic

    time_jump = get_time_jump_delta(poste)



    # Sauter à un temps

    st.sidebar.divider()

    st.sidebar.subheader("📍 Sauter à un temps")

    default_date = poste['current_sim_time'].date()

    default_time = poste['current_sim_time'].time()

    jump_date = st.sidebar.date_input("Date", value=default_date)

    jump_time = st.sidebar.time_input("Heure", value=default_time)

    if st.sidebar.button("Go"):

        poste['current_sim_time'] = datetime.combine(jump_date, jump_time)

        st.rerun()

    if st.sidebar.button("Fin"):

        poste["current_sim_time"] = df_full["Timestamp"].max()

        st.rerun()



    # Filtre Total Produit

    st.sidebar.divider()

    st.sidebar.subheader("📊 Filtre Total Produit")

    min_ts = df_full['Timestamp'].min()

    max_ts = df_full['Timestamp'].max()

    min_date = min_ts.date()

    max_date = max_ts.date()



    if "filter_start" not in poste:

        poste["filter_start"] = min_ts.to_pydatetime() if hasattr(min_ts, "to_pydatetime") else min_ts

    if "filter_end" not in poste:

        poste["filter_end"] = max_ts.to_pydatetime() if hasattr(max_ts, "to_pydatetime") else max_ts



    with st.sidebar.form(key=f"filter_form_{idx}"):

        start_date = st.date_input(

            "Date Début",

            value=poste["filter_start"].date(),

            min_value=min_date,

            max_value=max_date,

        )

        end_date = st.date_input(

            "Date Fin",

            value=poste["filter_end"].date(),

            min_value=min_date,

            max_value=max_date,

        )

        start_time = st.time_input("Heure Début", value=poste["filter_start"].time())

        end_time = st.time_input("Heure Fin", value=poste["filter_end"].time())

        submitted_filter = st.form_submit_button("Go")



    if submitted_filter:

        new_filter_start = datetime.combine(start_date, start_time)

        new_filter_end = datetime.combine(end_date, end_time)

        if new_filter_end < new_filter_start:

            st.sidebar.warning("Date/heure fin < début. Fin ajustée = début.")

            new_filter_end = new_filter_start

        poste["filter_start"] = new_filter_start

        poste["filter_end"] = new_filter_end

        st.rerun()



    filter_start = poste["filter_start"]

    filter_end = poste["filter_end"]



    # Update simulation time

    if not poste['is_paused']:

        poste['current_sim_time'] += time_jump



    # Simulation data + unified status logic

    color_class, status_msg, df_sim, last_row, last_activity = compute_poste_status(poste)

    poste['last_activity_time'] = last_activity



    # --- CALCUL DES STATISTIQUES ---

    if not df_sim.empty:

        df_filtered = df_sim[(df_sim['Timestamp'] >= filter_start) & (df_sim['Timestamp'] <= filter_end)]

        total_filtered = len(df_filtered)

       

        current_day = poste['current_sim_time'].date()

        df_today = df_sim[df_sim['Timestamp'].dt.date == current_day]

        total_today = len(df_today)



        minutes_day = df_today["Timestamp"].dt.hour * 60 + df_today["Timestamp"].dt.minute if not df_today.empty else pd.Series([], dtype="int64")

        shift_1_day = int(((minutes_day >= 6 * 60) & (minutes_day < 14 * 60 + 30)).sum()) if not df_today.empty else 0

        shift_2_day = int(((minutes_day >= 14 * 60 + 30) & (minutes_day < 23 * 60)).sum()) if not df_today.empty else 0

        total_day = int(len(df_today))

        shifts_day_table = pd.DataFrame(

            [

                {

                    "Poste": poste["name"],

                    "Date (sim)": str(current_day),

                    "Shift 1": shift_1_day,

                    "Shift 2": shift_2_day,

                    "Hors shift": int(total_day - shift_1_day - shift_2_day),

                    "Total": total_day,

                }

            ]

        )

       

        # Shift Calculation

        now_time = poste['current_sim_time'].time()

        shift_start_1 = pd.Timestamp(current_day).replace(hour=6, minute=0)

        shift_end_1 = pd.Timestamp(current_day).replace(hour=14, minute=30)

        shift_start_2 = pd.Timestamp(current_day).replace(hour=14, minute=30)

        shift_end_2 = pd.Timestamp(current_day).replace(hour=23, minute=0)

       

        if shift_start_1.time() <= now_time < shift_end_1.time():

            df_shift = df_today[(df_today['Timestamp'] >= shift_start_1) & (df_today['Timestamp'] < shift_end_1)]

        elif shift_start_2.time() <= now_time < shift_end_2.time():

            df_shift = df_today[(df_today['Timestamp'] >= shift_start_2) & (df_today['Timestamp'] < shift_end_2)]

        else:

            df_shift = pd.DataFrame()

        total_shift = len(df_shift)

       

        breakdown = df_sim['Splice'].value_counts().reset_index()

        breakdown.columns = ['Nom (Splice)', 'Quantité']

        last_row = df_sim.iloc[-1]



        if df_filtered.empty:

            shifts_table = pd.DataFrame(

                [

                    {"Shift": "Shift 1 (06:00-14:30)", "Pièces": 0},

                    {"Shift": "Shift 2 (14:30-23:00)", "Pièces": 0},

                    {"Shift": "Hors shift", "Pièces": 0},

                ]

            )

        else:

            minutes_f = df_filtered["Timestamp"].dt.hour * 60 + df_filtered["Timestamp"].dt.minute

            s1 = int(((minutes_f >= 6 * 60) & (minutes_f < 14 * 60 + 30)).sum())

            s2 = int(((minutes_f >= 14 * 60 + 30) & (minutes_f < 23 * 60)).sum())

            total_f = int(len(df_filtered))

            shifts_table = pd.DataFrame(

                [

                    {"Shift": "Shift 1 (06:00-14:30)", "Pièces": s1},

                    {"Shift": "Shift 2 (14:30-23:00)", "Pièces": s2},

                    {"Shift": "Hors shift", "Pièces": int(total_f - s1 - s2)},

                ]

            )

    else:

        total_filtered = total_today = total_shift = 0

        breakdown = pd.DataFrame(columns=['Nom (Splice)', 'Quantité'])

        last_row = None

        shifts_day_table = pd.DataFrame(

            [

                {

                    "Poste": poste["name"],

                    "Date (sim)": str(poste["current_sim_time"].date()),

                    "Shift 1": 0,

                    "Shift 2": 0,

                    "Hors shift": 0,

                    "Total": 0,

                }

            ]

        )

        shifts_table = pd.DataFrame(

            [

                {"Shift": "Shift 1 (06:00-14:30)", "Pièces": 0},

                {"Shift": "Shift 2 (14:30-23:00)", "Pièces": 0},

                {"Shift": "Hors shift", "Pièces": 0},

            ]

        )



    # --- DASHBOARD UI ---

    t1, t2, t3 = st.columns([1, 1, 1])

    with t1:

        st.markdown(
            f'<div class="computer-box {color_class}" '
            f'style="background-image:url(\'{MACHINE_ICON_URI}\');'
            f'background-repeat:no-repeat;background-position:center;'
            f'background-size:64%;">'
            f'</div>',
            unsafe_allow_html=True
        )

    with t2:

        shift_html = (
            '<div style="display: flex; flex-direction: column; align-items: center;">'
            '<div class="machine-circle">'
            '<div style="font-size: 14px; color: #666; margin-bottom: -5px; letter-spacing: 2px;">SHIFT</div>'
            f'{total_shift}'
            '<div style="font-size: 12px; color: #888; margin-top: -5px;">PIÈCES</div>'
            '</div>'
            '</div>'
        )
        st.markdown(shift_html, unsafe_allow_html=True)

    with t3:

        st.markdown("#### ⚡ Vitesse")

        poste['time_jump_value'] = st.slider("Val.", 1, 60, poste['time_jump_value'], label_visibility="collapsed")

        poste['time_jump_unit'] = st.radio("Unité", ["Sec", "Min", "Hrs"],

                                          index=["Sec", "Min", "Hrs"].index(poste['time_jump_unit']),

                                          horizontal=True, label_visibility="collapsed")

        if poste['is_paused']:

            st.error("PAUSE", icon="⏸️")

        else:

            st.success(f"🚀 {poste['time_jump_value']} {poste['time_jump_unit']}/s")



    st.subheader(f"Statut : {status_msg}")

    st.write(f"🕒 Temps Machine (Simulé) : **{poste['current_sim_time'].strftime('%Y-%m-%d %H:%M:%S')}**")

    if last_row is not None:

        st.write(f"📄 Dernière activité Excel : **{last_row['Date']} {last_row['Time']}**")

   

    st.divider()

    cols = st.columns(3)

    cols[0].metric("📦 Total Pièces Produites", total_filtered)

    cols[1].metric("📅 Pièces Aujourd'hui", total_today)

    cols[2].metric("🔗 Splice ID Actuel", last_row['Splice'] if last_row is not None else "---")

   

    st.divider()

    st.subheader("📊 Shifts : Nombre de pièces (jour simulé)")

    st.dataframe(shifts_day_table, hide_index=True, use_container_width=True)

   

    st.divider()

    st.subheader("🕒 Shifts : Nombre de pièces (selon le filtre)")

    st.dataframe(shifts_table, hide_index=True, use_container_width=True)

   

    st.divider()

    st.write("**Détails par Nom (Splice) :**")

    st.dataframe(breakdown, hide_index=True, use_container_width=True)

   

    st.divider()

    st.subheader("📋 Historique des activités")

    if not df_sim.empty:

        st.dataframe(df_sim[['Date', 'Time', 'Splice', 'Error-Text']].tail(10), use_container_width=True)

    else:

        st.info("En attente de données...")



    if not poste['is_paused']:

        time.sleep(poste['sim_delay'])

        st.rerun()



# 8. Main App Logic

if st.session_state.show_add_form:

    render_form()

elif st.session_state.selected_poste_idx is not None:

    render_dashboard()

else:

    render_home()

   

    # Auto-refresh home page to update statuses if there are postes

    if st.session_state.postes:

        # Check if any poste is not paused

        if any(not p['is_paused'] for p in st.session_state.postes):

            active_postes = [p for p in st.session_state.postes if not p['is_paused']]

            # Advance simulation for all postes in background

            for p in active_postes:

                p['current_sim_time'] += get_time_jump_delta(p)

            refresh_delay = min(float(p.get('sim_delay', 1.0)) for p in active_postes)

            time.sleep(max(0.1, refresh_delay))

            st.rerun()