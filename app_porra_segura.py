import streamlit as st
import pandas as pd
import requests
import json
import os
import unicodedata
import datetime
import plotly.express as px

st.set_page_config(page_title="Clasificación Porra Mundial 2026", layout="wide")

def normalizar_texto(texto):
    """Quita acentos, tildes y pasa a minúsculas para comparar a prueba de fallos"""
    if not isinstance(texto, str):
        return ""
    # Normaliza y elimina caracteres diacríticos (tildes)
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().strip()

# ==========================================
# DICCIONARIO DE TRADUCCIÓN (API -> EXCEL)
# ==========================================
TRADUCTOR_PAISES = {
    "Spain": "España",
    "Brazil": "Brasil",
    "Belgium": "Bélgica",
    "Switzerland": "Suiza",
    "Japan": "Japón",
    "Austria": "Austria",
    "Ivory Coast": "Costa de Marfil",
    "Cote d'Ivoire": "Costa de Marfil",
    "Côte d'Ivoire": "Costa de Marfil",
    "Czech Republic": "República Checa",
    "Czechia": "República Checa",
    "Algeria": "Argelia",
    "DR Congo": "RD Congo",
    "Congo DR": "RD Congo",
    "Panama": "Panamá",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "Uruguay": "Uruguay",
    "Ecuador": "Ecuador",
    "Canada": "Canadá",
    "Egypt": "Egipto",
    "Saudi Arabia": "Arabia Saudí",
    "Uzbekistan": "Uzbekistán",
    "Iraq": "Iraq",
    "Morocco": "Marruecos",
    "South Korea": "Corea del Sur",
    "Korea Republic": "Corea del Sur",
    "New Zealand": "Nueva Zelanda",
    "Curacao": "Curazao",
    "Curaçao": "Curazao",
    "Mexico": "México",
    "Cape Verde": "Cabo Verde",
    "Cape Verde Islands": "Cabo Verde",
    "Germany": "Alemania",
    "Norway": "Noruega",
    "Paraguay": "Paraguay",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Iran": "Irán",
    "South Africa": "Sudáfrica",
    "Turkey": "Turquía",
    "Türkiye": "Turquía",
    "Ghana": "Ghana",
    "Sweden": "Suecia",
    "Haiti": "Haití",
    "Senegal": "Senegal",
    "Scotland": "Escocia",
    "Tunisia": "Túnez",
    "Australia": "Australia",
    "France": "Francia",
    "Qatar": "Qatar",

# LOS 6 PAÍSES QUE FALTABAN PARA COMPLETAR LOS 48 DEL MUNDIAL
    "United States": "Estados Unidos",
    "USA": "Estados Unidos",
    "Netherlands": "Países Bajos",
    "England": "Inglaterra",
    "Argentina": "Argentina",
    "Colombia": "Colombia",
    "Croatia": "Croacia"
}

# ==========================================
# CÓDIGOS DE BANDERAS (Para imágenes FlagCDN)
# ==========================================
CODIGOS_BANDERAS = {
    "México": "mx", "Corea del Sur": "kr", "Sudáfrica": "za", "República Checa": "cz",
    "Canadá": "ca", "Bosnia-Herzegovina": "ba", "Qatar": "qa", "Suiza": "ch",
    "Brasil": "br", "Marruecos": "ma", "Haití": "ht", "Escocia": "gb-sct",
    "Estados Unidos": "us", "Paraguay": "py", "Australia": "au", "Turquía": "tr",
    "Alemania": "de", "Curazao": "cw", "Costa de Marfil": "ci", "Ecuador": "ec",
    "Países Bajos": "nl", "Japón": "jp", "Suecia": "se", "Túnez": "tn",
    "Bélgica": "be", "Egipto": "eg", "Irán": "ir", "Nueva Zelanda": "nz",
    "España": "es", "Cabo Verde": "cv", "Cabo Verde": "cpv","Arabia Saudí": "sa", "Uruguay": "uy",
    "Francia": "fr", "Senegal": "sn", "Iraq": "iq", "Noruega": "no",
    "Argentina": "ar", "Argelia": "dz", "Austria": "at", "Jordania": "jo",
    "Portugal": "pt", "RD Congo": "cd", "Uzbekistán": "uz", "Colombia": "co",
    "Inglaterra": "gb-eng", "Croacia": "hr", "Ghana": "gh", "Panamá": "pa"
}

# ==========================================
# 1. CONFIGURACIÓN DE API Y CONTRASEÑA
# ==========================================
API_KEY = st.secrets["API_KEY"]
PASSWORD_WEB = str(st.secrets["PASSWORD_WEB"])
CACHE_PARTIDOS = "cache_partidos.json"
CACHE_GOLEADORES = "cache_goleadores.json"

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔒 Acceso Privado - Porra Mundial Santo Tomas Lizeoa 2026")
        pwd_input = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pwd_input == PASSWORD_WEB:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# 2. MOTOR DE DATOS (API FOOTBALL-DATA.ORG)
# ==========================================
def llamar_api(endpoint, archivo_cache, forzar_actualizacion=False):
    if not forzar_actualizacion and os.path.exists(archivo_cache):
        with open(archivo_cache, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://api.football-data.org/v4/{endpoint}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        datos = response.json()
        if "errorCode" not in datos:
            with open(archivo_cache, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False)
            return datos
        else:
            st.error(f"⚠️ Error de la API: {datos.get('message', 'Desconocido')}")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# ==========================================
# 3. TRADUCTOR DE DATOS (ETL)
# ==========================================
def procesar_datos_api(datos_partidos, datos_goleadores):
    victorias = []
    empates = []
    goleadores_dict = {}

    if datos_partidos and "matches" in datos_partidos:
        for partido in datos_partidos["matches"]:
            if partido.get("status") == "FINISHED":
                score = partido.get("score", {}).get("fullTime", {})
                home_score = score.get("home")
                away_score = score.get("away")

                home_team_en = partido.get("homeTeam", {}).get("name", "")
                away_team_en = partido.get("awayTeam", {}).get("name", "")

                home_team = TRADUCTOR_PAISES.get(home_team_en, home_team_en)
                away_team = TRADUCTOR_PAISES.get(away_team_en, away_team_en)

                if home_score is not None and away_score is not None:
                    if home_score > away_score:
                        victorias.append(home_team)
                    elif away_score > home_score:
                        victorias.append(away_team)
                    else:
                        empates.extend([home_team, away_team])

    if datos_goleadores and "scorers" in datos_goleadores:
        for scorer in datos_goleadores["scorers"]:
            nombre = scorer.get("player", {}).get("name", "").lower()
            goles = scorer.get("goals", 0)
            goleadores_dict[nombre] = goles

    return victorias, empates, goleadores_dict

# ==========================================
# 4. CARGA DE ARCHIVOS LOCALES (CSVs)
# ==========================================
@st.cache_data
def load_csv_data():
    participants = pd.read_csv("Participantes.csv", sep=';')
    teams = pd.read_csv("Equipos.csv", sep=';')
    players = pd.read_csv("Jugadores.csv", sep=';')
    rules = pd.read_csv("Reglas.csv", sep=';')
    return participants, teams, players, rules

try:
    participants, teams, players, rules = load_csv_data()
    team_rules = rules[rules['Type'] == 'Team'].set_index('Group')[['Win', 'Draw']].astype(float)
    player_rules_raw = rules[rules['Type'].isin(['G1', 'G2', 'G3', 'G4', 'G5'])]
    player_rules = pd.Series(player_rules_raw['Group'].values, index=player_rules_raw['Type']).astype(float)
except FileNotFoundError:
    st.error("Faltan los archivos CSV. Súbelos a la misma carpeta.")
    st.stop()

# ==========================================
# 5. INTERFAZ Y CÁLCULO
# ==========================================
st.title("🏆 Porra Mundial 2026")

st.sidebar.header("⚙️ Sincronización")
forzar = False
if st.sidebar.button("🔄 Sincronizar con API-Football"):
    forzar = True
    st.sidebar.success("Sincronizando... (Consumiendo peticiones)")

datos_p = llamar_api("competitions/WC/matches", "cache_partidos.json", forzar)
datos_g = llamar_api("competitions/WC/scorers?limit=100", "cache_goleadores.json", forzar)
datos_e = llamar_api("competitions/WC/teams", "cache_equipos.json", forzar)
datos_s = llamar_api("competitions/WC/standings", "cache_standings.json", forzar)

api_victorias, api_empates, api_goleadores = procesar_datos_api(datos_p, datos_g)


# ==========================================
# 3.5. MOTOR DE BONIFICACIONES GLOBALES
# ==========================================
def calcular_bonuses_globales(datos_p, datos_s, goleadores_dict):
    equipos_bonus = {}
    detalles_bonus_equipo = {}

    def add_bonus(equipo, pts, motivo):
        if equipo not in equipos_bonus:
            equipos_bonus[equipo] = 0
            detalles_bonus_equipo[equipo] = []
        equipos_bonus[equipo] += pts
        detalles_bonus_equipo[equipo].append(f"{motivo} (+{pts})")

    # A. FASE DE GRUPOS
    if datos_s and "standings" in datos_s:
        todos_los_grupos_terminados = True
        lista_terceros = []

        for grupo in datos_s["standings"]:
            if grupo.get("type") == "TOTAL":
                tabla = grupo.get("table", [])

                # Candado de Grupo: ¿Han jugado todos en este grupo sus 3 partidos?
                grupo_terminado = tabla and all(team.get("playedGames", 0) >= 3 for team in tabla)

                if not grupo_terminado:
                    todos_los_grupos_terminados = False

                if grupo_terminado:
                    # El grupo terminó, repartimos 1º y 2º
                    for team in tabla:
                        pos = team.get("position")
                        name_en = team.get("team", {}).get("name", "")
                        name_es = TRADUCTOR_PAISES.get(name_en, name_en)

                        if pos == 1:
                            add_bonus(name_es, 20, "1º Grupo")
                        elif pos == 2:
                            add_bonus(name_es, 10, "2º Grupo")
                        elif pos == 3:
                            # Guardamos los datos del tercero para la liguilla final
                            lista_terceros.append({
                                "name": name_es,
                                "points": team.get("points", 0),
                                "gd": team.get("goalDifference", 0),
                                "gf": team.get("goalsFor", 0)
                            })

        # Candado Global de Terceros: Si TODOS los grupos han terminado
        if todos_los_grupos_terminados and len(lista_terceros) >= 8:
            # Ordenamos según reglas FIFA: Puntos -> Diferencia Goles -> Goles a Favor
            mejores_terceros = sorted(
                lista_terceros,
                key=lambda x: (x["points"], x["gd"], x["gf"]),
                reverse=True
            )
            # Repartimos el bonus SOLO a los 8 mejores de esa lista
            for equipo in mejores_terceros[:8]:
                add_bonus(equipo["name"], 5, "Clasificado como 3º")

    # B. ELIMINATORIAS Y FINAL
    mundial_terminado = False
    if datos_p and "matches" in datos_p:
        fases_eliminatoria = ["LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "SEMIFINALS"]
        for m in datos_p["matches"]:
            if m.get("status") == "FINISHED":
                stage = m.get("stage")

                # Candado Pichichi: Chequeamos si la gran final ya se ha jugado
                if stage == "FINAL":
                    mundial_terminado = True

                winner_enum = m.get("score", {}).get("winner")
                h_en = m.get("homeTeam", {}).get("name", "")
                a_en = m.get("awayTeam", {}).get("name", "")
                h_es = TRADUCTOR_PAISES.get(h_en, h_en)
                a_es = TRADUCTOR_PAISES.get(a_en, a_en)

                ganador, perdedor = None, None
                if winner_enum == "HOME_TEAM":
                    ganador, perdedor = h_es, a_es
                elif winner_enum == "AWAY_TEAM":
                    ganador, perdedor = a_es, h_es

                if ganador:
                    if stage in fases_eliminatoria:
                        add_bonus(ganador, 5, "Pasa Eliminatoria")
                    elif stage == "FINAL":
                        add_bonus(ganador, 50, "🏆 Campeón")
                        add_bonus(perdedor, 25, "🥈 Subcampeón")

    # C. PICHICHI (Solo se reparte cuando el Mundial haya terminado)
    jugadores_bonus = {}
    if mundial_terminado and goleadores_dict:
        max_goles = max(goleadores_dict.values())
        if max_goles > 0:
            for jug, goles in goleadores_dict.items():
                if goles == max_goles:
                    jugadores_bonus[jug] = 25

    return equipos_bonus, detalles_bonus_equipo, jugadores_bonus

bonus_eq, detalles_bonus_eq, bonus_jug = calcular_bonuses_globales(datos_p, datos_s, api_goleadores)

st.sidebar.write("---")
st.sidebar.subheader("📊 Resumen del Torneo")
st.sidebar.write(f"**Partidos procesados:** {len(api_victorias) + len(api_empates) // 2}")

tab_clasificacion, tab_elecciones, tab_marcador, tab_oficial, tab_estadisticas = st.tabs([
    "📊 Clasificación", "👀 Ver Elecciones", "🏟️ Marcador", "🏅 Grupos y Cruces", "📈 Estadísticas"
])

# ---------------------------------------------------------
# PESTAÑA 1: LA CLASIFICACIÓN
# ---------------------------------------------------------
with tab_clasificacion:
    st.markdown("<h2 style='text-align: center;'>🏆 Clasificación General</h2>", unsafe_allow_html=True)
    st.write("---")

    def calcular_puntos(row):
        p_id = row['ParticipantID']
        p_equipos, p_jugadores, p_bonus = 0, 0, 0

        # Equipos
        mis_equipos = teams[teams['ParticipantID'] == p_id].iloc[0]
        for grupo in team_rules.index:
            eq = mis_equipos.get(grupo, "")
            if pd.notna(eq) and isinstance(eq, str):
                eq = eq.strip()
                num_v = api_victorias.count(eq)
                num_e = api_empates.count(eq)
                p_equipos += (num_v * team_rules.loc[grupo, 'Win'])
                p_equipos += (num_e * team_rules.loc[grupo, 'Draw'])
                if eq in bonus_eq:
                    p_bonus += bonus_eq[eq]

        # Jugadores
        mis_jugadores = players[players['ParticipantID'] == p_id].iloc[0]
        for grupo in player_rules.index:
            jugadores_str = mis_jugadores.get(grupo, "")
            if pd.notna(jugadores_str) and isinstance(jugadores_str, str):
                for jug in jugadores_str.split(";"):
                    jug_limpio = normalizar_texto(jug)
                    if not jug_limpio or len(jug_limpio) < 2: continue

                    for api_jug, goles in api_goleadores.items():
                        api_limpio = normalizar_texto(api_jug)
                        if not api_limpio or len(api_limpio) < 2: continue

                        if jug_limpio in api_limpio or api_limpio in jug_limpio:
                            p_jugadores += (player_rules[grupo] * goles)
                            if api_jug in bonus_jug:
                                p_bonus += bonus_jug[api_jug]
                            break

        return pd.Series([p_equipos, p_jugadores, p_bonus, p_equipos + p_jugadores + p_bonus],
                         index=['PE', 'PJ', 'PB', 'PTS'])

    resultados = participants.join(participants.apply(calcular_puntos, axis=1))
    resultados = resultados.sort_values(by=['PTS', 'PE'], ascending=[False, False]).reset_index(drop=True)
    resultados.insert(0, 'Pos', resultados.index + 1)

    # 💾 GUARDAR MEMORIA HISTÓRICA
    fecha_hoy = str(datetime.date.today())
    archivo_historial = "historial_posiciones.csv"
    df_hoy = resultados[['Name', 'Pos', 'PTS']].copy()
    df_hoy['Fecha'] = fecha_hoy

    if os.path.exists(archivo_historial):
        historial_csv = pd.read_csv(archivo_historial)
        historial_csv = historial_csv[historial_csv['Fecha'] != fecha_hoy]
        historial_csv = pd.concat([historial_csv, df_hoy])
    else:
        historial_csv = df_hoy
    historial_csv.to_csv(archivo_historial, index=False)

    def poner_medallas(row):
        if row['Pos'] == 1: return f"🥇 {row['Name']}"
        elif row['Pos'] == 2: return f"🥈 {row['Name']}"
        elif row['Pos'] == 3: return f"🥉 {row['Name']}"
        elif row['Pos'] == len(resultados): return f"🔻 {row['Name']}"
        else: return f"  {row['Name']}"

    resultados['Participante'] = resultados.apply(poner_medallas, axis=1)
    df_mostrar = resultados[['Pos', 'Participante', 'PE', 'PJ', 'PB', 'PTS']]

    def estilo_liga(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        styles.loc[0, :] = 'background-color: rgba(46, 204, 113, 0.3);'
        styles.loc[1:2, :] = 'background-color: rgba(46, 204, 113, 0.1);'
        if len(df) > 3:
            styles.loc[df.index[-1], :] = 'background-color: rgba(231, 76, 60, 0.1);'
        styles['PTS'] = styles['PTS'] + ' font-weight: bold; font-size: 1.05em;'
        return styles

    df_estilizado = df_mostrar.style.apply(estilo_liga, axis=None).hide(axis="index")
    altura_tabla = (len(resultados) + 1) * 35 + 10
    st.dataframe(df_estilizado, use_container_width=True, height=altura_tabla)
    st.caption("🟩 **Zona de Podio** | 🟥 **Farolillo Rojo** | **PE**: Pts Equipos | **PJ**: Pts Jugadores | **PB**: Pts Bonus | **PTS**: Puntos Totales")

# ---------------------------------------------------------
# PESTAÑA 2: VER LAS ELECCIONES
# ---------------------------------------------------------
with tab_elecciones:
    st.markdown("### Selecciona un participante para ver su elección")
    amigo_elegido = st.selectbox("👤 Participante:", participants['Name'])
    id_amigo = participants[participants['Name'] == amigo_elegido]['ParticipantID'].iloc[0]

    mis_equipos = teams[teams['ParticipantID'] == id_amigo].iloc[0]
    mis_jugadores = players[players['ParticipantID'] == id_amigo].iloc[0]

    desglose_equipos, total_equipos, total_bonus_eq = [], 0, 0
    for grupo in team_rules.index:
        eq = mis_equipos.get(grupo, "")
        if pd.notna(eq) and isinstance(eq, str):
            eq = eq.strip()
            if not eq: continue

            pts_win = team_rules.loc[grupo, 'Win']
            pts_draw = team_rules.loc[grupo, 'Draw']
            num_victorias = api_victorias.count(eq)
            num_empates = api_empates.count(eq)
            puntos_base_equipo = (num_victorias * pts_win) + (num_empates * pts_draw)

            bono_pts = bonus_eq.get(eq, 0)
            str_bono = " | ".join(detalles_bonus_eq.get(eq, [])) if bono_pts > 0 else "-"
            estado = f"✅ {num_victorias}V / {num_empates}E" if puntos_base_equipo > 0 else "⏳ Pendiente / Derrotas"
            pts_totales = puntos_base_equipo + bono_pts

            desglose_equipos.append({
                "Equipo": eq, "Resultado": estado, "Bonus Logrados": str_bono, "Puntos Obtenidos": pts_totales
            })
            total_equipos += puntos_base_equipo
            total_bonus_eq += bono_pts
    df_equipos_amigo = pd.DataFrame(desglose_equipos)

    desglose_jugadores, total_jugadores, total_bonus_jug = [], 0, 0
    for grupo in player_rules.index:
        jugadores_str = mis_jugadores.get(grupo, "")
        if pd.notna(jugadores_str) and isinstance(jugadores_str, str):
            for jug in jugadores_str.split(";"):
                jug = jug.strip()
                if not jug or len(jug) < 2: continue

                jug_limpio = normalizar_texto(jug)
                goles_marcados, puntos_base, valor_gol = 0, 0, player_rules[grupo]
                bono_pts, str_bono = 0, "-"

                for api_jug, goles in api_goleadores.items():
                    api_limpio = normalizar_texto(api_jug)
                    if not api_limpio or len(api_limpio) < 2: continue

                    if jug_limpio in api_limpio or api_limpio in jug_limpio:
                        goles_marcados = goles
                        puntos_base = valor_gol * goles_marcados
                        if api_jug in bonus_jug:
                            bono_pts = bonus_jug[api_jug]
                            str_bono = "👑 Pichichi"
                        break

                pts_totales = puntos_base + bono_pts
                desglose_jugadores.append({
                    "Jugador": jug, "Goles": goles_marcados, "Cálculo": f"{goles_marcados} x {valor_gol}",
                    "Bonus Logrados": str_bono, "Total Puntos": pts_totales
                })
                total_jugadores += puntos_base
                total_bonus_jug += bono_pts
    df_jugadores_amigo = pd.DataFrame(desglose_jugadores)

    col1, col2 = st.columns(2)
    def resaltar_puntos(row, col_name):
        return ['background-color: rgba(46, 204, 113, 0.2)'] * len(row) if row[col_name] > 0 else [''] * len(row)

    with col1:
        st.success("🛡️ Puntos por Equipos")
        if not df_equipos_amigo.empty:
            altura_eq = (len(df_equipos_amigo) + 1) * 35 + 15
            st.dataframe(df_equipos_amigo.style.apply(resaltar_puntos, col_name="Puntos Obtenidos", axis=1),
                         use_container_width=True, hide_index=True, height=altura_eq)
        else: st.info("Sin equipos.")

    with col2:
        st.info("⚽ Puntos por Jugadores")
        if not df_jugadores_amigo.empty:
            altura_jug = (len(df_jugadores_amigo) + 1) * 35 + 15
            st.dataframe(df_jugadores_amigo.style.apply(resaltar_puntos, col_name="Total Puntos", axis=1),
                         use_container_width=True, hide_index=True, height=altura_jug)
        else: st.info("Sin jugadores.")

    st.write("---")
    st.markdown(f"### 🏆 Resumen de {amigo_elegido}")
    total_absoluto = total_equipos + total_jugadores + total_bonus_eq + total_bonus_jug
    met_col1, met_col2, met_col3, met_col4 = st.columns(4)
    met_col1.metric("Puntos Equipos", f"{total_equipos} pts")
    met_col2.metric("Puntos Jugadores", f"{total_jugadores} pts")
    met_col3.metric("Puntos Bonus", f"{total_bonus_eq + total_bonus_jug} pts")
    met_col4.metric("TOTAL", f"{total_absoluto} pts")

# ---------------------------------------------------------
# PESTAÑA 3: MARCADOR VISUAL DE PARTIDOS
# ---------------------------------------------------------
with tab_marcador:
    st.markdown("<h2 style='text-align: center;'>🏟️ Resultados del Mundial</h2>", unsafe_allow_html=True)
    st.write("---")

    if datos_p and "matches" in datos_p:
        estados_validos = ["FINISHED", "IN_PLAY", "PAUSED"]
        partidos_mostrar = [p for p in datos_p["matches"] if p.get("status") in estados_validos]

        if not partidos_mostrar:
            st.info("Aún no hay partidos para mostrar.")
        else:
            for p in partidos_mostrar:
                home = p.get("homeTeam", {}).get("name", "Local")
                away = p.get("awayTeam", {}).get("name", "Visitante")
                home_es = TRADUCTOR_PAISES.get(home, home)
                away_es = TRADUCTOR_PAISES.get(away, away)
                iso_h = CODIGOS_BANDERAS.get(home_es, "")
                iso_a = CODIGOS_BANDERAS.get(away_es, "")

                img_h = f"<img src='https://flagcdn.com/32x24/{iso_h}.png' width='32' style='vertical-align: text-bottom; border-radius: 3px;'>" if iso_h else "🏳️"
                img_a = f"<img src='https://flagcdn.com/32x24/{iso_a}.png' width='32' style='vertical-align: text-bottom; border-radius: 3px;'>" if iso_a else "🏳️"

                score_info = p.get("score", {})
                score_h = score_info.get("fullTime", {}).get("home")
                score_a = score_info.get("fullTime", {}).get("away")
                if score_h is None: score_h = score_info.get("regularTime", {}).get("home", 0)
                if score_a is None: score_a = score_info.get("regularTime", {}).get("away", 0)

                en_vivo = p.get("status") in ["IN_PLAY", "PAUSED"]

                # DISEÑO ADAPTABLE A MÓVILES (FLEXBOX)
                if en_vivo:
                    marcador_html = f"<div style='border: 2px solid #e74c3c; border-radius: 10px; padding: 2px 10px; color: #e74c3c;'><h3 style='margin:0; text-align:center;'>{score_h} - {score_a}</h3><div style='font-size: 10px; text-align:center; font-weight: bold;'>🔴 EN VIVO</div></div>"
                else:
                    marcador_html = f"<div style='border: 2px solid #4CAF50; border-radius: 10px; padding: 5px 10px;'><h3 style='margin:0; text-align:center;'>{score_h} - {score_a}</h3></div>"

                st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 5px; background-color: rgba(0,0,0,0.05); border-radius: 10px;'>
                    <div style='text-align: right; width: 40%; font-size: 1.1em;'><b>{home_es}</b> {img_h}</div>
                    <div style='text-align: center; width: 20%;'>{marcador_html}</div>
                    <div style='text-align: left; width: 40%; font-size: 1.1em;'>{img_a} <b>{away_es}</b></div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No se han podido cargar los partidos.")

    st.markdown("<br><h2 style='text-align: center;'>⚽ Top Goleadores</h2>", unsafe_allow_html=True)
    st.write("---")

    if api_goleadores:
        goleadores_ordenados = sorted(api_goleadores.items(), key=lambda x: (-x[1], x[0]))
        col_g1, col_g2 = st.columns(2)
        for i, (nombre, goles) in enumerate(goleadores_ordenados):
            columna_actual = col_g1 if i % 2 == 0 else col_g2
            with columna_actual:
                st.markdown(f"🏃‍♂️ **{nombre.title()}**: {goles} goles")
    else:
        st.info("Aún no hay goleadores.")

# ---------------------------------------------------------
# PESTAÑA 4: CLASIFICACIÓN OFICIAL
# ---------------------------------------------------------
with tab_oficial:
    st.markdown("<h2 style='text-align: center;'>🏅 Situación del Mundial</h2>", unsafe_allow_html=True)
    selector_fase = st.radio("Ver fase:", ["Fase de Grupos", "Cruces Directos (Eliminatorias)"], horizontal=True)
    st.write("---")

    if selector_fase == "Fase de Grupos":
        if datos_s and "standings" in datos_s:
            grupos = datos_s["standings"]
            for i in range(0, len(grupos), 2):
                col_izq, col_der = st.columns(2)
                for j, col in enumerate([col_izq, col_der]):
                    if (i + j) < len(grupos):
                        grupo_data = grupos[i + j]
                        nombre_grupo = grupo_data["group"].replace("_", " ")
                        with col:
                            st.subheader(f"📍 {nombre_grupo}")
                            filas_grupo = []
                            for team in grupo_data["table"]:
                                name_en = team["team"]["name"]
                                name_es = TRADUCTOR_PAISES.get(name_en, name_en)
                                filas_grupo.append({
                                    "Pos": team["position"], "Equipo": f"{name_es}", "PJ": team["playedGames"],
                                    "PG": team["won"], "PE": team["draw"], "PP": team["lost"],
                                    "DG": team["goalDifference"], "Pts": team["points"]
                                })
                            st.table(pd.DataFrame(filas_grupo))
        else:
            st.warning("No hay datos de clasificación disponibles.")
    else:
        st.markdown("### ⚔️ Cuadro de Eliminatorias")
        if datos_p and "matches" in datos_p:
            eliminatorias = [m for m in datos_p["matches"] if m["stage"] != "GROUP_STAGE"]
            if not eliminatorias:
                st.info("Aún no hay cruces definidos.")
            else:
                rondas = {
                    "LAST_32": "Dieciseisavos", "LAST_16": "Octavos", "QUARTER_FINALS": "Cuartos",
                    "SEMI_FINALS": "Semifinales", "SEMIFINALS": "Semifinales", "THIRD_PLACE": "Tercer Puesto",
                    "FINAL": "¡GRAN FINAL!"
                }
                for code, nombre_ronda in rondas.items():
                    partidos_ronda = [m for m in eliminatorias if m["stage"] == code]
                    if partidos_ronda:
                        with st.expander(f"👉 {nombre_ronda}", expanded=True):
                            for m in partidos_ronda:
                                h_en = m["homeTeam"]["name"]
                                a_en = m["awayTeam"]["name"]
                                h_es = TRADUCTOR_PAISES.get(h_en, h_en or "TBD")
                                a_es = TRADUCTOR_PAISES.get(a_en, a_en or "TBD")
                                score_h = m["score"]["fullTime"]["home"] if m["score"]["fullTime"]["home"] is not None else "-"
                                score_a = m["score"]["fullTime"]["away"] if m["score"]["fullTime"]["away"] is not None else "-"
                                st.write(f"**{h_es}** {score_h} - {score_a} **{a_es}**")

# ---------------------------------------------------------
# PESTAÑA 5: ESTADÍSTICAS
# ---------------------------------------------------------
with tab_estadisticas:
    st.markdown("<h2 style='text-align: center;'>📈 Carrera por el Mundial</h2>", unsafe_allow_html=True)
    st.write("---")

    if os.path.exists("historial_posiciones.csv"):
        datos_historicos = pd.read_csv("historial_posiciones.csv")
        if datos_historicos['Fecha'].nunique() > 1:
            eje_y = "PTS" if 'PTS' in datos_historicos.columns else "Pos"
            titulo_y = "Puntos Acumulados" if 'PTS' in datos_historicos.columns else "Posición"

            fig = px.line(
                datos_historicos, x="Fecha", y=eje_y, color="Name", markers=True,
                hover_data={"Fecha": False, "Name": True, "Pos": True, "PTS": True} if 'PTS' in datos_historicos.columns else {}
            )
            fig.update_layout(
                xaxis_title="", yaxis_title=titulo_y, hovermode="x unified",
                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, title=None),
                height=550, margin=dict(l=10, r=10, t=30, b=10)
            )
            if eje_y == "Pos": fig.update_yaxes(autorange="reversed", dtick=1)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Recopilando datos... Vuelve mañana para ver la evolución.")
    else:
        st.warning("Aún no hay archivo histórico creado.")
