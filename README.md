# Fichas de Jugadores FB — Inteligencia Deportiva Pumas

Página (GitHub Pages) donde cualquiera del departamento elige un jugador y descarga su
ficha en **PDF tamaño carta**. Nadie necesita instalar nada: solo abrir el link.

```
fichas_pumas/
├── config.py          <- RUTAS de tu compu + CATÁLOGO de atributos por posición
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

Al terminar, `faltantes_fotos.txt` y `faltantes_mapas.txt` listan quién no tiene imagen.

## 3. Nombres de fotos y mapas de calor

El nombre del archivo = columna **JUGADOR** del Excel (se ignoran mayúsculas, acentos y espacios):

```
Humberto Mancilla.jpg
Jaime Obregón.png
```

Si hay dos jugadores con el mismo nombre en equipos distintos, agrega el equipo tal cual viene en el Excel
después de dos guiones bajos:

```
Diego Sánchez__Atlante FC Under 19.jpg
```

Formatos: jpg, jpeg, png, webp. Se buscan también en subcarpetas.
Las fotos se recortan a 4:5 (centradas, cargadas hacia arriba). Los mapas no se recortan.

## 4. Cambiar atributos (catálogo)

Todo en `config.py`:

- `METRICAS`: nombre que sale en la ficha → (columna del Excel, "conteo" | "porcentaje").
- `CATALOGO_POSICIONES`: por posición, qué métricas van en **Ofensiva / Defensiva / Posesión**.
  El número de barras por sección es libre; la ficha ajusta el alto de las filas sola.
- `MODO_VALORES`: `"total"` (actual) o `"per90"`.
- `GRUPO_COMPARACION`: para la mejora futura. Por métrica define contra quién se saca el máximo:
  `"todos"` (actual), `"posicion"` o una lista de posiciones:
  ```python
  GRUPO_COMPARACION = {
      "Duelos defensivos ganados": "posicion",
      "Centros a destino": ["Lateral por derecha", "Lateral por izquierda",
                            "Volante por derecha", "Volante por izquierda"],
  }
  ```

Luego `actualizar.bat`.

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
- **PDF de todo el equipo**: elige un equipo en el filtro → un solo PDF con una hoja por jugador
  (respeta también los filtros de posición y búsqueda).
