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
CARPETA_EXCEL = r"datos/excel"
CARPETA_FOTOS = r"datos/fotos"          # se busca también en subcarpetas
CARPETA_MAPAS = r"datos/mapas"          # mapas de calor, misma regla de nombres

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
# 3) MÉTRICAS DISPONIBLES
# =============================================================================
# nombre en la ficha : (columna exacta del Excel, tipo)
#   tipo "conteo"     -> número (se puede pasar a por-90 con MODO_VALORES)
#   tipo "porcentaje" -> ya viene en %, nunca se divide entre minutos
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
}

# =============================================================================
# 4) CATÁLOGO POR POSICIÓN  (TEMPORAL — tomado de radar_golstats_jugador.ipynb)
# =============================================================================
# Orden de las secciones en la ficha. Cada lista = barras de esa sección.
SECCIONES = ["Ofensiva", "Defensiva", "Posesión"]

_LATERAL = {
    "Ofensiva":  ["Duelos ofensivos", "Duelos ofensivos ganados", "Duelos ofensivos (%)"],
    "Defensiva": ["Duelos defensivos", "Duelos defensivos (%)", "Recuperaciones 1/4",
                  "Recuperaciones 2/4", "Recuperaciones 3/4", "Intercepciones",
                  "Duelos aéreos", "Duelos aéreos ganados"],
    "Posesión":  ["Centros", "Centros a destino", "Pases acertados 2/4",
                  "Pases acertados 3/4", "Pases acertados 4/4", "Pérdidas por despojo"],
}
_VOLANTE_CENTRAL = {
    "Ofensiva":  ["Duelos ofensivos", "Tiros a gol"],
    "Defensiva": ["Duelos defensivos ganados", "Recuperaciones 2/4", "Recuperaciones 3/4",
                  "Recuperaciones 4/4", "Intercepciones", "Duelos aéreos ganados"],
    "Posesión":  ["Pases acertados 2/4", "Pases acertados 3/4", "Pases acertados 4/4",
                  "Pérdidas por despojo"],
}
_VOLANTE_BANDA = {
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

CATALOGO_POSICIONES = {
    "Defensa central": {
        "Ofensiva":  ["Duelos ofensivos", "Duelos ofensivos (%)"],
        "Defensiva": ["Duelos defensivos ganados", "Duelos defensivos (%)",
                      "Recuperaciones 1/4", "Recuperaciones 2/4", "Intercepciones",
                      "Duelos aéreos ganados"],
        "Posesión":  ["Pases acertados 2/4", "Pases acertados 3/4"],
    },
    "Lateral por derecha": _LATERAL,
    "Lateral por izquierda": _LATERAL,
    "Volante defensivo": _VOLANTE_CENTRAL,
    "Volante ofensivo": _VOLANTE_CENTRAL,
    "Volante por derecha": _VOLANTE_BANDA,
    "Volante por izquierda": _VOLANTE_BANDA,
    "Delantero": {
        "Ofensiva":  ["Goles", "Asistencias", "Tiros a gol", "Tiros de cabeza",
                      "Duelos ofensivos", "Faltas recibidas"],
        "Defensiva": ["Duelos defensivos ganados", "Recuperaciones 4/4", "Intercepciones",
                      "Duelos aéreos", "Duelos aéreos ganados"],
        "Posesión":  ["Pases acertados 3/4", "Pases acertados 4/4", "Pérdidas por despojo"],
    },
    # "Portero": {...}   # sin catálogo por ahora: su ficha sale sin barras
}

# =============================================================================
# 5) CÁLCULO DE LAS BARRAS
# =============================================================================
# "total" -> valor crudo del Excel (lo que pediste por ahora)
# "per90" -> conteos divididos entre minutos x 90 (los % no se tocan)
MODO_VALORES = "total"

# Para el máximo de referencia solo cuentan jugadores con al menos estos minutos
# (0 = todos). Útil sobre todo en modo "per90".
MIN_MINUTOS_REFERENCIA = 0

# Contra quién se compara cada métrica para sacar el máximo.
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
FOTO_TAMANO = (480, 600)        # px, se recorta a 4:5 (centrado, cargado arriba)
MAPA_LADO_MAX = 900             # px, el mapa se reduce sin recortar
