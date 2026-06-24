import streamlit as st
import pandas as pd
import requests
import json
import os
import unicodedata
import datetime
import plotly.express as px
import time

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
    "Bosnia and Herzegovina": "Bosnia",
    "Bosnia-Herzegovina": "Bosnia",
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
    "Canadá": "ca", "Bosnia": "ba", "Qatar": "qa", "Suiza": "ch",
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

# ==========================================
# 1. PANTALLA DE BIENVENIDA (SPLASH SCREEN)
# ==========================================
# Inicializamos el estado si no existe
if "bienvenida_mostrada" not in st.session_state:
    st.session_state["bienvenida_mostrada"] = False

# Si aún no se ha mostrado la animación, entramos aquí
if not st.session_state["bienvenida_mostrada"]:
    st.markdown("<h1 style='text-align: center;'> Porra patrocinada por </h1>", unsafe_allow_html=True)

    # Opción A: Si tienes la imagen en internet (URL)
    url_imagen = "data:image/png;base64,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"
    st.image(url_imagen, use_container_width=True)

    # Opción B: Si tienes la imagen guardada en la misma carpeta que el script
    # st.image("logo_mundial.png", use_container_width=True)

    # Pausamos el servidor durante 3 segundos
    time.sleep(2)

    # Cambiamos el estado para que la próxima vez no vuelva a entrar aquí
    st.session_state["bienvenida_mostrada"] = True

    # Forzamos a Streamlit a recargar la página y saltarse este bloque
    st.rerun()


# El resto de tu código (Motor de datos, ETL, pestañas, etc.) continuará aquí abajo...


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
datos_g = llamar_api("competitions/WC/scorers?limit=150", "cache_goleadores.json", forzar)
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
# ---------------------------------------------------------
# PESTAÑA 4: CLASIFICACIÓN OFICIAL
# ---------------------------------------------------------
with tab_oficial:
    st.markdown("<h2 style='text-align: center;'>🏅 Situación del Mundial</h2>", unsafe_allow_html=True)
    selector_fase = st.radio("Ver fase:", ["Fase de Grupos", "Cruces Directos (Eliminatorias)"], horizontal=True)
    st.write("---")

    if selector_fase == "Fase de Grupos":
        if datos_s and "standings" in datos_s:
            
            # ==========================================
            # 1. MOTOR LÓGICO DE LOS 3º CLASIFICADOS
            # ==========================================
            # Extraemos en tiempo real a todos los equipos que van 3º 
            # para saber quién está dentro y quién fuera.
            terceros_live = []
            for grupo in datos_s["standings"]:
                if grupo.get("type") == "TOTAL":
                    tabla = grupo.get("table", [])
                    if len(tabla) >= 3:
                        team = tabla[2] # El índice 2 corresponde a la 3ª posición
                        name_en = team["team"]["name"]
                        name_es = TRADUCTOR_PAISES.get(name_en, name_en)
                        terceros_live.append({
                            "Grupo": grupo["group"].replace("_", " "),
                            "Equipo": name_es,
                            "Pts": team["points"],
                            "DG": team["goalDifference"],
                            "GF": team["goalsFor"],
                            "PJ": team["playedGames"]
                        })

            # Creamos el DataFrame y ordenamos con reglas FIFA
            df_terceros = pd.DataFrame(terceros_live)
            if not df_terceros.empty:
                df_terceros = df_terceros.sort_values(
                    by=['Pts', 'DG', 'GF'], 
                    ascending=[False, False, False]
                ).reset_index(drop=True)
                df_terceros.insert(0, 'Pos', df_terceros.index + 1)
                
                # Guardamos en una lista los nombres de los 8 mejores para usarlos de referencia
                clasificados_terceros = df_terceros.loc[df_terceros['Pos'] <= 8, 'Equipo'].tolist()
            else:
                clasificados_terceros = []

            # ==========================================
            # 2. RENDERIZADO DE LOS 12 GRUPOS (Con colores)
            # ==========================================
            def aplicar_color_grupo(row):
                # VERDE: 1º, 2º o si eres un 3º que está dentro del Top 8
                if row['Pos'] in [1, 2] or (row['Pos'] == 3 and row['Equipo'] in clasificados_terceros):
                    color = 'rgba(46, 204, 113, 0.2)'
                # ROJO: 4º o si eres un 3º que no llega al corte
                else:
                    color = 'rgba(231, 76, 60, 0.2)'
                return [f'background-color: {color}'] * len(row)

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
                                    "Pos": team["position"], "Equipo": name_es, "PJ": team["playedGames"],
                                    "PG": team["won"], "PE": team["draw"], "PP": team["lost"],
                                    "DG": team["goalDifference"], "Pts": team["points"]
                                })
                            df_grupo = pd.DataFrame(filas_grupo)
                            # Usamos st.dataframe con style para aplicar el CSS sin mostrar el índice feo
                            st.dataframe(df_grupo.style.apply(aplicar_color_grupo, axis=1), use_container_width=True, hide_index=True)

            # ==========================================
            # 3. TABLA RANKING DE TERCEROS
            # ==========================================
            st.write("---")
            st.markdown("<h3 style='text-align: center;'>⚖️ Clasificación de Terceros (Pasan los 8 mejores)</h3>", unsafe_allow_html=True)

            if not df_terceros.empty:
                def aplicar_color_terceros(row):
                    # VERDE para el Top 8, ROJO para el resto
                    color = 'rgba(46, 204, 113, 0.2)' if row['Pos'] <= 8 else 'rgba(231, 76, 60, 0.2)'
                    return [f'background-color: {color}'] * len(row)

                st.dataframe(df_terceros.style.apply(aplicar_color_terceros, axis=1), use_container_width=True, hide_index=True)
            else:
                st.info("Aún no hay datos suficientes para calcular los terceros.")

        else:
            st.warning("No hay datos de clasificación disponibles.")
            
    else:
        # ==========================================
        # 4. CUADRO DE ELIMINATORIAS (Se mantiene intacto)
        # ==========================================
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
