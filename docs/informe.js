/* =============================================================================
   informe.js — Informe gráfico (PDF horizontal 16:9) con radares, con pdf-lib
   Todo el diseño (colores, medidas, textos) está en DISENO_INFORME.
   Unidades: puntos. Página = 960 x 540 pt (mismo formato que la presentación).
   Coordenadas: x desde la izquierda, y desde ARRIBA.
   ========================================================================== */
const DISENO_INFORME = {
  pagina: { w: 960, h: 540 },
  fondo: 'assets/fondo_informe.jpg',
  colores: {
    navy: '#0C2A4E', gold: '#B08A4E', ink: '#0C2A4E', soft: '#5A6470', faint: '#8B93A0',
    avatar: '#BFC4CA', cancha: '#3E7A50',
  },
  // Radar del jugador: colores por tercios, en el orden de las stats (como radar_wyscout)
  tercios: ['#1A78CF', '#FF9300', '#D70232'],
  ordenRadar: ['Ofensiva', 'Posesión', 'Defensiva'],   // porteros usan el orden de sus secciones
  // Radar vs promedio (como el comparativo de PyPizza)
  jugador: '#1A78CF', jugadorCaja: '#6495ED', promedio: '#FF9300', lineasComparativo: '#0C2A4E',

  foto: { x: 56, y: 60, w: 96, h: 120 },
  datos: { x: 166, y: 70, w: 180 },
  mapa: { x: 364, y: 60, w: 232, h: 160 },
  estadisticas: { x: 612, y: 60, w: 320, yFin: 234, columnas: 5 },
  radarJugador: { cx: 176, cy: 358, r: 72, titulo: 'PERFIL DEL JUGADOR' },
  radarPromedio: { cx: 784, cy: 358, r: 72, titulo: 'VS PROMEDIO' },
  canchas: { x: 372, y: 270, w: 58, h: 86, dx: 82, dy: 108 },
  yLeyenda: 474,        // leyenda + nota de cada radar (arriba de la línea azul del fondo)
  yPie: 519,            // pie de página (debajo de la línea azul)
  credito: 'Elaborado por Inteligencia Deportiva Pumas',
  fuente: 'GolStats',
  textoPorteros: 'No se cuenta con información por zonas de cancha para el análisis de porteros.',
};

const Informe = (() => {
  const { rgb, StandardFonts, PDFDocument, BlendMode } = PDFLib;
  const D = DISENO_INFORME;
  const P = D.pagina;

  const hex = (h) => {
    const n = parseInt(h.slice(1), 16);
    return rgb(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255);
  };
  const C = Object.fromEntries(Object.entries(D.colores).map(([k, v]) => [k, hex(v)]));
  const BLANCO = rgb(1, 1, 1);
  // texto azul marino sobre fondos claros, blanco sobre fondos oscuros
  const claro = (h) => {
    const n = parseInt(h.slice(1), 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255]
      .map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] > 0.3;
  };

  // ------------------------------------------------------------------ recursos
  const cacheBytes = new Map();
  async function bytes(url) {
    if (!url) return null;
    if (!cacheBytes.has(url)) {
      cacheBytes.set(url, fetch(url).then(r => (r.ok ? r.arrayBuffer() : null)).catch(() => null));
    }
    return cacheBytes.get(url);
  }

  async function embed(doc, b) {
    if (!b) return null;
    try { return await doc.embedJpg(b); } catch (e) { /* no es jpg */ }
    try { return await doc.embedPng(b); } catch (e) { return null; }
  }

  async function nuevoDoc() {
    const doc = await PDFDocument.create();
    doc.setTitle('Informe de jugador — Pumas UNAM');
    doc.setAuthor('Inteligencia Deportiva Pumas');
    doc.setCreator('Fichas de Jugadores — Inteligencia Deportiva Pumas');
    const f = {
      reg: await doc.embedFont(StandardFonts.Helvetica),
      bold: await doc.embedFont(StandardFonts.HelveticaBold),
      ital: await doc.embedFont(StandardFonts.HelveticaOblique),
    };
    const fondo = await embed(doc, await bytes(D.fondo));
    return { doc, f, fondo, imgs: new Map() };
  }

  async function img(ctx, url) {
    if (!url) return null;
    if (!ctx.imgs.has(url)) ctx.imgs.set(url, await embed(ctx.doc, await bytes(url)));
    return ctx.imgs.get(url);
  }

  // ------------------------------------------------------------------ texto seguro (WinAnsi)
  const okChar = new Map();
  function limpio(font, s) {
    s = String(s ?? '');
    let out = '';
    for (const ch of s) {
      if (!okChar.has(ch)) {
        try { font.widthOfTextAtSize(ch, 10); okChar.set(ch, ch); }
        catch (e) {
          const base = ch.normalize('NFD').replace(/[̀-ͯ]/g, '');
          let ok = '';
          try { font.widthOfTextAtSize(base, 10); ok = base; } catch (e2) { ok = ''; }
          okChar.set(ch, ok);
        }
      }
      out += okChar.get(ch);
    }
    return out;
  }

  // ------------------------------------------------------------------ primitivas (y desde arriba)
  function mk(page, ctx) {
    const Y = (y) => P.h - y;
    const ancho = (s, font, size) => font.widthOfTextAtSize(limpio(font, s), size);
    const t = (s, x, y, o = {}) => {
      const font = o.font || ctx.f.reg;
      let size = o.size || 9;
      s = limpio(font, s);
      if (o.maxW) {
        while (size > (o.minSize || 6) && font.widthOfTextAtSize(s, size) > o.maxW) size -= 0.25;
        if (font.widthOfTextAtSize(s, size) > o.maxW) {
          while (s.length > 1 && font.widthOfTextAtSize(s + '…', size) > o.maxW) s = s.slice(0, -1);
          s += '…';
        }
      }
      const w = font.widthOfTextAtSize(s, size);
      const xx = o.align === 'right' ? x - w : o.align === 'center' ? x - w / 2 : x;
      page.drawText(s, { x: xx, y: Y(y), size, font, color: o.color || C.ink, opacity: o.opacity });
      return w;
    };
    const r = (x, y, w, h, color, o = {}) => page.drawRectangle({
      x, y: Y(y + h), width: w, height: h, color, opacity: o.opacity,
      borderColor: o.border, borderWidth: o.border ? (o.bw || 0.75) : 0,
    });
    const l = (x1, y1, x2, y2, color, th = 0.75, dash) => page.drawLine({
      start: { x: x1, y: Y(y1) }, end: { x: x2, y: Y(y2) }, thickness: th, color, dashArray: dash,
    });
    // trazo SVG en coordenadas de página (y hacia abajo)
    const path = (d, o = {}) => page.drawSvgPath(d, {
      x: 0, y: P.h, color: o.color, opacity: o.opacity,
      borderColor: o.border, borderWidth: o.border ? (o.bw || 0.75) : 0, borderOpacity: o.borderOpacity,
      borderDashArray: o.dash,
    });
    const circ = (cx, cy, rr, o = {}) => page.drawCircle({
      x: cx, y: Y(cy), size: rr, color: o.color, opacity: o.opacity,
      borderColor: o.border, borderWidth: o.border ? (o.bw || 0.75) : 0, borderDashArray: o.dash,
    });
    // texto girado, centrado en (x, y); rot en grados (sentido antihorario)
    const tr = (s, x, y, rot, o = {}) => {
      const font = o.font || ctx.f.reg, size = o.size || 6;
      s = limpio(font, s);
      const w = font.widthOfTextAtSize(s, size), th = (rot * Math.PI) / 180;
      const ox = x - Math.cos(th) * w / 2 + Math.sin(th) * size * 0.36;
      const oy = Y(y) - Math.sin(th) * w / 2 - Math.cos(th) * size * 0.36;
      page.drawText(s, { x: ox, y: oy, size, font, color: o.color || C.ink, rotate: PDFLib.degrees(rot) });
    };
    return { t, r, l, path, circ, ancho, tr };
  }

  const f2 = (n) => Math.round(n * 100) / 100;
  const caja = (x, y, w, h, rad) =>
    `M${f2(x + rad)},${f2(y)} H${f2(x + w - rad)} A${rad},${rad} 0 0 1 ${f2(x + w)},${f2(y + rad)} ` +
    `V${f2(y + h - rad)} A${rad},${rad} 0 0 1 ${f2(x + w - rad)},${f2(y + h)} H${f2(x + rad)} ` +
    `A${rad},${rad} 0 0 1 ${f2(x)},${f2(y + h - rad)} V${f2(y + rad)} A${rad},${rad} 0 0 1 ${f2(x + rad)},${f2(y)} Z`;
  // gajo de radar: ángulos en radianes, 0 = arriba, sentido horario
  const pt = (cx, cy, rr, a) => [cx + rr * Math.sin(a), cy - rr * Math.cos(a)];
  function gajo(cx, cy, r0, r1, a0, a1) {
    const [x0, y0] = pt(cx, cy, r1, a0), [x1, y1] = pt(cx, cy, r1, a1);
    const [x2, y2] = pt(cx, cy, r0, a1), [x3, y3] = pt(cx, cy, r0, a0);
    return `M${f2(x0)},${f2(y0)} A${f2(r1)},${f2(r1)} 0 0 1 ${f2(x1)},${f2(y1)} ` +
      `L${f2(x2)},${f2(y2)} A${f2(r0)},${f2(r0)} 0 0 0 ${f2(x3)},${f2(y3)} Z`;
  }

  // ------------------------------------------------------------------ formato
  const fmtV = (v, tipo) => {
    if (v === null || v === undefined) return '–';
    if (tipo === 'porcentaje') return `${Math.round(v)}%`;
    return Number.isInteger(v) ? String(v) : (Math.abs(v) < 10 ? v.toFixed(1) : String(Math.round(v)));
  };
  const jornadasTxt = (comp) => (comp.jornadas ? `J${comp.jornadas[0]}–J${comp.jornadas[1]}` : '');
  const coloresPorTercios = (n) => {
    const tercio = Math.ceil(n / 3);
    const out = [];
    D.tercios.forEach((c) => { for (let i = 0; i < tercio; i++) out.push(c); });
    return out.slice(0, n);
  };
  // parte un texto en 2 líneas lo más parejas posible (si es largo)
  function partir(s, maxChars = 13) {
    if (s.length <= maxChars || !s.includes(' ')) return [s];
    const p = s.split(' ');
    let mejor = [s], dif = 1e9;
    for (let k = 1; k < p.length; k++) {
      const a = p.slice(0, k).join(' '), b = p.slice(k).join(' ');
      const d = Math.max(a.length, b.length);
      if (d < dif) { dif = d; mejor = [a, b]; }
    }
    return mejor;
  }

  // ------------------------------------------------------------------ stats en orden del radar
  function filasRadar(jug) {
    const orden = jug.ordenSecciones || [];
    const secs = [...D.ordenRadar.filter((s) => orden.includes(s)), ...orden.filter((s) => !D.ordenRadar.includes(s))];
    const filas = [];
    secs.forEach((s) => (jug.secciones[s] || []).forEach(([m, v, max, tipo, contra, prom]) =>
      filas.push({ sec: s, m, v, max, tipo, contra, prom })));
    return { secs, filas };
  }

  // ------------------------------------------------------------------ radar (estilo PyPizza)
  function radar(g, ctx, filas, cfg, modo) {
    const { t, path, circ, ancho } = g;
    const { cx, cy, r } = cfg;
    const N = filas.length;
    const paso = (2 * Math.PI) / N;
    const r0 = modo === 'jugador' ? r * (20 / 120) : r * 0.06;   // inner_circle_size
    const frac = (v, max) => (v != null && max) ? Math.max(0, Math.min(1, v / max)) : 0;
    const rad = (fr) => r0 + (r - r0) * fr;
    const colores = coloresPorTercios(N);
    const bold = ctx.f.bold;

    const valorEnCaja = (txt, a, rr, fondo, size = 6.2) => {
      const w = ancho(txt, bold, size) + 4.4, h = size + 3.2;
      const [x, y] = pt(cx, cy, rr, a);
      path(caja(x - w / 2, y - h / 2, w, h, 1.6), { color: hex(fondo), border: C.navy, bw: 0.45 });
      t(txt, x, y + size * 0.36, { font: bold, size, color: claro(fondo) ? C.navy : BLANCO, align: 'center' });
      return h;
    };

    if (modo === 'jugador') {
      filas.forEach((f, i) => {
        const a0 = i * paso, a1 = a0 + paso, col = hex(colores[i]);
        path(gajo(cx, cy, r0, r, a0, a1), { color: col, opacity: 0.4 });                  // máximo (blank_alpha 0.4)
        const fr = frac(f.v, f.max);
        if (fr > 0) path(gajo(cx, cy, r0, rad(fr), a0, a1), { color: col });               // valor del jugador
      });
      // separadores entre gajos (edgecolor #F2F2F2)
      for (let i = 0; i < N; i++) {
        const [x0, y0] = pt(cx, cy, r0, i * paso), [x1, y1] = pt(cx, cy, r, i * paso);
        g.l(x0, y0, x1, y1, hex('#F2F2F2'), 1);
      }
      filas.forEach((f, i) => {
        const a = i * paso + paso / 2, fr = frac(f.v, f.max);
        valorEnCaja(fmtV(f.v, f.tipo), a, Math.min(Math.max(rad(fr), r0 + 11), r - 5), colores[i]);
      });
    } else {
      const L = hex(D.lineasComparativo);
      filas.forEach((f, i) => {
        const a0 = i * paso, a1 = a0 + paso;
        const fj = frac(f.v, f.max), fp = frac(f.prom, f.max);
        const capas = [[fj, hex(D.jugador)], [fp, hex(D.promedio)]].sort((x, y) => y[0] - x[0]);
        capas.forEach(([fr, col]) => { if (fr > 0) path(gajo(cx, cy, r0, rad(fr), a0, a1), { color: col, border: L, bw: 0.6 }); });
      });
      // rejilla: líneas rectas, círculos punteados y el último círculo
      for (let i = 0; i < N; i++) {
        const [x0, y0] = pt(cx, cy, r0, i * paso), [x1, y1] = pt(cx, cy, r, i * paso);
        g.l(x0, y0, x1, y1, L, 0.6);
      }
      [0.25, 0.5, 0.75].forEach((k) => circ(cx, cy, rad(k), { border: L, bw: 0.5, dash: [3, 1.5, 0.8, 1.5] }));
      circ(cx, cy, r, { border: L, bw: 0.8 });
      // valor del jugador en caja azul (el promedio va escrito junto al nombre de la stat)
      filas.forEach((f, i) => {
        const a = i * paso + paso / 2;
        valorEnCaja(fmtV(f.v, f.tipo), a, Math.min(Math.max(rad(frac(f.v, f.max)), r0 + 11), r - 5), D.jugadorCaja);
      });
    }

    // nombres de las stats alrededor, girados siguiendo el círculo (como PyPizza);
    // en la mitad de abajo se voltean para que se lean derechos
    const size = 5, lh = 6;
    const maxW = Math.max(28, ((2 * Math.PI * (r + 8)) / N) * 0.95);   // ancho del sector a esa altura
    const envolver = (txt) => {
      const out = [];
      txt.split(' ').forEach((p) => {
        const prev = out.length ? out[out.length - 1] : null;
        if (prev !== null && ancho(prev + ' ' + p, ctx.f.reg, size) <= maxW) out[out.length - 1] = prev + ' ' + p;
        else out.push(p);
      });
      return out;
    };
    filas.forEach((f, i) => {
      const a = i * paso + paso / 2;
      const lineas = envolver(f.m);
      const n = lineas.length;
      const aDeg = (a * 180) / Math.PI;
      const rot = -aDeg + (aDeg > 90 && aDeg < 270 ? 180 : 0);
      const th = (rot * Math.PI) / 180;
      const [bx, by] = pt(cx, cy, r + 5 + (n * lh) / 2, a);          // centro del bloque de texto
      lineas.forEach((s, k) => {
        const d = ((n - 1) / 2 - k) * lh;                              // renglón 1 arriba, renglón 2 abajo
        const sz = Math.min(size, size * maxW / Math.max(1, ancho(s, ctx.f.reg, size)) );
        g.tr(s, bx - Math.sin(th) * d, by - Math.cos(th) * d, rot, { size: Math.max(4.8, sz), color: C.ink });
      });
    });
  }

  function leyenda(g, ctx, cx, y, items) {
    const { t, r, ancho } = g;
    const size = 6.6, gap = 12;
    const total = items.reduce((a, [s]) => a + 10 + ancho(s, ctx.f.reg, size), 0) + gap * (items.length - 1);
    let x = cx - total / 2;
    items.forEach(([s, col]) => {
      r(x, y - 6.2, 7, 7, hex(col));
      x += 10;
      x += t(s, x, y, { size, color: C.soft }) + gap;
    });
  }

  // ------------------------------------------------------------------ canchita por cuartos
  function cancha(g, ctx, x, y, w, h, titulo, vals, tipo, etiquetas) {
    const { t, r, l, path, circ } = g;
    const B = BLANCO;
    r(x, y, w, h, C.cancha);
    r(x, y, w, h, undefined, { border: B, bw: 0.8 });
    const q = h / 4;
    for (let k = 1; k < 4; k++) l(x, y + k * q, x + w, y + k * q, B, k === 2 ? 0.7 : 0.5, k === 2 ? undefined : [2.5, 1.8]);
    const aw = w * 0.59, ah = h * 0.157;   // áreas (40.32/68, 16.5/105)
    r(x + (w - aw) / 2, y, aw, ah, undefined, { border: B, bw: 0.5 });
    r(x + (w - aw) / 2, y + h - ah, aw, ah, undefined, { border: B, bw: 0.5 });
    circ(x + w / 2, y + h / 2, w * 0.135, { border: B, bw: 0.5 });
    // 4/4 arriba (rival) ... 1/4 abajo (propio)
    vals.forEach((v, k) => {
      const yc = y + h - (k + 0.5) * q;
      let txt = '–';
      if (v !== null && v !== undefined) {
        txt = tipo === 'porcentaje' ? `${Math.round(v)}%`
          : tipo === 'balance' ? (v > 0 ? `+${fmtV(v)}` : fmtV(v)) : fmtV(v);
      }
      const size = 9.5, wt = g.ancho(txt, ctx.f.bold, size) + 6, ht = size + 3;
      path(caja(x + w / 2 - wt / 2, yc - ht / 2, wt, ht, 2), { color: hex('#0C2A4E'), opacity: 0.55 });
      t(txt, x + w / 2, yc + size * 0.36, { font: ctx.f.bold, size, color: B, align: 'center' });
      if (etiquetas) t(`${k + 1}/4`, x - 5, yc + 2.3, { size: 6.4, color: C.soft, align: 'right' });
    });
    t(titulo, x + w / 2, y - 5, { font: ctx.f.bold, size: 7, color: C.navy, align: 'center', maxW: w + 22 });
  }

  // ------------------------------------------------------------------ silueta gris (sin foto)
  function silueta(g, x, y, w, h) {
    const col = C.avatar;
    const s = Math.min(w, h * 0.8);
    const x0 = x + (w - s) / 2, base = y + h;
    g.circ(x0 + s / 2, base - s * 0.86, s * 0.21, { color: col });
    g.path(`M${f2(x0 + s * 0.08)},${f2(base)} V${f2(base - s * 0.2)} ` +
      `C${f2(x0 + s * 0.08)},${f2(base - s * 0.5)} ${f2(x0 + s * 0.28)},${f2(base - s * 0.58)} ${f2(x0 + s * 0.5)},${f2(base - s * 0.58)} ` +
      `C${f2(x0 + s * 0.72)},${f2(base - s * 0.58)} ${f2(x0 + s * 0.92)},${f2(base - s * 0.5)} ${f2(x0 + s * 0.92)},${f2(base - s * 0.2)} ` +
      `V${f2(base)} Z`, { color: col });
  }

  // ------------------------------------------------------------------ página
  async function pagina(ctx, jug, comp, meta) {
    const page = ctx.doc.addPage([P.w, P.h]);
    const g = mk(page, ctx);
    const { t, l } = g;
    const { f } = ctx;
    if (ctx.fondo) page.drawImage(ctx.fondo, { x: 0, y: 0, width: P.w, height: P.h });

    // ---------- foto (sin recuadro; el blanco de la foto se funde con el fondo)
    const F = D.foto;
    const foto = await img(ctx, jug.foto);
    if (foto) {
      const s = Math.min(F.w / foto.width, F.h / foto.height);
      const w = foto.width * s, h = foto.height * s;
      page.drawImage(foto, { x: F.x + (F.w - w) / 2, y: P.h - (F.y + F.h), width: w, height: h, blendMode: BlendMode.Multiply });
    } else silueta(g, F.x, F.y, F.w, F.h);

    // ---------- nombre y datos
    const Dt = D.datos;
    const nombre = (jug.nombre || '').toUpperCase();
    let size = 17;
    let lineas = [nombre];
    if (g.ancho(nombre, f.bold, size) > Dt.w) {
      lineas = partir(nombre, Math.ceil(nombre.length / 2));
      while (size > 11 && Math.max(...lineas.map((s) => g.ancho(s, f.bold, size))) > Dt.w) size -= 0.5;
    }
    let y = Dt.y;
    lineas.forEach((s) => { t(s, Dt.x, y, { font: f.bold, size, color: C.navy, maxW: Dt.w }); y += size * 1.08; });
    y += 3;
    t(jug.equipo || '', Dt.x, y, { size: 8, color: C.soft, maxW: Dt.w });
    y += 11;
    t([comp.label, jornadasTxt(comp)].filter(Boolean).join('  ·  ').toUpperCase(), Dt.x, y,
      { font: f.bold, size: 6.8, color: C.gold, maxW: Dt.w });
    if (jug.subido || (jug.tambienEn && jug.tambienEn.length)) {
      y += 10;
      t(jug.subido ? `Registrado en U${jug.categoria}` : `También con minutos en ${jug.tambienEn.join(', ')}`,
        Dt.x, y, { font: f.ital, size: 6.6, color: C.soft, maxW: Dt.w });
    }
    y += 18;
    [['Posición', jug.posicion], ['NUI', jug.nui], ['Edad', jug.edad != null ? `${jug.edad} años` : null]]
      .forEach(([lab, val]) => {
        t(lab, Dt.x, y, { size: 7, color: C.soft });
        t(val || '–', Dt.x + 44, y, { font: f.bold, size: 8.5, color: C.ink, maxW: Dt.w - 44 });
        y += 14;
      });

    // ---------- mapa de calor
    const M = D.mapa;
    t('MAPA DE CALOR', M.x + M.w / 2, M.y + 7, { font: f.bold, size: 7.5, color: C.navy, align: 'center' });
    const my = M.y + 14, mh = M.h - 14;
    const mapa = await img(ctx, jug.mapa);
    if (mapa) {
      const s = Math.min(M.w / mapa.width, mh / mapa.height);
      const w = mapa.width * s, h = mapa.height * s;
      page.drawImage(mapa, { x: M.x + (M.w - w) / 2, y: P.h - (my + (mh - h) / 2 + h), width: w, height: h });
    } else {
      t('Sin mapa de calor', M.x + M.w / 2, my + mh / 2, { font: f.ital, size: 8.5, color: C.faint, align: 'center' });
    }

    // ---------- estadísticas: minutos, partidos, % min. posibles + las stats del catálogo
    //   con % relacionado: % en grande y el dato crudo abajo; sin %: el dato crudo
    const Es = D.estadisticas;
    t('ESTADÍSTICAS', Es.x + Es.w / 2, Es.y + 7, { font: f.bold, size: 7.5, color: C.navy, align: 'center' });
    const maxMin = comp.jornadas ? (comp.jornadas[1] - comp.jornadas[0] + 1) * 90 : null;
    const inf = jug.informe || {};
    const ordenSec = filasRadar(jug).secs;
    const desglose = [...(inf.desglose || [])].sort((a, b) => ordenSec.indexOf(a[0]) - ordenSec.indexOf(b[0]));
    const datos = [
      ['Minutos', jug.minutos.toLocaleString('es-MX'), null],
      ['Partidos', String(jug.partidos), null],
      ['% min. posibles', maxMin ? `${Math.round((jug.minutos / maxMin) * 100)}%` : '–', null],
      ...desglose.map(([, lab, v, tipo, crudo]) => [lab, fmtV(v, tipo), crudo != null ? fmtV(crudo) : null]),
    ];
    const nc = Es.columnas, cw = Es.w / nc;
    const filasEs = Math.ceil(datos.length / nc);
    const rh = Math.min(58, (Es.yFin - (Es.y + 16)) / filasEs);
    const big = Math.min(19, rh * 0.36);
    datos.forEach(([lab, val, crudo], k) => {
      const xc = Es.x + cw * (k % nc) + cw / 2;
      let y = Es.y + 16 + Math.floor(k / nc) * rh + big * 0.9;
      t(val, xc, y, { font: f.bold, size: big, color: C.gold, align: 'center', maxW: cw - 4, minSize: 9 });
      y += 7.5;
      if (crudo != null) { t(crudo, xc, y, { font: f.bold, size: 6.4, color: C.navy, align: 'center' }); y += 6.8; }
      partir(lab, 15).slice(0, 2).forEach((s) => {
        t(s, xc, y, { size: 5.8, color: C.soft, align: 'center', maxW: cw - 3, minSize: 4.8 });
        y += 6.4;
      });
    });

    // ---------- radares y canchitas
    const yL = D.yLeyenda;
    const { secs, filas } = filasRadar(jug);
    if (!jug.conDatos || !filas.length) {
      const msg = !jug.conDatos
        ? [`Sin minutos registrados en ${comp.label}${comp.jornadas ? ' (' + jornadasTxt(comp) + ')' : ''}.`,
          'No se cuenta con datos suficientes para un análisis estadístico.']
        : [`Sin catálogo de atributos para la posición "${jug.posicion}".`, ''];
      t(msg[0], P.w / 2, 350, { font: f.bold, size: 11, color: C.soft, align: 'center' });
      if (msg[1]) t(msg[1], P.w / 2, 368, { font: f.ital, size: 9.5, color: C.soft, align: 'center' });
    } else {
      const RJ = D.radarJugador, RP = D.radarPromedio;
      t(RJ.titulo, RJ.cx, 244, { font: f.bold, size: 8, color: C.navy, align: 'center' });
      radar(g, ctx, filas, RJ, 'jugador');
      const nSec = secs.length;
      leyenda(g, ctx, RJ.cx, yL, secs.slice(0, 3).map((s, k) => [s, D.tercios[k]]).slice(0, Math.max(1, Math.min(3, nSec))));
      t('Sector completo = máximo de la liga o de su grupo de posición; área coloreada = valor del jugador.', RJ.cx, yL + 11,
        { font: f.ital, size: 5.9, color: C.soft, align: 'center', maxW: 300 });

      t(`${RP.titulo} · ${comp.label}`.toUpperCase(), RP.cx, 244, { font: f.bold, size: 8, color: C.navy, align: 'center', maxW: 300 });
      radar(g, ctx, filas, RP, 'promedio');
      leyenda(g, ctx, RP.cx, yL, [['Jugador', D.jugador], ['Promedio', D.promedio]]);
      t(`Promedio de la liga o de su grupo de posición (jugadores con ${meta.minPromedio ?? 270}+ min); sector completo = máximo.`,
        RP.cx, yL + 11, { font: f.ital, size: 5.9, color: C.soft, align: 'center', maxW: 300 });

      const Ca = D.canchas;
      const zonas = inf.zonas || [];
      if (jug.posicion === 'Portero' || !zonas.length) {
        t(D.textoPorteros, P.w / 2, 360, { font: f.ital, size: 8.5, color: C.soft, align: 'center', maxW: 250 });
        if (jug.posicion !== 'Portero') { /* jugador de campo sin zonas: mismo espacio vacío */ }
      } else {
        zonas.slice(0, 6).forEach(([titulo, vals, tipo], k) => {
          const x = Ca.x + (k % 3) * Ca.dx, y0 = Ca.y + Math.floor(k / 3) * Ca.dy;
          cancha(g, ctx, x, y0, Ca.w, Ca.h, titulo, vals, tipo, k % 3 === 0);
        });
      }
    }

    // ---------- pie de página (debajo de la línea azul)
    t(`Fuente: ${D.fuente} · ${comp.label}${comp.jornadas ? ' · ' + jornadasTxt(comp) : ''} · Datos al ${meta.generado.split(' ')[0]}`,
      38, D.yPie, { size: 6.4, color: C.faint, maxW: 300 });
    t(D.credito, P.w - 38, D.yPie, { font: f.bold, size: 7, color: C.navy, align: 'right' });
  }

  async function generar(jugadores, comp, meta) {
    const ctx = await nuevoDoc();
    for (const j of jugadores) await pagina(ctx, j, comp, meta);
    return ctx.doc.save();
  }

  return { generar };
})();