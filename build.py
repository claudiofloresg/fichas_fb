# -*- coding: utf-8 -*-
"""
build.py — Registro (NUI) + Matrix GolStats + fotos + mapas  ->  docs/  (la página)
===================================================================================
Uso:   python build.py

Flujo
  1. El REGISTRO (Excel en CARPETA_NUI: NOMBRE | NUI | EQUIPO) define quién tiene
     ficha y en qué categoría (U19, U21...). El nombre que se imprime es el del registro.
  2. Cada Matrix (CARPETA_EXCEL) es una competencia. Se detecta su categoría (U19/U21)
     y se buscan ahí los registrados de esa categoría: su nombre completo se empata
     con el nombre corto de la Matrix ("José Humberto Mancilla López" <-> "Humberto Mancilla").
  3. Registrados sin minutos (no están en la Matrix) salen igual, en ceros.
  4. Registrados en OTRA categoría que tienen minutos en esta Matrix (U19 que sube
     a U21 o U21 que baja a U19) salen también en esta lista, con estas stats.
  5. Los máximos de las barras se calculan con TODA la liga de esa Matrix.

Genera
  docs/data/fichas.js      datos que usa la página
  docs/img/fotos/*.jpg     fotos igualadas en tamaño
  docs/img/mapas/*.jpg     mapas de calor reducidos (uno por jugador y liga)
  reporte_build.txt        quién no tiene foto/mapa/minutos, empates dudosos, etc.
"""
import difflib
import json
import math
import os
import re
import sys
import unicodedata
from datetime import date, datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

import config as C

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
OUT_DATA = os.path.join(DOCS, "data", "fichas.js")
OUT_FOTOS = os.path.join(DOCS, "img", "fotos")
OUT_MAPAS = os.path.join(DOCS, "img", "mapas")
REPORTE = os.path.join(BASE, "reporte_build.txt")

cfg = lambda nombre, default=None: getattr(C, nombre, default)  # noqa: E731


# ============================================================================= utilidades
def ruta(p):
    return p if os.path.isabs(p) else os.path.join(BASE, p)


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def es_vacio(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in {"", "nan", "NaT", "None"}


def to_number(x):
    if es_vacio(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace("%", "").replace("\xa0", "").replace(" ", "")
    if s.lower() in {"nan", "none", "null", "-"}:
        return np.nan
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) in (1, 2) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def num(v, dec=None):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), dec) if dec is not None else float(v)


def categoria(texto):
    """'Pumas UNAM U21', 'Sub-19', 'Under 19', 'SUB21' -> 21 (int) o None."""
    m = re.search(r"(?:\bu|\bsub|\bunder)[\s_-]*(\d{2})\b", slug(texto).replace("_", " "))
    return int(m.group(1)) if m else None


def fecha_txt(v):
    if es_vacio(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return v.strftime("%d/%m/%Y")
    return str(v).strip().split(" ")[0]


def edad_desde(nac):
    try:
        d = datetime.strptime(nac, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None
    hoy = date.today()
    return hoy.year - d.year - ((hoy.month, hoy.day) < (d.month, d.day))


def titulo_si_mayusculas(nombre):
    """'JOSE HUMBERTO MANCILLA' -> 'Jose Humberto Mancilla' (si viene todo en mayúsculas)."""
    if nombre.isupper():
        return " ".join(p.capitalize() if p.lower() not in {"de", "del", "la", "las", "los", "y"} else p.lower()
                        for p in nombre.split())
    return nombre


def etiqueta_competencia(stem):
    if stem in cfg("ETIQUETAS_COMPETENCIA", {}):
        return C.ETIQUETAS_COMPETENCIA[stem]
    t = re.sub(r"(?i)^matri[xz][\s_]*(jugadores|porteros)[\s_]*", "", stem)
    t = re.sub(r"(?i)J\d+\s*-\s*J\d+", "", t)
    return re.sub(r"[_\s]+", " ", t).strip() or stem


def jornadas(stem, titulo_hoja):
    for fuente in (str(titulo_hoja), stem):
        m = re.search(r"J\s*(\d+)\s*-\s*J\s*(\d+)", fuente, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def mapear_posicion(p):
    if es_vacio(p):
        return None
    p = str(p).split(",")[0].strip()
    por_slug = {slug(k): v for k, v in C.MAPEO_POSICIONES.items()}
    return por_slug.get(slug(p), p)


# ============================================================================= empate de nombres
CONECTORES = {"de", "del", "la", "las", "los", "y", "da", "dos", "van", "von"}


def tokens(nombre):
    return [t for t in slug(nombre).split("_") if t and t not in CONECTORES]


def _token_igual(a, b):
    if a == b:
        return 2
    if len(a) >= 4 and len(b) >= 4 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85:
        return 1  # typo menor: "cortes"~"cortez"
    return 0


def puntaje(nombre_matrix, nombre_registro):
    """>0 si TODAS las palabras del nombre corto (Matrix) están, en orden, dentro
    del nombre completo (registro). Más alto = mejor. 0 = no es la misma persona."""
    tm, tr = tokens(nombre_matrix), tokens(nombre_registro)
    if not tm or len(tm) > len(tr):
        return 0
    i, total = 0, 0
    for t in tm:
        while i < len(tr) and not _token_igual(t, tr[i]):
            i += 1
        if i == len(tr):
            return 0
        total += _token_igual(t, tr[i])
        i += 1
    return total * 10 + (5 if tm == tr else 0)


# ============================================================================= imágenes
def indexar_imagenes(carpeta):
    idx = {}
    carpeta = ruta(carpeta)
    if not os.path.isdir(carpeta):
        print(f"  [aviso] no existe la carpeta {carpeta}")
        return idx
    for raiz, _, archivos in os.walk(carpeta):
        for a in archivos:
            stem, ext = os.path.splitext(a)
            if ext.lower() in C.EXTENSIONES_IMAGEN:
                idx.setdefault(slug(stem), os.path.join(raiz, a))
    return idx


def indexar_mapas(carpeta):
    """Mapas de calor: {categoria: indice} por subcarpeta (U19, U21...) + None: sueltos en la raíz."""
    out = {None: {}}
    carpeta = ruta(carpeta)
    if not os.path.isdir(carpeta):
        print(f"  [aviso] no existe la carpeta {carpeta}")
        return out
    for a in sorted(os.listdir(carpeta)):
        p = os.path.join(carpeta, a)
        if os.path.isdir(p):
            cat = categoria(a)
            if cat is None:
                print(f"  [aviso] mapas: la subcarpeta '{a}' no indica liga (U19, U21...); se omite")
                continue
            out.setdefault(cat, {}).update(indexar_imagenes(p))
        elif os.path.splitext(a)[1].lower() in C.EXTENSIONES_IMAGEN:
            out[None].setdefault(slug(os.path.splitext(a)[0]), p)
    return out


def buscar_imagen(idx, *claves):
    for k in claves:
        if k and slug(k) in idx:
            return idx[slug(k)]
    return None


_MTIME_CODIGO = max(os.path.getmtime(os.path.join(BASE, f)) for f in ("build.py", "config.py"))


def al_dia(src, dst):
    return os.path.exists(dst) and os.path.getmtime(dst) >= max(os.path.getmtime(src), _MTIME_CODIGO)


def _mascara_jugador(im):
    """Máscara de lo que NO es fondo (transparente o blanco)."""
    rgba = np.asarray(im.convert("RGBA")).astype(np.int16)
    alfa = rgba[..., 3]
    if alfa.min() < 250:                          # PNG con transparencia
        return alfa > 25
    rgb = rgba[..., :3]
    return (rgb.min(axis=2) < 232) | ((rgb.max(axis=2) - rgb.min(axis=2)) > 18)


def procesar_foto(src, dst):
    """Recorta al jugador y lo escala igual para todas las fotos (mismo alto, pegado abajo)."""
    if al_dia(src, dst):
        return
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    W, H = C.FOTO_TAMANO
    lienzo = Image.new("RGB", (W, H), (255, 255, 255))

    mask = _mascara_jugador(im)
    filas, cols = np.where(mask)
    if len(filas) < 50:                            # no se detectó nada: recorte normal
        plano = Image.new("RGB", im.size, (255, 255, 255))
        plano.paste(im, mask=im.split()[-1])
        ImageOps.fit(plano, (W, H), Image.LANCZOS, centering=(0.5, 0.2)).save(dst, "JPEG", quality=88)
        return
    y0, y1, x0, x1 = filas.min(), filas.max() + 1, cols.min(), cols.max() + 1
    sujeto = im.crop((x0, y0, x1, y1))
    original = sujeto
    m0 = _mascara_jugador(original)
    banda = np.where(m0[int(original.height * 0.9):].any(axis=0))[0]          # hombros (10% de abajo)
    ancho_hombros = (banda.max() - banda.min() + 1) if len(banda) else original.width
    esc = (cfg("FOTO_ALTO_JUGADOR", 0.86) * H) / original.height
    esc = max(esc, (W * 1.02) / ancho_hombros)        # que los hombros llenen todo el ancho (sin huecos a los lados)
    sujeto = original.resize((max(1, round(original.width * esc)), max(1, round(original.height * esc))), Image.LANCZOS)
    m2 = _mascara_jugador(sujeto)
    # centrado horizontal usando el centro de la cabeza (tercio superior del sujeto)
    cabeza = np.where(m2[: max(1, sujeto.height // 3)])[1]
    cx = cabeza.mean() if len(cabeza) else sujeto.width / 2
    hombros = np.where(m2[int(sujeto.height * 0.9):].any(axis=0))[0]
    x = round(W / 2 - cx)
    if len(hombros):                                   # sin hueco blanco a la izquierda ni a la derecha
        x = min(x, -int(hombros.min()))
        x = max(x, W - int(hombros.max()) - 1)
    # pegado abajo; si quedó más alto que el recuadro, se deja un margen arriba y se recorta el torso
    y = H - sujeto.height if sujeto.height <= H * 0.96 else round(H * 0.04)
    lienzo.paste(sujeto, (x, y), sujeto)
    lienzo.save(dst, "JPEG", quality=88, optimize=True)


def procesar_mapa(src, dst):
    if al_dia(src, dst):
        return
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    im.thumbnail((C.MAPA_LADO_MAX, C.MAPA_LADO_MAX), Image.LANCZOS)
    fondo = Image.new("RGB", im.size, (255, 255, 255))
    fondo.paste(im, mask=im.split()[-1])
    fondo.save(dst, "JPEG", quality=88, optimize=True)


# ============================================================================= registro (NUI)
def _col(df, forzada, candidatos):
    if forzada:
        return forzada if forzada in df.columns else None
    for c in df.columns:
        if slug(c) in candidatos:
            return c
    return None


def cargar_registro():
    """Excel(es) de CARPETA_NUI -> lista de dicts {nombre, nui, equipo, cat, posicion, nacimiento}."""
    reg = []
    carpeta = ruta(cfg("CARPETA_NUI", "datos/nui"))
    if not os.path.isdir(carpeta):
        print(f"  [aviso] no existe la carpeta del registro {carpeta}")
        return reg
    for f in sorted(os.listdir(carpeta)):
        if not f.lower().endswith((".xlsx", ".xlsm", ".xls", ".csv")) or f.startswith("~$"):
            continue
        path = os.path.join(carpeta, f)
        hojas = {"csv": pd.read_csv(path, header=None, dtype=object)} if f.lower().endswith(".csv") \
            else pd.read_excel(path, sheet_name=None, header=None, dtype=object)
        for hoja, crudo in hojas.items():
            fila = next((i for i in range(min(15, len(crudo)))
                         if any("nui" in slug(c).split("_") for c in crudo.iloc[i] if not es_vacio(c))), None)
            if fila is None:
                continue
            df = crudo.iloc[fila + 1:].copy()
            df.columns = [str(c).strip() for c in crudo.iloc[fila]]
            c_nui = _col(df, cfg("REGISTRO_COL_NUI") or cfg("NUI_COL_NUI"), {"nui"})
            c_nom = _col(df, cfg("REGISTRO_COL_NOMBRE"),
                         {"nombre", "nombre_completo", "jugador", "nombre_del_jugador"})
            c_eq = _col(df, cfg("REGISTRO_COL_EQUIPO"), {"equipo", "categoria", "club"})
            c_pos = _col(df, cfg("REGISTRO_COL_POSICION"), {"posicion", "pos"})
            c_nac = _col(df, cfg("REGISTRO_COL_NACIMIENTO"), {"fecha_de_nacimiento", "nacimiento", "fecha_nacimiento"})
            if not c_nom:
                print(f"  [aviso] {f} / {hoja}: no encontré la columna NOMBRE")
                continue
            n0 = len(reg)
            for _, r in df.iterrows():
                nombre = r.get(c_nom)
                if es_vacio(nombre):
                    continue
                nombre = re.sub(r"\s+", " ", str(nombre)).strip()
                nui = r.get(c_nui) if c_nui else None
                if isinstance(nui, (float, np.floating)) and float(nui).is_integer():
                    nui = int(nui)
                nui = None if es_vacio(nui) else str(nui).strip()
                equipo = None if (not c_eq or es_vacio(r.get(c_eq))) else str(r.get(c_eq)).strip()
                cat = categoria(equipo) if equipo else None
                if cat is None:
                    cat = categoria(hoja) or categoria(f)
                reg.append({
                    "nombre": titulo_si_mayusculas(nombre),
                    "nui": nui,
                    "equipo": equipo or (f"{cfg('NOMBRE_EQUIPO_FICHA', 'Pumas UNAM')} U{cat}" if cat else None),
                    "cat": cat,
                    "posicion": mapear_posicion(r.get(c_pos)) if c_pos else None,
                    "nacimiento": fecha_txt(r.get(c_nac)) if c_nac else None,
                })
            print(f"  Registro: {f} / {hoja}: {len(reg) - n0} jugadores")
    sin_cat = [r["nombre"] for r in reg if r["cat"] is None]
    if sin_cat:
        print(f"  [aviso] {len(sin_cat)} registrados sin categoría en EQUIPO (ej. '{sin_cat[0]}'); no saldrán")
    return reg


# ============================================================================= catálogo
def catalogo():
    activo = cfg("CATALOGO_ACTIVO", "estandarizado")
    cats = cfg("CATALOGOS") or {"inicial": cfg("CATALOGO_POSICIONES", {})}
    if activo not in cats:
        print(f"[ERROR] CATALOGO_ACTIVO = '{activo}' no existe. Opciones: {list(cats)}")
        sys.exit(1)
    return cats[activo]


def metricas_de(posicion):
    return cfg("METRICAS_PORTERO", {}) if posicion == "Portero" else C.METRICAS


def secciones_de(posicion):
    """Secciones (en orden) y sus items [(metrica, comparación)] para una posición."""
    cat = catalogo().get(posicion, {})
    orden = cfg("SECCIONES_PORTERO", []) if posicion == "Portero" else C.SECCIONES
    orden = [s for s in orden if s in cat] + [s for s in cat if s not in orden]
    out = []
    for sec in orden:
        items = [(it, None) if isinstance(it, str) else (it[0], it[1]) for it in cat[sec]]
        out.append((sec, items))
    return out


def validar_catalogo():
    errores = []
    for pos in catalogo():
        for sec, items in secciones_de(pos):
            for m, comp in items:
                if m not in metricas_de(pos):
                    errores.append(f"'{pos}' / {sec}: la métrica '{m}' no está en "
                                   f"{'METRICAS_PORTERO' if pos == 'Portero' else 'METRICAS'}")
                if comp not in (None, "liga", "grupo"):
                    errores.append(f"'{pos}' / {sec} / {m}: comparación '{comp}' (usa \"liga\" o \"grupo\")")
    if errores:
        print("\n[ERROR] Revisa config.py:\n  - " + "\n  - ".join(errores))
        sys.exit(1)


def grupo_de(metrica, posicion):
    """Solo catálogo inicial: GRUPO_COMPARACION por métrica."""
    g = cfg("GRUPO_COMPARACION", {}).get(metrica, cfg("GRUPO_COMPARACION_DEFAULT", "todos"))
    if g == "todos":
        return None
    if g == "posicion":
        return {posicion}
    return set(g)


# ============================================================================= Matrix
def leer_matrix(path, es_portero=False):
    stem = os.path.splitext(os.path.basename(path))[0]
    titulo = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=None, nrows=1).iloc[0, 0]
    df = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=C.FILA_ENCABEZADO)
    df.columns = [str(c).strip() for c in df.columns]
    if C.COL_JUGADOR not in df.columns:
        print(f"  [aviso] {os.path.basename(path)}: no trae la columna '{C.COL_JUGADOR}' en la fila "
              f"{C.FILA_ENCABEZADO + 1} (formato distinto); se omite")
        return None
    df = df[df[C.COL_JUGADOR].notna() & (df[C.COL_JUGADOR].astype(str).str.strip() != "")].reset_index(drop=True)
    label = etiqueta_competencia(stem)
    es_pumas = df[C.COL_EQUIPO].astype(str).map(slug).str.contains(slug(C.FILTRO_EQUIPO_FICHAS), regex=False)
    cat = categoria(label) or categoria(stem)
    if cat is None and es_pumas.any():
        cat = categoria(df.loc[es_pumas, C.COL_EQUIPO].iloc[0])

    minutos = df[C.COL_MINUTOS].map(to_number).fillna(0)
    if es_portero:
        pos_cat = pd.Series("Portero", index=df.index)
        metricas = cfg("METRICAS_PORTERO", {})
    else:
        pos_cat = df[C.COL_POSICION].map(mapear_posicion)
        metricas = C.METRICAS
    grupos = cfg("GRUPOS_POSICION", {})
    grupo = pos_cat.map(lambda p: grupos.get(p, p))

    # el Excel a veces trae dobles espacios en los encabezados: se compara sin ellos
    por_texto = {re.sub(r"\s+", " ", c): c for c in df.columns}
    valores, faltan = {}, []
    for m, (col, tipo) in metricas.items():
        real = col if col in df.columns else por_texto.get(re.sub(r"\s+", " ", col))
        if real is None:
            valores[m] = pd.Series(np.nan, index=df.index)
            faltan.append(col)
            continue
        v = df[real].map(to_number).fillna(0)
        if tipo != "porcentaje" and C.MODO_VALORES == "per90":
            v = v * 90 / minutos.replace(0, np.nan)
        valores[m] = v

    ref = minutos >= C.MIN_MINUTOS_REFERENCIA
    ref_prom = minutos >= cfg("INFORME_MIN_MINUTOS_PROMEDIO", 270)
    cache = {}

    def maximo(m, posicion, comp):
        """comp: 'liga' (toda la Matrix), 'grupo' (GRUPOS_POSICION de esa posición) o None (catálogo inicial)."""
        if comp == "grupo":
            g = grupos.get(posicion, posicion)
            key, mask = (m, "g", g), ref & (grupo == g)
        elif comp == "liga":
            key, mask = (m, "liga"), ref
        else:
            gs = grupo_de(m, posicion)
            key = (m, None if gs is None else tuple(sorted(gs)))
            mask = ref if gs is None else ref & pos_cat.isin(gs)
        if key not in cache:
            s = valores[m][mask].dropna()
            cache[key] = float(s.max()) if len(s) else None
        return cache[key]

    def promedio(m, posicion, comp):
        """Promedio (informe gráfico) del mismo grupo que el máximo, solo con jugadores con
        al menos INFORME_MIN_MINUTOS_PROMEDIO minutos."""
        if comp == "grupo":
            mask = ref_prom & (grupo == grupos.get(posicion, posicion))
            key = (m, "prom_g", grupos.get(posicion, posicion))
        elif comp == "liga":
            mask, key = ref_prom, (m, "prom_liga")
        else:
            gs = grupo_de(m, posicion)
            mask = ref_prom if gs is None else ref_prom & pos_cat.isin(gs)
            key = (m, "prom", None if gs is None else tuple(sorted(gs)))
        if key not in cache:
            s = valores[m][mask].dropna()
            cache[key] = float(s.mean()) if len(s) else None
        return cache[key]

    def crudo(col, i):
        """Valor crudo de una columna del Excel (tolera dobles espacios). None si no existe."""
        real = col if col in df.columns else por_texto.get(re.sub(r"\s+", " ", col))
        if real is None:
            return None
        v = to_number(df.at[i, real])
        return None if math.isnan(v) else float(v)

    return {
        "path": path, "stem": stem, "label": label, "cat": cat, "titulo": titulo, "es_portero": es_portero,
        "jornadas": jornadas(stem, titulo), "df": df, "es_pumas": es_pumas,
        "minutos": minutos, "pos_cat": pos_cat, "valores": valores, "maximo": maximo, "faltan": faltan,
        "promedio": promedio, "crudo": crudo,
    }


def empatar(fuentes, label, cat, candidatos, rep):
    """Asigna filas Pumas de las Matrix (campo + porteros) a jugadores del registro.
    Devuelve {id_registro: (indice_fuente, indice_fila)}."""
    filas, nombres, minutos = [], {}, {}
    hay_porteros = any(f["es_portero"] for f in fuentes)
    for fi, mx in enumerate(fuentes):
        for i in mx["df"].index[mx["es_pumas"].values]:
            if hay_porteros and not mx["es_portero"] and mx["pos_cat"][i] == "Portero":
                continue  # el portero se toma de su Matrix de porteros
            k = (fi, i)
            filas.append(k)
            nombres[k] = str(mx["df"].at[i, C.COL_JUGADOR]).strip()
            minutos[k] = int(mx["minutos"][i])
    asignado, usados = {}, set()

    # 1) empates manuales (NUI -> nombre Matrix)
    manual = {str(k): slug(v) for k, v in cfg("EMPATES_MANUALES", {}).items()}
    for c in candidatos:
        if c["nui"] and c["nui"] in manual:
            k = next((k for k in filas if slug(nombres[k]) == manual[c["nui"]] and k not in usados), None)
            if k is not None:
                asignado[c["rid"]] = k
                usados.add(k)

    # 2) automáticos: mejor puntaje; los de la misma categoría tienen prioridad
    pares = []
    for k in filas:
        if k in usados:
            continue
        for c in candidatos:
            if c["rid"] in asignado:
                continue
            p = puntaje(nombres[k], c["nombre"])
            if p:
                pares.append((p + (1000 if c["cat"] == cat else 0), k, c["rid"], c["nombre"]))
    pares.sort(key=lambda x: -x[0])
    por_fila = {}
    for p, k, rid, nom in pares:
        por_fila.setdefault(k, []).append((p, rid, nom))
    for p, k, rid, nom in pares:
        if k in usados or rid in asignado:
            continue
        rivales = [x for x in por_fila[k] if x[0] == p and x[1] != rid and x[1] not in asignado]
        if rivales:
            rep["dudosos"].append(f"[{label}] '{nombres[k]}' coincide igual con: "
                                  f"{nom} / {' / '.join(r[2] for r in rivales)}  -> usa EMPATES_MANUALES")
            usados.add(k)
            continue
        asignado[rid] = k
        usados.add(k)

    for k in filas:
        if k not in usados:
            rep["sin_registro"].append(f"[{label}] {nombres[k]}  ({minutos[k]} min)")
    return asignado


def desglose_stats(src_mx, i, posicion):
    """Informe gráfico, cuadro "Estadísticas": las stats del catálogo con su % relacionado.
    Devuelve [[seccion, etiqueta, valor_grande, tipo_grande, dato_crudo_abajo], ...]."""
    metricas = metricas_de(posicion)
    norm = lambda c: re.sub(r"\s+", " ", str(c)).strip()  # noqa: E731
    pct_de = {norm(k): v for k, v in cfg("INFORME_PORCENTAJES", {}).items()}
    items = [(sec, m) for sec, its in secciones_de(posicion) for m, _ in its]
    cols_conteo = {norm(metricas[m][0]) for _, m in items if metricas[m][1] != "porcentaje"}
    out = []
    for sec, m in items:
        col, tipo = metricas[m]
        v = src_mx["valores"][m][i]
        v = None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
        if tipo == "porcentaje":
            socios = [c for c, p in pct_de.items() if norm(p) == norm(col)]
            if any(c in cols_conteo for c in socios):
                continue                                  # ya sale junto con su conteo
            crudo = src_mx["crudo"](socios[0], i) if socios else None
            out.append([sec, re.sub(r"\s*\(%\)\s*$", "", m), num(v, 1), "porcentaje", num(crudo, 1)])
        elif norm(col) in pct_de and src_mx["crudo"](pct_de[norm(col)], i) is not None:
            out.append([sec, m, num(src_mx["crudo"](pct_de[norm(col)], i), 1), "porcentaje", num(v, 1)])
        else:
            out.append([sec, m, num(v, 1), "conteo", None])
    return out


def leer_carpeta(carpeta):
    carpeta = ruta(carpeta)
    if not os.path.isdir(carpeta):
        return []
    return sorted(os.path.join(carpeta, f) for f in os.listdir(carpeta)
                  if f.lower().endswith((".xlsx", ".xlsm", ".xls")) and not f.startswith("~$"))


# ============================================================================= main
def main():
    validar_catalogo()
    print(f"Catálogo activo: {cfg('CATALOGO_ACTIVO', 'inicial')}")
    excels = leer_carpeta(C.CARPETA_EXCEL)
    if not excels:
        print(f"[ERROR] No hay archivos Excel en {ruta(C.CARPETA_EXCEL)}")
        sys.exit(1)
    for d in (OUT_FOTOS, OUT_MAPAS, os.path.dirname(OUT_DATA)):
        os.makedirs(d, exist_ok=True)

    idx_fotos = indexar_imagenes(C.CARPETA_FOTOS)
    idx_mapas = indexar_mapas(C.CARPETA_MAPAS)
    print(f"Fotos encontradas: {len(idx_fotos)}   Mapas encontrados: "
          + ", ".join(f"{'sueltos' if k is None else f'U{k}'} {len(v)}" for k, v in idx_mapas.items() if v or k is None))

    registro = cargar_registro()
    for k, r in enumerate(registro):
        r["rid"] = f"r{k}"
        r["id"] = slug(r["nui"] or r["nombre"])
    print(f"Registrados: {len(registro)}")
    if not registro:
        print("[ERROR] El registro (CARPETA_NUI) está vacío: no hay a quién hacerle ficha.")
        sys.exit(1)

    # Matrix de porteros, por categoría
    porteros = {}
    for p in leer_carpeta(cfg("CARPETA_PORTEROS", "datos/porteros")):
        mp = leer_matrix(p, es_portero=True)
        if mp is None:
            continue
        if mp["cat"] is None:
            print(f"  [aviso] porteros: no pude detectar la categoría de {os.path.basename(p)}; se omite")
            continue
        porteros.setdefault(mp["cat"], []).append(mp)
        print(f"Porteros U{mp['cat']}: {os.path.basename(p)} — {len(mp['df'])} porteros en la liga")
        for c in mp["faltan"]:
            print(f"  [aviso] columna que no viene en la Matrix de porteros: {c}")

    rep = {k: [] for k in ("sin_foto", "sin_mapa", "sin_minutos", "sin_registro", "dudosos", "subidos", "sin_nui")}
    usados_img = set()
    competencias = []
    tambien_en = {}          # rid -> [labels de otras categorías donde tiene minutos]

    # 1) empatar registro <-> cada Matrix (primero todas, para juntar los alias de cada jugador)
    comps = []
    alias = {}               # rid -> nombres con los que aparece en las Matrix (para buscar fotos)
    for path in excels:
        mx = leer_matrix(path)
        if mx is None:
            continue
        cat = mx["cat"]
        print(f"\n== {mx['label']}  ({os.path.basename(path)}) — categoría U{cat}, {len(mx['df'])} jugadores en la liga")
        if cat is None:
            print("  [aviso] no pude detectar la categoría (U19/U21) de este archivo; se omite")
            continue
        for c in mx["faltan"]:
            print(f"  [aviso] columna que no viene en este Excel: {c}")
        fuentes = [mx]
        mps = porteros.get(cat, [])
        if mps:
            mp = next((x for x in mps if x["label"] == mx["label"]), mps[0])
            fuentes.append(mp)
        else:
            print(f"  [aviso] no hay Matrix de porteros U{cat} en {cfg('CARPETA_PORTEROS', 'datos/porteros')}")
        propios = [r for r in registro if r["cat"] == cat]
        otros = [r for r in registro if r["cat"] and r["cat"] != cat] \
            if cfg("INCLUIR_OTRAS_CATEGORIAS", cfg("INCLUIR_CATEGORIA_INFERIOR", True)) else []
        asignado = empatar(fuentes, mx["label"], cat, propios + otros, rep)
        for rid, (fi, i) in asignado.items():
            alias.setdefault(rid, []).append(str(fuentes[fi]["df"].at[i, C.COL_JUGADOR]).strip())
        comps.append(dict(mx=mx, fuentes=fuentes, cat=cat, propios=propios, otros=otros, asignado=asignado))

    # 2) armar las fichas
    grupos = cfg("GRUPOS_POSICION", {})
    for cp in comps:
        mx, fuentes, cat, asignado = cp["mx"], cp["fuentes"], cp["cat"], cp["asignado"]
        jugadores = []
        for r in cp["propios"] + [x for x in cp["otros"] if x["rid"] in asignado]:
            k = asignado.get(r["rid"])
            subido = r["cat"] != cat
            con_datos = k is not None
            src_mx, i = (fuentes[k[0]], k[1]) if con_datos else (None, None)
            df = src_mx["df"] if con_datos else None
            posicion = src_mx["pos_cat"][i] if con_datos else r["posicion"]
            if subido:
                rep["subidos"].append(f"[{mx['label']}] {r['nombre']} (registrado U{r['cat']}) "
                                      f"= '{df.at[i, C.COL_JUGADOR]}', {int(src_mx['minutos'][i])} min")
                tambien_en.setdefault(r["rid"], []).append(mx["label"])
            if not con_datos:
                rep["sin_minutos"].append(f"[{mx['label']}] {r['nombre']}")
            if not r["nui"]:
                rep["sin_nui"].append(r["nombre"])

            foto = mapa = None
            src = buscar_imagen(idx_fotos, r["nui"], r["nombre"], *alias.get(r["rid"], []))
            if src:
                foto = f"img/fotos/{r['id']}.jpg"
                if foto not in usados_img:
                    procesar_foto(src, os.path.join(DOCS, foto))
                usados_img.add(foto)
            else:
                rep["sin_foto"].append(r["nombre"])
            claves = (r["nui"], r["nombre"], *alias.get(r["rid"], []))
            src = buscar_imagen(idx_mapas.get(cat, {}), *claves) or buscar_imagen(idx_mapas[None], *claves)
            if src:
                mapa = f"img/mapas/{r['id']}_u{cat}.jpg"
                if mapa not in usados_img:
                    procesar_mapa(src, os.path.join(DOCS, mapa))
                usados_img.add(mapa)
            else:
                rep["sin_mapa"].append(f"[{mx['label']}] {r['nombre']}")

            # barras: solo si tiene minutos (sin minutos -> la ficha muestra un aviso)
            secciones, orden = {}, []
            if con_datos:
                metricas = metricas_de(posicion)
                for sec, items in secciones_de(posicion):
                    filas = []
                    for m, comp in items:
                        tipo = metricas[m][1]
                        dec = 1 if tipo == "porcentaje" else (2 if C.MODO_VALORES == "per90" else 0)
                        if comp == "grupo" or posicion == "Portero":
                            ref_txt = grupos.get(posicion, posicion)
                        elif comp is None and grupo_de(m, posicion) is not None:
                            ref_txt = "Posición"
                        else:
                            ref_txt = "Liga"
                        filas.append([m, num(src_mx["valores"][m][i], dec),
                                      num(src_mx["maximo"](m, posicion, comp), dec), tipo, ref_txt,
                                      num(src_mx["promedio"](m, posicion, comp), 2)])
                    secciones[sec] = filas
                    orden.append(sec)

            # informe gráfico: participación (goles, asistencias...) y canchitas por cuartos
            informe = None
            if con_datos:
                es_por = posicion == "Portero"
                desglose = desglose_stats(src_mx, i, posicion)
                zonas = None
                if not es_por and cfg("INFORME_ZONAS"):
                    zonas = []
                    for titulo, col, tipo in C.INFORME_ZONAS:
                        if tipo == "balance":
                            a = [src_mx["crudo"](f"{col[0]} {q}/4", i) for q in (1, 2, 3, 4)]
                            b = [src_mx["crudo"](f"{col[1]} {q}/4", i) for q in (1, 2, 3, 4)]
                            vals = [None if x is None or y is None else x - y for x, y in zip(a, b)]
                        else:
                            vals = [src_mx["crudo"](f"{col} {q}/4", i) for q in (1, 2, 3, 4)]
                        if all(v is None for v in vals):
                            continue
                        zonas.append([titulo, [num(v, 1) for v in vals], tipo])
                informe = {"desglose": desglose, "zonas": zonas}

            if con_datos:
                nac = fecha_txt(df.at[i, C.COL_NACIMIENTO]) if C.COL_NACIMIENTO in df.columns else None
                edad = to_number(df.at[i, C.COL_EDAD]) if C.COL_EDAD in df.columns else np.nan
                edad = None if math.isnan(edad) else int(edad)
            else:
                nac, edad = r["nacimiento"], None
            nac = nac or r["nacimiento"]
            if edad is None:
                edad = edad_desde(nac)

            jugadores.append({
                "id": r["id"],
                "rid": r["rid"],
                "nombre": r["nombre"],
                "nombreMatrix": str(df.at[i, C.COL_JUGADOR]).strip() if con_datos else None,
                "nui": r["nui"],
                "equipo": r["equipo"],
                "categoria": r["cat"],
                "subido": subido,
                "conDatos": con_datos,
                "posicion": posicion,
                "edad": edad,
                "nacimiento": nac,
                "minutos": int(src_mx["minutos"][i]) if con_datos else 0,
                "partidos": int(np.nan_to_num(to_number(df.at[i, C.COL_PARTIDOS]))) if con_datos else 0,
                "foto": foto,
                "mapa": mapa,
                "ordenSecciones": orden,
                "secciones": secciones,
                "informe": informe,
            })

        jugadores.sort(key=lambda j: (j["subido"], slug(j["nombre"])))
        print(f"\n  {mx['label']} — fichas: {sum(not j['subido'] for j in jugadores)} registrados U{cat}"
              f" ({sum(not j['conDatos'] for j in jugadores)} sin minutos)"
              + (f" + {sum(j['subido'] for j in jugadores)} de otra categoría" if cp["otros"] else ""))
        competencias.append({
            "id": slug(mx["stem"]),
            "label": mx["label"],
            "categoria": cat,
            "archivo": os.path.basename(mx["path"]),
            "jornadas": list(mx["jornadas"]) if mx["jornadas"] else None,
            "jugadores": jugadores,
        })

    for comp in competencias:
        for j in comp["jugadores"]:
            j["tambienEn"] = [] if j["subido"] else tambien_en.get(j["rid"], [])
            del j["rid"]
    competencias.sort(key=lambda c: (c["categoria"], c["label"]))

    # borrar imágenes que ya no se usan
    for sub in ("fotos", "mapas"):
        d = os.path.join(DOCS, "img", sub)
        for f in os.listdir(d):
            if os.path.isdir(os.path.join(d, f)):
                continue
            if f"img/{sub}/{f}" not in usados_img and not f.startswith("."):
                os.remove(os.path.join(d, f))

    payload = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modo": C.MODO_VALORES,
        "minPromedio": cfg("INFORME_MIN_MINUTOS_PROMEDIO", 270),
        "secciones": C.SECCIONES,
        "competencias": competencias,
    }
    with open(OUT_DATA, "w", encoding="utf-8") as f:
        f.write("window.FICHAS = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    # Obliga al navegador a bajar la versión nueva de los .js (evita caché)
    idx = os.path.join(DOCS, "index.html")
    html = open(idx, encoding="utf-8").read()
    html = re.sub(r'src="((?:data/fichas|ficha|informe|app)\.js)(?:\?v=\d+)?"',
                  lambda m: f'src="{m.group(1)}?v={datetime.now():%Y%m%d%H%M%S}"', html)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)

    # reporte
    titulos = {
        "sin_registro": "Pumas en la Matrix que NO están en el registro (primer equipo, otra categoría o nombre que no empató)",
        "dudosos": "Empates dudosos (no se asignaron)",
        "subidos": "Registrados en otra categoría con minutos en esta liga (suben o bajan)",
        "sin_minutos": "Registrados sin minutos en la Matrix (su ficha sale con aviso, sin barras)",
        "sin_nui": "Registrados sin NUI",
        "sin_foto": "Sin foto",
        "sin_mapa": "Sin mapa de calor",
    }
    with open(REPORTE, "w", encoding="utf-8") as f:
        f.write(f"Reporte de actualización — {payload['generado']}\n")
        for k, t in titulos.items():
            items = sorted(set(rep[k]))
            f.write(f"\n=== {t}: {len(items)}\n" + "".join(f"  - {x}\n" for x in items))
    for viejo in ("faltantes_fotos.txt", "faltantes_mapas.txt", "faltantes_nui.txt"):
        if os.path.exists(os.path.join(BASE, viejo)):
            os.remove(os.path.join(BASE, viejo))

    n = sum(len(c["jugadores"]) for c in competencias)
    print(f"\nListo -> {os.path.relpath(OUT_DATA, BASE)}  ({n} fichas, {os.path.getsize(OUT_DATA)/1024:.0f} KB)")
    for k in ("sin_registro", "dudosos", "sin_minutos", "sin_foto", "sin_mapa"):
        if rep[k]:
            print(f"  {titulos[k].split(' (')[0]}: {len(set(rep[k]))}")
    print("  Detalle en reporte_build.txt")


if __name__ == "__main__":
    main()
