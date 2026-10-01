# Fichas de Jugadores — Inteligencia Deportiva Pumas

Página (GitHub Pages) donde cualquiera del departamento elige un jugador **de Pumas** (U19, U21…)
y descarga su ficha en **PDF tamaño carta**. Nadie necesita instalar nada: solo abrir el link.

- Solo se generan fichas de jugadores de Pumas (`FILTRO_EQUIPO_FICHAS` en `config.py`).
- Las barras se comparan contra el máximo de **toda la liga** (todos los equipos del Excel).

```
fichas_pumas/
├── config.py          <- RUTAS, filtro Pumas, NUI y CATÁLOGO de atributos por posición
├── build.py           <- lee Excel + fotos + mapas y genera docs/
├── actualizar.bat     <- (Windows) build + publicar en GitHub, doble clic
├── actualizar.sh      <- (Mac/Linux) lo mismo
├── ver_local.bat      <- ver la página en tu compu antes de publicar
└── docs/              <- ESTO es la página que publica GitHub Pages
    ├── index.html  app.js  ficha.js      (ficha.js = diseño del PDF)
    ├── data/fichas.js                    (se genera solo)
    ├── img/fotos  img/mapas              (se generan solos)
    └── vendor/pdf-lib.min.js
```

Los Excel, fotos y mapas originales **no se suben** a GitHub: solo lo necesario para la
ficha (fotos reducidas y las stats del catálogo).

---

## 1. Primera vez (solo tú o quien mantenga la página)

1. Instala **Python 3** (marca *"Add Python to PATH"*) y **Git** (git-scm.com).
2. En esta carpeta abre una terminal y corre:
   ```
   pip install -r requirements.txt
   ```
3. Abre `config.py` y pon tus rutas:
   ```python
   CARPETA_EXCEL = r"C:\Users\...\Matrices GolStats"
   CARPETA_FOTOS = r"C:\Users\...\Fotos Jugadores"
   CARPETA_MAPAS = r"C:\Users\...\Mapas de Calor"
   CARPETA_NUI   = r"C:\Users\...\NUI"
   ```
4. Crea el repositorio en GitHub (github.com → **New repository**, p. ej. `Pumas_FichasJugadores`,
   público, **sin** README).
5. En la terminal, dentro de esta carpeta:
   ```
   git init
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/Pumas_FichasJugadores.git
   ```
6. Doble clic a **`actualizar.bat`** (genera y sube todo).
7. En GitHub: **Settings → Pages → Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: **main** / carpeta **/docs** → **Save**
8. En 1-2 min aparece el link: `https://TU_USUARIO.github.io/Pumas_FichasJugadores/`.
   Ese es el link que se comparte al departamento.

Solo quien tenga permiso en el repo puede cambiar la data. Los demás solo ven.

## 2. Cada vez que haya datos nuevos

1. Deja el Excel nuevo en `CARPETA_EXCEL` (y fotos/mapas nuevos en sus carpetas).
2. Doble clic a **`actualizar.bat`**.

Cada `.xlsx` de la carpeta es una **Competencia** en la página (U19, U21, …). Si reemplazas el
archivo J1-J7 por J1-J9, borra el viejo para que no salgan los dos.

Al terminar, `reporte_build.txt` lista a quién le falta algo.

## 3. Registro (quién tiene ficha)

El Excel en `CARPETA_NUI` manda. Formato (una fila por jugador):

| NOMBRE | NUI | EQUIPO |
|---|---|---|
| José Humberto Mancilla López | 000000 | Pumas UNAM U21 |

Opcionales: **POSICIÓN** y **FECHA DE NACIMIENTO** (sirven para los que aún no tienen minutos).

- En la página, cada competencia (U19, U21) muestra **solo los registrados en esa categoría**.
  Los de primer equipo o no registrados ya no salen.
- El nombre que se imprime es el del registro (escríbelo normal, con acentos).
- El programa busca a cada registrado en la Matrix de su liga aunque ahí venga cortado
  ("José Humberto Mancilla López" ↔ "Humberto Mancilla" o "Jose Mancilla"). Ignora mayúsculas y acentos.
- Registrados **sin minutos** salen igual: barras en 0 si tienen POSICIÓN; si no, un aviso.
- Registrados con minutos en **otra categoría** (U19 que sube a U21 o U21 que baja a U19): salen en la
  lista de su categoría (con la etiqueta "También en …") y también en la lista de la otra, en un grupo
  aparte, con sus stats de esa Matrix.
- Si alguien no empata o empata mal: `EMPATES_MANUALES` en `config.py` (NUI → nombre como viene en la Matrix).

Después de cada `actualizar.bat` revisa **`reporte_build.txt`**: Pumas de la Matrix que no están en el
registro, empates dudosos, sin minutos, sin foto, sin mapa.

## 3b. Fotos y mapas de calor

Se buscan en este orden (se ignoran mayúsculas, acentos y espacios; también en subcarpetas):

1. `NUI.png` → `151446.png` (lo más seguro)
2. nombre completo del registro → `José Humberto Mancilla López.png`
3. nombre de la Matrix → `Humberto Mancilla.png`

Las fotos se igualan solas: se detecta al jugador (fondo blanco o transparente), se recorta y se escala
para que todos ocupen el mismo alto. Si los quieres más grandes o más chicos: `FOTO_ALTO_JUGADOR`
en `config.py` (0.86 por defecto).

## 4. Catálogo de stats (y cómo regresar)

En `config.py`, sección 3:

```python
CATALOGO_ACTIVO = "estandarizado"     # o "inicial"
```

- **estandarizado**: 15 stats por posición (5 Ofensiva, 5 Defensiva, 5 Posesión). Cada una dice contra
  quién se compara: `"liga"` (máximo de toda la liga) o `"grupo"` (máximo de su grupo de posición:
  Centrales, Laterales, Medios = volante defensivo + ofensivo, Bandas, Delanteros, Porteros).
  En la ficha se ve a la derecha de cada barra: `máx 28 · Liga`, `máx 20 · Centrales`.
- **inicial**: el catálogo temporal del cuaderno de radares, todo contra la liga.
- Para regresar: cambia la palabra y corre `actualizar.bat`.

Editar una stat: en `CATALOGO_ESTANDARIZADO` cambia el nombre o el `"liga"`/`"grupo"`. Si la stat es
nueva, agrégala primero en `METRICAS` (nombre en la ficha → columna exacta del Excel).

**Porteros**: su Matrix va en `CARPETA_PORTEROS` (`datos/porteros`), solo los datos. Sus fotos, mapas y NUI
van con todos los demás, y aparecen en la misma lista de la página. Sus stats están en `METRICAS_PORTERO`
y sus secciones son Atajadas, Área y juego aéreo, Distribución.

Jugadores sin minutos: su ficha sale sin barras, con el aviso "Sin minutos registrados…".

## 5. Cambiar el diseño del PDF

`docs/ficha.js`, objeto `DISENO` al inicio: colores de cada sección, posiciones de la foto, mapa,
textos del pie. Medidas en puntos (72 pt = 1 pulgada; carta = 612 × 792).
Logo: reemplaza `docs/assets/logo.png`.

## 6. Probar en tu compu antes de publicar

Doble clic a `ver_local.bat` → se abre `http://localhost:8000`.
(Abrir `docs/index.html` directo con doble clic no carga las fotos; usa `ver_local.bat`.)

## Notas

- La página es pública para quien tenga el link (no aparece en Google: `noindex`).
  Si se necesita privada, GitHub Pages en repo privado requiere plan GitHub Pro/Team.
- Enlace directo a una ficha: al elegir un jugador la URL cambia (`?c=...&j=...`); ese link se puede mandar.
- **PDF de toda la plantilla**: un solo PDF con una hoja por jugador de la lista
  (respeta los filtros de posición y búsqueda). La búsqueda acepta nombre o NUI.
