/* =============================================================================
   ficha.js — dibuja la ficha en PDF tamaño carta (vectorial, con pdf-lib)
   Todo el diseño (colores, medidas, textos) está en DISENO.
   Unidades: puntos (1 pulgada = 72 pt). Carta = 612 x 792 pt.
   ========================================================================== */
const DISENO = {
  pagina: { w: 612, h: 792, margen: 36 },
  colores: {
    navy: '#0C2A4E', gold: '#B9902E', ink: '#12181E', soft: '#4B5560', faint: '#8B93A0',
    line: '#D5D9D2', track: '#E7E9E5', zebra: '#F6F7F4', placeholder: '#EEF0EC',
  },
  // Colores de la ficha = colores del club: barras azul marino, líneas de sección oro
  barra: '#0C2A4E',
  lineaSeccion: '#B9902E',
  foto: { x: 36, y: 112, w: 96, h: 120 },
  datos: { x: 146, w: 116 },      // columna "Datos del jugador"
  minutos: { x: 274, w: 106 },    // columna "Minutos de juego"
  mapa: { x: 396, y: 112, w: 180, h: 124 },
  secciones: { yIni: 254, yFin: 724, header: 24, gap: 6, filaMin: 14, filaMax: 22 },
  credito: 'Elaborado por Inteligencia Deportiva Pumas',
  fuente: 'GolStats',
};

const Ficha = (() => {
  const { rgb, StandardFonts, PDFDocument } = PDFLib;
  const P = DISENO.pagina;

  const hex = (h) => {
    const n = parseInt(h.slice(1), 16);
    return rgb(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255);
  };
  const C = Object.fromEntries(Object.entries(DISENO.colores).map(([k, v]) => [k, hex(v)]));

  // ------------------------------------------------------------------ recursos
  const cacheBytes = new Map();
  async function bytes(url) {
    if (!url) return null;
    if (!cacheBytes.has(url)) {
      cacheBytes.set(url, fetch(url).then(r => (r.ok ? r.arrayBuffer() : null)).catch(() => null));
    }
    return cacheBytes.get(url);
  }

  async function nuevoDoc() {
    const doc = await PDFDocument.create();
    doc.setTitle('Ficha de jugador — Pumas UNAM');
    doc.setAuthor('Inteligencia Deportiva Pumas');
    doc.setCreator('Fichas de Jugadores — Inteligencia Deportiva Pumas');
    const f = {
      reg: await doc.embedFont(StandardFonts.Helvetica),
      bold: await doc.embedFont(StandardFonts.HelveticaBold),
      ital: await doc.embedFont(StandardFonts.HelveticaOblique),
    };
    const logoB = await bytes('assets/logo.png');
    let logo = null;
    try { if (logoB) logo = await doc.embedPng(logoB); } catch (e) { logo = null; }
    return { doc, f, logo, imgs: new Map() };
  }

  async function img(ctx, url) {
    if (!url) return null;
    if (!ctx.imgs.has(url)) {
      const b = await bytes(url);
      let im = null;
      if (b) {
        try { im = await ctx.doc.embedJpg(b); }
        catch (e) { try { im = await ctx.doc.embedPng(b); } catch (e2) { im = null; } }
      }
      ctx.imgs.set(url, im);
    }
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

  // ------------------------------------------------------------------ primitivas (y = desde arriba)
  function mk(page, ctx) {
    const Y = (y) => P.h - y;
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
      page.drawText(s, { x: xx, y: Y(y), size, font, color: o.color || C.ink });
      return w;
    };
    const r = (x, y, w, h, color, o = {}) => page.drawRectangle({
      x, y: Y(y + h), width: w, height: h, color,
      borderColor: o.border, borderWidth: o.border ? (o.bw || 0.75) : 0,
    });
    const l = (x1, y1, x2, y2, color, th = 0.75) => page.drawLine({
      start: { x: x1, y: Y(y1) }, end: { x: x2, y: Y(y2) }, thickness: th, color,
    });
    const im = (image, x, y, w, h, contain) => {
      let dw = w, dh = h;
      if (contain) {
        const s = Math.min(w / image.width, h / image.height);
        dw = image.width * s; dh = image.height * s;
      }
      page.drawImage(image, { x: x + (w - dw) / 2, y: Y(y + (h - dh) / 2 + dh), width: dw, height: dh });
    };
    return { t, r, l, im };
  }

  // ------------------------------------------------------------------ formato
  const fmt = (v, tipo, modo) => {
    if (v === null || v === undefined) return '–';
    if (tipo === 'porcentaje') return `${(Math.round(v * 10) / 10).toString()}%`;
    if (modo === 'per90') return v.toFixed(2);
    return Number.isInteger(v) ? String(v) : v.toFixed(1);
  };
  const jornadasTxt = (comp) => (comp.jornadas ? `J${comp.jornadas[0]}–J${comp.jornadas[1]}` : '');

  // ------------------------------------------------------------------ página
  async function pagina(ctx, jug, comp, meta) {
    const page = ctx.doc.addPage([P.w, P.h]);
    const { t, r, l, im } = mk(page, ctx);
    const { f } = ctx;
    const M = P.margen, R = P.w - M;

    // ---------- encabezado: competencia, nombre y equipo (logo centrado con el bloque de texto)
    r(0, 0, P.w, 6, C.navy);
    r(0, 6, P.w, 2, hex(DISENO.colores.gold));
    let xT = M;
    if (ctx.logo) {
      const h = 54, w = ctx.logo.width * (h / ctx.logo.height);
      const yLogo = 58 - h / 2;   // 58 = centro vertical del bloque de texto (eyebrow 38 · nombre 64 · equipo 81)
      page.drawImage(ctx.logo, { x: M, y: P.h - yLogo - h, width: w, height: h });
      xT = M + w + 14;
    }
    const eyebrow = ['FICHA DE JUGADOR', comp.label, jornadasTxt(comp)].filter(Boolean).join('   ·   ');
    t(eyebrow.toUpperCase(), xT, 38, { font: f.bold, size: 8, color: C.gold, maxW: R - xT });
    t(jug.nombre.toUpperCase(), xT, 64, { font: f.bold, size: 24, color: C.navy, maxW: R - xT, minSize: 13 });
    // equipo de registro; si juega en una categoría superior o también tiene minutos en otra, se indica
    let lineaEquipo = jug.equipo || '';
    if (jug.subido) lineaEquipo += `   ·   Registrado en U${jug.categoria}, stats de ${comp.label}`;
    //else if (jug.tambienEn && jug.tambienEn.length) lineaEquipo += `   ·   También con minutos en ${jug.tambienEn.join(', ')}`;
    t(lineaEquipo, xT, 81, { size: 10, color: C.soft, maxW: R - xT, minSize: 7 });
    l(M, 96, R, 96, C.navy, 2);

    // ---------- foto
    const F = DISENO.foto;
    const foto = await img(ctx, jug.foto);
    if (foto) im(foto, F.x, F.y, F.w, F.h, false);
    else {
      r(F.x, F.y, F.w, F.h, C.placeholder);
      t('Sin foto', F.x + F.w / 2, F.y + F.h / 2 + 3, { size: 9, color: C.faint, align: 'center', font: f.ital });
    }
    r(F.x, F.y, F.w, F.h, undefined, { border: C.navy, bw: 1 });

    // ---------- datos (etiqueta chica arriba, valor en negritas abajo)
    const titulo = (txt, x, w, y0) => {
      t(txt, x, y0 + 6, { font: f.bold, size: 8, color: C.navy, maxW: w });
      l(x, y0 + 10, x + w, y0 + 10, hex(DISENO.colores.gold), 1.2);
    };
    const bloque = (txt, col, filas) => {
      titulo(txt, col.x, col.w, F.y);
      let y = F.y + 22;
      for (const [lab, val] of filas) {
        t(lab, col.x, y, { size: 7, color: C.soft, maxW: col.w });
        t(val ?? '–', col.x, y + 11.5, { font: f.bold, size: 10.5, color: C.ink, maxW: col.w, minSize: 7 });
        y += 24.5;
      }
    };
    const maxMin = comp.jornadas ? (comp.jornadas[1] - comp.jornadas[0] + 1) * 90 : null;
    bloque('DATOS DEL JUGADOR', DISENO.datos, [
      ['NUI', jug.nui],
      ['Posición', jug.posicion],
      ['Edad', jug.edad != null ? `${jug.edad} años` : null],
      ['Fecha de nacimiento', jug.nacimiento],
    ]);
    bloque('MINUTOS DE JUEGO', DISENO.minutos, [
      ['Minutos jugados', jug.minutos.toLocaleString('es-MX')],
      ['Partidos jugados', String(jug.partidos)],
      ['Minutos por partido', jug.partidos ? String(Math.round(jug.minutos / jug.partidos)) : null],
      [maxMin ? `% min. posibles (${jornadasTxt(comp)})` : '% de minutos posibles',
        maxMin ? `${Math.round((jug.minutos / maxMin) * 100)}%` : null],
    ]);

    // ---------- mapa de calor
    const Mp = DISENO.mapa;
    titulo('MAPA DE CALOR', Mp.x, Mp.w, Mp.y);
    const my = Mp.y + 16, mh = Mp.h - 16;
    const mapa = await img(ctx, jug.mapa);
    if (mapa) im(mapa, Mp.x, my, Mp.w, mh, true);
    else {
      r(Mp.x, my, Mp.w, mh, C.placeholder);
      t('Sin mapa de calor', Mp.x + Mp.w / 2, my + mh / 2 + 3, { size: 9, color: C.faint, align: 'center', font: f.ital });
    }

    // ---------- secciones con barras
    const S = DISENO.secciones;
    const secs = meta.secciones.map(s => [s, (jug.secciones && jug.secciones[s]) || []]);
    const nFilas = secs.reduce((a, [, fs]) => a + fs.length, 0);
    let yy = S.yIni;
    if (!nFilas) {
      const aviso = !jug.conDatos
        ? `Sin minutos registrados en ${comp.label}${comp.jornadas ? ' (' + jornadasTxt(comp) + ')' : ''}.`
        : `Sin catálogo de atributos para la posición "${jug.posicion}".`;
      r(M, yy, R - M, 60, C.placeholder);
      t(aviso, P.w / 2, yy + 34, { size: 10, color: C.soft, align: 'center', font: f.ital });
    } else {
      const disp = S.yFin - S.yIni - secs.length * (S.header + S.gap);
      const fh = Math.max(S.filaMin, Math.min(S.filaMax, disp / nFilas));
      const xLab = M + 6, xVal = 262, xBar = 272, xBarEnd = 530, xMax = 538;
      for (const [sec, filas] of secs) {
        const col = hex(DISENO.barra), colLinea = hex(DISENO.lineaSeccion);
        // título centrado con líneas a los lados
        const titulo = sec.toUpperCase();
        const tw = f.bold.widthOfTextAtSize(limpio(f.bold, titulo), 10.5);
        const yc = yy + 12;
        l(M, yc - 3.5, P.w / 2 - tw / 2 - 10, yc - 3.5, colLinea, 1.4);
        l(P.w / 2 + tw / 2 + 10, yc - 3.5, R, yc - 3.5, colLinea, 1.4);
        t(titulo, P.w / 2, yc, { font: f.bold, size: 10.5, color: C.navy, align: 'center' });
        yy += S.header;
        if (!filas.length) {
          t('Sin atributos en esta sección para la posición.', P.w / 2, yy + 10, { size: 8.5, color: C.faint, align: 'center', font: f.ital });
          yy += 16 + S.gap;
          continue;
        }
        const size = Math.min(9.5, fh * 0.6);
        const bh = Math.min(10, fh * 0.52);
        filas.forEach(([nombre, val, max, tipo], i) => {
          if (i % 2 === 0) r(M, yy, R - M, fh, C.zebra);
          const base = yy + fh / 2 + size * 0.35;
          t(nombre, xLab, base, { size, maxW: xVal - xLab - 44 });
          t(fmt(val, tipo, meta.modo), xVal, base, { font: f.bold, size: size + 0.5, align: 'right' });
          const by = yy + (fh - bh) / 2;
          r(xBar, by, xBarEnd - xBar, bh, C.track);
          const frac = (val != null && max) ? Math.max(0, Math.min(1, val / max)) : 0;
          if (frac > 0) r(xBar, by, (xBarEnd - xBar) * frac, bh, col);
          t(max != null ? `máx ${fmt(max, tipo, meta.modo)}` : '', xMax, base, { size: Math.min(7.5, size - 1), color: C.faint });
          yy += fh;
        });
        yy += S.gap;
      }
    }

    // ---------- pie de página (el crédito va hasta el final)
    const yp = 734;
    l(M, yp, R, yp, C.line, 0.75);
    t(`Fuente: ${DISENO.fuente} · ${comp.label}${comp.jornadas ? ' · ' + jornadasTxt(comp) : ''}`, M, yp + 12,
      { size: 7, color: C.faint, maxW: 250 });
    t(`Datos al ${meta.generado.split(' ')[0]}`, R, yp + 12, { size: 7, color: C.faint, align: 'right' });
    const modoTxt = meta.modo === 'per90' ? 'valores por 90 minutos' : 'valores totales';
    t(`Barra: valor del jugador respecto al máximo de toda la liga (${modoTxt}).`, M, yp + 24,
      { size: 7, color: C.faint });
    t(DISENO.credito, P.w / 2, yp + 38, { font: f.bold, size: 8.5, color: C.navy, align: 'center' });
  }

  async function generar(jugadores, comp, meta) {
    const ctx = await nuevoDoc();
    for (const j of jugadores) await pagina(ctx, j, comp, meta);
    return ctx.doc.save();
  }

  return { generar };
})();
