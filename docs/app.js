/* app.js — filtros, lista de jugadores, vista previa y descargas */
(() => {
  const D = window.FICHAS;
  const $ = (id) => document.getElementById(id);
  const selComp = $('selComp'), selPos = $('selPos'), selReg = $('selReg'), txt = $('txtBuscar');
  const lista = $('lista'), count = $('count'), status = $('status');
  const btnPdf = $('btnPdf'), btnEquipo = $('btnEquipo'), frame = $('preview'), empty = $('empty');

  if (!D || !D.competencias || !D.competencias.length) {
    empty.textContent = 'No hay datos cargados. Corre actualizar.bat para generarlos.';
    return;
  }
  $('meta').innerHTML = `Datos actualizados<br><b>${D.generado}</b>`;

  const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const nombreArchivo = (s) => norm(s).replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  const opt = (v, t) => { const o = document.createElement('option'); o.value = v; o.textContent = t; return o; };

  let comp = null, actual = null, urlPrev = null, ocupado = false;

  D.competencias.forEach((c) => selComp.appendChild(
    opt(c.id, c.label + (c.jornadas ? ` · J${c.jornadas[0]}–J${c.jornadas[1]}` : ''))));

  function cargarComp() {
    comp = D.competencias.find((c) => c.id === selComp.value) || D.competencias[0];
    const pos = [...new Set(comp.jugadores.map((j) => j.posicion || 'Sin posición'))].sort((a, b) => a.localeCompare(b, 'es'));
    const posPrev = selPos.value;
    selPos.innerHTML = '';
    selPos.appendChild(opt('', 'Todas'));
    pos.forEach((p) => selPos.appendChild(opt(p, p)));
    if (pos.includes(posPrev)) selPos.value = posPrev;
    // filtro de registro: propios de la categoría / de otras categorías con minutos aquí
    const regPrev = selReg.value;
    const hayInferiores = comp.jugadores.some((j) => j.subido);
    selReg.innerHTML = '';
    selReg.appendChild(opt('', 'Todos'));
    selReg.appendChild(opt('reg', `Registrados en U${comp.categoria}`));
    if (hayInferiores) selReg.appendChild(opt('sub', 'De otra categoría con minutos aquí'));
    selReg.parentElement.style.display = hayInferiores ? '' : 'none';
    if ([...selReg.options].some((o) => o.value === regPrev)) selReg.value = regPrev;
    pintarLista();
  }

  function filtrados() {
    const q = norm(txt.value.trim());
    return comp.jugadores.filter((j) =>
      (!selPos.value || (j.posicion || 'Sin posición') === selPos.value) &&
      (!selReg.value || (selReg.value === 'sub') === !!j.subido) &&
      (!q || norm(j.nombre).includes(q) || String(j.nui || '').includes(q)));
  }

  function pintarLista() {
    const js = filtrados();
    lista.innerHTML = '';
    const frag = document.createDocumentFragment();
    let grupo = false;
    js.forEach((j) => {
      if (j.subido && !grupo) {
        grupo = true;
        const h = document.createElement('li');
        h.className = 'grupo';
        h.textContent = `Registrados en otra categoría con minutos en U${comp.categoria}`;
        frag.appendChild(h);
      }
      const li = document.createElement('li');
      li.dataset.id = j.id;
      if (actual && actual.id === j.id) li.classList.add('sel');
      li.innerHTML = `<span class="n"></span><span class="m"></span><span class="e"></span>`;
      li.querySelector('.n').textContent = j.nombre;
      li.querySelector('.m').textContent = `${j.minutos.toLocaleString('es-MX')} min`;
      li.querySelector('.e').textContent = `${j.posicion || 'Sin posición'}${j.nui ? ' · NUI ' + j.nui : ''}`;
      const tags = [];
      if (j.subido) tags.push(['U' + j.categoria, 'sube']);
      if (!j.conDatos) tags.push(['Sin minutos', 'cero']);
      (j.tambienEn || []).forEach((t) => tags.push(['También en ' + t.replace(/^Liga MX\s*/i, ''), 'tb']));
      tags.forEach(([t, c]) => {
        const b = document.createElement('span'); b.className = 'tag ' + c; b.textContent = t;
        li.querySelector('.e').appendChild(b);
      });
      li.addEventListener('click', () => seleccionar(j));
      frag.appendChild(li);
    });
    lista.appendChild(frag);
    count.textContent = `${js.length} jugador${js.length === 1 ? '' : 'es'}`;
    if (!js.length) { const v = document.createElement('li'); v.className = 'grupo'; v.textContent = 'Sin resultados'; lista.appendChild(v); }
    btnEquipo.disabled = !js.length;
    btnEquipo.title = `Un PDF con las ${js.length} fichas de la lista (respeta filtros)`;
  }

  async function seleccionar(j) {
    actual = j;
    document.querySelectorAll('#lista li').forEach((li) => li.classList.toggle('sel', li.dataset.id === j.id));
    $('titulo').textContent = j.nombre;
    $('subtitulo').textContent = [j.equipo, j.posicion, `${j.minutos.toLocaleString('es-MX')} min en ${comp.label}`]
      .filter(Boolean).join(' · ');
    btnPdf.disabled = false;
    const u = new URL(location.href);
    u.searchParams.set('c', comp.id); u.searchParams.set('j', j.id);
    history.replaceState(null, '', u);
    status.textContent = 'Generando vista previa…';
    try {
      const bytes = await Ficha.generar([j], comp, D);
      if (actual !== j) return;
      if (urlPrev) URL.revokeObjectURL(urlPrev);
      urlPrev = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      frame.src = urlPrev + '#toolbar=0&navpanes=0&view=Fit';
      empty.style.display = 'none';
      status.textContent = '';
    } catch (e) {
      console.error(e);
      status.textContent = 'Error al generar la ficha: ' + e.message;
    }
  }

  function descargar(bytes, nombre) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
    a.download = nombre;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  btnPdf.addEventListener('click', async () => {
    if (!actual || ocupado) return;
    ocupado = true; btnPdf.disabled = true;
    try {
      const bytes = await Ficha.generar([actual], comp, D);
      descargar(bytes, `Ficha_${nombreArchivo(actual.nombre)}_${nombreArchivo(comp.label)}.pdf`);
    } catch (e) { status.textContent = 'Error: ' + e.message; }
    ocupado = false; btnPdf.disabled = false;
  });

  btnEquipo.addEventListener('click', async () => {
    const js = filtrados();
    if (!js.length || ocupado) return;
    ocupado = true; btnEquipo.disabled = true;
    status.textContent = `Generando ${js.length} fichas…`;
    try {
      const bytes = await Ficha.generar(js, comp, D);
      descargar(bytes, `Fichas_Pumas_${nombreArchivo(comp.label)}${selPos.value ? '_' + nombreArchivo(selPos.value) : ''}.pdf`);
      status.textContent = `Listo: ${js.length} fichas.`;
    } catch (e) { status.textContent = 'Error: ' + e.message; }
    ocupado = false; btnEquipo.disabled = false;
  });

  selComp.addEventListener('change', () => { actual = null; cargarComp(); });
  selPos.addEventListener('change', pintarLista);
  selReg.addEventListener('change', pintarLista);
  txt.addEventListener('input', pintarLista);

  // enlace directo: ?c=<competencia>&j=<jugador>
  const qs = new URLSearchParams(location.search);
  if (qs.get('c') && D.competencias.some((c) => c.id === qs.get('c'))) selComp.value = qs.get('c');
  cargarComp();
  const pre = qs.get('j') && comp.jugadores.find((j) => j.id === qs.get('j'));
  if (pre) seleccionar(pre);
})();
