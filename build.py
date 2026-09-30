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
  docs/img/mapas/*.jpg     mapas de calor reducidos
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
    t = re.sub(r"(?i)^matri[xz][\s_]*jugadores[\s_]*", "", stem)
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
    esc = (cfg("FOTO_ALTO_JUGADOR", 0.86) * H) / sujeto.height
    sujeto = sujeto.resize((max(1, round(sujeto.width * esc)), max(1, round(sujeto.height * esc))), Image.LANCZOS)
    # centrado horizontal usando el centro de la cabeza (tercio superior del sujeto)
    m2 = _mascara_jugador(sujeto)
    cabeza = np.where(m2[: max(1, sujeto.height // 3)])[1]
    cx = cabeza.mean() if len(cabeza) else sujeto.width / 2
    x = round(W / 2 - cx)
    y = H - sujeto.height
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
def validar_catalogo():
    errores = []
    for pos, secs in C.CATALOGO_POSICIONES.items():
        for sec, lista in secs.items():
            if sec not in C.SECCIONES:
                errores.append(f"'{pos}': sección '{sec}' no está en SECCIONES")
            for m in lista:
                if m not in C.METRICAS:
                    errores.append(f"'{pos}' / {sec}: la métrica '{m}' no está en METRICAS")
    if errores:
        print("\n[ERROR] Revisa config.py:\n  - " + "\n  - ".join(errores))
        sys.exit(1)


def grupo_de(metrica, posicion):
    g = C.GRUPO_COMPARACION.get(metrica, C.GRUPO_COMPARACION_DEFAULT)
    if g == "todos":
        return None
    if g == "posicion":
        return {posicion}
    return set(g)


# ============================================================================= Matrix
def leer_matrix(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    titulo = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=None, nrows=1).iloc[0, 0]
    df = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=C.FILA_ENCABEZADO)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df[C.COL_JUGADOR].notna() & (df[C.COL_JUGADOR].astype(str).str.strip() != "")].reset_index(drop=True)
    label = etiqueta_competencia(stem)
    es_pumas = df[C.COL_EQUIPO].astype(str).map(slug).str.contains(slug(C.FILTRO_EQUIPO_FICHAS), regex=False)
    cat = categoria(label) or categoria(stem)
    if cat is None and es_pumas.any():
        cat = categoria(df.loc[es_pumas, C.COL_EQUIPO].iloc[0])

    minutos = df[C.COL_MINUTOS].map(to_number).fillna(0)
    pos_cat = df[C.COL_POSICION].map(mapear_posicion)
    valores = {}
    for m, (col, tipo) in C.METRICAS.items():
        if col not in df.columns:
            valores[m] = pd.Series(np.nan, index=df.index)
            continue
        v = df[col].map(to_number).fillna(0)
        if tipo != "porcentaje" and C.MODO_VALORES == "per90":
            v = v * 90 / minutos.replace(0, np.nan)
        valores[m] = v

    ref = minutos >= C.MIN_MINUTOS_REFERENCIA
    cache = {}

    def maximo(m, posicion):
        g = grupo_de(m, posicion)
        key = (m, None if g is None else tuple(sorted(g)))
        if key not in cache:
            mask = ref if g is None else ref & pos_cat.isin(g)
            s = valores[m][mask].dropna()
            cache[key] = float(s.max()) if len(s) else None
        return cache[key]

    faltan = sorted({col for col, _ in C.METRICAS.values() if col not in df.columns})
    return {
        "path": path, "stem": stem, "label": label, "cat": cat, "titulo": titulo,
        "jornadas": jornadas(stem, titulo), "df": df, "es_pumas": es_pumas,
        "minutos": minutos, "pos_cat": pos_cat, "valores": valores, "maximo": maximo, "faltan": faltan,
    }


def empatar(mx, candidatos, rep):
    """Asigna filas Pumas de la Matrix a jugadores del registro. Devuelve {id_registro: indice_fila}."""
    df = mx["df"]
    filas = list(df.index[mx["es_pumas"].values])
    nombres = {i: str(df.at[i, C.COL_JUGADOR]).strip() for i in filas}
    asignado, usados = {}, set()

    # 1) empates manuales (NUI -> nombre Matrix)
    manual = {str(k): slug(v) for k, v in cfg("EMPATES_MANUALES", {}).items()}
    for c in candidatos:
        if c["nui"] and c["nui"] in manual:
            fila = next((i for i in filas if slug(nombres[i]) == manual[c["nui"]]), None)
            if fila is not None:
                asignado[c["rid"]] = fila
                usados.add(fila)

    # 2) automáticos: mejor puntaje; los de la misma categoría tienen prioridad
    pares = []
    for i in filas:
        if i in usados:
            continue
        for c in candidatos:
            if c["rid"] in asignado:
                continue
            p = puntaje(nombres[i], c["nombre"])
            if p:
                pares.append((p + (1000 if c["cat"] == mx["cat"] else 0), i, c["rid"], c["nombre"]))
    pares.sort(key=lambda x: -x[0])
    por_fila = {}
    for p, i, rid, nom in pares:
        por_fila.setdefault(i, []).append((p, rid, nom))
    for p, i, rid, nom in pares:
        if i in usados or rid in asignado:
            continue
        rivales = [x for x in por_fila[i] if x[0] == p and x[1] != rid and x[1] not in asignado]
        if rivales:
            rep["dudosos"].append(f"[{mx['label']}] '{nombres[i]}' coincide igual con: "
                                  f"{nom} / {' / '.join(r[2] for r in rivales)}  -> usa EMPATES_MANUALES")
            usados.add(i)
            continue
        asignado[rid] = i
        usados.add(i)

    for i in filas:
        if i not in usados:
            rep["sin_registro"].append(f"[{mx['label']}] {nombres[i]}  ({int(mx['minutos'][i])} min)")
    return asignado


# ============================================================================= main
def main():
    validar_catalogo()
    carpeta = ruta(C.CARPETA_EXCEL)
    excels = sorted(
        os.path.join(carpeta, f) for f in os.listdir(carpeta)
        if f.lower().endswith((".xlsx", ".xlsm", ".xls")) and not f.startswith("~$")
    ) if os.path.isdir(carpeta) else []
    if not excels:
        print(f"[ERROR] No hay archivos Excel en {carpeta}")
        sys.exit(1)
    for d in (OUT_FOTOS, OUT_MAPAS, os.path.dirname(OUT_DATA)):
        os.makedirs(d, exist_ok=True)

    idx_fotos = indexar_imagenes(C.CARPETA_FOTOS)
    idx_mapas = indexar_imagenes(C.CARPETA_MAPAS)
    print(f"Fotos encontradas: {len(idx_fotos)}   Mapas encontrados: {len(idx_mapas)}")

    registro = cargar_registro()
    for k, r in enumerate(registro):
        r["rid"] = f"r{k}"
        r["id"] = slug(r["nui"] or r["nombre"])
    print(f"Registrados: {len(registro)}")
    if not registro:
        print("[ERROR] El registro (CARPETA_NUI) está vacío: no hay a quién hacerle ficha.")
        sys.exit(1)

    rep = {k: [] for k in ("sin_foto", "sin_mapa", "sin_minutos", "sin_registro", "dudosos", "subidos", "sin_nui")}
    usados_img = set()
    competencias = []
    tambien_en = {}          # rid -> [labels de otras categorías donde tiene minutos]

    # 1) empatar registro <-> cada Matrix (primero todas, para juntar los alias de cada jugador)
    matrices = []
    alias = {}               # rid -> nombres con los que aparece en las Matrix (para buscar fotos)
    for path in excels:
        mx = leer_matrix(path)
        cat = mx["cat"]
        print(f"\n== {mx['label']}  ({os.path.basename(path)}) — categoría U{cat}, {len(mx['df'])} jugadores en la liga")
        if cat is None:
            print("  [aviso] no pude detectar la categoría (U19/U21) de este archivo; se omite")
            continue
        for c in mx["faltan"]:
            print(f"  [aviso] columna que no viene en este Excel: {c}")
        mx["propios"] = [r for r in registro if r["cat"] == cat]
        mx["inferiores"] = [r for r in registro if r["cat"] and r["cat"] != cat] \
            if cfg("INCLUIR_OTRAS_CATEGORIAS", cfg("INCLUIR_CATEGORIA_INFERIOR", True)) else []
        mx["asignado"] = empatar(mx, mx["propios"] + mx["inferiores"], rep)
        for rid, i in mx["asignado"].items():
            alias.setdefault(rid, []).append(str(mx["df"].at[i, C.COL_JUGADOR]).strip())
        matrices.append(mx)

    # 2) armar las fichas
    for mx in matrices:
        df, cat, asignado = mx["df"], mx["cat"], mx["asignado"]
        propios, inferiores = mx["propios"], mx["inferiores"]
        jugadores = []
        for r in propios + [x for x in inferiores if x["rid"] in asignado]:
            i = asignado.get(r["rid"])
            subido = r["cat"] != cat
            con_datos = i is not None
            posicion = mx["pos_cat"][i] if con_datos else r["posicion"]
            if subido:
                rep["subidos"].append(f"[{mx['label']}] {r['nombre']} (registrado U{r['cat']}) "
                                      f"= '{df.at[i, C.COL_JUGADOR]}', {int(mx['minutos'][i])} min")
                tambien_en.setdefault(r["rid"], []).append(mx["label"])
            if not con_datos:
                rep["sin_minutos"].append(f"[{mx['label']}] {r['nombre']}"
                                          + ("" if r["posicion"] else "  (sin POSICIÓN en el registro: sin barras)"))
            if not r["nui"]:
                rep["sin_nui"].append(r["nombre"])

            nombre_mx = str(df.at[i, C.COL_JUGADOR]).strip() if con_datos else None
            foto = mapa = None
            src = buscar_imagen(idx_fotos, r["nui"], r["nombre"], *alias.get(r["rid"], []))
            if src:
                foto = f"img/fotos/{r['id']}.jpg"
                if foto not in usados_img:
                    procesar_foto(src, os.path.join(DOCS, foto))
                usados_img.add(foto)
            else:
                rep["sin_foto"].append(r["nombre"])
            src = buscar_imagen(idx_mapas, r["nui"], r["nombre"], *alias.get(r["rid"], []))
            if src:
                mapa = f"img/mapas/{r['id']}.jpg"
                if mapa not in usados_img:
                    procesar_mapa(src, os.path.join(DOCS, mapa))
                usados_img.add(mapa)
            else:
                rep["sin_mapa"].append(r["nombre"])

            secciones = {}
            for sec in C.SECCIONES:
                filas = []
                for m in C.CATALOGO_POSICIONES.get(posicion, {}).get(sec, []):
                    tipo = C.METRICAS[m][1]
                    dec = 1 if tipo == "porcentaje" else (2 if C.MODO_VALORES == "per90" else 0)
                    v = num(mx["valores"][m][i], dec) if con_datos else 0
                    filas.append([m, v, num(mx["maximo"](m, posicion), dec), tipo])
                secciones[sec] = filas

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
                "nombreMatrix": nombre_mx,
                "nui": r["nui"],
                "equipo": r["equipo"],
                "categoria": r["cat"],
                "subido": subido,
                "conDatos": con_datos,
                "posicion": posicion,
                "edad": edad,
                "nacimiento": nac,
                "minutos": int(mx["minutos"][i]) if con_datos else 0,
                "partidos": int(np.nan_to_num(to_number(df.at[i, C.COL_PARTIDOS]))) if con_datos else 0,
                "foto": foto,
                "mapa": mapa,
                "secciones": secciones,
            })

        jugadores.sort(key=lambda j: (j["subido"], slug(j["nombre"])))
        print(f"\n  {mx['label']} — fichas: {sum(not j['subido'] for j in jugadores)} registrados U{cat}"
              f" ({sum(not j['conDatos'] for j in jugadores)} sin minutos)"
              + (f" + {sum(j['subido'] for j in jugadores)} de otra categoría" if inferiores else ""))
        competencias.append({
            "id": slug(mx["stem"]),
            "label": mx["label"],
            "categoria": cat,
            "archivo": os.path.basename(path),
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
            if f"img/{sub}/{f}" not in usados_img and not f.startswith("."):
                os.remove(os.path.join(d, f))

    payload = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modo": C.MODO_VALORES,
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
    html = re.sub(r'src="((?:data/fichas|ficha|app)\.js)(?:\?v=\d+)?"',
                  lambda m: f'src="{m.group(1)}?v={datetime.now():%Y%m%d%H%M%S}"', html)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)

    # reporte
    titulos = {
        "sin_registro": "Pumas en la Matrix que NO están en el registro (primer equipo, otra categoría o nombre que no empató)",
        "dudosos": "Empates dudosos (no se asignaron)",
        "subidos": "Registrados en otra categoría con minutos en esta liga (suben o bajan)",
        "sin_minutos": "Registrados sin minutos en la Matrix (ficha en ceros)",
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
