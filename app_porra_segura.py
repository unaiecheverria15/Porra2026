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
# ==========================================
# CÓDIGOS DE BANDERAS (Para imágenes FlagCDN)
# ==========================================
CODIGOS_BANDERAS = {
    # Grupo A
    "México": "mx", "Corea del Sur": "kr", "Sudáfrica": "za", "República Checa": "cz",
    # Grupo B
    "Canadá": "ca", "Bosnia-Herzegovina": "ba", "Qatar": "qa", "Suiza": "ch",
    # Grupo C
    "Brasil": "br", "Marruecos": "ma", "Haití": "ht", "Escocia": "gb-sct",
    # Grupo D
    "Estados Unidos": "us", "Paraguay": "py", "Australia": "au", "Turquía": "tr",
    # Grupo E
    "Alemania": "de", "Curazao": "cw", "Costa de Marfil": "ci", "Ecuador": "ec",
    # Grupo F
    "Países Bajos": "nl", "Japón": "jp", "Suecia": "se", "Túnez": "tn",
    # Grupo G
    "Bélgica": "be", "Egipto": "eg", "Irán": "ir", "Nueva Zelanda": "nz",
    # Grupo H
    "España": "es", "Cabo Verde": "cv", "Arabia Saudí": "sa", "Uruguay": "uy",
    # Grupo I
    "Francia": "fr", "Senegal": "sn", "Iraq": "iq", "Noruega": "no",
    # Grupo J
    "Argentina": "ar", "Argelia": "dz", "Austria": "at", "Jordania": "jo",
    # Grupo K
    "Portugal": "pt", "RD Congo": "cd", "Uzbekistán": "uz", "Colombia": "co",
    # Grupo L
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
        st.title("🔒 Acceso Privado - Porra Mundial STL 2026")
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
    """Llama a la API de football-data.org y guarda en caché en silencio"""
    if not forzar_actualizacion and os.path.exists(archivo_cache):
        with open(archivo_cache, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://api.football-data.org/v4/{endpoint}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        datos = response.json()

        # Comprobamos si la API nos devuelve algo válido de forma general
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
    """Extrae quién ha ganado, empatado y cuántos goles llevan"""
    victorias = []
    empates = []
    goleadores_dict = {}

    # 1. Procesar Partidos
    if datos_partidos and "matches" in datos_partidos:
        for partido in datos_partidos["matches"]:
            # Solo puntuamos si el partido ha terminado ('FINISHED')
            if partido.get("status") == "FINISHED":
                score = partido.get("score", {}).get("fullTime", {})
                home_score = score.get("home")
                away_score = score.get("away")

                # Nombres de los equipos (Traducidos)
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

    # 2. Procesar Goleadores
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
    # Preparar reglas
    team_rules = rules[rules['Type'] == 'Team'].set_index('Group')[['Win', 'Draw']].astype(float)
    player_rules_raw = rules[rules['Type'].isin(['G1', 'G2', 'G3', 'G4', 'G5'])]
    player_rules = pd.Series(player_rules_raw['Group'].values, index=player_rules_raw['Type']).astype(float)
except FileNotFoundError:
    st.error("Faltan los archivos CSV. Súbelos a la misma carpeta.")
    st.stop()

# ==========================================
# 5. INTERFAZ, CÁLCULO Y PESTAÑAS
# ==========================================
st.title("🏆 Porra Mundial 2026")

# Panel Administrador (Barra lateral)
st.sidebar.header("⚙️ Sincronización")
forzar = False
if st.sidebar.button("🔄 Sincronizar con API-Football"):
    forzar = True
    st.sidebar.success("Sincronizando... (Consumiendo peticiones)")

# Obtener datos de la API
datos_p = llamar_api("competitions/WC/matches", "cache_partidos.json", forzar)
datos_g = llamar_api("competitions/WC/scorers?limit=100", "cache_goleadores.json", forzar)
datos_e = llamar_api("competitions/WC/teams", "cache_equipos.json", forzar)
datos_s = llamar_api("competitions/WC/standings", "cache_standings.json", forzar) # <-- NUEVA LÍNEA

api_victorias, api_empates, api_goleadores = procesar_datos_api(datos_p, datos_g)

st.sidebar.write("---")
st.sidebar.subheader("📊 Resumen del Torneo")
st.sidebar.write(f"**Partidos procesados:** {len(api_victorias) + len(api_empates) // 2}")

# --- CREACIÓN DE PESTAÑAS ---
tab_clasificacion, tab_elecciones, tab_marcador, tab_oficial, tab_estadisticas, tab_diccionario = st.tabs([
    "📊 Clasificación", "👀 Ver Elecciones", "🏟️ Marcador", "🏅 Grupos y Cruces", "📈 Estadísticas", "📖 Nombres Oficiales"
])

# ---------------------------------------------------------
# PESTAÑA 1: LA CLASIFICACIÓN (ESTILO LIGA EUROPEA)
# ---------------------------------------------------------
with tab_clasificacion:
    st.markdown("<h2 style='text-align: center;'>🏆 Clasificación General</h2>", unsafe_allow_html=True)
    st.write("---")


    def calcular_puntos(row):
        p_id = row['ParticipantID']
        p_equipos, p_jugadores = 0, 0

        # 1. Calcular Equipos
        mis_equipos = teams[teams['ParticipantID'] == p_id].iloc[0]
        for grupo in team_rules.index:
            eq = mis_equipos.get(grupo, "")
            if pd.notna(eq) and isinstance(eq, str):
                eq = eq.strip()

                # Novedad: Contamos y sumamos matemáticamente
                num_v = api_victorias.count(eq)
                num_e = api_empates.count(eq)

                p_equipos += (num_v * team_rules.loc[grupo, 'Win'])
                p_equipos += (num_e * team_rules.loc[grupo, 'Draw'])

        # 2. Calcular Jugadores
        mis_jugadores = players[players['ParticipantID'] == p_id].iloc[0]
        for grupo in player_rules.index:
            jugadores_str = mis_jugadores.get(grupo, "")
            if pd.notna(jugadores_str) and isinstance(jugadores_str, str):
                for jug in jugadores_str.split(";"):
                    jug_limpio = normalizar_texto(jug)

                    if not jug_limpio or len(jug_limpio) < 2:
                        continue

                    for api_jug, goles in api_goleadores.items():
                        api_limpio = normalizar_texto(api_jug)

                        if not api_limpio or len(api_limpio) < 2:
                            continue

                        if jug_limpio in api_limpio or api_limpio in jug_limpio:
                            p_jugadores += (player_rules[grupo] * goles)

        return pd.Series([p_equipos, p_jugadores, p_equipos + p_jugadores],
                         index=['PE', 'PJ', 'PTS'])


    # Generar tabla base
    resultados = participants.join(participants.apply(calcular_puntos, axis=1))

    # Ordenar por Puntos Totales
    resultados = resultados.sort_values(by=['PTS', 'PE'], ascending=[False, False]).reset_index(drop=True)

    # Formatear al estilo Liga
    resultados.insert(0, 'Pos', resultados.index + 1)

    # ---------------------------------------------------------
    # 💾 NUEVO: GUARDAR MEMORIA HISTÓRICA PARA LA GRÁFICA
    # ---------------------------------------------------------
    fecha_hoy = str(datetime.date.today())
    archivo_historial = "historial_posiciones.csv"

    # Cogemos solo el Nombre, la Posición y la Fecha
    df_hoy = resultados[['Name', 'Pos']].copy()
    df_hoy['Fecha'] = fecha_hoy

    if os.path.exists(archivo_historial):
        historial_csv = pd.read_csv(archivo_historial)
        # Borramos la foto de hoy si ya existía (por si sincronizas varias veces el mismo día)
        historial_csv = historial_csv[historial_csv['Fecha'] != fecha_hoy]
        # Juntamos el pasado con el día de hoy
        historial_csv = pd.concat([historial_csv, df_hoy])
    else:
        historial_csv = df_hoy

    historial_csv.to_csv(archivo_historial, index=False)


    # ---------------------------------------------------------

    def poner_medallas(row):
        if row['Pos'] == 1:
            return f"🥇 {row['Name']}"
        elif row['Pos'] == 2:
            return f"🥈 {row['Name']}"
        elif row['Pos'] == 3:
            return f"🥉 {row['Name']}"
        elif row['Pos'] == len(resultados):
            return f"🔻 {row['Name']}"
        else:
            return f"  {row['Name']}"


    resultados['Participante'] = resultados.apply(poner_medallas, axis=1)

    # Seleccionar las columnas que se van a mostrar
    df_mostrar = resultados[['Pos', 'Participante', 'PE', 'PJ', 'PTS']]


    # Aplicar diseño de colores
    def estilo_liga(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        # Líder (Campeón) - Verde destacado
        styles.loc[0, :] = 'background-color: rgba(46, 204, 113, 0.3);'
        # 2º y 3º puesto (Europa) - Verde suave
        styles.loc[1:2, :] = 'background-color: rgba(46, 204, 113, 0.1);'
        # Último puesto (Descenso) - Rojo suave
        if len(df) > 3:
            styles.loc[df.index[-1], :] = 'background-color: rgba(231, 76, 60, 0.1);'

        # La columna de puntos totales siempre en negrita
        styles['PTS'] = styles['PTS'] + ' font-weight: bold; font-size: 1.05em;'
        return styles


    # Aplicamos el estilo y ocultamos el índice lateral feo
    df_estilizado = df_mostrar.style.apply(estilo_liga, axis=None).hide(axis="index")

    # Calculamos la altura dinámica para que se vea la tabla entera
    altura_tabla = (len(resultados) + 1) * 35 + 10

    # Renderizamos la tabla en Streamlit forzando la altura
    st.dataframe(
        df_estilizado,
        use_container_width=True,
        height=altura_tabla
    )

    # Añadimos la leyenda de las reglas estilo TV
    st.caption(
        "🟩 **Zona de Podio** | 🟥 **Farolillo Rojo** | **PE**: Pts Equipos | **PJ**: Pts Jugadores | **PTS**: Puntos Totales")

# ---------------------------------------------------------
# PESTAÑA 2: VER LAS ELECCIONES DE TUS AMIGOS (DESGLOSE DETALLADO)
# ---------------------------------------------------------
with tab_elecciones:
    st.markdown("### Selecciona un amigo para ver su porra")

    # Creamos un desplegable con los nombres de todos tus amigos
    amigo_elegido = st.selectbox("👤 Participante:", participants['Name'])

    # Buscamos el ID de ese amigo
    id_amigo = participants[participants['Name'] == amigo_elegido]['ParticipantID'].iloc[0]

    # Obtenemos sus filas correspondientes
    mis_equipos = teams[teams['ParticipantID'] == id_amigo].iloc[0]
    mis_jugadores = players[players['ParticipantID'] == id_amigo].iloc[0]

    # --- 1. DESGLOSE INDIVIDUAL DE EQUIPOS ---
    desglose_equipos = []
    total_equipos = 0

    for grupo in team_rules.index:
        eq = mis_equipos.get(grupo, "")
        if pd.notna(eq) and isinstance(eq, str):
            eq = eq.strip()
            if not eq:
                continue

            # Capturamos el valor de la regla para este bombo específico
            pts_win = team_rules.loc[grupo, 'Win']
            pts_draw = team_rules.loc[grupo, 'Draw']

            # CONTAMOS cuántas victorias y empates tiene el equipo en toda la lista
            num_victorias = api_victorias.count(eq)
            num_empates = api_empates.count(eq)

            # Multiplicamos la cantidad de resultados por sus puntos correspondientes
            puntos_totales_equipo = (num_victorias * pts_win) + (num_empates * pts_draw)

            if puntos_totales_equipo > 0:
                estado = f"✅ {num_victorias}V / {num_empates}E"
            else:
                estado = "⏳ Pendiente / Derrotas"

            desglose_equipos.append({
                "Equipo": eq,
                "Bombo": grupo,
                "Resultado": estado,
                "Puntos Obtenidos": puntos_totales_equipo
            })
            total_equipos += puntos_totales_equipo

    df_equipos_amigo = pd.DataFrame(desglose_equipos)

    # --- 2. DESGLOSE INDIVIDUAL DE JUGADORES ---
    desglose_jugadores = []
    total_jugadores = 0

    for grupo in player_rules.index:
        jugadores_str = mis_jugadores.get(grupo, "")
        if pd.notna(jugadores_str) and isinstance(jugadores_str, str):
            # Separamos los jugadores si hay varios en el mismo bombo
            for jug in jugadores_str.split(";"):
                jug = jug.strip()
                if not jug or len(jug) < 2:
                    continue

                jug_limpio = normalizar_texto(jug)
                goles_marcados = 0
                puntos = 0

                # Capturamos el valor del gol según el bombo de este jugador
                valor_gol = player_rules[grupo]

                # Buscamos al jugador específico en la API
                for api_jug, goles in api_goleadores.items():
                    api_limpio = normalizar_texto(api_jug)
                    if not api_limpio or len(api_limpio) < 2:
                        continue

                    if jug_limpio in api_limpio or api_limpio in jug_limpio:
                        goles_marcados = goles
                        puntos = valor_gol * goles_marcados
                        break  # Si lo encontramos, dejamos de buscar

                desglose_jugadores.append({
                    "Jugador": jug,
                    "Bombo": grupo,
                    "Goles": goles_marcados,
                    "Valor/Gol": f"{valor_gol} pts",
                    "Cálculo": f"{goles_marcados} x {valor_gol}",
                    "Total Puntos": puntos
                })
                total_jugadores += puntos

    df_jugadores_amigo = pd.DataFrame(desglose_jugadores)

    # --- 3. RENDERIZADO VISUAL CON ESTILOS ---
    col1, col2 = st.columns(2)


    # Función para resaltar de verde las filas que sumen puntos
    def resaltar_puntos(row, col_name):
        if row[col_name] > 0:
            return ['background-color: rgba(46, 204, 113, 0.2)'] * len(row)
        return [''] * len(row)


    with col1:
        st.success("🛡️ Puntos por Equipos")
        if not df_equipos_amigo.empty:
            # Calculamos la altura: ~35px por fila + 35px de cabecera + un pequeño margen
            altura_equipos = (len(df_equipos_amigo) + 1) * 35 + 15

            st.dataframe(
                df_equipos_amigo.style.apply(resaltar_puntos, col_name="Puntos Obtenidos", axis=1),
                use_container_width=True,
                hide_index=True,
                height=altura_equipos
            )
        else:
            st.info("Aún no hay equipos seleccionados.")

    with col2:
        st.info("⚽ Puntos por Jugadores")
        if not df_jugadores_amigo.empty:
            # Calculamos la altura para los jugadores
            altura_jugadores = (len(df_jugadores_amigo) + 1) * 35 + 15

            st.dataframe(
                df_jugadores_amigo.style.apply(resaltar_puntos, col_name="Total Puntos", axis=1),
                use_container_width=True,
                hide_index=True,
                height=altura_jugadores
            )
        else:
            st.info("Aún no hay jugadores seleccionados.")

    st.write("---")

    # --- 4. MÉTRICAS TOTALES ---
    st.markdown(f"### 🏆 Resumen de {amigo_elegido}")
    total_absoluto = total_equipos + total_jugadores

    met_col1, met_col2, met_col3 = st.columns(3)
    met_col1.metric("Total Equipos", f"{total_equipos} pts")
    met_col2.metric("Total Jugadores", f"{total_jugadores} pts")
    met_col3.metric("PUNTOS TOTALES", f"{total_absoluto} pts")

# ---------------------------------------------------------
# PESTAÑA 3: MARCADOR VISUAL DE PARTIDOS
# ---------------------------------------------------------
with tab_marcador:
    st.markdown("<h2 style='text-align: center;'>🏟️ Resultados del Mundial</h2>", unsafe_allow_html=True)
    st.write("---")

    # 1. SECCIÓN DE PARTIDOS
    if datos_p and "matches" in datos_p:
        # Ampliamos el filtro: Terminados, En Juego y Pausados (Descanso)
        estados_validos = ["FINISHED", "IN_PLAY", "PAUSED"]
        partidos_mostrar = [p for p in datos_p["matches"] if p.get("status") in estados_validos]

        if not partidos_mostrar:
            st.info("Aún no hay partidos terminados ni en juego para mostrar.")
        else:
            for p in partidos_mostrar:
                # Extraemos nombres originales en inglés
                home = p.get("homeTeam", {}).get("name", "Local")
                away = p.get("awayTeam", {}).get("name", "Visitante")

                # Los pasamos por tu traductor
                home_es = TRADUCTOR_PAISES.get(home, home)
                away_es = TRADUCTOR_PAISES.get(away, away)

                # Buscamos el código ISO de la bandera
                iso_h = CODIGOS_BANDERAS.get(home_es, "")
                iso_a = CODIGOS_BANDERAS.get(away_es, "")

                # Creamos la imagen HTML (si no hay código, ponemos bandera blanca)
                img_h = f"<img src='https://flagcdn.com/32x24/{iso_h}.png' width='32' style='vertical-align: text-bottom; border-radius: 3px;'>" if iso_h else "🏳️"
                img_a = f"<img src='https://flagcdn.com/32x24/{iso_a}.png' width='32' style='vertical-align: text-bottom; border-radius: 3px;'>" if iso_a else "🏳️"

                # Extraemos los goles (si la API devuelve None en vivo, ponemos 0)
                score_info = p.get("score", {})
                score_h = score_info.get("fullTime", {}).get("home")
                score_a = score_info.get("fullTime", {}).get("away")

                # En algunos casos en vivo, fullTime es None pero regularTime tiene el marcador
                if score_h is None:
                    score_h = score_info.get("regularTime", {}).get("home", 0)
                if score_a is None:
                    score_a = score_info.get("regularTime", {}).get("away", 0)

                # Identificamos si el partido está en directo
                estado_actual = p.get("status")
                en_vivo = estado_actual in ["IN_PLAY", "PAUSED"]

                # Diseño visual de la tarjeta
                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    st.markdown(f"<h3 style='text-align: right; margin-top: 15px;'>{home_es} {img_h}</h3>",
                                unsafe_allow_html=True)
                with col2:
                    if en_vivo:
                        # Diseño rojo y texto EN VIVO para los partidos en directo
                        st.markdown(
                            f"<div style='text-align: center; border: 2px solid #e74c3c; border-radius: 10px; padding: 5px; margin-top: 5px; color: #e74c3c;'><h2 style='margin:0;'>{score_h} - {score_a}</h2><span style='font-size: 14px; font-weight: bold;'>🔴 EN VIVO</span></div>",
                            unsafe_allow_html=True)
                    else:
                        # Diseño verde habitual para los terminados
                        st.markdown(
                            f"<h2 style='text-align: center; border: 2px solid #4CAF50; border-radius: 10px; padding: 5px; margin-top: 5px;'>{score_h} - {score_a}</h2>",
                            unsafe_allow_html=True)
                with col3:
                    st.markdown(f"<h3 style='text-align: left; margin-top: 15px;'>{img_a} {away_es}</h3>",
                                unsafe_allow_html=True)

                st.write("")
    else:
        st.warning("No se han podido cargar los partidos. Comprueba la sincronización.")

    # 2. SECCIÓN DE GOLEADORES
    st.markdown("<br><h2 style='text-align: center;'>⚽ Top Goleadores</h2>", unsafe_allow_html=True)
    st.write("---")

    if api_goleadores:
        # Ordenamos los goleadores de mayor a menor número de goles
        goleadores_ordenados = sorted(api_goleadores.items(), key=lambda x: x[1], reverse=True)

        # Creamos dos columnas para que la lista no quede demasiado estirada
        col_g1, col_g2 = st.columns(2)

        for i, (nombre, goles) in enumerate(goleadores_ordenados):
            # Alternamos entre la columna izquierda y derecha
            columna_actual = col_g1 if i % 2 == 0 else col_g2

            # Ponemos el nombre bonito (primera letra mayúscula)
            nombre_bonito = nombre.title()

            with columna_actual:
                st.markdown(f"🏃‍♂️ **{nombre_bonito}**: {goles} goles")
    else:
        st.info("Aún no hay goleadores registrados en el torneo.")
# ---------------------------------------------------------
# PESTAÑA 4: CLASIFICACIÓN OFICIAL MUNDIAL (GRUPOS Y CRUCES)
# ---------------------------------------------------------
with tab_oficial:
    st.markdown("<h2 style='text-align: center;'>🏅 Situación del Mundial</h2>", unsafe_allow_html=True)

    selector_fase = st.radio("Ver fase:", ["Fase de Grupos", "Cruces Directos (Eliminatorias)"], horizontal=True)
    st.write("---")

    if selector_fase == "Fase de Grupos":
        if datos_s and "standings" in datos_s:
            # En 2026 hay 12 grupos (A-L). Vamos a mostrarlos de 2 en 2.
            grupos = datos_s["standings"]

            for i in range(0, len(grupos), 2):
                col_izq, col_der = st.columns(2)

                # Renderizar dos grupos por fila
                for j, col in enumerate([col_izq, col_der]):
                    if (i + j) < len(grupos):
                        grupo_data = grupos[i + j]
                        nombre_grupo = grupo_data["group"].replace("_", " ")

                        with col:
                            st.subheader(f"📍 {nombre_grupo}")

                            # Construir tabla del grupo con Ganados, Empatados y Perdidos
                            filas_grupo = []
                            for team in grupo_data["table"]:
                                name_en = team["team"]["name"]
                                name_es = TRADUCTOR_PAISES.get(name_en, name_en)

                                filas_grupo.append({
                                    "Pos": team["position"],
                                    "Equipo": f"{name_es}",
                                    "PJ": team["playedGames"],
                                    "PG": team["won"],
                                    "PE": team["draw"],
                                    "PP": team["lost"],
                                    "DG": team["goalDifference"],
                                    "Pts": team["points"]
                                })

                            df_grupo = pd.DataFrame(filas_grupo)
                            st.table(df_grupo)
        else:
            st.warning("No hay datos de clasificación disponibles aún.")

    else:
        # SECCIÓN DE ELIMINATORIAS (CRUCES)
        st.markdown("### ⚔️ Cuadro de Eliminatorias")

        # Filtramos partidos que NO sean de fase de grupos
        if datos_p and "matches" in datos_p:
            eliminatorias = [m for m in datos_p["matches"] if m["stage"] != "GROUP_STAGE"]

            if not eliminatorias:
                st.info("Las eliminatorias comenzarán tras la Fase de Grupos. ¡Aún no hay cruces definidos!")
            else:
                # Diccionario corregido para agrupar por ronda (Incluye Semifinales y 3º Puesto)
                rondas = {
                    "LAST_32": "Dieciseisavos de Final",
                    "LAST_16": "Octavos de Final",
                    "QUARTER_FINALS": "Cuartos de Final",
                    "SEMI_FINALS": "Semifinales",
                    "SEMIFINALS": "Semifinales",  # Por si la API cambia la nomenclatura
                    "THIRD_PLACE": "Tercer y Cuarto Puesto",
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

                                score_h = m["score"]["fullTime"]["home"] if m["score"]["fullTime"][
                                                                                "home"] is not None else "-"
                                score_a = m["score"]["fullTime"]["away"] if m["score"]["fullTime"][
                                                                                "away"] is not None else "-"

                                st.write(f"**{h_es}** {score_h} - {score_a} **{a_es}**")
# ---------------------------------------------------------
# PESTAÑA 5: ESTADÍSTICAS Y EVOLUCIÓN
# ---------------------------------------------------------
with tab_estadisticas:
    st.markdown("<h2 style='text-align: center;'>📈 Evolución del Mundial</h2>", unsafe_allow_html=True)
    st.write("---")

    if os.path.exists("historial_posiciones.csv"):
        datos_historicos = pd.read_csv("historial_posiciones.csv")

        # Comprobamos si hay al menos 2 días distintos para poder trazar una línea
        dias_registrados = datos_historicos['Fecha'].nunique()

        if dias_registrados > 1:
            st.markdown("### 🏎️ Carrera por el Título (Posiciones)")

            # Crear la gráfica interactiva con Plotly
            fig = px.line(
                datos_historicos,
                x="Fecha",
                y="Pos",
                color="Name",
                markers=True,
                hover_name="Name"
            )

            # La magia gráfica: Invertimos el eje Y para que el puesto #1 esté arriba de la gráfica
            fig.update_yaxes(autorange="reversed", title_text="Posición en la Tabla", dtick=1)
            fig.update_xaxes(title_text="Día del Torneo")

            # Ajustes visuales para que se vea como un cuadro de mandos deportivo
            fig.update_layout(
                legend_title_text="Participantes",
                hovermode="x unified",
                height=600  # Hacemos la gráfica alta para que las líneas no se aplasten
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "📊 **Recopilando datos...** El sistema acaba de hacer su primera 'foto' a la clasificación. Vuelve mañana o en la próxima actualización para ver cómo se dibujan las líneas de evolución.")
    else:
        st.warning(
            "Aún no hay archivo histórico creado. Ve a la pestaña de clasificación para generar el primer registro.")
