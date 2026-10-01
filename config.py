# -*- coding: utf-8 -*-
"""
config.py — TODO lo que se edita a mano vive aquí.
=====================================================

1) RUTAS de tu computadora (Excel, fotos, mapas de calor).
2) CATÁLOGO de atributos por posición (qué barras salen en cada sección).
3) Cómo se calculan las barras (total / por 90, grupo de comparación).

Después de editar, corre  actualizar.bat  (Windows) o  ./actualizar.sh  (Mac/Linux).
"""

# =============================================================================
# 1) RUTAS
# =============================================================================
# Puedes usar rutas absolutas de tu compu, p. ej.:
#   CARPETA_EXCEL = r"C:\Users\claudio\Drive\Scouting FB 26-27\Matrices"
# Cada .xlsx dentro de CARPETA_EXCEL se vuelve una "Competencia" en la página.
CARPETA_EXCEL = r"C:\Users\Servicio Social\fichas_fb\datos\excel"
CARPETA_FOTOS = r"C:\Users\Servicio Social\fichas_fb\datos\fotos"
CARPETA_MAPAS = r"C:\Users\Servicio Social\fichas_fb\datos\mapas"
CARPETA_NUI = r"C:\Users\Servicio Social\fichas_fb\datos\nui"
CARPETA_PORTEROS = r"C:\Users\Servicio Social\fichas_fb\datos\porteros"

# =============================================================================
# 1b) SOLO PUMAS
# =============================================================================
# Solo se generan fichas de los jugadores cuyo EQUIPO contenga este texto
# (sin importar mayúsculas/acentos). Los máximos de las barras SIEMPRE se
# calculan con TODA la liga.
FILTRO_EQUIPO_FICHAS = "Universidad Nacional"
# Cómo se muestra el equipo en la ficha: "Club Universidad Nacional Under 19" -> "Pumas UNAM U19"
NOMBRE_EQUIPO_FICHA = "Pumas UNAM"

# =============================================================================
# 1c) REGISTRO (Excel en CARPETA_NUI)  ->  QUIÉN tiene ficha
# =============================================================================
# Formato:  NOMBRE | NUI | EQUIPO           (una fila por jugador registrado)
#   José Humberto Mancilla López | 000000 | Pumas UNAM U21
# Opcionales (si existen se usan):  POSICIÓN | FECHA DE NACIMIENTO
#   -> POSICIÓN sirve para los que no tienen minutos: salen sus barras en 0.
# El nombre se escribe normal (con acentos); la búsqueda ignora mayúsculas y acentos.
# La categoría (U19, U21, Sub 21, Sub-19...) se lee del EQUIPO.
# None = el programa detecta la columna solo por su encabezado.
REGISTRO_COL_NOMBRE = None
REGISTRO_COL_NUI = None
REGISTRO_COL_EQUIPO = None
REGISTRO_COL_POSICION = None
REGISTRO_COL_NACIMIENTO = None

# Jugadores registrados en una categoría que tienen minutos en otra (U19 que sube
# a U21 o U21 que baja a U19): también salen en la lista de esa otra liga, en un
# grupo aparte, con sus stats de esa Matrix.
INCLUIR_OTRAS_CATEGORIAS = True

# Si el programa no logra empatar a alguien con la Matrix (o empata mal),
# se fuerza aquí:  NUI -> nombre tal cual viene en la columna JUGADOR de la Matrix.
# Aplica en todas las Matrix donde aparezca ese nombre con Pumas.
EMPATES_MANUALES = {
    # "000000": "Humberto Mancilla",
}

# Nombre de la hoja y fila del encabezado real (GolStats: fila 3 => header=2)
HOJA_EXCEL = 0                          # 0 = primera hoja, o "Matriz Jugadores"
FILA_ENCABEZADO = 2

# Texto que se muestra por competencia. Llave = nombre del archivo SIN .xlsx.
# Si un archivo no está aquí, el texto se arma solo a partir del nombre.
ETIQUETAS_COMPETENCIA = {
    # "Matrix_Jugadores_J1-J9_Liga_MX_U19_AP26": "Liga MX U19 · Apertura 2026",
}

# =============================================================================
# 2) COLUMNAS DEL EXCEL (GolStats)
# =============================================================================
COL_JUGADOR = "JUGADOR"
COL_EQUIPO = "EQUIPO"
COL_POSICION = "Posición"
COL_MINUTOS = "Minutos jugados"
COL_PARTIDOS = "Partidos jugados"
COL_EDAD = "Edad"
COL_NACIMIENTO = "Fecha de nacimiento"

# Etiqueta GolStats -> posición del catálogo
MAPEO_POSICIONES = {
    "Defensa central": "Defensa central",
    "Lateral por derecha": "Lateral por derecha",
    "Lateral por izquierda": "Lateral por izquierda",
    "Volante defensivo": "Volante defensivo",
    "Volante ofensivo": "Volante ofensivo",
    "Volante por derecha": "Volante por derecha",
    "Volante por izquierda": "Volante por izquierda",
    "Delantero": "Delantero",
    "Portero": "Portero",
    "Defensa": "Defensa central",      # alias
    "Medio": "Volante defensivo",      # alias (ambiguo)
}

# =============================================================================
# 3) CATÁLOGO ACTIVO   <<< EL SWITCH >>>
# =============================================================================
# "estandarizado" -> 15 stats por posición (5 Ofensiva, 5 Defensiva, 5 Posesión),
#                    cada una comparada contra la liga o contra su grupo de posición.
# "inicial"       -> el catálogo temporal del cuaderno de radares (todo contra la liga).
# Para regresar: cambia la palabra y corre actualizar.bat.
CATALOGO_ACTIVO = "estandarizado"

# =============================================================================
# 3b) MÉTRICAS DISPONIBLES (jugadores de campo)
# =============================================================================
# nombre en la ficha : (columna exacta del Excel, tipo)
#   tipo "conteo"     -> número tal cual
#   tipo "porcentaje" -> ya viene en % en el Excel
METRICAS = {
    # --- Ofensiva ---
    "Goles":                        ("Goles", "conteo"),
    "Asistencias":                  ("Asistencias", "conteo"),
    "Tiros a gol":                  ("Tiros a gol", "conteo"),
    "Tiros a destino":              ("Tiros a destino", "conteo"),
    "Tiros de cabeza":              ("Tiros a gol de cabeza", "conteo"),
    "Duelos ofensivos":             ("Regates", "conteo"),
    "Duelos ofensivos ganados":     ("Regates acertados", "conteo"),
    "Duelos ofensivos (%)":         ("% de duelos ofensivos ganados", "porcentaje"),
    "Faltas recibidas":             ("Faltas recibidas", "conteo"),
    # --- Posesión ---
    "Pases":                        ("Pases", "conteo"),
    "Pases acertados":              ("Pases acertados", "conteo"),
    "Pases acertados (%)":          ("% total de pases acertados", "porcentaje"),
    "Pases acertados 2/4":          ("Pases acertados 2/4", "conteo"),
    "Pases acertados 3/4":          ("Pases acertados 3/4", "conteo"),
    "Pases acertados 4/4":          ("Pases acertados 4/4", "conteo"),
    "Pases no acertados 2/4":       ("Pases no acertados 2/4", "conteo"),
    "Pases no acertados 3/4":       ("Pases no acertados 3/4", "conteo"),
    "Pases no acertados 4/4":       ("Pases no acertados 4/4", "conteo"),
    "Centros":                      ("Centros", "conteo"),
    "Centros a destino":            ("Centros a destino", "conteo"),
    "Pérdidas por despojo":         ("Pérdidas por despojo", "conteo"),
    "Pérdidas por despojo 2/4":     ("Pérdidas por despojo 2/4", "conteo"),
    "Pérdidas por despojo 3/4":     ("Pérdidas por despojo 3/4", "conteo"),
    "Pérdidas por despojo 4/4":     ("Pérdidas por despojo 4/4", "conteo"),
    # --- Defensiva ---
    "Duelos defensivos":            ("Duelos defensivos", "conteo"),
    "Duelos defensivos ganados":    ("Duelos defensivos ganados", "conteo"),
    "Duelos defensivos (%)":        ("% de duelos defensivos ganados", "porcentaje"),
    "Duelos aéreos":                ("Duelos aéreos", "conteo"),
    "Duelos aéreos ganados":        ("Duelos aéreos ganados", "conteo"),
    "Intercepciones":               ("Intercepciones", "conteo"),
    "Recuperaciones 1/4":           ("Recuperaciones de balón 1/4", "conteo"),
    "Recuperaciones 2/4":           ("Recuperaciones de balón 2/4", "conteo"),
    "Recuperaciones 3/4":           ("Recuperaciones de balón 3/4", "conteo"),
    "Recuperaciones 4/4":           ("Recuperaciones de balón 4/4", "conteo"),
    # --- agregadas para el catálogo estandarizado ---
    "Regates acertados":            ("Regates acertados", "conteo"),
    "Ocasión generada":             ("Ocasión generada", "conteo"),
    "Tiros a gol de cabeza":        ("Tiros a gol de cabeza", "conteo"),
    "Despejes":                     ("Despejes", "conteo"),
    "Recuperaciones de balón":      ("Recuperaciones de balón", "conteo"),
    "Recuperaciones cancha rival":  ("Recuperaciones de balón cancha rival", "conteo"),
}

# Métricas de PORTEROS (salen de la Matrix de porteros, CARPETA_PORTEROS)
METRICAS_PORTERO = {
    "Paradas":                      ("Paradas del Portero", "conteo"),
    "Paradas atrapando el balón":   ("Paradas del portero atrapando el balón", "conteo"),
    "Paradas sin retener":          ("Paradas del portero no se queda con el balón", "conteo"),
    "Goles recibidos":              ("Goles recibidos", "conteo"),
    "Porterías en cero":            ("Porterías en cero", "conteo"),
    "Penales atajados":             ("Penales enfrentados por el portero atajado", "conteo"),
    "Puñetazos":                    ("Puñetazos del portero", "conteo"),
    "Salidas fuera del área":       ("Salidas del portero fuera del área", "conteo"),
    "Despejes a destino":           ("Despeje a destino", "conteo"),
    "Despejes sin destino":         ("Despeje sin destino", "conteo"),
    "Pases acertados":              ("Pases del portero acertados", "conteo"),
    "Pases largos acertados":       ("Pases balón largo acertados", "conteo"),
    "Saques de meta cortos acertados": ("Saque de meta raso / en corto acertado", "conteo"),
    "Saques de meta largos acertados": ("Saque de meta largo / por alto acertado", "conteo"),
    "Saques con la mano acertados": ("Saque con manos del portero  acertado", "conteo"),  # ojo: doble espacio en el Excel
}

# =============================================================================
# 4) CATÁLOGO ESTANDARIZADO (15 stats por posición)
# =============================================================================
# Cada stat va como ("Nombre", "liga") o ("Nombre", "grupo"):
#   "liga"  -> se compara contra el máximo de TODA la liga
#   "grupo" -> se compara contra el máximo de su GRUPO de posición (abajo)
# Decisiones tomadas del documento "Catálogo de stats por posición".
GRUPOS_POSICION = {
    "Defensa central": "Centrales",
    "Lateral por derecha": "Laterales",
    "Lateral por izquierda": "Laterales",
    "Volante defensivo": "Medios",
    "Volante ofensivo": "Medios",
    "Volante por derecha": "Bandas",
    "Volante por izquierda": "Bandas",
    "Delantero": "Delanteros",
    "Portero": "Porteros",
}

SECCIONES = ["Ofensiva", "Defensiva", "Posesión"]
SECCIONES_PORTERO = ["Atajadas", "Área y juego aéreo", "Distribución"]

L, G = "liga", "grupo"

_EST_LATERAL = {
    "Ofensiva":  [("Asistencias", L), ("Ocasión generada", G), ("Regates acertados", G),
                  ("Duelos ofensivos (%)", L), ("Faltas recibidas", L)],
    "Defensiva": [("Duelos defensivos ganados", L), ("Duelos defensivos (%)", L),
                  ("Intercepciones", L), ("Recuperaciones de balón", L), ("Duelos aéreos ganados", G)],
    "Posesión":  [("Centros", G), ("Centros a destino", G), ("Pases acertados 3/4", L),
                  ("Pases acertados 4/4", L), ("Pérdidas por despojo", G)],
}
_EST_BANDA = {
    "Ofensiva":  [("Goles", L), ("Asistencias", L), ("Tiros a gol", L),
                  ("Ocasión generada", L), ("Regates acertados", G)],
    "Defensiva": [("Duelos defensivos ganados", L), ("Duelos defensivos (%)", L),
                  ("Recuperaciones de balón", L), ("Recuperaciones cancha rival", L), ("Intercepciones", G)],
    "Posesión":  [("Centros", G), ("Centros a destino", G), ("Pases acertados 3/4", G),
                  ("Pases acertados 4/4", G), ("Pérdidas por despojo", G)],
}

CATALOGO_ESTANDARIZADO = {
    "Defensa central": {
        "Ofensiva":  [("Goles", G), ("Tiros a gol de cabeza", L), ("Regates acertados", G),
                      ("Duelos ofensivos (%)", L), ("Faltas recibidas", G)],
        "Defensiva": [("Duelos defensivos ganados", G), ("Duelos defensivos (%)", L),
                      ("Duelos aéreos ganados", L), ("Intercepciones", L), ("Despejes", L)],
        "Posesión":  [("Pases acertados", L), ("Pases acertados (%)", L), ("Pases acertados 2/4", L),
                      ("Pases acertados 3/4", L), ("Pérdidas por despojo", G)],
    },
    "Lateral por derecha": _EST_LATERAL,
    "Lateral por izquierda": _EST_LATERAL,
    "Volante defensivo": {
        "Ofensiva":  [("Asistencias", L), ("Ocasión generada", G), ("Tiros a gol", G),
                      ("Regates acertados", G), ("Faltas recibidas", G)],
        "Defensiva": [("Duelos defensivos ganados", L), ("Duelos defensivos (%)", L),
                      ("Intercepciones", L), ("Recuperaciones de balón", L), ("Duelos aéreos ganados", G)],
        "Posesión":  [("Pases acertados", G), ("Pases acertados (%)", L), ("Pases acertados 2/4", G),
                      ("Pases acertados 3/4", L), ("Pérdidas por despojo", G)],
    },
    "Volante ofensivo": {
        "Ofensiva":  [("Goles", L), ("Asistencias", L), ("Tiros a gol", G),
                      ("Ocasión generada", G), ("Regates acertados", G)],
        "Defensiva": [("Duelos defensivos ganados", G), ("Duelos defensivos (%)", L),
                      ("Recuperaciones de balón", L), ("Recuperaciones cancha rival", G), ("Intercepciones", G)],
        "Posesión":  [("Pases acertados", G), ("Pases acertados (%)", L), ("Pases acertados 3/4", G),
                      ("Pases acertados 4/4", G), ("Pérdidas por despojo", G)],
    },
    "Volante por derecha": _EST_BANDA,
    "Volante por izquierda": _EST_BANDA,
    "Delantero": {
        "Ofensiva":  [("Goles", L), ("Asistencias", L), ("Tiros a gol", L),
                      ("Tiros a destino", L), ("Ocasión generada", G)],
        "Defensiva": [("Duelos defensivos ganados", G), ("Duelos defensivos (%)", L),
                      ("Recuperaciones de balón", G), ("Recuperaciones cancha rival", G), ("Duelos aéreos ganados", L)],
        "Posesión":  [("Pases acertados", G), ("Pases acertados (%)", L), ("Pases acertados 3/4", G),
                      ("Pases acertados 4/4", G), ("Pérdidas por despojo", G)],
    },
    # Porteros: se comparan contra todos los porteros de su liga (Matrix de porteros)
    "Portero": {
        "Atajadas":           [("Paradas", L), ("Paradas atrapando el balón", L), ("Goles recibidos", L),
                               ("Porterías en cero", L), ("Penales atajados", L)],
        "Área y juego aéreo": [("Puñetazos", L), ("Salidas fuera del área", L), ("Paradas sin retener", L),
                               ("Despejes a destino", L), ("Despejes sin destino", L)],
        "Distribución":       [("Pases acertados", L), ("Pases largos acertados", L),
                               ("Saques de meta cortos acertados", L), ("Saques de meta largos acertados", L),
                               ("Saques con la mano acertados", L)],
    },
}

# =============================================================================
# 4b) CATÁLOGO INICIAL (TEMPORAL — tomado de radar_golstats_jugador.ipynb)
# =============================================================================
_INI_LATERAL = {
    "Ofensiva":  ["Duelos ofensivos", "Duelos ofensivos ganados", "Duelos ofensivos (%)"],
    "Defensiva": ["Duelos defensivos", "Duelos defensivos (%)", "Recuperaciones 1/4",
                  "Recuperaciones 2/4", "Recuperaciones 3/4", "Intercepciones",
                  "Duelos aéreos", "Duelos aéreos ganados"],
    "Posesión":  ["Centros", "Centros a destino", "Pases acertados 2/4",
                  "Pases acertados 3/4", "Pases acertados 4/4", "Pérdidas por despojo"],
}
_INI_VOLANTE_CENTRAL = {
    "Ofensiva":  ["Duelos ofensivos", "Tiros a gol"],
    "Defensiva": ["Duelos defensivos ganados", "Recuperaciones 2/4", "Recuperaciones 3/4",
                  "Recuperaciones 4/4", "Intercepciones", "Duelos aéreos ganados"],
    "Posesión":  ["Pases acertados 2/4", "Pases acertados 3/4", "Pases acertados 4/4",
                  "Pérdidas por despojo"],
}
_INI_VOLANTE_BANDA = {
    "Ofensiva":  ["Goles", "Asistencias", "Tiros a gol", "Duelos ofensivos"],
    "Defensiva": ["Duelos defensivos ganados", "Recuperaciones 2/4", "Recuperaciones 3/4",
                  "Recuperaciones 4/4", "Intercepciones", "Duelos aéreos",
                  "Duelos aéreos ganados"],
    "Posesión":  ["Centros", "Centros a destino", "Pases acertados 2/4",
                  "Pases acertados 3/4", "Pases acertados 4/4", "Pases no acertados 2/4",
                  "Pases no acertados 3/4", "Pases no acertados 4/4",
                  "Pérdidas por despojo 2/4", "Pérdidas por despojo 3/4",
                  "Pérdidas por despojo 4/4"],
}

CATALOGO_INICIAL = {
    "Defensa central": {
        "Ofensiva":  ["Duelos ofensivos", "Duelos ofensivos (%)"],
        "Defensiva": ["Duelos defensivos ganados", "Duelos defensivos (%)",
                      "Recuperaciones 1/4", "Recuperaciones 2/4", "Intercepciones",
                      "Duelos aéreos ganados"],
        "Posesión":  ["Pases acertados 2/4", "Pases acertados 3/4"],
    },
    "Lateral por derecha": _INI_LATERAL,
    "Lateral por izquierda": _INI_LATERAL,
    "Volante defensivo": _INI_VOLANTE_CENTRAL,
    "Volante ofensivo": _INI_VOLANTE_CENTRAL,
    "Volante por derecha": _INI_VOLANTE_BANDA,
    "Volante por izquierda": _INI_VOLANTE_BANDA,
    "Delantero": {
        "Ofensiva":  ["Goles", "Asistencias", "Tiros a gol", "Tiros de cabeza",
                      "Duelos ofensivos", "Faltas recibidas"],
        "Defensiva": ["Duelos defensivos ganados", "Recuperaciones 4/4", "Intercepciones",
                      "Duelos aéreos", "Duelos aéreos ganados"],
        "Posesión":  ["Pases acertados 3/4", "Pases acertados 4/4", "Pérdidas por despojo"],
    },
    # "Portero": {...}   # sin catálogo por ahora: su ficha sale sin barras
}

CATALOGOS = {"estandarizado": CATALOGO_ESTANDARIZADO, "inicial": CATALOGO_INICIAL}

# =============================================================================
# 5) CÁLCULO DE LAS BARRAS
# =============================================================================
# "total" -> valor crudo del Excel (lo que pediste por ahora)
# "per90" -> conteos divididos entre minutos x 90 (los % no se tocan)
MODO_VALORES = "total"

# Para el máximo de referencia solo cuentan jugadores con al menos estos minutos
# (0 = todos). Útil sobre todo en modo "per90".
MIN_MINUTOS_REFERENCIA = 0

# (Solo para el catálogo "inicial") Contra quién se compara cada métrica.
#   "todos"     -> todos los jugadores de la competencia (default actual)
#   "posicion"  -> solo jugadores de la misma posición del catálogo
#   ["Defensa central", "Lateral por derecha", ...] -> ese grupo de posiciones
# Deja vacío para que TODO sea "todos". Ejemplo para la mejora futura:
#   "Duelos defensivos ganados": "posicion",
#   "Centros a destino": ["Lateral por derecha", "Lateral por izquierda",
#                         "Volante por derecha", "Volante por izquierda"],
GRUPO_COMPARACION = {}
GRUPO_COMPARACION_DEFAULT = "todos"

# =============================================================================
# 6) IMÁGENES
# =============================================================================
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
FOTO_TAMANO = (480, 600)        # px, 4:5
# Todas las fotos se igualan: se detecta al jugador (quitando fondo blanco o
# transparente) y se escala para que ocupe esta fracción del alto del recuadro,
# pegado abajo. Más alto = jugador más grande.
FOTO_ALTO_JUGADOR = 0.86
# Nombre de archivo de fotos/mapas: se busca en este orden
#   1) el NUI            ->  151446.png          (lo más seguro)
#   2) nombre completo   ->  José Humberto Mancilla López.png
#   3) nombre de la Matrix -> Humberto Mancilla.png
MAPA_LADO_MAX = 900             # px, el mapa se reduce sin recortar
