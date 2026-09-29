# -*- coding: utf-8 -*-
"""
build.py — Excel(es) + fotos + mapas de calor  ->  docs/  (la página)
======================================================================
Uso:   python build.py

Genera:
  docs/data/fichas.js      datos de todos los jugadores (solo lo que usa la ficha)
  docs/img/fotos/*.jpg     fotos recortadas 4:5
  docs/img/mapas/*.png     mapas de calor reducidos

Reglas para nombrar fotos y mapas (en sus carpetas, se buscan subcarpetas):
  "Nombre Apellido.jpg"                    -> igual que la columna JUGADOR
  "Nombre Apellido__Equipo del Excel.jpg"  -> solo si hay dos jugadores con el mismo nombre
  Mayúsculas, acentos, espacios, guiones y guiones bajos se ignoran al comparar.
"""
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

import config as C

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
OUT_DATA = os.path.join(DOCS, "data", "fichas.js")
OUT_FOTOS = os.path.join(DOCS, "img", "fotos")
OUT_MAPAS = os.path.join(DOCS, "img", "mapas")


# ----------------------------------------------------------------------------- utilidades
def ruta(p):
    return p if os.path.isabs(p) else os.path.join(BASE, p)


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def to_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null", "-"}:
        return np.nan
    es_pct = "%" in s
    s = s.replace("%", "").replace("\xa0", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) in (1, 2) else s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return np.nan
    return v


def num(v, dec=None):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), dec) if dec is not None else float(v)


def equipo_corto(eq):
    e = re.sub(r"\s+Under\s+U?(\d+)$", r" U\1", str(eq).strip())
    e = re.sub(r"\s+", " ", e)
    if C.NOMBRE_EQUIPO_FICHA and slug(C.FILTRO_EQUIPO_FICHAS) in slug(e):
        cat = re.search(r"\bU\s?(\d+)\b", e)
        return f"{C.NOMBRE_EQUIPO_FICHA} U{cat.group(1)}" if cat else C.NOMBRE_EQUIPO_FICHA
    return e


def etiqueta_competencia(stem, titulo_hoja):
    if stem in C.ETIQUETAS_COMPETENCIA:
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


# ----------------------------------------------------------------------------- imágenes
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
                idx.setdefault(slug(stem.replace("__", " zzsepzz ")), os.path.join(raiz, a))
    return idx


def buscar_imagen(idx, nombre, equipo):
    return idx.get(f"{slug(nombre)}_zzsepzz_{slug(equipo)}") or idx.get(slug(nombre))


def al_dia(src, dst):
    return os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src)


def procesar_foto(src, dst):
    if al_dia(src, dst):
        return
    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fondo = Image.new("RGB", im.size, (255, 255, 255))
        fondo.paste(im, mask=im.split()[-1])
        im = fondo
    im = im.convert("RGB")
    w, h = C.FOTO_TAMANO
    im = ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.2))
    im.save(dst, "JPEG", quality=85, optimize=True)


def procesar_mapa(src, dst):
    if al_dia(src, dst):
        return
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGBA")
    im.thumbnail((C.MAPA_LADO_MAX, C.MAPA_LADO_MAX), Image.LANCZOS)
    fondo = Image.new("RGB", im.size, (255, 255, 255))
    fondo.paste(im, mask=im.split()[-1])
    fondo.save(dst, "JPEG", quality=88, optimize=True)


# ----------------------------------------------------------------------------- NUI
def _es_vacio(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() in {"", "nan", "NaT"}


def _texto_nui(v):
    if _es_vacio(v):
        return None
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        v = int(v)
    return str(v).strip()


def cargar_nui():
    """Lee todos los Excel de CARPETA_NUI -> lista de (tokens_nombre, nombre_slug, nui)."""
    registros = []
    carpeta = ruta(C.CARPETA_NUI)
    if not os.path.isdir(carpeta):
        print(f"  [aviso] no existe la carpeta de NUI {carpeta}")
        return registros
    for f in sorted(os.listdir(carpeta)):
        if not f.lower().endswith((".xlsx", ".xlsm", ".xls", ".csv")) or f.startswith("~$"):
            continue
        path = os.path.join(carpeta, f)
        hojas = {"csv": pd.read_csv(path, header=None, dtype=object)} if f.lower().endswith(".csv") \
            else pd.read_excel(path, sheet_name=None, header=None, dtype=object)
        for hoja, crudo in hojas.items():
            # fila de encabezado = la primera (de las 15 primeras) que tenga una celda con "NUI"
            fila = next((i for i in range(min(15, len(crudo)))
                         if any("nui" in slug(c).split("_") for c in crudo.iloc[i] if not _es_vacio(c))), None)
            if fila is None:
                continue
            df = crudo.iloc[fila + 1:].copy()
            df.columns = [str(c).strip() for c in crudo.iloc[fila]]
            col_nui = C.NUI_COL_NUI or next(c for c in df.columns if "nui" in slug(c).split("_"))
            if C.NUI_COLS_NOMBRE:
                cols_nom = C.NUI_COLS_NOMBRE
            else:
                cand = [c for c in df.columns if slug(c) in {"jugador", "nombre", "nombre_completo", "nombre_del_jugador"}]
                if not cand:
                    print(f"  [aviso] {f} / {hoja}: no encontré columna de nombre; usa NUI_COLS_NOMBRE en config.py")
                    continue
                cols_nom = [cand[0]]
            for _, r in df.iterrows():
                nui = _texto_nui(r.get(col_nui))
                nombre = " ".join(str(r[c]).strip() for c in cols_nom if not _es_vacio(r.get(c)))
                if nui and nombre:
                    registros.append((set(slug(nombre).split("_")), slug(nombre), nui))
        print(f"  NUI: {f} leído")
    print(f"NUI cargados: {len(registros)}")
    return registros


def buscar_nui(registros, nombre):
    s = slug(nombre)
    exactos = [r for r in registros if r[1] == s]
    if len(exactos) == 1:
        return exactos[0][2]
    # "Humberto Mancilla" (GolStats) dentro de "Humberto Mancilla Pérez" (registro)
    tokens = set(s.split("_"))
    parciales = {r[2] for r in registros if tokens <= r[0]}
    return parciales.pop() if len(parciales) == 1 else None


# ----------------------------------------------------------------------------- catálogo
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


# ----------------------------------------------------------------------------- una competencia
def procesar_excel(path, idx_fotos, idx_mapas, nuis, usados, faltantes):
    stem = os.path.splitext(os.path.basename(path))[0]
    titulo = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=None, nrows=1).iloc[0, 0]
    df = pd.read_excel(path, sheet_name=C.HOJA_EXCEL, header=C.FILA_ENCABEZADO)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df[C.COL_JUGADOR].notna() & (df[C.COL_JUGADOR].astype(str).str.strip() != "")]

    jr = jornadas(stem, titulo)
    label = etiqueta_competencia(stem, titulo)
    es_ficha = df[C.COL_EQUIPO].astype(str).map(slug).str.contains(slug(C.FILTRO_EQUIPO_FICHAS), regex=False)
    print(f"\n== {label}  ({os.path.basename(path)}) — {len(df)} jugadores en la liga, "
          f"{int(es_ficha.sum())} con ficha")
    if not es_ficha.any():
        print(f"  [aviso] ningún EQUIPO contiene '{C.FILTRO_EQUIPO_FICHAS}' (FILTRO_EQUIPO_FICHAS en config.py)")

    cols_faltan = sorted({col for col, _ in C.METRICAS.values() if col not in df.columns})
    if cols_faltan:
        print("  [aviso] columnas que no vienen en este Excel (sus barras saldrán vacías):")
        for c in cols_faltan:
            print(f"     - {c}")

    minutos = df[C.COL_MINUTOS].map(to_number).fillna(0)
    partidos = df[C.COL_PARTIDOS].map(to_number).fillna(0)
    pos_orig = df[C.COL_POSICION].astype(str).str.split(",").str[0].str.strip()
    pos_cat = pos_orig.map(lambda p: C.MAPEO_POSICIONES.get(p, p))

    valores = {}
    for m, (col, tipo) in C.METRICAS.items():
        if col not in df.columns:
            valores[m] = pd.Series(np.nan, index=df.index)
            continue
        v = df[col].map(to_number)
        if tipo == "porcentaje":
            v = v.fillna(0)
        else:
            v = v.fillna(0)
            if C.MODO_VALORES == "per90":
                v = v * 90 / minutos.replace(0, np.nan)
        valores[m] = v

    ref_mask = minutos >= C.MIN_MINUTOS_REFERENCIA
    max_cache = {}

    def maximo(m, posicion):
        g = grupo_de(m, posicion)
        key = (m, None if g is None else tuple(sorted(g)))
        if key not in max_cache:
            mask = ref_mask if g is None else ref_mask & pos_cat.isin(g)
            s = valores[m][mask].dropna()
            max_cache[key] = float(s.max()) if len(s) else None
        return max_cache[key]

    jugadores = []
    for i in df.index[es_ficha.values]:
        nombre = str(df.at[i, C.COL_JUGADOR]).strip()
        equipo = str(df.at[i, C.COL_EQUIPO]).strip()
        pid = slug(f"{nombre}_{equipo}")
        posicion = pos_cat[i]

        foto = mapa = None
        src = buscar_imagen(idx_fotos, nombre, equipo)
        if src:
            foto = f"img/fotos/{pid}.jpg"
            procesar_foto(src, os.path.join(DOCS, foto))
            usados.add(foto)
        else:
            faltantes["fotos"].add(f"{nombre}  ({equipo})")
        src = buscar_imagen(idx_mapas, nombre, equipo)
        if src:
            mapa = f"img/mapas/{pid}.jpg"
            procesar_mapa(src, os.path.join(DOCS, mapa))
            usados.add(mapa)
        else:
            faltantes["mapas"].add(f"{nombre}  ({equipo})")

        nui = buscar_nui(nuis, nombre)
        if not nui:
            faltantes["nui"].add(f"{nombre}  ({equipo})")

        secciones = {}
        for sec in C.SECCIONES:
            filas = []
            for m in C.CATALOGO_POSICIONES.get(posicion, {}).get(sec, []):
                tipo = C.METRICAS[m][1]
                dec = 1 if tipo == "porcentaje" else (2 if C.MODO_VALORES == "per90" else 0)
                filas.append([m, num(valores[m][i], dec), num(maximo(m, posicion), dec), tipo])
            secciones[sec] = filas

        nac = df.at[i, C.COL_NACIMIENTO] if C.COL_NACIMIENTO in df.columns else None
        if isinstance(nac, (pd.Timestamp, datetime)):
            nac = nac.strftime("%d/%m/%Y")
        elif nac is not None and not (isinstance(nac, float) and math.isnan(nac)):
            nac = str(nac).strip()
        else:
            nac = None

        edad = to_number(df.at[i, C.COL_EDAD]) if C.COL_EDAD in df.columns else np.nan
        jugadores.append({
            "id": pid,
            "nombre": nombre,
            "equipo": equipo,
            "equipoCorto": equipo_corto(equipo),
            "nui": nui,
            "posicion": posicion,
            "posicionExcel": pos_orig[i],
            "edad": None if math.isnan(edad) else int(edad),
            "nacimiento": nac,
            "minutos": int(minutos[i]),
            "partidos": int(partidos[i]),
            "foto": foto,
            "mapa": mapa,
            "secciones": secciones,
        })

    jugadores.sort(key=lambda j: (j["equipoCorto"], slug(j["nombre"])))
    return {
        "id": slug(stem),
        "label": label,
        "archivo": os.path.basename(path),
        "titulo": None if pd.isna(titulo) else str(titulo),
        "jornadas": list(jr) if jr else None,
        "jugadores": jugadores,
    }


# ----------------------------------------------------------------------------- main
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

    nuis = cargar_nui()

    usados, faltantes = set(), {"fotos": set(), "mapas": set(), "nui": set()}
    competencias = [procesar_excel(p, idx_fotos, idx_mapas, nuis, usados, faltantes) for p in excels]

    # borrar imágenes que ya no se usan
    for sub in ("fotos", "mapas"):
        d = os.path.join(DOCS, "img", sub)
        for f in os.listdir(d):
            if f"img/{sub}/{f}" not in usados and not f.startswith("."):
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

    n = sum(len(c["jugadores"]) for c in competencias)
    print(f"\nListo -> {os.path.relpath(OUT_DATA, BASE)}  ({n} fichas, "
          f"{os.path.getsize(OUT_DATA)/1024:.0f} KB)")
    for tipo in ("fotos", "mapas", "nui"):
        if faltantes[tipo]:
            print(f"  Sin {tipo if tipo == 'nui' else tipo[:-1]}: {len(faltantes[tipo])} jugadores "
                  f"(lista en faltantes_{tipo}.txt)")
        with open(os.path.join(BASE, f"faltantes_{tipo}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(faltantes[tipo])))


if __name__ == "__main__":
    main()
