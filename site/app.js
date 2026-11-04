/* VIGIA-Dengue — o boletim no navegador.
 *
 * Lê dados/painel.json (gerado por src/vigia/exportar_site.py no build) e
 * desenha as oito seções. JavaScript puro, sem framework: gráficos e mapas são
 * SVG montados aqui, com os rótulos em HTML por cima para continuarem
 * legíveis em qualquer largura de tela.
 *
 * Regra da casa: nenhum número fixo no texto. Tudo que a página afirma vem
 * do JSON da semana.
 */
"use strict";
(function () {

const COD_FOCO = 5300108;
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const TELAS = [
  ["panorama", "Panorama"], ["mapa", "Mapa e municípios"], ["series", "Séries temporais"],
  ["ranking", "Ranking"], ["modelo", "Desempenho"], ["ras", "Por RA"],
  ["clima", "Alarmes e clima"], ["dicionario", "Dicionário"],
];
const ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
const COR_RISCO = {
  "baixo": "var(--color-accent-200)", "moderado": "var(--color-accent-400)",
  "alto": "var(--color-accent-600)", "muito alto": "var(--color-accent-800)",
};
const MODELOS = {
  Combinado: { nome: "Combinado (em operação)", cor: "var(--color-accent-700)", w: 2.6, dash: "none" },
  LightGBM: { nome: "Aprendizado (LightGBM)", cor: "var(--color-accent-400)", w: 1.6, dash: "6 4" },
  Logistica: { nome: "Interpretável (logística)", cor: "var(--color-neutral-600)", w: 1.4, dash: "3 3" },
  Referencia: { nome: "Referência (persistência)", cor: "var(--color-neutral-500)", w: 1.4, dash: "1 4" },
};
// Faixa térmica favorável ao Aedes aegypti, a mesma régua da base analítica,
// e o corte de "chuva frequente" na janela de 14 dias.
const FAIXA_AEDES = [21, 32];
const DIAS_CHUVA_FREQUENTE = 7;
const ORDEM_PAPEL = ["preditor essencial", "preditor", "origem do alvo", "apoio"];

const S = {
  tela: "panorama", periodo: 52, ordem: "prob", busca: "", ind: "vul",
  sel: COD_FOCO, medida: "casos", dicBusca: "", dicBloco: "", dicPapel: "",
};
let D = null, RIDE = null, RAS = null;
const GRAF = {};          // metadados dos gráficos, para a dica ao passar o cursor
const DICA_MAPA = {};     // conteúdo da dica de cada polígono

// ---------------------------------------------------------------- formatos
const fmt = (v, c = 0) => (v == null || !isFinite(v)) ? "—"
  : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
const pct = v => (v == null || !isFinite(v)) ? "—" : Math.round(v * 100) + "%";
const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const dia = d => new Date(d + "T12:00:00");
const mesAno = d => MESES[+d.slice(5, 7) - 1] + "/" + d.slice(2, 4);
const diaMes = d => d.slice(8, 10) + "/" + d.slice(5, 7);
const diaMesAno = d => d.slice(8, 10) + "/" + d.slice(5, 7) + "/" + d.slice(0, 4);
const rotSemana = se => String(se % 100).padStart(2, "0") + "/" + Math.floor(se / 100);
const estreita = () => window.innerWidth <= 640;
const porCod = cod => D.municipios.find(m => m.cod === cod);
const sinal = v => v == null ? "—" : v === 0 ? "igual" : (v > 0 ? "+" : "−") + Math.abs(v) + "%";

function periodoSemana(inicio) {
  const a = dia(inicio), b = new Date(a.getTime() + 6 * 864e5);
  if (a.getMonth() === b.getMonth()) {
    return `${a.getDate()} a ${b.getDate()} de ${MESES[b.getMonth()]}. de ${b.getFullYear()}`;
  }
  return `${a.getDate()} de ${MESES[a.getMonth()]}. a ${b.getDate()} de ${MESES[b.getMonth()]}. de ${b.getFullYear()}`;
}
function redondo(v) {
  if (!(v > 0)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
}

// ---------------------------------------------------------------- gráfico
// Linhas sobre grade horizontal. Os rótulos ficam em HTML, posicionados em
// porcentagem do viewBox, para não encolher junto com o SVG no celular.
function grafico(id, rot, linhas, o) {
  // No celular o gráfico ganha proporção mais alta: na largura de um telefone,
  // 760 × 280 viraria uma faixa de 130 px, sem espaço para os rótulos.
  const movel = estreita();
  const W = movel ? 380 : (o.W || 760), H = movel ? Math.max(260, Math.round((o.H || 280) * 0.95)) : (o.H || 280);
  const L = movel ? 40 : (o.L || 54), R = movel ? 10 : 18, T = 16, B = 30;
  const n = rot.length, iw = W - L - R, ih = H - T - B, min = o.min || 0, max = o.max;
  const px = i => L + (n < 2 ? iw / 2 : i / (n - 1) * iw);
  const py = v => T + ih - ((v - min) / (max - min || 1)) * ih;
  const caminho = vs => {
    let d = "", pena = false;
    vs.forEach((v, i) => {
      if (v == null || !isFinite(v)) { pena = false; return; }
      d += (pena ? "L" : "M") + px(i).toFixed(1) + " " + py(v).toFixed(1);
      pena = true;
    });
    return d;
  };
  const pctX = x => (x / W * 100).toFixed(2) + "%", pctY = y => (y / H * 100).toFixed(2) + "%";
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.titulo || "")}">`;
  let rotulos = "";
  const nt = o.nt || 4, fy = o.fy || (v => fmt(v));
  for (let k = 0; k <= nt; k++) {
    const v = min + (max - min) * k / nt, y = py(v);
    svg += `<line x1="${L}" x2="${W - R}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--color-divider)" stroke-width="1"/>`;
    rotulos += `<div class="g-rot y" style="left:${pctX(L - 10)};top:${pctY(y)}">${fy(v)}</div>`;
  }
  if (o.limiar != null) {
    const y = py(o.limiar).toFixed(1);
    svg += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="var(--color-text)" stroke-width="1" stroke-dasharray="5 4" opacity=".55"/>`;
  }
  if (o.hi) {
    let d = caminho(o.hi);
    for (let i = n - 1; i >= 0; i--) d += "L" + px(i).toFixed(1) + " " + py(o.lo[i]).toFixed(1);
    svg += `<path d="${d}Z" fill="var(--color-accent-200)" opacity=".85" stroke="none"/>`;
  }
  linhas.forEach(l => {
    svg += `<path d="${caminho(l.v)}" fill="none" stroke="${l.cor}" stroke-width="${l.w}" stroke-dasharray="${l.dash || "none"}" stroke-linejoin="round" stroke-linecap="round"/>`;
  });
  if (o.valores) {
    const l = linhas[0];
    l.v.forEach((v, i) => {
      if (v == null) return;
      const ultimo = i === n - 1;
      svg += `<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="${ultimo ? 5 : 3}" fill="${ultimo ? "var(--color-bg)" : l.cor}" stroke="${l.cor}" stroke-width="${ultimo ? 2 : 1}"/>`;
      rotulos += `<div class="g-rot valor" style="left:${pctX(px(i))};top:${pctY(py(v))}">${o.valores(v)}</div>`;
    });
  } else if (o.ponto) {
    const l = linhas[0], v = l.v[n - 1];
    if (v != null) svg += `<circle cx="${px(n - 1).toFixed(1)}" cy="${py(v).toFixed(1)}" r="4" fill="var(--color-bg)" stroke="${l.cor}" stroke-width="1.6"/>`;
  }
  svg += "</svg>";
  const passo = o.passo || Math.max(1, Math.ceil(n / 6));
  for (let i = 0; i < n; i += passo) {
    rotulos += `<div class="g-rot x" style="left:${pctX(px(i))};top:${pctY(H - 8)}">${esc(rot[i])}</div>`;
  }
  if (o.dica) GRAF[id] = { W, H, T, ih, L, iw, n, dica: o.dica };
  return `<div class="grafico" data-g="${id}">${svg}${rotulos}<div class="g-guia"></div><div class="g-dica"></div></div>`;
}

// ------------------------------------------------------------------ mapas
function projetar(geo, W, H) {
  let minX = 180, maxX = -180, minY = 90, maxY = -90;
  const itens = [];
  geo.features.forEach(f => {
    const aneis = [], g = f.geometry;
    const anda = (c, p) => {
      if (p === 0) {
        c.forEach(([x, y]) => {
          if (x < minX) minX = x; if (x > maxX) maxX = x;
          if (y < minY) minY = y; if (y > maxY) maxY = y;
        });
        aneis.push(c); return;
      }
      c.forEach(k => anda(k, p - 1));
    };
    if (g.type === "Polygon") anda(g.coordinates, 1);
    else if (g.type === "MultiPolygon") anda(g.coordinates, 2);
    itens.push({ props: f.properties, aneis });
  });
  const k = Math.cos((minY + maxY) / 2 * Math.PI / 180);
  const lw = (maxX - minX) * k, lh = maxY - minY, e = Math.min(W / lw, H / lh) * 0.96;
  const ox = (W - lw * e) / 2, oy = (H - lh * e) / 2;
  const pr = ([x, y]) => [ox + (x - minX) * k * e, oy + (maxY - y) * e];
  return itens.map(it => {
    let sx = 0, sy = 0, c = 0;
    const d = it.aneis.map(a => a.map((p, i) => {
      const q = pr(p); sx += q[0]; sy += q[1]; c++;
      return (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1);
    }).join("") + "Z").join("");
    return { props: it.props, d, cx: sx / c, cy: sy / c };
  });
}

// ------------------------------------------------------------ pedaços
const cabeca = (num, titulo, texto) => `
  <div class="cabeca">
    <div class="rotulo">${num}</div>
    <h2 class="titulo-2">${titulo}</h2>
    ${texto ? `<p class="texto justo">${texto}</p>` : ""}
  </div>`;
const seg = (acao, atual, opcoes) => `<div class="seg" role="group">${opcoes.map(([v, r]) =>
  `<button type="button" class="seg-opt" data-acao="${acao}" data-valor="${v}" aria-pressed="${String(v) === String(atual)}">${r}</button>`).join("")}</div>`;
const linhaValor = (rot, val) => `<div class="linha"><span>${rot}</span><span>${val}</span></div>`;
const barraProb = (p, fina) => `<div class="barra-prob${fina ? " fina" : ""}"><b style="width:${((p || 0) * 100).toFixed(1)}%"></b><s style="left:${(D.limiar * 100).toFixed(1)}%"></s></div>`;
const listaFatores = fs => fs.length ? fs.join(", ") : "sem fator dominante";

// ============================================================== I PANORAMA
function vistaPanorama() {
  const f = D.foco, h = D.horizonte, lim = D.limiar, emAlerta = f.prob >= lim;
  const variacao = f.variacao == null ? "" : f.variacao === 0
    ? ", o mesmo número da semana anterior"
    : `, ${Math.abs(f.variacao)}% ${f.variacao < 0 ? "a menos" : "a mais"} que na semana anterior`;
  const lede = `Nesta semana, estima-se que Brasília teve ${fmt(f.est)} casos de dengue, o equivalente a ${fmt(f.inc, 1)} por 100 mil habitantes${variacao}. O modelo calcula ${pct(f.prob)} de chance de o risco chegar a alto ou muito alto nas próximas ${h} semanas, ${emAlerta ? "acima" : "abaixo"} do limiar de alerta de ${pct(lim)}.`;

  const nEntorno = D.entorno.emAlerta;
  const entornoFrase = nEntorno === 0 ? "Nenhum município do Entorno passou do limiar."
    : nEntorno === 1 ? "1 município do Entorno passou do limiar."
      : `${nEntorno} municípios do Entorno passaram do limiar.`;
  const alertaFrase = emAlerta
    ? `Brasília está em alerta: ${pct(f.prob)} de chance de risco alto ou muito alto em ${h} semanas. Pesaram mais: ${listaFatores(f.fatores)}.`
    : `Brasília não está em alerta nesta semana. ${entornoFrase}`;

  const escala = D.ordemRisco.map(r => `<div class="${r === f.risco ? "atual" : ""}"><i style="background:${COR_RISCO[r]}"></i>${cap(r)}</div>`).join("");
  const s = D.serie.slice(-S.periodo);
  const est = s.map(p => p.e), hi = s.map(p => p.hi == null ? p.e : p.hi), lo = s.map(p => p.lo == null ? p.e : p.lo);
  const max = redondo(Math.max(...hi.concat(est).filter(v => v != null)) * 1.05);
  const casos = grafico("casos", s.map(p => mesAno(p.d)), [
    { v: est, cor: "var(--color-accent-800)", w: 2 },
    { v: s.map(p => p.n), cor: "var(--color-neutral-600)", w: 1.2, dash: "4 4" },
  ], {
    max, hi, lo, ponto: true, titulo: "Casos estimados de dengue em Brasília por semana",
    passo: Math.ceil(s.length / (estreita() ? 4 : 6)),
    dica: i => `<strong>semana de ${diaMesAno(s[i].d)}</strong>${fmt(s[i].e)} casos estimados<br>${fmt(s[i].n)} notificados${lo[i] !== hi[i] ? `<br><span class="mudo">margem: ${fmt(lo[i])} a ${fmt(hi[i])}</span>` : ""}`,
  });

  return `<section class="secao">
    <div class="cabeca">
      <div class="rotulo">I · Panorama de Brasília</div>
      <h1 class="titulo-1">Dengue em Brasília: risco ${esc(f.risco)}</h1>
      <p class="lede justo">${lede}</p>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="rotulo">Casos estimados</div><div class="kpi-valor">${fmt(f.est)}</div>
        <div class="kpi-nota">${sinal(f.variacao)} frente à semana anterior · ${fmt(f.casos)} já notificados</div></div>
      <div class="kpi"><div class="rotulo">Incidência</div><div class="kpi-valor">${fmt(f.inc, 1)}</div>
        <div class="kpi-nota">casos por 100 mil habitantes${f.canalQ3 != null ? ` · o esperado para a época vai até ${fmt(f.canalQ3, 1)}` : ""}</div></div>
      <div class="kpi"><div class="rotulo">Nível de risco</div><div class="kpi-valor texto-risco">${cap(esc(f.risco))}</div>
        <div class="escala">${escala}</div></div>
      <div class="kpi"><div class="rotulo">Chance de risco alto em ${h} semanas</div><div class="kpi-valor">${pct(f.prob)}</div>
        ${barraProb(f.prob)}<div class="kpi-nota">traço: limiar de alerta de ${pct(lim)}</div></div>
    </div>
    <div>
      <div class="faixa"><span class="tag tag-outline">${emAlerta ? "Em alerta" : "Fora de alerta"}</span><span>${alertaFrase}</span></div>
      ${f.provisorio ? `<div class="faixa"><span class="tag tag-neutral">Dado provisório</span><span>Só ${pct(f.completude)} das notificações desta semana já foram digitadas. Os ${fmt(f.casos)} casos notificados ainda vão subir; por isso o boletim trabalha com os ${fmt(f.est)} casos estimados.</span></div>` : ""}
    </div>
    <div class="duas-uma">
      <div class="coluna">
        <div class="barra-titulo"><h3>Casos estimados por semana</h3>${seg("periodo", S.periodo, [[52, "52 semanas"], [156, "3 anos"]])}</div>
        ${casos}
        <div class="legenda"><span><i class="traco"></i>casos estimados</span><span><i class="traco tracejado"></i>casos já notificados</span><span><i class="caixa"></i>margem de incerteza</span></div>
      </div>
      <div class="coluna-larga">
        <div class="linhas">
          <h4 style="margin-bottom:6px">O Entorno nesta semana</h4>
          ${linhaValor("Municípios", fmt(D.entorno.municipios))}
          ${linhaValor("Casos estimados", fmt(D.entorno.est))}
          ${linhaValor("Em risco alto ou muito alto", fmt(D.entorno.altoRisco))}
          ${linhaValor("Em alerta", fmt(D.entorno.emAlerta))}
          <p class="pequeno mudo justo" style="margin-top:12px">Quem mora no Entorno trabalha e estuda em Brasília, e o vírus acompanha esse vaivém diário nos dois sentidos.</p>
        </div>
        <div class="coluna" style="gap:8px">
          <h4>O que mais pesou na previsão</h4>
          <div class="lista-numerada">${(f.fatores.length ? f.fatores : ["sem fator dominante"]).map((t, i) => `<div><b>${i + 1}</b><span>${esc(cap(t))}</span></div>`).join("")}</div>
        </div>
      </div>
    </div>
  </section>`;
}

// ========================================================= II MAPA E MUNICÍPIOS
const COR_INDICE = { calmo: "var(--indice-calmo)", atencao: "var(--indice-atencao)", elevado: "var(--indice-elevado)", alerta: "var(--indice-alerta)", sem_dado: "var(--indice-sem-dado)" };
const cartao = (titulo, estado, nivel, leitura, conselho, evidencia) => `
  <div class="card indice">
    <div class="card-kicker">${titulo}</div>
    <div class="indice-nivel"><i style="background:${COR_INDICE[estado]}"></i>${nivel}</div>
    <p>${leitura}</p>
    ${conselho ? `<p class="conselho">${conselho}</p>` : ""}
    ${evidencia ? `<p class="evidencia">${evidencia}</p>` : ""}
  </div>`;

function indices(m) {
  const h = D.horizonte, lim = D.limiar, des = D.desempenho;
  const anos = `${des.anos[0]}–${des.anos[1]}`;
  const combinado = des.resumo.find(r => r.modelo === "Combinado");

  // Previsão: "previsão", e não "risco", para não brigar com o risco de hoje.
  let c1;
  if (m.prob == null) {
    c1 = cartao(`Previsão para ${h} semanas`, "sem_dado", "Sem previsão", "A semana mais recente não tem os preditores essenciais.");
  } else {
    const [estado, nivel, conselho] = m.prob >= lim
      ? ["alerta", "Alerta", "Intensifique o combate aos criadouros. Com febre, procure uma unidade de saúde."]
      : m.prob >= 0.5 ? ["atencao", "Atenção", "Reforce a busca por água parada e o uso de repelente."]
        : ["calmo", "Sem alerta", "Mantenha a rotina: elimine água parada uma vez por semana."];
    const evidencia = m.cod === COD_FOCO
      ? `Validado em ${anos}: em Brasília, no limiar de ${pct(lim)}, ${pct(des.vppBrasilia)} dos alertas se confirmaram.`
      : combinado ? `Validação temporal ${anos} nos ${D.totalMunicipios} municípios: AUC de ${fmt(combinado.auc, 3)}.` : "";
    c1 = cartao(`Previsão para ${h} semanas`, estado, nivel, `${pct(m.prob)} de chance de risco alto ou muito alto em ${h} semanas.`, conselho, evidencia);
  }

  // Transmissão: p(Rt>1) das duas últimas semanas, a variável da regra R3.
  let c2;
  const r3 = D.alarmes.regras.find(r => r.id === "R3");
  if (m.pRt1 == null) {
    c2 = cartao("Transmissão", "sem_dado", "Sem dado", "Probabilidade de Rt acima de 1 indisponível nesta semana.");
  } else {
    const agora = m.pRt1, antes = m.pRt1Anterior;
    const [estado, nivel, conselho] = (antes != null && agora >= 0.9 && antes >= 0.9)
      ? ["alerta", "Crescendo", "Duas semanas seguidas em alta: costuma anteceder aumento de casos."]
      : agora >= 0.9 ? ["atencao", "Subindo", "Cada caso começa a gerar mais de um. Vale acompanhar."]
        : ["calmo", "Estável", "O ritmo de novos casos não está acelerando."];
    let evidencia = "";
    if (r3 && m.liftR3 != null) evidencia = `Aqui, quando passou de 90% por duas semanas, a incidência ${r3.lag} semanas depois foi ${fmt(m.liftR3, 1)} vezes a normal da época.`;
    else if (r3) evidencia = `No território, acima de 90% por duas semanas antecedeu incidência ${fmt(r3.lift, 1)} vezes a normal da época, em ${fmt(r3.episodios)} episódios.`;
    c2 = cartao("Transmissão", estado, nivel,
      `Probabilidade de Rt acima de 1: ${pct(agora)} nesta semana${antes != null ? `, ${pct(antes)} na anterior` : ""}.`, conselho, evidencia);
  }

  // Clima: contexto, não previsão.
  const cl = D.clima.municipios.find(c => c.cod === m.cod);
  const contexto = "Contexto, não previsão: no histórico do território, gatilhos climáticos sozinhos não anteciparam dengue.";
  let c3;
  if (!cl) {
    c3 = cartao("Clima para o Aedes (14 dias)", "sem_dado", "Sem previsão", "Previsão do tempo indisponível para este município.", "", contexto);
  } else {
    const naFaixa = cl.temp != null && cl.temp >= FAIXA_AEDES[0] && cl.temp <= FAIXA_AEDES[1];
    const [estado, nivel, conselho] = (!naFaixa || cl.dias === 0)
      ? ["calmo", "Pouco favorável", "Tempo desfavorável ao mosquito nos próximos dias."]
      : cl.dias >= DIAS_CHUVA_FREQUENTE ? ["elevado", "Muito favorável", "Esvazie pratos de planta, calhas e pneus depois de cada chuva."]
        : ["atencao", "Favorável", "Chuva e calor ajudam o mosquito: olho em recipientes com água."];
    c3 = cartao("Clima para o Aedes (14 dias)", estado, nivel,
      `${fmt(cl.chuva14)} mm em ${cl.dias} dias de chuva; ${cl.temp == null ? "temperatura indisponível" : `média de ${fmt(cl.temp)} °C`}.`, conselho, contexto);
  }

  // Qualidade do dado: quanto da semana já foi digitado.
  const temC = m.completude != null;
  const [estado4, nivel4, conselho4] = (!m.provisorio || (temC && m.completude >= 0.9))
    ? ["calmo", "Consolidado", "Os números da semana já estão praticamente completos."]
    : (temC && m.completude >= 0.6) ? ["atencao", "Em consolidação", "Os números ainda podem subir um pouco."]
      : ["elevado", "Provisório", "Os números da semana ainda vão subir: leia como estimativa."];
  const c4 = cartao("Qualidade do dado", estado4, nivel4,
    `${fmt(m.casos)} casos notificados de ${fmt(m.est)} estimados${temC ? ` (${pct(m.completude)} digitado)` : ""}.`, conselho4,
    "A notificação chega com atraso; o nowcasting do InfoDengue estima os casos que ainda vão entrar.");
  return `<div class="indices">${c1}${c2}${c3}${c4}</div>`;
}

const MEDIDAS = {
  casos: { rot: "Casos", campo: "e", cor: "var(--color-accent-800)", f: v => fmt(v), nota: "Casos estimados por semana, já corrigidos do atraso de notificação. O círculo aberto é a semana mais recente." },
  risco: { rot: "Risco à frente", campo: "p", cor: "var(--color-accent-600)", f: pct, nota: null },
  temperatura: { rot: "Temperatura", campo: "t", cor: "var(--indice-alerta)", f: v => fmt(v) + "°", nota: "Temperatura média de cada semana, em graus Celsius." },
  umidade: { rot: "Umidade", campo: "u", cor: "var(--color-accent-500)", f: v => fmt(v) + "%", nota: "Umidade relativa média de cada semana." },
};

function semanaASemana(m) {
  const md = MEDIDAS[S.medida], vs = m.semanas.map(s => s[md.campo]);
  const validos = vs.filter(v => v != null);
  let min = 0, max = 1, fy = md.f;
  if (S.medida === "casos") max = redondo(Math.max(1, ...validos) * 1.25);
  else if (S.medida === "risco") { min = 0; max = 1; fy = pct; }
  else if (validos.length) {
    min = Math.floor(Math.min(...validos) - 3); max = Math.ceil(Math.max(...validos) + 3);
    if (S.medida === "umidade") { min = Math.max(0, min); max = Math.min(100, max); }
  }
  const nota = md.nota || `Chance de risco alto ou muito alto ${D.horizonte} semanas depois de cada semana. A linha tracejada marca o limiar de alerta de ${pct(D.limiar)}.`;
  const g = validos.length ? grafico("semanas", m.semanas.map(s => diaMes(s.d)), [{ v: vs, cor: md.cor, w: 2 }], {
    min, max, fy, valores: md.f, nt: 4, H: 250, passo: estreita() ? 2 : 1, titulo: `${md.rot} em ${m.nome}, semana a semana`,
    limiar: S.medida === "risco" ? D.limiar : null,
  }) : `<p class="mudo">Sem dado de ${md.rot.toLowerCase()} para este município.</p>`;
  return `<div class="coluna">
    <div class="barra-titulo"><h3>Semana a semana em ${esc(m.nome)}</h3>${seg("medida", S.medida, Object.entries(MEDIDAS).map(([k, v]) => [k, v.rot]))}</div>
    ${g}<p class="pequeno mudo">${nota}</p></div>`;
}

function vistaMapa() {
  const m = porCod(S.sel) || D.foco;
  const contagem = {}; D.ordemRisco.forEach(r => contagem[r] = 0);
  D.municipios.forEach(x => contagem[x.risco] = (contagem[x.risco] || 0) + 1);
  let bsb = null;
  const paths = RIDE.slice().sort((a, b) => (a.props.cod === m.cod) - (b.props.cod === m.cod)).map(p => {
    const x = porCod(p.props.cod), ativo = p.props.cod === m.cod;
    if (p.props.cod === COD_FOCO) bsb = p;
    const k = "r" + p.props.cod;
    DICA_MAPA[k] = x ? `<strong>${esc(x.nome)}</strong>${fmt(x.est)} casos est. · ${fmt(x.inc, 1)} por 100 mil<br><span class="mudo">Risco ${esc(x.risco)} · chance de alerta ${pct(x.prob)}</span>` : "<strong>Sem dado nesta semana</strong>";
    return `<path d="${p.d}" data-k="${k}" data-cod="${p.props.cod}" fill="${x ? COR_RISCO[x.risco] : "var(--color-neutral-200)"}" stroke="${ativo ? "var(--color-text)" : "color-mix(in srgb, var(--color-text) 35%, transparent)"}" stroke-width="${ativo ? 2.4 : 0.7}" vector-effect="non-scaling-stroke"><title>${x ? esc(x.nome) : ""}</title></path>`;
  }).join("");
  const kicker = m.cod === COD_FOCO ? "Distrito Federal" : (m.uf === "GO" ? "Goiás" : "Minas Gerais") + " · Entorno";
  const opcoes = D.municipios.slice().sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
    .map(x => `<option value="${x.cod}"${x.cod === m.cod ? " selected" : ""}>${esc(x.nome)}</option>`).join("");

  return `<section class="secao">
    ${cabeca("II · Mapa e municípios", `Os ${D.totalMunicipios} municípios da RIDE-DF`,
      `Cada município aparece com o nível de risco da semana ${D.semanaRotulo}. Passe o cursor para ver os números; clique ou toque num município para abrir a ficha e os índices da semana dele.`)}
    <div class="duas-uma">
      <div class="coluna" style="gap:14px">
        <div class="mapa">
          <svg viewBox="0 0 800 620" role="img" aria-label="Mapa de risco dos municípios da RIDE-DF">${paths}
            ${bsb ? `<text x="${bsb.cx.toFixed(1)}" y="${(bsb.cy + 6).toFixed(1)}">Brasília</text>` : ""}</svg>
          <div class="dica-mapa"></div>
        </div>
        <div class="legenda" style="font-size:13px;color:var(--color-text)">${D.ordemRisco.map(r => `<span><i class="quadrado" style="background:${COR_RISCO[r]}"></i>${cap(r)} <span class="mudo num">· ${contagem[r] || 0}</span></span>`).join("")}</div>
      </div>
      <div class="coluna-larga" style="gap:20px">
        <label class="coluna" style="gap:6px"><span class="pequeno mudo">Escolher município</span>
          <select class="select" id="sel-mun">${opcoes}</select></label>
        <div class="card" style="gap:4px">
          <div class="card-kicker">${kicker}</div>
          <div class="ficha-nome">${esc(m.nome)}</div>
          ${linhaValor("Casos estimados", fmt(m.est))}
          ${linhaValor("Por 100 mil hab.", fmt(m.inc, 1))}
          ${linhaValor("Nível de risco", cap(esc(m.risco)))}
          ${linhaValor("Chance de alerta", pct(m.prob))}
          ${linhaValor("População", fmt(m.pop))}
          <div class="pequeno mudo" style="padding-top:8px;border-top:1px solid var(--color-divider)">Pesaram mais: ${esc(listaFatores(m.fatores))}</div>
          ${m.cod !== COD_FOCO ? `<button class="btn btn-primary" type="button" data-acao="sel" data-valor="${COD_FOCO}" style="margin-top:12px;align-self:flex-start">Voltar para Brasília</button>` : ""}
        </div>
        <p class="pequeno mudo justo">O nível combina duas leituras: a incidência frente ao que costuma acontecer na mesma época do ano no município (o canal endêmico) e patamares fixos de 10, 30 e 60 casos por 100 mil habitantes. Prevalece a mais grave.</p>
      </div>
    </div>
    <div class="coluna" style="gap:14px">
      <h3>Índices da semana em ${esc(m.nome)}</h3>
      ${indices(m)}
    </div>
    ${semanaASemana(m)}
  </section>`;
}

// =========================================================== III SÉRIES
function vistaSeries() {
  const ns = S.periodo;
  const cb = D.comparacao.Brasilia.slice(-ns), ce = D.comparacao.Entorno.slice(-ns);
  const comp = grafico("comp", cb.map(p => mesAno(p.d)), [
    { v: cb.map(p => p.v), cor: "var(--color-accent-700)", w: 2.2 },
    { v: ce.map(p => p.v), cor: "var(--color-neutral-600)", w: 1.5, dash: "5 4" },
  ], {
    max: redondo(Math.max(...cb.concat(ce).map(p => p.v)) * 1.05), W: 1100, H: 320,
    passo: Math.ceil(ns / (estreita() ? 4 : 8)), titulo: "Incidência por 100 mil: Brasília e Entorno",
    dica: i => `<strong>semana de ${diaMesAno(cb[i].d)}</strong>Brasília: ${fmt(cb[i].v, 1)} por 100 mil<br>Entorno: ${ce[i] ? fmt(ce[i].v, 1) : "—"} por 100 mil`,
  });
  const s = D.serie.slice(-16);
  const hi = s.map(p => p.hi == null ? p.e : p.hi), lo = s.map(p => p.lo == null ? p.e : p.lo);
  const notif = grafico("notif", s.map(p => diaMes(p.d)), [
    { v: s.map(p => p.e), cor: "var(--color-accent-800)", w: 2 },
    { v: s.map(p => p.n), cor: "var(--color-neutral-600)", w: 1.2, dash: "4 4" },
  ], {
    max: redondo(Math.max(...hi) * 1.05), hi, lo, H: 260, passo: estreita() ? 5 : 3,
    titulo: "Casos notificados e estimados nas últimas 16 semanas",
    dica: i => `<strong>semana de ${diaMesAno(s[i].d)}</strong>${fmt(s[i].e)} estimados<br>${fmt(s[i].n)} notificados`,
  });
  return `<section class="secao">
    ${cabeca("III · Séries temporais", "Brasília frente ao Entorno", "Incidência por 100 mil habitantes, padronizada pela população de cada grupo — o que torna as duas curvas comparáveis apesar da diferença de porte.")}
    <div class="barra-titulo">
      <div class="legenda"><span><i class="traco bsb"></i>Brasília</span><span><i class="traco entorno"></i>Entorno (RIDE)</span></div>
      ${seg("periodo", S.periodo, [[52, "52 semanas"], [156, "3 anos"]])}
    </div>
    ${comp}
    <hr class="hr">
    <div class="duas-uma">
      <div class="coluna">
        <h3>Notificado e estimado, últimas 16 semanas</h3>
        <p class="pequeno mudo" style="font-size:13px">A distância entre as duas linhas é o atraso de notificação, corrigido por <em>nowcasting</em>.</p>
        ${notif}
        <div class="legenda"><span><i class="traco"></i>estimado</span><span><i class="traco tracejado"></i>notificado</span><span><i class="caixa"></i>margem de incerteza</span></div>
      </div>
      <div class="card">
        <div class="card-kicker">Por que usar casos estimados</div>
        <p class="justo" style="font-size:14px;line-height:1.65">As semanas mais recentes chegam subnotificadas: a digitação retroativa ainda não ocorreu. Um alerta baseado nos casos observados leria queda onde há alta. Toda a incidência e a classificação de risco deste boletim usam os casos estimados.</p>
      </div>
    </div>
  </section>`;
}

// =========================================================== IV RANKING
function listaRanking() {
  const lista = D.municipios.slice();
  if (S.ordem === "inc") lista.sort((a, b) => (b.inc || 0) - (a.inc || 0));
  else if (S.ordem === "casos") lista.sort((a, b) => (b.est || 0) - (a.est || 0));
  else lista.sort((a, b) => (b.prob || 0) - (a.prob || 0));
  return lista.map((m, i) => ({ m, pos: i + 1 }));
}
const semAcento = s => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function corpoRanking() {
  const q = semAcento(S.busca.trim());
  const linhas = listaRanking().filter(x => !q || semAcento(x.m.nome).includes(q));
  if (!linhas.length) return `<tr><td colspan="7" class="mudo">Nenhum município com esse nome.</td></tr>`;
  return linhas.map(({ m, pos }) => `<tr class="${m.cod === COD_FOCO ? "destaque" : ""}">
    <td class="num mudo">${pos}</td>
    <td><div class="nome-mun">${esc(m.nome)} <span class="pequeno mudo" style="font-family:var(--font-body);font-weight:400">${m.uf}</span></div><div class="pequeno mudo">${esc(cap(listaFatores(m.fatores)))}</div></td>
    <td class="dir">${fmt(m.est)}</td>
    <td class="dir">${fmt(m.inc, 1)}</td>
    <td><span style="display:inline-flex;gap:7px;align-items:center;font-size:13px;white-space:nowrap"><i class="quadrado" style="width:11px;height:11px;background:${COR_RISCO[m.risco]}"></i>${cap(esc(m.risco))}</span></td>
    <td><div style="display:flex;gap:10px;align-items:center">${barraProb(m.prob, true)}<span class="num" style="font-size:13px;width:36px;text-align:right">${pct(m.prob)}</span></div></td>
    <td>${(m.prob || 0) >= D.limiar ? `<span class="tag tag-outline">Em alerta</span>` : ""}</td>
  </tr>`).join("");
}

function vistaRanking() {
  const lista = listaRanking(), pos = lista.find(x => x.m.cod === COD_FOCO).pos;
  const criterio = { prob: "chance de alerta", inc: "incidência", casos: "casos estimados" }[S.ordem];
  const emAlerta = D.municipios.filter(m => (m.prob || 0) >= D.limiar).length;
  return `<section class="secao">
    ${cabeca("IV · Ranking e relatório", "Quem tem mais chance de entrar em risco alto",
      `Brasília ocupa a posição ${pos} de ${D.totalMunicipios} em ${criterio} nesta semana. ${emAlerta === 1 ? "1 município está" : `${emAlerta} municípios estão`} acima do limiar de alerta de ${pct(D.limiar)}.`)}
    <div class="filtros" style="justify-content:space-between">
      <input class="input" id="busca-ranking" type="search" placeholder="Buscar município" value="${esc(S.busca)}" style="width:280px" aria-label="Buscar município">
      <div class="filtros"><span class="pequeno mudo">Ordenar por</span>
        ${seg("ordem", S.ordem, [["prob", "Chance de alerta"], ["inc", "Incidência"], ["casos", "Casos"]])}
        <button class="btn btn-secondary" type="button" data-acao="baixar-ranking">Baixar a tabela (CSV)</button>
      </div>
    </div>
    <div class="tabela-rolavel"><table class="table" style="min-width:840px">
      <thead><tr><th style="width:36px">#</th><th>Município</th><th class="dir">Casos est.</th><th class="dir">Por 100 mil</th><th>Risco</th><th style="width:200px">Chance de alerta</th><th>Situação</th></tr></thead>
      <tbody id="corpo-ranking">${corpoRanking()}</tbody>
    </table></div>
    <p class="pequeno mudo">Linha destacada: Brasília. O traço vertical na barra marca o limiar de alerta de ${pct(D.limiar)}. Semana ${D.semanaRotulo}, casos estimados.</p>
  </section>`;
}

function baixarRanking() {
  const cel = v => /[;"\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const dec = (v, c) => v == null ? "" : Number(v).toFixed(c).replace(".", ",");
  const linhas = [["posicao", "municipio", "uf", "casos_notificados", "casos_estimados", "incidencia_100k", "risco", "chance_de_alerta_pct", "em_alerta", "fatores"]];
  listaRanking().forEach(({ m, pos }) => linhas.push([pos, m.nome, m.uf, m.casos, dec(m.est, 1), dec(m.inc, 1), m.risco,
    m.prob == null ? "" : Math.round(m.prob * 100), (m.prob || 0) >= D.limiar ? "sim" : "nao", listaFatores(m.fatores)]));
  // Ponto e vírgula e vírgula decimal: abre direto no Excel em português.
  const csv = "﻿" + linhas.map(l => l.map(cel).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = `vigia-dengue_ranking_SE${String(D.semana % 100).padStart(2, "0")}-${Math.floor(D.semana / 100)}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ======================================================== V DESEMPENHO
function vistaModelo() {
  const des = D.desempenho;
  const anos = Array.from(new Set(des.porAno.map(r => r.ano))).sort();
  const ordem = ["Referencia", "Logistica", "LightGBM", "Combinado"];
  const auc = grafico("auc", anos.map(String), ordem.map(k => Object.assign({
    v: anos.map(a => (des.porAno.find(r => r.ano === a && r.modelo === k) || {}).auc),
  }, MODELOS[k])), {
    min: 0.65, max: 0.95, nt: 6, fy: v => fmt(v, 2), W: 1100, H: 300, passo: 1, titulo: "AUC por ano e modelo",
    dica: i => `<strong>${anos[i]}</strong>` + ["Combinado", "LightGBM", "Logistica", "Referencia"].map(k => {
      const r = des.porAno.find(x => x.ano === anos[i] && x.modelo === k);
      return `${MODELOS[k].nome}: ${r ? fmt(r.auc, 3) : "—"}`;
    }).join("<br>"),
  });
  const pb = des.pesoBoosting;
  const tabela = ["Combinado", "LightGBM", "Logistica", "Referencia"].map(k => des.resumo.find(r => r.modelo === k)).filter(Boolean)
    .map(r => `<tr class="${r.modelo === "Combinado" ? "destaque" : ""}"><td class="nome-mun">${MODELOS[r.modelo].nome}</td><td class="dir">${fmt(r.auc, 3)}</td><td class="dir">${fmt(r.sens, 3)}</td><td class="dir">${fmt(r.espec, 3)}</td><td class="dir">${fmt(r.vpp, 3)}</td><td class="dir">${fmt(r.brier, 3)}</td></tr>`).join("");
  const glossario = [
    ["Sensibilidade", "Das semanas que de fato chegaram a risco alto, quantas o modelo avisou antes."],
    ["Especificidade", "Das semanas calmas, quantas ele deixou de alarmar à toa."],
    ["VPP", "Quando o modelo avisa, quantas vezes o risco alto de fato veio."],
    ["AUC", "Capacidade geral de separar semanas de risco das calmas: 0,5 é acaso, 1 é perfeito."],
    ["Brier", "Erro médio das probabilidades; quanto menor, melhor."],
  ].map(([t, d]) => `<div style="padding:9px 0;border-bottom:1px solid var(--color-divider);font-size:13px;line-height:1.55"><strong style="font-weight:600">${t}.</strong> ${d}</div>`).join("");
  return `<section class="secao">
    ${cabeca("V · Desempenho do modelo", "Quanto o alerta acertou no passado", `Cada ano é avaliado com um modelo treinado apenas nos anos anteriores, nunca no próprio. O desfecho é risco alto ou muito alto ${D.horizonte} semanas à frente.`)}
    <div class="coluna">
      <h3>Capacidade de separar semanas de risco (AUC), por ano</h3>
      ${auc}
      <div class="legenda">${["Combinado", "LightGBM", "Logistica", "Referencia"].map(k => `<span><svg width="24" height="6" style="overflow:visible"><line x1="0" x2="24" y1="3" y2="3" stroke="${MODELOS[k].cor}" stroke-width="${MODELOS[k].w}" stroke-dasharray="${MODELOS[k].dash}"/></svg>${MODELOS[k].nome}</span>`).join("")}</div>
    </div>
    <div class="duas-uma">
      <div class="coluna">
        <div class="tabela-rolavel"><table class="table" style="min-width:560px">
          <thead><tr><th>Modelo</th><th class="dir">AUC</th><th class="dir">Sensibilidade</th><th class="dir">Especificidade</th><th class="dir">VPP</th><th class="dir">Brier</th></tr></thead>
          <tbody>${tabela}</tbody></table></div>
        <p class="pequeno mudo">Médias de ${des.anos[0]} a ${des.anos[1]}, sobre os ${D.totalMunicipios} municípios. O boletim opera com o combinado (${fmt(pb, 1)} × LightGBM + ${fmt(1 - pb, 1)} × persistência).</p>
        <div class="faixa" style="margin-top:8px"><span class="tag tag-outline">Em Brasília</span><span>No limiar de alerta de ${pct(D.limiar)}, ${pct(des.vppBrasilia)} dos alertas do combinado se confirmaram na validação ${des.anos[0]}–${des.anos[1]}.</span></div>
      </div>
      <div class="linhas"><h4 style="margin-bottom:4px">Como ler cada medida</h4>${glossario}</div>
    </div>
  </section>`;
}

// ============================================================ VI POR RA
const INDICADORES = {
  vul: { nome: "índice de vulnerabilidade (0 a 100)", col: "Índice", get: p => (D.ras[p.cod] || {}).indice, f: v => fmt(v, 1) },
  pop: { nome: "habitantes", col: "População", get: p => p.pop, f: v => fmt(v) },
  dens: { nome: "hab./km²", col: "Densidade", get: p => p.dens, f: v => fmt(v) },
};

function vistaRas() {
  const ind = INDICADORES[S.ind];
  const linhas = RAS.map(r => ({ r, v: D.ras[r.props.cod], val: ind.get(r.props) }));
  const vals = linhas.map(x => x.val).filter(v => v != null);
  const vmin = Math.min(...vals), vmax = Math.max(...vals);
  const paths = linhas.map(x => {
    const k = "a" + x.r.props.cod;
    const op = x.val == null ? 0.05 : 0.1 + 0.9 * (x.val - vmin) / (vmax - vmin || 1);
    DICA_MAPA[k] = `<strong>${esc(x.r.props.nome)}</strong>${ind.col}: ${x.val == null ? "sem dado" : ind.f(x.val)}<br><span class="mudo">${x.v ? `Esgoto inadequado ${fmt(x.v.esgoto, 1)}% · sem rede de água ${fmt(x.v.agua, 1)}%` : `${fmt(x.r.props.pop)} habitantes`}</span>`;
    return `<path d="${x.r.d}" data-k="${k}" fill="var(--color-accent-600)" fill-opacity="${op.toFixed(2)}" stroke="var(--color-bg)" stroke-width="1" vector-effect="non-scaling-stroke"><title>${esc(x.r.props.nome)}</title></path>`;
  }).join("");
  const tabela = linhas.slice().sort((a, b) => (b.val ?? -1) - (a.val ?? -1)).map(x => `<tr><td>${esc(x.r.props.nome)}</td><td class="dir">${x.val == null ? "—" : ind.f(x.val)}</td><td class="dir">${x.v ? fmt(x.v.esgoto, 1) + "%" : "—"}</td><td class="dir">${x.v ? fmt(x.v.agua, 1) + "%" : "—"}</td></tr>`).join("");
  const comEsgoto = Object.values(D.ras).filter(v => v.esgoto != null).sort((a, b) => a.esgoto - b.esgoto);
  const menor = comEsgoto[0], maior = comEsgoto[comEsgoto.length - 1];
  return `<section class="secao">
    ${cabeca("VI · Brasília por Região Administrativa", "As condições de cada RA",
      `Não há contagem de casos por RA, mas há condição: ${fmt(menor.esgoto, 2)}% de esgotamento inadequado em ${esc(menor.nome)} contra ${fmt(maior.esgoto, 1)}% em ${esc(maior.nome)}. O índice soma esgoto, água, lixo, bueiros e pavimento do Censo 2022.`)}
    ${seg("ind", S.ind, [["vul", "Vulnerabilidade"], ["pop", "População"], ["dens", "Densidade"]])}
    <div class="metade">
      <div class="coluna">
        <div class="mapa mapa-ras">
          <svg viewBox="0 0 800 560" role="img" aria-label="Mapa das Regiões Administrativas do DF">${paths}</svg>
          <div class="dica-mapa"></div>
        </div>
        <div class="legenda" style="align-items:center"><span>${ind.f(vmin)}</span><span class="gradiente"></span><span>${ind.f(vmax)}</span><span>· ${ind.nome}</span></div>
      </div>
      <div class="tabela-rolavel" style="max-height:560px;overflow:auto">
        <table class="table"><thead><tr><th>Região Administrativa</th><th class="dir">${ind.col}</th><th class="dir">Esgoto inad.</th><th class="dir">Sem água</th></tr></thead><tbody>${tabela}</tbody></table>
      </div>
    </div>
    <div class="faixa justo" style="display:block;font-size:14px;line-height:1.65"><strong style="font-weight:600">Este mapa não exibe casos de dengue por RA.</strong> Não existe fonte pública com essa série: o InfoDengue opera apenas no nível municipal, o painel da SES-DF não expõe os dados de forma programática, o LIRAa é publicado como relatório fechado e os microdados do SINAN dependem do FTP do DATASUS. Repartir os casos do DF entre as RAs na proporção da população produziria um mapa apenas aparentemente informativo, que reproduziria o mapa populacional e esconderia a desigualdade intraurbana real — justamente o que se quer medir.</div>
  </section>`;
}

// ===================================================== VII ALARMES E CLIMA
function vistaClima() {
  const al = D.alarmes, cl = D.clima;
  const regras = al.regras.map(r => `<div class="regra"><b>${r.id}</b>
    <div class="regra-corpo"><strong>${esc(r.nome)}</strong><span>${esc(r.descricao)}</span>
      <span class="pequeno mudo num">Efeito medido ${r.lag} semanas depois: incidência ${fmt(r.lift, 2)} vezes a habitual · ${fmt(r.episodios)} episódios</span></div>
    <span class="tag ${r.aprovada ? "tag-outline" : "tag-neutral"}">${r.aprovada ? "Aprovada" : "Reprovada"}</span></div>`).join("");
  const ativos = al.ativos.length ? al.ativos.map(a => `<div class="regra"><b>${a.id}</b>
    <div class="regra-corpo"><strong>${esc(a.municipio)}: ${esc(a.nome)}</strong>
      <span>Valor do gatilho: ${pct(a.valor)}. Aqui, depois de gatilhos assim, a incidência ${a.lag} semanas depois foi ${fmt(a.lift, 1)} vezes a habitual.</span></div>
    <span class="tag tag-outline">Ativo</span></div>`).join("") : "";
  const bsb = cl.municipios.find(m => m.cod === COD_FOCO);
  let leitura = "";
  if (bsb) {
    const favoravel = bsb.temp != null && bsb.temp >= FAIXA_AEDES[0] && bsb.temp <= FAIXA_AEDES[1];
    leitura = `Temperatura ${favoravel ? "dentro" : "fora"} da faixa favorável ao <em>Aedes aegypti</em> (${FAIXA_AEDES[0]} a ${FAIXA_AEDES[1]} °C)${bsb.dias >= DIAS_CHUVA_FREQUENTE ? ", com chuva frequente." : "."}`;
  }
  const maxCh = Math.max(1, ...cl.municipios.map(m => m.chuva14 || 0));
  const chuva = cl.municipios.slice().sort((a, b) => (b.chuva14 || 0) - (a.chuva14 || 0)).map(m => `<div style="${m.cod === COD_FOCO ? "background:var(--color-accent-100)" : ""}"><span>${esc(m.nome)}</span><span class="barra-prob"><b style="width:${((m.chuva14 || 0) / maxCh * 100).toFixed(1)}%"></b></span><span class="num" style="text-align:right">${fmt(m.chuva14)} mm</span></div>`).join("");
  const periodo = al.periodo ? `${al.periodo[0]}–${al.periodo[1]}` : "";
  const crit = al.criterio;
  const faltam = cl.faltantes.length;
  return `<section class="secao">
    ${cabeca("VII · Alarmes e clima", "Sinais que costumam vir antes da dengue")}
    <div class="faixa"><span class="tag ${ativos ? "tag-outline" : "tag-neutral"}">${al.ativos.length ? `${al.ativos.length} ${al.ativos.length === 1 ? "alarme" : "alarmes"}` : "Nenhum alarme"}</span>
      <span>${al.ativos.length ? `Há alarmes ativos na semana ${rotSemana(al.semana)}.` : `Nenhuma regra aprovada disparou na semana ${rotSemana(al.semana)}, a mais recente verificada.`}</span></div>
    ${ativos ? `<div class="coluna" style="gap:0">${ativos}</div>` : ""}
    <div class="duas-uma">
      <div class="coluna" style="gap:0">
        <h3 style="margin-bottom:6px">As ${al.regras.length} regras testadas no histórico${periodo ? ` ${periodo}` : ""}</h3>
        ${crit ? `<p class="pequeno mudo" style="font-size:13px;margin-bottom:10px">Uma regra só vira alarme se, nas vezes em que ligou, a incidência semanas depois ficou ao menos ${fmt(crit.lift, 1)} vez acima do habitual, em ${crit.episodios} episódios ou mais.</p>` : ""}
        ${regras}
      </div>
      <div class="coluna-larga" style="gap:22px">
        <div class="card" style="gap:4px">
          <div class="card-kicker">Previsão para Brasília · próximos 14 dias</div>
          ${bsb ? linhaValor("Chuva em 7 dias", fmt(bsb.chuva7, 1) + " mm") + linhaValor("Chuva em 14 dias", fmt(bsb.chuva14, 1) + " mm") + linhaValor("Dias com chuva", `${bsb.dias} de 14`) + linhaValor("Temperatura média", fmt(bsb.temp, 1) + " °C") : `<p class="mudo">Sem previsão para Brasília nesta coleta.</p>`}
          <p class="pequeno mudo" style="margin-top:10px">${leitura}</p>
        </div>
        <p class="pequeno mudo justo">No histórico do território, gatilho climático isolado não antecipou dengue. Por isso o clima aparece aqui como contexto, e não como previsão.</p>
      </div>
    </div>
    <div class="coluna" style="gap:8px">
      <h3>Chuva prevista em 14 dias, por município</h3>
      <div class="chuva">${chuva}</div>
      <p class="pequeno mudo">Previsão ${esc(cl.fonte)} coletada para a semana ${rotSemana(cl.semana)}.${faltam ? ` Sem previsão para ${faltam} ${faltam === 1 ? "município" : "municípios"}: ${cl.faltantes.map(esc).join(", ")}.` : ""}</p>
    </div>
  </section>`;
}

// ========================================================= VIII DICIONÁRIO
function corpoDicionario() {
  const q = semAcento(S.dicBusca.trim());
  const cols = D.dicionario.colunas.filter(c =>
    (!S.dicBloco || c.bloco === S.dicBloco) && (!S.dicPapel || c.papel === S.dicPapel)
    && (!q || semAcento(c.coluna + " " + c.descricao).includes(q)));
  const html = cols.length ? cols.map(c => `<tr>
    <td><span class="cod">${esc(c.coluna).replace(/_/g, "_<wbr>")}</span></td><td>${esc(c.bloco)}</td>
    <td style="min-width:280px">${esc(c.descricao)}</td><td class="sem-quebra"><span class="cod">${esc(c.tipo)}</span></td>
    <td>${esc(c.fonte)}</td><td style="white-space:nowrap">${esc(cap(c.papel))}</td>
    <td class="dir">${c.preenchida == null ? "—" : fmt(c.preenchida, 1) + "%"}</td></tr>`).join("")
    : `<tr><td colspan="7" class="mudo">Nenhuma coluna com esses filtros.</td></tr>`;
  return { html, n: cols.length };
}

function vistaDicionario() {
  const cols = D.dicionario.colunas;
  const conta = {}; cols.forEach(c => conta[c.papel] = (conta[c.papel] || 0) + 1);
  const papeis = ORDEM_PAPEL.filter(p => conta[p]).concat(Object.keys(conta).filter(p => !ORDEM_PAPEL.includes(p)));
  const blocos = Array.from(new Set(cols.map(c => c.bloco))).sort((a, b) => a.localeCompare(b, "pt-BR"));
  const grupos = [];
  D.dicionario.glossario.forEach(g => {
    let gr = grupos.find(x => x.nome === g.grupo);
    if (!gr) grupos.push(gr = { nome: g.grupo, itens: [] });
    gr.itens.push(g);
  });
  const corpo = corpoDicionario();
  const opc = (lista, atual, todos) => `<option value="">${todos}</option>` + lista.map(v => `<option value="${esc(v)}"${v === atual ? " selected" : ""}>${esc(cap(v))}</option>`).join("");
  return `<section class="secao">
    ${cabeca("VIII · Dicionário de dados", "O que cada coluna da base significa",
      `A base analítica tem ${cols.length} colunas, numa linha por município e semana. O dicionário é gerado a partir do código e testado contra a base: se uma coluna entra sem descrição, o teste falha. Assim esta página nunca descreve uma base que deixou de existir.`)}
    <div class="contagem">${papeis.map(p => `<div><b>${conta[p]}</b><span>${esc(cap(p))}</span></div>`).join("")}</div>
    <div class="filtros" style="justify-content:space-between">
      <div class="filtros">
        <input class="input" id="busca-dic" type="search" placeholder="Buscar coluna ou descrição" value="${esc(S.dicBusca)}" style="width:260px" aria-label="Buscar coluna ou descrição">
        <select class="select" id="dic-bloco" aria-label="Filtrar por bloco">${opc(blocos, S.dicBloco, "Todos os blocos")}</select>
        <select class="select" id="dic-papel" aria-label="Filtrar por papel">${opc(papeis, S.dicPapel, "Todos os papéis")}</select>
        <span class="pequeno mudo num" id="dic-contagem">${corpo.n} de ${cols.length} colunas</span>
      </div>
      <div class="filtros">
        <a class="btn btn-secondary" href="dados/dicionario_de_dados.csv" download>Baixar o dicionário (CSV)</a>
        <a class="btn btn-secondary" href="dados/glossario.csv" download>Baixar o glossário (CSV)</a>
      </div>
    </div>
    <div class="tabela-rolavel"><table class="table" style="min-width:900px">
      <thead><tr><th>Coluna</th><th>Bloco</th><th>Descrição</th><th>Tipo</th><th>Fonte</th><th>Papel</th><th class="dir">Preenchida</th></tr></thead>
      <tbody id="corpo-dic">${corpo.html}</tbody></table></div>
    <div class="coluna" style="gap:16px">
      <h3>O que cada termo significa</h3>
      <div class="glossario">${grupos.map(g => `<section><h4>${esc(g.nome)}</h4><dl>${g.itens.map(i => `<dt>${esc(i.termo)}</dt><dd>${esc(i.significado)}</dd>`).join("")}</dl></section>`).join("")}</div>
    </div>
  </section>`;
}

// ================================================================ quadro
const VISTAS = {
  panorama: vistaPanorama, mapa: vistaMapa, series: vistaSeries, ranking: vistaRanking,
  modelo: vistaModelo, ras: vistaRas, clima: vistaClima, dicionario: vistaDicionario,
};
const abas = document.getElementById("abas");
const conteudo = document.getElementById("conteudo");
const botaoTema = document.getElementById("botao-tema");

function telaDoEndereco() {
  const h = location.hash.slice(1);
  return VISTAS[h] ? h : "panorama";
}

function desenharAbas() {
  abas.innerHTML = TELAS.map(([id, r], i) =>
    `<a href="#${id}"${S.tela === id ? ' aria-current="page"' : ""}><span>${ROMANOS[i]}</span>${r}</a>`).join("");
  const atual = abas.querySelector("[aria-current]");
  if (atual && abas.scrollWidth > abas.clientWidth) {
    abas.scrollLeft = atual.offsetLeft - abas.clientWidth / 2 + atual.offsetWidth / 2;
  }
}

function render() {
  desenharAbas();
  if (!D) return;
  conteudo.innerHTML = VISTAS[S.tela]();
  const nome = TELAS.find(t => t[0] === S.tela)[1];
  document.title = S.tela === "panorama" ? `VIGIA-Dengue · Semana ${D.semanaRotulo}` : `${nome} · VIGIA-Dengue`;
}

function aplicarTema(t) {
  document.documentElement.setAttribute("data-tema", t);
  botaoTema.textContent = t === "escuro" ? "Modo claro" : "Modo escuro";
}
aplicarTema(document.documentElement.getAttribute("data-tema") || "claro");
// Sem escolha salva, o boletim acompanha o tema do sistema também depois de
// aberto (o celular que escurece à noite, por exemplo).
if (window.matchMedia) {
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ev => {
    let salvo = null;
    try { salvo = localStorage.getItem("vigia-tema"); } catch (e) { /* janela privada */ }
    if (!salvo) aplicarTema(ev.matches ? "escuro" : "claro");
  });
}
botaoTema.addEventListener("click", () => {
  const t = document.documentElement.getAttribute("data-tema") === "escuro" ? "claro" : "escuro";
  aplicarTema(t);
  try { localStorage.setItem("vigia-tema", t); } catch (e) { /* janela privada */ }
});

window.addEventListener("hashchange", () => {
  S.tela = telaDoEndereco();
  render();
  window.scrollTo(0, 0);
});

document.addEventListener("click", e => {
  const alvo = e.target.closest("[data-acao], .mapa path[data-cod]");
  if (!alvo || !D) return;
  if (alvo.matches("path[data-cod]")) { S.sel = +alvo.dataset.cod; render(); return; }
  const v = alvo.dataset.valor;
  switch (alvo.dataset.acao) {
    case "periodo": S.periodo = +v; break;
    case "ordem": S.ordem = v; break;
    case "ind": S.ind = v; break;
    case "medida": S.medida = v; break;
    case "sel": S.sel = +v; break;
    case "baixar-ranking": baixarRanking(); return;
    default: return;
  }
  render();
});

document.addEventListener("change", e => {
  if (!D) return;
  if (e.target.id === "sel-mun") { S.sel = +e.target.value; render(); }
  else if (e.target.id === "dic-bloco") { S.dicBloco = e.target.value; atualizarDicionario(); }
  else if (e.target.id === "dic-papel") { S.dicPapel = e.target.value; atualizarDicionario(); }
});

// A busca troca só o corpo da tabela: redesenhar a seção inteira tiraria o
// foco do campo a cada letra.
document.addEventListener("input", e => {
  if (!D) return;
  if (e.target.id === "busca-ranking") {
    S.busca = e.target.value;
    document.getElementById("corpo-ranking").innerHTML = corpoRanking();
  } else if (e.target.id === "busca-dic") {
    S.dicBusca = e.target.value; atualizarDicionario();
  }
});
function atualizarDicionario() {
  const c = corpoDicionario();
  document.getElementById("corpo-dic").innerHTML = c.html;
  document.getElementById("dic-contagem").textContent = `${c.n} de ${D.dicionario.colunas.length} colunas`;
}

// Dicas: guia vertical nos gráficos e caixinha nos mapas.
let graficoAtivo = null, mapaAtivo = null;
function esconderGrafico() {
  if (!graficoAtivo) return;
  graficoAtivo.querySelector(".g-guia").style.display = "none";
  graficoAtivo.querySelector(".g-dica").style.display = "none";
  graficoAtivo = null;
}
function esconderMapa() {
  if (mapaAtivo) mapaAtivo.querySelector(".dica-mapa").style.display = "none";
  mapaAtivo = null;
}
function aoMover(e) {
  const g = e.target.closest ? e.target.closest(".grafico[data-g]") : null;
  if (g !== graficoAtivo) esconderGrafico();
  if (g && GRAF[g.dataset.g]) {
    const m = GRAF[g.dataset.g], r = g.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width * m.W;
    const i = Math.max(0, Math.min(m.n - 1, Math.round((x - m.L) / m.iw * (m.n - 1))));
    const gx = (m.L + (m.n < 2 ? m.iw / 2 : i / (m.n - 1) * m.iw)) / m.W * 100;
    const guia = g.querySelector(".g-guia"), dica = g.querySelector(".g-dica");
    guia.style.cssText = `display:block;left:${gx}%;top:${m.T / m.H * 100}%;height:${m.ih / m.H * 100}%`;
    dica.innerHTML = m.dica(i);
    dica.style.display = "block";
    dica.style.top = "0";
    dica.style.left = gx + "%";
    dica.style.transform = gx > 55 ? "translateX(calc(-100% - 10px))" : "translateX(10px)";
    graficoAtivo = g;
  }
  const mapa = e.target.closest ? e.target.closest(".mapa") : null;
  const path = mapa && e.pointerType === "mouse" ? e.target.closest("path[data-k]") : null;
  if (mapa !== mapaAtivo || !path) esconderMapa();
  if (path && DICA_MAPA[path.dataset.k]) {
    const r = mapa.getBoundingClientRect(), dica = mapa.querySelector(".dica-mapa");
    dica.innerHTML = DICA_MAPA[path.dataset.k];
    dica.style.display = "block";
    dica.style.left = Math.max(6, Math.min(e.clientX - r.left + 16, r.width - 236)) + "px";
    dica.style.top = Math.max(6, e.clientY - r.top - 76) + "px";
    mapaAtivo = mapa;
  }
}
document.addEventListener("pointermove", aoMover);
document.addEventListener("pointerdown", e => { if (e.pointerType !== "mouse") aoMover(e); });
document.addEventListener("pointerleave", () => { esconderGrafico(); esconderMapa(); });

// Rótulos e passos dos eixos dependem da largura: redesenha ao cruzar o
// ponto de quebra do celular.
let eraEstreita = estreita();
window.addEventListener("resize", () => {
  if (estreita() !== eraEstreita) { eraEstreita = estreita(); render(); }
});

S.tela = telaDoEndereco();
desenharAbas();
fetch("dados/painel.json", { cache: "no-cache" })
  .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
  .then(dados => {
    D = dados;
    RIDE = projetar(D.malha, 800, 620);
    RAS = projetar(D.malhaRas, 800, 560);
    document.getElementById("topo-semana").textContent = `Semana ${D.semanaRotulo} · ${periodoSemana(D.dataInicio)}`;
    const g = D.geradoEm;
    let rodape = `Boletim gerado em ${g.slice(8, 10)}/${g.slice(5, 7)}/${g.slice(0, 4)} às ${g.slice(11, 16)} (horário de Brasília), com dados até a semana ${D.semanaRotulo}.`;
    if (D.semanaMaisRecente > D.semana) {
      rodape += ` A semana ${rotSemana(D.semanaMaisRecente)} já tem dados de parte dos municípios e entra quando o território estiver completo.`;
    }
    document.getElementById("rodape-gerado").textContent = rodape;
    render();
  })
  .catch(err => {
    conteudo.innerHTML = `<p class="carregando">Não foi possível carregar os dados da semana (${esc(err.message)}). Tente recarregar a página.</p>`;
  });
})();
