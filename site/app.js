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
  tela: "panorama", periodo: 52, ordem: "prob", busca: "", ind: "indice",
  mun: COD_FOCO, medida: "casos", dicBusca: "", dicBloco: "", dicPapel: "",
  // Séries: o padrão são dois anos. A série inteira é dominada pelo pico de
  // 2024 e a situação de agora vira uma linha rente ao chão.
  periodoSerie: 104, relSe: null, escala: "ra",
};
let D = null, RIDE = null, RAS = null;
let SETORES = null, SETORES_RAS = null, setoresPedido = false, setoresErro = null;
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
const maisDias = (d, n) => { const x = dia(d); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };
// Número curto para legenda de faixa: "348 mil" lê melhor que 348.000, e
// percentual pequeno precisa da casa decimal para não juntar faixas.
const curto = v => Math.abs(v) >= 1000 ? fmt(v / 1000) + " mil" : (Math.abs(v) >= 10 || v === Math.round(v)) ? fmt(v) : fmt(v, 1);
// Tendência recente: média de casos das últimas 3 semanas sobre a das
// últimas 8. A faixa morta de 10% em volta de 1 evita que ruído vire seta.
function tendencia(r) {
  if (r == null) return null;
  return r >= 1.1 ? { seta: "▲", nome: "subindo", cor: "var(--indice-elevado)" }
    : r <= 0.9 ? { seta: "▼", nome: "caindo", cor: "var(--indice-calmo)" }
      : { seta: "▬", nome: "estável", cor: "var(--color-neutral-600)" };
}
const celTendencia = r => {
  const t = tendencia(r);
  return t ? `<span class="tend" style="color:${t.cor}" title="${t.nome}">${t.seta} ${fmt(r, 2)}</span>` : "—";
};
// Arquivo CSV no formato do Excel em português: ponto e vírgula, vírgula
// decimal e BOM para os acentos.
function baixarCsv(linhas, nome) {
  const cel = v => /[;"\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const csv = "﻿" + linhas.map(l => l.map(cel).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const dec = (v, c) => v == null ? "" : Number(v).toFixed(c).replace(".", ",");
// Faixas por quantil, e não escala linear: a população das RAs vai de 2 mil a
// 348 mil, e numa escala linear 18 das 31 cairiam no mesmo tom claro. Por
// quartil cada faixa recebe cerca de um quarto das áreas. Quando um quarto ou
// mais está no mínimo (as quadras com 0% de esgoto inadequado, por exemplo),
// o mínimo vira faixa própria e o resto se divide em tercis.
const CORES_FAIXA = ["var(--color-accent-200)", "var(--color-accent-400)", "var(--color-accent-600)", "var(--color-accent-800)"];
function classes(valores, sufixo = "") {
  const v = valores.filter(x => x != null && isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return { rotulos: [], de: () => -1 };
  const q = (lista, p) => { const i = (lista.length - 1) * p, a = Math.floor(i); return lista[a] + (lista[Math.min(a + 1, lista.length - 1)] - lista[a]) * (i - a); };
  const min = v[0], nMin = v.filter(x => x === min).length;
  const zero = nMin / v.length >= 0.25 && nMin < v.length;
  const base = zero ? v.filter(x => x > min) : v;
  let bordas = zero ? [base[0], q(base, 1 / 3), q(base, 2 / 3), base[base.length - 1]]
    : [min, q(v, 0.25), q(v, 0.5), q(v, 0.75), v[v.length - 1]];
  bordas = bordas.filter((c, i) => i === 0 || c > bordas[i - 1]);
  const rotulos = zero ? [curto(min) + sufixo] : [];
  if (bordas.length === 1) rotulos.push(curto(bordas[0]) + sufixo);
  for (let i = 0; i < bordas.length - 1; i++) rotulos.push(`${curto(bordas[i])} a ${curto(bordas[i + 1])}${sufixo}`);
  const desloca = zero ? 1 : 0;
  const de = x => {
    if (x == null || !isFinite(x)) return -1;
    if (zero && x === min) return 0;
    for (let i = 1; i < bordas.length; i++) if (x <= bordas[i]) return desloca + i - 1;
    return desloca + Math.max(0, bordas.length - 2);
  };
  return { rotulos, de };
}
const legendaFaixas = (c, unidade) => `<div class="legenda" style="align-items:center">${c.rotulos.map((r, i) => `<span><i class="quadrado" style="background:${CORES_FAIXA[i]}"></i>${r}</span>`).join("")}<span class="mudo">· ${unidade}</span></div>`;

function periodoSemana(inicio) {
  const a = dia(inicio), b = new Date(a.getTime() + 6 * 864e5);
  if (a.getMonth() === b.getMonth()) {
    return `${a.getDate()} a ${b.getDate()} de ${MESES[b.getMonth()]}. de ${b.getFullYear()}`;
  }
  return `${a.getDate()} de ${MESES[a.getMonth()]}. a ${b.getDate()} de ${MESES[b.getMonth()]}. de ${b.getFullYear()}`;
}
// Frescor da fonte: um boletim de alerta precisa dizer de quando é o dado.
// Sem isso não dá para distinguir "está calmo" de "ninguém atualizou".
const HORAS_PARADO = 72;
function horasDesde(iso) {
  if (!iso) return null;
  const t = Date.parse(iso);
  return isFinite(t) ? Math.max(0, (Date.now() - t) / 36e5) : null;
}
function quando(h, iso) {
  if (h < 1) return `há ${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `há ${Math.round(h)} h`;
  const d = new Date(Date.parse(iso) - 3 * 36e5).toISOString();   // horário de Brasília
  return `em ${diaMesAno(d.slice(0, 10))}`;
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
  // Trecho de previsão: do índice `corte` em diante a primeira linha sai
  // tracejada, sobre um fundo que o marca. Os dois trechos dividem o ponto do
  // corte, para a linha não abrir um buraco na emenda. O fundo vem antes do
  // limiar, para não cobri-lo.
  const corte = o.corte != null && o.corte < n - 1 ? o.corte : null;
  if (corte != null) {
    const x0 = (px(corte) + px(corte + 1)) / 2;
    svg += `<rect x="${x0.toFixed(1)}" y="${T}" width="${(W - R - x0).toFixed(1)}" height="${ih}" fill="var(--color-accent-100)" opacity=".8"/>`;
    rotulos += `<div class="g-rot previsao" style="left:${pctX(x0 + 6)};top:${pctY(T + 4)}">previsão</div>`;
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
  linhas.forEach((l, k) => {
    if (k === 0 && corte != null) {
      const antes = l.v.map((v, i) => i <= corte ? v : null), depois = l.v.map((v, i) => i >= corte ? v : null);
      svg += `<path d="${caminho(antes)}" fill="none" stroke="${l.cor}" stroke-width="${l.w}" stroke-linejoin="round" stroke-linecap="round"/>`;
      svg += `<path d="${caminho(depois)}" fill="none" stroke="${l.cor}" stroke-width="${l.w}" stroke-dasharray="6 5" stroke-linejoin="round" stroke-linecap="round"/>`;
      return;
    }
    svg += `<path d="${caminho(l.v)}" fill="none" stroke="${l.cor}" stroke-width="${l.w}" stroke-dasharray="${l.dash || "none"}" stroke-linejoin="round" stroke-linecap="round"/>`;
  });
  if (o.valores) {
    const l = linhas[0], marcado = o.atual != null ? o.atual : n - 1;
    l.v.forEach((v, i) => {
      if (v == null) return;
      const ultimo = i === marcado;
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
// `lim` permite projetar duas malhas no mesmo enquadramento (as quadras com o
// contorno das RAs por cima). Cada feição devolve também o centro do seu maior
// anel, onde cabe o nome: a média dos vértices cai fora de RA com ilha.
function limites(geo) {
  let minX = 180, maxX = -180, minY = 90, maxY = -90;
  const anda = c => {
    if (typeof c[0] === "number") {
      if (c[0] < minX) minX = c[0]; if (c[0] > maxX) maxX = c[0];
      if (c[1] < minY) minY = c[1]; if (c[1] > maxY) maxY = c[1];
      return;
    }
    c.forEach(anda);
  };
  geo.features.forEach(f => anda(f.geometry.coordinates));
  return { minX, maxX, minY, maxY };
}
function projetar(geo, W, H, lim) {
  const { minX, maxX, minY, maxY } = lim || limites(geo);
  const k = Math.cos((minY + maxY) / 2 * Math.PI / 180);
  const lw = (maxX - minX) * k, lh = maxY - minY, e = Math.min(W / lw, H / lh) * 0.96;
  const ox = (W - lw * e) / 2, oy = (H - lh * e) / 2;
  const pr = ([x, y]) => [ox + (x - minX) * k * e, oy + (maxY - y) * e];
  return geo.features.map(f => {
    const g = f.geometry;
    const aneis = g.type === "Polygon" ? g.coordinates : g.type === "MultiPolygon" ? g.coordinates.flat() : [];
    let maior = null, area = -1;
    const d = aneis.map(a => {
      const q = a.map(pr);
      // Área e centroide do anel (fórmula do laço).
      let s = 0, cx = 0, cy = 0;
      for (let i = 0; i < q.length - 1; i++) {
        const t = q[i][0] * q[i + 1][1] - q[i + 1][0] * q[i][1];
        s += t; cx += (q[i][0] + q[i + 1][0]) * t; cy += (q[i][1] + q[i + 1][1]) * t;
      }
      if (Math.abs(s) > area && s !== 0) { area = Math.abs(s); maior = [cx / (3 * s), cy / (3 * s)]; }
      return q.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("") + "Z";
    }).join("");
    const c = maior || pr(aneis[0] ? aneis[0][0] : [minX, minY]);
    return { props: f.properties, d, cx: c[0], cy: c[1] };
  });
}
// Nomes sobre o mapa sem se atropelarem: os maiores primeiro, e quem
// encostar num nome já posto fica só na dica e na tabela. A caixa de cada
// nome leva em conta o comprimento do texto, no tamanho de letra do mapa.
function desempilhar(itens, tamanho, folga = 8) {
  const postos = [];
  return itens.filter(it => {
    const w = String(it.props.nome).length * tamanho * 0.5 + folga, h = tamanho * 1.15 + folga;
    const c = { x0: it.cx - w / 2, x1: it.cx + w / 2, y0: it.cy - h / 2, y1: it.cy + h / 2 };
    if (postos.some(q => !(c.x1 < q.x0 || c.x0 > q.x1 || c.y1 < q.y0 || c.y0 > q.y1))) return false;
    postos.push(c); return true;
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

// ------------------------------------------------- o município escolhido
// Panorama, mapa, séries e relatório mostram o mesmo município, e o endereço
// guarda a escolha: vigia.guimm.site/#panorama/planaltina abre direto em
// Planaltina (GO). A série completa de cada município vem num arquivo próprio,
// baixado só quando alguém o escolhe; a de Brasília já vem no painel.json.
const TELAS_MUN = new Set(["panorama", "mapa", "series", "ranking"]);
const UF_NOME = { DF: "Distrito Federal", GO: "Goiás", MG: "Minas Gerais" };
const SERIES = {}, SERIES_PEDIDAS = {};
const munAtual = () => porCod(S.mun) || D.foco;
const porSlug = slug => D.municipios.find(m => m.slug === slug);
const nomeUf = m => m.cod === COD_FOCO ? m.nome : `${m.nome} (${m.uf})`;
const enderecoDe = (tela, cod) => "#" + tela + (TELAS_MUN.has(tela) && cod !== COD_FOCO && porCod(cod) ? "/" + porCod(cod).slug : "");

function serieDe(cod) {
  if (cod === COD_FOCO) return D.serie;
  if (SERIES[cod]) return SERIES[cod];
  if (!SERIES_PEDIDAS[cod]) {
    SERIES_PEDIDAS[cod] = true;
    fetch(`dados/municipios/${cod}.json`, { cache: "no-cache" })
      .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(j => { SERIES[cod] = j.serie; if (S.mun === cod) render(); })
      .catch(err => { SERIES[cod] = { erro: err.message }; if (S.mun === cod) render(); });
  }
  return null;
}
function variacaoDe(s) {
  if (s.length < 2 || !s[s.length - 2].e) return null;
  return Math.round((s[s.length - 1].e - s[s.length - 2].e) / s[s.length - 2].e * 100);
}
function seletorMunicipio() {
  const lista = D.municipios.slice().sort((a, b) => (b.cod === COD_FOCO) - (a.cod === COD_FOCO) || a.nome.localeCompare(b.nome, "pt-BR"));
  return `<label class="seletor-mun"><span class="pequeno mudo">Município</span>
    <select class="select" data-mun aria-label="Escolher o município">${lista.map(m => `<option value="${m.cod}"${m.cod === S.mun ? " selected" : ""}>${esc(m.nome)} — ${m.uf}</option>`).join("")}</select></label>`;
}
const topoMun = rotulo => `<div class="topo-mun"><div class="rotulo">${rotulo}</div>${seletorMunicipio()}</div>`;
// Enquanto a série do município chega (ou se falhar), a seção mostra o
// seletor e um aviso — nunca uma tela em branco.
function esperandoSerie(rotulo, m, serie) {
  const msg = serie && serie.erro
    ? `Não foi possível carregar a série de ${esc(nomeUf(m))} (${esc(serie.erro)}). Tente recarregar a página.`
    : `Carregando a série de ${esc(nomeUf(m))}…`;
  return `<section class="secao"><div class="cabeca">${topoMun(rotulo)}</div><p class="carregando">${msg}</p></section>`;
}
const serieOk = s => s && !s.erro;

// ============================================================== I PANORAMA
function vistaPanorama() {
  const f = munAtual(), bsb = f.cod === COD_FOCO, nome = f.nome;
  const serie = serieDe(f.cod);
  const rotulo = `I · Panorama de ${esc(nome)} · ${UF_NOME[f.uf] || f.uf}`;
  if (!serieOk(serie)) return esperandoSerie(rotulo, f, serie);
  const h = D.horizonte, lim = D.limiar, emAlerta = (f.prob || 0) >= lim;
  const vr = bsb ? D.foco.variacao : variacaoDe(serie);
  const variacao = vr == null ? "" : vr === 0
    ? ", o mesmo número da semana anterior"
    : `, ${Math.abs(vr)}% ${vr < 0 ? "a menos" : "a mais"} que na semana anterior`;
  const lede = `Nesta semana, estima-se que ${esc(nomeUf(f))} teve ${fmt(f.est)} ${f.est === 1 ? "caso" : "casos"} de dengue, o equivalente a ${fmt(f.inc, 1)} por 100 mil habitantes${variacao}. O modelo calcula ${pct(f.prob)} de chance de o risco chegar a alto ou muito alto nas próximas ${h} semanas, ${emAlerta ? "acima" : "abaixo"} do limiar de alerta de ${pct(lim)}.`;

  // Posição na chance de alerta: a lista do JSON já vem nessa ordem.
  const pos = D.municipios.findIndex(m => m.cod === f.cod) + 1;
  const nEntorno = D.entorno.emAlerta;
  const entornoFrase = nEntorno === 0 ? "Nenhum município do Entorno passou do limiar."
    : nEntorno === 1 ? "1 município do Entorno passou do limiar."
      : `${nEntorno} municípios do Entorno passaram do limiar.`;
  const alertaFrase = emAlerta
    ? `${esc(nome)} está em alerta: ${pct(f.prob)} de chance de risco alto ou muito alto em ${h} semanas. Pesaram mais: ${esc(listaFatores(f.fatores))}.`
    : bsb ? `Brasília não está em alerta nesta semana. ${entornoFrase}`
      : `${esc(nome)} não está em alerta nesta semana. É o ${pos}º de ${D.totalMunicipios} municípios em chance de alerta.`;

  const escala = D.ordemRisco.map(r => `<div class="${r === f.risco ? "atual" : ""}"><i style="background:${COR_RISCO[r]}"></i>${cap(r)}</div>`).join("");
  const s = serie.slice(-S.periodo);
  const est = s.map(p => p.e), hi = s.map(p => p.hi == null ? p.e : p.hi), lo = s.map(p => p.lo == null ? p.e : p.lo);
  const max = redondo(Math.max(1, ...hi.concat(est).filter(v => v != null)) * 1.05);
  const casos = grafico("casos", s.map(p => mesAno(p.d)), [
    { v: est, cor: "var(--color-accent-800)", w: 2 },
    { v: s.map(p => p.n), cor: "var(--color-neutral-600)", w: 1.2, dash: "4 4" },
  ], {
    max, hi, lo, ponto: true, titulo: `Casos estimados de dengue em ${nome} por semana`,
    passo: Math.ceil(s.length / (estreita() ? 4 : 6)),
    dica: i => `<strong>semana de ${diaMesAno(s[i].d)}</strong>${fmt(s[i].e)} casos estimados<br>${fmt(s[i].n)} notificados${lo[i] !== hi[i] ? `<br><span class="mudo">margem: ${fmt(lo[i])} a ${fmt(hi[i])}</span>` : ""}`,
  });

  const b = D.foco;
  const contexto = bsb ? `<div class="linhas">
          <h4 style="margin-bottom:6px">O Entorno nesta semana</h4>
          ${linhaValor("Municípios", fmt(D.entorno.municipios))}
          ${linhaValor("Casos estimados", fmt(D.entorno.est))}
          ${linhaValor("Em risco alto ou muito alto", fmt(D.entorno.altoRisco))}
          ${linhaValor("Em alerta", fmt(D.entorno.emAlerta))}
          <p class="pequeno mudo justo" style="margin-top:12px">Quem mora no Entorno trabalha e estuda em Brasília, e o vírus acompanha esse vaivém diário nos dois sentidos.</p>
        </div>` : `<div class="linhas">
          <h4 style="margin-bottom:6px">Brasília nesta semana</h4>
          ${linhaValor("Casos estimados", fmt(b.est))}
          ${linhaValor("Por 100 mil hab.", fmt(b.inc, 1))}
          ${linhaValor("Nível de risco", cap(esc(b.risco)))}
          ${linhaValor("Chance de alerta", pct(b.prob))}
          <p class="pequeno mudo justo" style="margin-top:12px">Brasília concentra trabalho e estudo de toda a região, e o vírus acompanha esse vaivém diário nos dois sentidos. <a href="#panorama">Ver o panorama de Brasília</a>.</p>
        </div>`;

  return `<section class="secao">
    <div class="cabeca">
      ${topoMun(rotulo)}
      <h1 class="titulo-1">Dengue em ${esc(nome)}: risco ${esc(f.risco)}</h1>
      <p class="lede justo">${lede}</p>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="rotulo">Casos estimados</div><div class="kpi-valor">${fmt(f.est)}</div>
        <div class="kpi-nota">${sinal(vr)} frente à semana anterior · ${fmt(f.casos)} já notificados</div></div>
      <div class="kpi"><div class="rotulo">Incidência</div><div class="kpi-valor">${fmt(f.inc, 1)}</div>
        <div class="kpi-nota">casos por 100 mil habitantes${f.canalQ3 != null ? ` · o esperado para a época vai até ${fmt(f.canalQ3, 1)}` : ""}</div></div>
      <div class="kpi"><div class="rotulo">Nível de risco</div><div class="kpi-valor texto-risco">${cap(esc(f.risco))}</div>
        <div class="escala">${escala}</div></div>
      <div class="kpi"><div class="rotulo">Chance de risco alto em ${h} semanas</div><div class="kpi-valor">${pct(f.prob)}</div>
        ${barraProb(f.prob)}<div class="kpi-nota">traço: limiar de alerta de ${pct(lim)}</div></div>
    </div>
    <div>
      <div class="faixa"><span class="tag tag-outline">${emAlerta ? "Em alerta" : "Fora de alerta"}</span><span>${alertaFrase}</span></div>
      ${(() => {
        const hv = horasDesde(D.verificadoEm);
        return hv != null && hv > HORAS_PARADO ? `<div class="faixa"><span class="tag tag-outline">Dado parado</span><span>A fonte não é verificada desde ${quando(hv, D.verificadoEm).replace(/^em /, "")}, há ${Math.floor(hv / 24)} dias. O ciclo diário de atualização pode ter parado: confira antes de usar este boletim.</span></div>` : "";
      })()}
      ${f.provisorio ? `<div class="faixa"><span class="tag tag-neutral">Dado provisório</span><span>Só ${pct(f.completude)} das notificações desta semana já foram digitadas. Os ${fmt(f.casos)} casos notificados ainda vão subir; por isso o boletim trabalha com os ${fmt(f.est)} casos estimados.</span></div>` : ""}
      ${bsb ? `<div class="faixa"><span class="tag tag-neutral">Cidades do DF</span><span>Mora em Planaltina, Ceilândia, Taguatinga ou outra cidade do DF? Os números do Distrito Federal são de Brasília inteira: não existe fonte pública com casos por Região Administrativa. As condições de cada uma (esgoto, água, lixo, drenagem) estão em <a href="#ras">VI · Por RA</a>. Planaltina de Goiás, município do Entorno, tem panorama próprio: <a href="${enderecoDe("panorama", (porSlug("planaltina") || {}).cod)}">ver Planaltina (GO)</a>.</span></div>` : ""}
    </div>
    <div class="duas-uma">
      <div class="coluna">
        <div class="barra-titulo"><h3>Casos estimados por semana</h3>${seg("periodo", S.periodo, [[52, "52 semanas"], [156, "3 anos"]])}</div>
        ${casos}
        <div class="legenda"><span><i class="traco"></i>casos estimados</span><span><i class="traco tracejado"></i>casos já notificados</span><span><i class="caixa"></i>margem de incerteza</span></div>
        <p class="pequeno mudo"><a href="${enderecoDe("series", f.cod)}">A série completa de ${esc(nome)}, desde ${serie[0].d.slice(0, 4)}</a> · <a href="${enderecoDe("mapa", f.cod)}">os índices da semana</a> · <a href="${enderecoDe("ranking", f.cod)}">o relatório de qualquer semana</a></p>
      </div>
      <div class="coluna-larga">
        ${contexto}
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
  // Em "Risco à frente" o eixo é a semana PREVISTA: a chance calculada na
  // semana t fala do risco em t + horizonte. O gráfico avança além do dado, e
  // esse trecho sai tracejado, como previsão.
  const h = D.horizonte, ultima = m.semanas.length ? m.semanas[m.semanas.length - 1].d : null;
  let rot = m.semanas.map(s => diaMes(s.d)), corte = null, atual = null;
  if (S.medida === "risco") {
    rot = m.semanas.map(s => diaMes(maisDias(s.d, 7 * h)));
    corte = atual = Math.max(0, m.semanas.length - 1 - h);
  }
  const nota = md.nota || `Cada ponto é a semana prevista: a chance de risco alto ou muito alto calculada ${h} semanas antes. O trecho tracejado, no fundo marcado, é a previsão para as próximas ${h} semanas; o círculo aberto é a semana de ${ultima ? diaMes(ultima) : "hoje"}, a mais recente com dado. A linha pontilhada marca o limiar de alerta de ${pct(D.limiar)}.`;
  const g = validos.length ? grafico("semanas", rot, [{ v: vs, cor: md.cor, w: 2 }], {
    min, max, fy, valores: md.f, nt: 4, H: 250, passo: estreita() ? 2 : 1, titulo: `${md.rot} em ${m.nome}, semana a semana`,
    limiar: S.medida === "risco" ? D.limiar : null, corte, atual,
  }) : `<p class="mudo">Sem dado de ${md.rot.toLowerCase()} para este município.</p>`;
  return `<div class="coluna">
    <div class="barra-titulo"><h3>Semana a semana em ${esc(m.nome)}</h3>${seg("medida", S.medida, Object.entries(MEDIDAS).map(([k, v]) => [k, v.rot]))}</div>
    ${g}<p class="pequeno mudo">${nota}</p></div>`;
}

function vistaMapa() {
  const m = munAtual();
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
          <select class="select" data-mun>${opcoes}</select></label>
        <div class="card" style="gap:4px">
          <div class="card-kicker">${kicker}</div>
          <div class="ficha-nome">${esc(m.nome)}</div>
          ${linhaValor("Casos estimados", fmt(m.est))}
          ${linhaValor("Por 100 mil hab.", fmt(m.inc, 1))}
          ${linhaValor("Nível de risco", cap(esc(m.risco)))}
          ${linhaValor("Chance de alerta", pct(m.prob))}
          ${linhaValor("População", fmt(m.pop))}
          <div class="pequeno mudo" style="padding-top:8px;border-top:1px solid var(--color-divider)">Pesaram mais: ${esc(listaFatores(m.fatores))}</div>
          <div class="filtros" style="margin-top:12px">
            <a class="btn btn-primary" href="${enderecoDe("panorama", m.cod)}">Panorama completo de ${esc(m.nome)}</a>
            ${m.cod !== COD_FOCO ? `<button class="btn btn-secondary" type="button" data-acao="sel" data-valor="${COD_FOCO}">Voltar para Brasília</button>` : ""}
          </div>
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
const PERIODOS_SERIE = [[52, "1 ano"], [104, "2 anos"], [260, "5 anos"], [0, "Tudo"]];
const recorte = lista => S.periodoSerie ? lista.slice(-S.periodoSerie) : lista.slice();
// Rótulo do eixo de datas: mês e ano no recorte curto, só o ano no longo.
const rotuloData = (lista) => lista.length > 300 ? lista.map(p => p.d.slice(0, 4)) : lista.map(p => mesAno(p.d));
const passoData = (lista) => lista.length > 300 ? 52 : Math.ceil(lista.length / (estreita() ? 4 : 8));

function vistaSeries() {
  const m = munAtual(), bsb = m.cod === COD_FOCO, nome = m.nome;
  const serie = serieDe(m.cod);
  const rotulo = `III · Séries temporais · ${esc(nomeUf(m))}`;
  if (!serieOk(serie)) return esperandoSerie(rotulo, m, serie);
  const s = recorte(serie), primeira = serie[0];
  const hi = s.map(p => p.hi == null ? p.e : p.hi), lo = s.map(p => p.lo == null ? p.e : p.lo);
  const historia = grafico("historia", rotuloData(s), [
    { v: s.map(p => p.e), cor: "var(--color-accent-800)", w: 1.8 },
    { v: s.map(p => p.n), cor: "var(--color-neutral-600)", w: 1, dash: "4 4" },
  ], {
    max: redondo(Math.max(1, ...hi.concat(s.map(p => p.e)).filter(v => v != null)) * 1.05), hi, lo, W: 1100, H: 320, ponto: true,
    passo: passoData(s), titulo: `Casos de dengue em ${nome} por semana`,
    dica: i => `<strong>semana ${rotSemana(s[i].se)} · ${diaMesAno(s[i].d)}</strong>${fmt(s[i].e)} casos estimados<br>${fmt(s[i].n)} notificados${lo[i] !== hi[i] ? `<br><span class="mudo">margem: ${fmt(lo[i])} a ${fmt(hi[i])}</span>` : ""}`,
  });
  // Canal endêmico: a incidência contra o limite esperado da época (o
  // terceiro quartil histórico daquela semana do ano, só com anos anteriores).
  const canal = grafico("canal", rotuloData(s), [
    { v: s.map(p => p.inc), cor: "var(--color-accent-800)", w: 1.8 },
    { v: s.map(p => p.q3), cor: "var(--color-neutral-600)", w: 1.3, dash: "5 4" },
  ], {
    max: redondo(Math.max(1, ...s.map(p => Math.max(p.inc || 0, p.q3 || 0))) * 1.05), W: 1100, H: 260,
    passo: passoData(s), titulo: `Incidência de ${nome} e limite esperado da época`,
    dica: i => `<strong>semana ${rotSemana(s[i].se)} · ${diaMesAno(s[i].d)}</strong>${fmt(s[i].inc, 1)} por 100 mil<br>esperado até ${s[i].q3 == null ? "— (sem histórico)" : fmt(s[i].q3, 1)}`,
  });
  // Comparação: Brasília frente ao Entorno; qualquer outro município, frente
  // a Brasília. As duas curvas por 100 mil, que é o que as torna comparáveis.
  let comp, tituloComp, legendaComp;
  if (bsb) {
    const ns = s.length, cb = D.comparacao.Brasilia.slice(-ns), ce = D.comparacao.Entorno.slice(-ns);
    comp = grafico("comp", rotuloData(cb), [
      { v: cb.map(p => p.v), cor: "var(--color-accent-700)", w: 2.2 },
      { v: ce.map(p => p.v), cor: "var(--color-neutral-600)", w: 1.5, dash: "5 4" },
    ], {
      max: redondo(Math.max(1, ...cb.concat(ce).map(p => p.v)) * 1.05), W: 1100, H: 320,
      passo: passoData(cb), titulo: "Incidência por 100 mil: Brasília e Entorno",
      dica: i => `<strong>semana de ${diaMesAno(cb[i].d)}</strong>Brasília: ${fmt(cb[i].v, 1)} por 100 mil<br>Entorno: ${ce[i] ? fmt(ce[i].v, 1) : "—"} por 100 mil`,
    });
    tituloComp = "Brasília frente ao Entorno";
    legendaComp = `<span><i class="traco bsb"></i>Brasília</span><span><i class="traco entorno"></i>Entorno (RIDE)</span>`;
  } else {
    const deBsb = {};
    D.serie.forEach(p => { deBsb[p.d] = p.inc; });
    comp = grafico("comp", rotuloData(s), [
      { v: s.map(p => p.inc), cor: "var(--color-accent-700)", w: 2.2 },
      { v: s.map(p => deBsb[p.d] == null ? null : deBsb[p.d]), cor: "var(--color-neutral-600)", w: 1.5, dash: "5 4" },
    ], {
      max: redondo(Math.max(1, ...s.map(p => Math.max(p.inc || 0, deBsb[p.d] || 0))) * 1.05), W: 1100, H: 320,
      passo: passoData(s), titulo: `Incidência por 100 mil: ${nome} e Brasília`,
      dica: i => `<strong>semana de ${diaMesAno(s[i].d)}</strong>${esc(nome)}: ${fmt(s[i].inc, 1)} por 100 mil<br>Brasília: ${deBsb[s[i].d] == null ? "—" : fmt(deBsb[s[i].d], 1)} por 100 mil`,
    });
    tituloComp = `${esc(nome)} frente a Brasília`;
    legendaComp = `<span><i class="traco bsb"></i>${esc(nome)}</span><span><i class="traco entorno"></i>Brasília</span>`;
  }
  const acima = s.filter(p => p.q3 != null && p.inc != null && p.inc > p.q3).length;
  const comQ3 = s.filter(p => p.q3 != null).length;
  const u = serie.slice(-16);
  const uhi = u.map(p => p.hi == null ? p.e : p.hi), ulo = u.map(p => p.lo == null ? p.e : p.lo);
  const notif = grafico("notif", u.map(p => diaMes(p.d)), [
    { v: u.map(p => p.e), cor: "var(--color-accent-800)", w: 2 },
    { v: u.map(p => p.n), cor: "var(--color-neutral-600)", w: 1.2, dash: "4 4" },
  ], {
    max: redondo(Math.max(1, ...uhi) * 1.05), hi: uhi, lo: ulo, H: 260, passo: estreita() ? 5 : 3,
    titulo: "Casos notificados e estimados nas últimas 16 semanas",
    dica: i => `<strong>semana de ${diaMesAno(u[i].d)}</strong>${fmt(u[i].e)} estimados<br>${fmt(u[i].n)} notificados`,
  });
  const texto = bsb
    ? `Série de Brasília, semana a semana, de ${rotSemana(primeira.se)} a ${D.semanaRotulo}. O InfoDengue publica casos por município, e o Distrito Federal é um único município: esta é a série do território inteiro, cidades-satélite incluídas.`
    : `Série de ${esc(nomeUf(m))}, semana a semana, de ${rotSemana(primeira.se)} a ${D.semanaRotulo}, com os mesmos cálculos de Brasília: casos estimados pelo InfoDengue, incidência por 100 mil habitantes e canal endêmico do próprio município.${m.pop < 20000 ? ` Com ${fmt(m.pop)} habitantes, poucos casos já movem muito a incidência: leia as variações com cautela.` : ""}`;
  return `<section class="secao">
    <div class="cabeca">
      ${topoMun(rotulo)}
      <h2 class="titulo-2">A dengue em ${esc(nome)} desde ${primeira.d.slice(0, 4)}</h2>
      <p class="texto justo">${texto}</p>
    </div>
    <div class="barra-titulo">
      <h3>Casos por semana</h3>
      ${seg("periodo-serie", S.periodoSerie, PERIODOS_SERIE)}
    </div>
    ${historia}
    <div class="legenda"><span><i class="traco"></i>casos estimados</span><span><i class="traco tracejado"></i>casos já notificados</span><span><i class="caixa"></i>margem de incerteza do <em>nowcasting</em></span></div>
    <hr class="hr">
    <div class="coluna">
      <h3>Canal endêmico</h3>
      <p class="pequeno mudo" style="font-size:13px">Incidência acima do limite esperado indica atividade acima do padrão histórico daquela semana do ano no município. No período mostrado, ${fmt(acima)} de ${fmt(comQ3)} semanas passaram do limite.</p>
      ${canal}
      <div class="legenda"><span><i class="traco"></i>incidência por 100 mil</span><span><i class="traco entorno"></i>limite esperado (terceiro quartil histórico da semana)</span></div>
    </div>
    <hr class="hr">
    <div class="coluna">
      <h3>${tituloComp}</h3>
      <p class="pequeno mudo" style="font-size:13px">Incidência por 100 mil habitantes${bsb ? ", padronizada pela população de cada grupo" : ""} — o que torna as duas curvas comparáveis apesar da diferença de porte.</p>
      ${comp}
      <div class="legenda">${legendaComp}</div>
    </div>
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
  if (!linhas.length) return `<tr><td colspan="8" class="mudo">Nenhum município com esse nome.</td></tr>`;
  return linhas.map(({ m, pos }) => `<tr class="${m.cod === COD_FOCO ? "destaque" : ""}">
    <td class="num mudo">${pos}</td>
    <td><div class="nome-mun"><a class="link-mun" href="${enderecoDe("panorama", m.cod)}">${esc(m.nome)}</a> <span class="pequeno mudo" style="font-family:var(--font-body);font-weight:400">${m.uf}</span></div><div class="pequeno mudo">${esc(cap(listaFatores(m.fatores)))}</div></td>
    <td class="dir">${fmt(m.est)}</td>
    <td class="dir">${fmt(m.inc, 1)}</td>
    <td class="dir">${celTendencia(m.tend)}</td>
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
    <div class="tabela-rolavel"><table class="table" style="min-width:920px">
      <thead><tr><th style="width:36px">#</th><th>Município</th><th class="dir">Casos est.</th><th class="dir">Por 100 mil</th><th class="dir">Tendência</th><th>Risco</th><th style="width:200px">Chance de alerta</th><th>Situação</th></tr></thead>
      <tbody id="corpo-ranking">${corpoRanking()}</tbody>
    </table></div>
    <p class="pequeno mudo">Linha destacada: Brasília. O traço vertical na barra marca o limiar de alerta de ${pct(D.limiar)}. Semana ${D.semanaRotulo}, casos estimados. <strong style="font-weight:600">Tendência</strong> não é previsão: é a média de casos das últimas 3 semanas dividida pela das últimas 8. Acima de 1,1 a curva está subindo (▲); abaixo de 0,9, caindo (▼). Entra no modelo como uma das variáveis.</p>
    <hr class="hr">
    ${relatorio()}
  </section>`;
}

// Relatório de Brasília em qualquer semana da série: o retrato de uma semana
// passada, com o que o boletim dizia dela.
function relatorio() {
  const m = munAtual(), serie = serieDe(m.cod);
  if (!serieOk(serie)) return `<div class="coluna"><div class="barra-titulo"><h3>Relatório da semana: ${esc(nomeUf(m))}</h3>${seletorMunicipio()}</div><p class="carregando">${serie && serie.erro ? `Não foi possível carregar a série (${esc(serie.erro)}).` : "Carregando a série…"}</p></div>`;
  const se = S.relSe || serie[serie.length - 1].se;
  const r = serie.find(p => p.se === se) || serie[serie.length - 1];
  const opcoes = serie.slice().reverse().map(p => `<option value="${p.se}"${p.se === r.se ? " selected" : ""}>Semana ${rotSemana(p.se)} · ${diaMesAno(p.d)}</option>`).join("");
  const margem = r.lo != null && r.hi != null && r.lo !== r.hi ? ` <span class="pequeno mudo">(margem ${fmt(r.lo)} a ${fmt(r.hi)})</span>` : "";
  const completa = r.pv ? `não${r.c != null ? ` — ${pct(r.c)} digitado` : ""}` : "sim";
  const linhas = [
    ["Casos notificados", fmt(r.n)],
    ["Casos estimados", fmt(r.e) + margem],
    ["Incidência por 100 mil", fmt(r.inc, 1)],
    ["Limite esperado da época", r.q3 == null ? "— (sem anos anteriores)" : fmt(r.q3, 1)],
    ["Nível de risco", r.r ? cap(esc(r.r)) : "—"],
    [`Chance de risco alto em ${D.horizonte} semanas`, r.p == null ? "— (sem previsão)" : pct(r.p) + (r.p >= D.limiar ? ` <span class="tag tag-outline">Em alerta</span>` : "")],
    ["Notificação completa", completa],
  ].map(([a, b]) => `<tr><td>${a}</td><td class="dir">${b}</td></tr>`).join("");
  return `<div class="duas-uma">
    <div class="coluna">
      <div class="barra-titulo"><h3>Relatório da semana: ${esc(nomeUf(m))}</h3>
        <div class="filtros">${seletorMunicipio()}<select class="select" id="rel-semana" aria-label="Escolher a semana">${opcoes}</select></div></div>
      <table class="table relatorio"><tbody>${linhas}</tbody></table>
      <p class="texto"><strong style="font-weight:600">O que mais pesou na previsão:</strong> ${esc(listaFatores(r.f))}.</p>
      ${r.pv ? `<div class="faixa"><span class="tag tag-neutral">Dado provisório</span><span>Notificação ainda incompleta nesta semana${r.c != null ? ` (${pct(r.c)} digitado)` : ""}. Os casos observados tendem a subir.</span></div>` : ""}
    </div>
    <div class="card">
      <div class="card-kicker">A série inteira</div>
      <p style="font-size:14px;line-height:1.6">${fmt(serie.length)} semanas, de ${rotSemana(serie[0].se)} a ${rotSemana(serie[serie.length - 1].se)}: casos notificados e estimados, margem, incidência, limite esperado, risco, chance de alerta, fatores e completude da notificação.</p>
      <button class="btn btn-primary" type="button" data-acao="baixar-serie" style="align-self:flex-start;margin-top:6px">Baixar a série de ${esc(m.nome)} (CSV)</button>
    </div>
  </div>`;
}

function baixarSerie() {
  const linhas = [["semana_epidemiologica", "inicio_da_semana", "casos_notificados", "casos_estimados", "casos_est_min", "casos_est_max",
    "incidencia_100k", "limite_esperado_q3", "risco", "chance_de_alerta_pct", "fatores", "dado_provisorio", "completude_pct"]];
  const m = munAtual(), serie = serieDe(m.cod);
  if (!serieOk(serie)) return;
  serie.forEach(p => linhas.push([rotSemana(p.se), p.d, p.n, dec(p.e, 1), dec(p.lo, 1), dec(p.hi, 1), dec(p.inc, 2), dec(p.q3, 2),
    p.r || "", p.p == null ? "" : dec(p.p * 100, 1), listaFatores(p.f), p.pv ? "sim" : "nao", p.c == null ? "" : dec(p.c * 100, 1)]));
  baixarCsv(linhas, `vigia-dengue_${m.slug}_serie-completa_ate-SE${String(D.semana % 100).padStart(2, "0")}-${Math.floor(D.semana / 100)}.csv`);
}

function baixarRanking() {
  const linhas = [["posicao", "municipio", "uf", "casos_notificados", "casos_estimados", "incidencia_100k", "tendencia_mm3_mm8", "risco", "chance_de_alerta_pct", "em_alerta", "fatores"]];
  listaRanking().forEach(({ m, pos }) => linhas.push([pos, m.nome, m.uf, m.casos, dec(m.est, 1), dec(m.inc, 1), dec(m.tend, 2), m.risco,
    m.prob == null ? "" : Math.round(m.prob * 100), (m.prob || 0) >= D.limiar ? "sim" : "nao", listaFatores(m.fatores)]));
  baixarCsv(linhas, `vigia-dengue_ranking_SE${String(D.semana % 100).padStart(2, "0")}-${Math.floor(D.semana / 100)}.csv`);
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
    .map(r => `<tr class="${r.modelo === "Combinado" ? "destaque" : ""}"><td class="nome-mun">${MODELOS[r.modelo].nome}</td><td class="dir">${fmt(r.auc, 3)}</td><td class="dir">${fmt(r.auprc, 3)}</td><td class="dir">${fmt(r.sens, 3)}</td><td class="dir">${fmt(r.espec, 3)}</td><td class="dir">${fmt(r.vpp, 3)}</td><td class="dir">${fmt(r.brier, 3)}</td></tr>`).join("");
  const glossario = [
    ["Sensibilidade", "Das semanas que de fato chegaram a risco alto, quantas o modelo avisou antes."],
    ["Especificidade", "Das semanas calmas, quantas ele deixou de alarmar à toa."],
    ["VPP", "Quando o modelo avisa, quantas vezes o risco alto de fato veio."],
    ["AUC", "Capacidade geral de separar semanas de risco das calmas: 0,5 é acaso, 1 é perfeito."],
    ["AUPRC", "Como a AUC, mas olhando só para os avisos: resume a precisão do alerta em todos os limiares. Quanto mais perto de 1, melhor."],
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
        <div class="tabela-rolavel"><table class="table" style="min-width:640px">
          <thead><tr><th>Modelo</th><th class="dir">AUC</th><th class="dir">AUPRC</th><th class="dir">Sensibilidade</th><th class="dir">Especificidade</th><th class="dir">VPP</th><th class="dir">Brier</th></tr></thead>
          <tbody>${tabela}</tbody></table></div>
        <p class="pequeno mudo">Médias de ${des.anos[0]} a ${des.anos[1]}, sobre os ${D.totalMunicipios} municípios. O boletim opera com o combinado (${fmt(pb, 1)} × LightGBM + ${fmt(1 - pb, 1)} × persistência).</p>
        <div class="faixa" style="margin-top:8px"><span class="tag tag-outline">Em Brasília</span><span>No limiar de alerta de ${pct(D.limiar)}, ${pct(des.vppBrasilia)} dos alertas do combinado se confirmaram na validação ${des.anos[0]}–${des.anos[1]}.</span></div>
      </div>
      <div class="linhas"><h4 style="margin-bottom:4px">Como ler cada medida</h4>${glossario}</div>
    </div>
  </section>`;
}

// ============================================================ VI POR RA
// Os indicadores existem nas duas escalas, com nomes diferentes onde a coisa
// medida muda: população e densidade são da RA (na quadra, o que há é o número
// de domicílios), e o índice da quadra se chama "de criadouro" porque nela só
// entram condições locais, sem o componente populacional.
const PCT = { unid: "% dos domicílios", f: v => fmt(v, 1) + "%", sufixo: "%" };
const INDICADORES = {
  indice: { nome: "Vulnerabilidade", cab: "Índice (0 a 100)", unid: "índice de 0 a 100", f: v => fmt(v, 1), ra: p => (D.ras[p.cod] || {}).indice,
    nomeQ: "Índice de criadouro", q: p => p.indice,
    texto: "Média das condições abaixo, cada uma como distância relativa dentro do próprio DF. Ordena as RAs numa leitura só; não pondera as dimensões, porque não há estudo local que sustente pesos diferentes.",
    textoQ: "Na quadra o índice junta só as condições locais (esgoto, água, lixo, bueiro e pavimento), sem o componente populacional; por isso se chama de criadouro." },
  pop: { nome: "População", unid: "habitantes", f: v => fmt(v), ra: p => p.pop,
    nomeQ: "Domicílios", unidQ: "domicílios no setor", fQ: v => fmt(v), q: p => p.dom,
    texto: "Habitantes de cada RA. Mostra onde há mais gente exposta, não onde a condição é pior.",
    textoQ: "Número de domicílios de cada setor censitário. População e densidade são atributos da RA; na quadra, o que o Censo dá é a contagem de domicílios." },
  dens: { nome: "Densidade", unid: "hab./km²", f: v => fmt(v), ra: p => p.dens, soRa: true,
    texto: "Habitantes por km² de cada RA. Áreas densas favorecem a circulação do vírus entre vizinhos." },
  esgoto: Object.assign({ nome: "Esgoto inadequado", ra: p => (D.ras[p.cod] || {}).esgoto, q: p => p.esgoto,
    texto: "Domicílios com esgoto em fossa rudimentar, vala ou outra forma — água parada exposta." }, PCT),
  agua: Object.assign({ nome: "Sem água de rede", ra: p => (D.ras[p.cod] || {}).agua, q: p => p.agua,
    texto: "Domicílios sem ligação à rede geral. Levam ao armazenamento em caixas e tonéis, criadouro clássico do Aedes aegypti." }, PCT),
  lixo: Object.assign({ nome: "Lixo sem coleta", ra: p => (D.ras[p.cod] || {}).lixo, q: p => p.lixo,
    texto: "Lixo queimado, enterrado ou com outro destino, que acumula recipientes com água parada." }, PCT),
  bueiro: Object.assign({ nome: "Sem bueiro", ra: p => (D.ras[p.cod] || {}).bueiro, q: p => p.bueiro,
    texto: "Domicílios em face de rua sem boca de lobo. É a drenagem que decide se a chuva escoa ou empoça, e o Aedes se cria em água parada, não corrente: é o indicador de fluxo das águas na escala em que o mosquito vive." }, PCT),
  pavimento: Object.assign({ nome: "Rua sem pavimento", ra: p => (D.ras[p.cod] || {}).pavimento, q: p => p.pavimento,
    texto: "Domicílios em face de rua sem pavimento, onde a água empoça mesmo havendo drenagem." }, PCT),
};

function carregarSetores() {
  if (setoresPedido) return;
  setoresPedido = true;
  fetch("dados/setores.json", { cache: "no-cache" })
    .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(geo => {
      // As quadras ocupam só a mancha urbana: o enquadramento é o delas, e o
      // contorno das RAs vai por cima, no mesmo enquadramento, para orientar.
      const lim = limites(geo);
      SETORES = projetar(geo, 800, 620, lim);
      SETORES_RAS = projetar(D.malhaRas, 800, 620, lim);
      if (S.tela === "ras") render();
    })
    .catch(err => { setoresErro = err.message; if (S.tela === "ras") render(); });
}

function mapaQuadras(ind) {
  if (!SETORES) {
    carregarSetores();
    return `<p class="carregando">${setoresErro ? `Não foi possível carregar as quadras (${esc(setoresErro)}).` : "Carregando as quadras do DF…"}</p>`;
  }
  const valor = p => ind.q(p), f = ind.fQ || ind.f, unid = ind.unidQ || ind.unid;
  const cl = classes(SETORES.map(s => valor(s.props)), ind.sufixo || "");
  const paths = SETORES.map(s => {
    const p = s.props, v = valor(p), c = cl.de(v), k = "s" + p.cod;
    DICA_MAPA[k] = `<strong>${esc(p.ra)}</strong>${esc(ind.nomeQ || ind.nome)}: ${v == null ? "sem dado" : f(v)}<br><span class="mudo">Setor ${esc(p.cod)} · ${fmt(p.dom)} domicílios</span>`;
    return `<path d="${s.d}" data-k="${k}" fill="${c < 0 ? "var(--color-neutral-200)" : CORES_FAIXA[c]}" stroke="none"/>`;
  }).join("");
  const contornos = SETORES_RAS.map(r => `<path class="contorno" d="${r.d}"/>`).join("");
  const doms = SETORES.map(s => s.props.dom).filter(v => v != null).sort((a, b) => a - b);
  const mediana = doms.length ? doms[Math.floor(doms.length / 2)] : null;
  const piores = SETORES.filter(s => valor(s.props) != null).sort((a, b) => valor(b.props) - valor(a.props)).slice(0, 12);
  const tituloPiores = ind.q === INDICADORES.pop.q ? "As doze quadras com mais domicílios" : "As doze quadras em pior situação neste indicador";
  return `<div class="coluna" style="gap:12px">
      <div class="mapa mapa-ras mapa-quadra">
        <svg viewBox="0 0 800 620" role="img" aria-label="Mapa dos setores censitários urbanos do DF">${paths}${contornos}</svg>
        <div class="dica-mapa"></div>
      </div>
      ${legendaFaixas(cl, unid)}
      <p class="pequeno mudo justo">${fmt(SETORES.length)} setores censitários urbanos, com mediana de ${fmt(mediana)} domicílios cada. O setor é a menor unidade que o IBGE publica: algumas quadras. Os traços finos são os limites das RAs. O risco de dengue continua sendo municipal: esta camada mostra onde a condição local favorece o criadouro, não onde há caso.</p>
    </div>
    <div class="coluna" style="gap:8px">
      <h3>${tituloPiores}</h3>
      <div class="tabela-rolavel"><table class="table" style="min-width:560px">
        <thead><tr><th>Região Administrativa</th><th>Setor</th><th class="dir">${esc(ind.nomeQ || ind.nome)}</th><th class="dir">Domicílios</th></tr></thead>
        <tbody>${piores.map(s => `<tr><td>${esc(s.props.ra)}</td><td><span class="cod">${esc(s.props.cod)}</span></td><td class="dir">${f(valor(s.props))}</td><td class="dir">${fmt(s.props.dom)}</td></tr>`).join("")}</tbody>
      </table></div>
    </div>`;
}

function mapaRas(ind) {
  const linhas = RAS.map(r => ({ r, val: ind.ra(r.props) }));
  const cl = classes(linhas.map(x => x.val), ind.sufixo || "");
  const paths = linhas.map(x => {
    const k = "a" + x.r.props.cod, v = D.ras[x.r.props.cod], c = cl.de(x.val);
    DICA_MAPA[k] = `<strong>${esc(x.r.props.nome)}</strong>${ind.nome}: ${x.val == null ? "sem dado" : ind.f(x.val)}<br><span class="mudo">${fmt(x.r.props.pop)} habitantes${v ? ` · esgoto inadequado ${fmt(v.esgoto, 1)}%` : ""}</span>`;
    return `<path d="${x.r.d}" data-k="${k}" fill="${c < 0 ? "var(--color-neutral-200)" : CORES_FAIXA[c]}" class="ra"><title>${esc(x.r.props.nome)}</title></path>`;
  }).join("");
  // Divisa em duas camadas, como nos mapas impressos: um traço escuro largo e
  // um fio claro por cima. Separa tanto duas RAs claras quanto duas escuras,
  // o que um traço de uma cor só não consegue.
  // Todos os traços escuros primeiro e os fios depois: intercalados, o traço
  // de uma RA cobriria o fio da vizinha na divisa que as duas dividem.
  const divisas = RAS.map(r => `<path class="divisa" d="${r.d}"/>`).join("") + RAS.map(r => `<path class="divisa-fio" d="${r.d}"/>`).join("");
  // Nome sobre a região: com 31 polígonos, passar o cursor um a um para saber
  // qual é qual inviabiliza a leitura. No celular o espaço entre nomes cresce,
  // e ficam menos nomes, maiores.
  const movel = estreita();
  const nomeadas = desempilhar(RAS.slice().sort((a, b) => (b.props.area || 0) - (a.props.area || 0)), movel ? 27 : 17);
  const nomes = nomeadas.map(r => `<text class="rot-ra${movel ? " grande" : ""}" x="${r.cx.toFixed(1)}" y="${(r.cy + 5).toFixed(1)}">${esc(r.props.nome)}</text>`).join("");
  const tabela = linhas.slice().sort((a, b) => (b.val ?? -1) - (a.val ?? -1)).map(x => `<tr><td>${esc(x.r.props.nome)}<div class="pequeno mudo cod" title="Código IBGE do subdistrito">${esc(x.r.props.cod)}</div></td><td class="dir">${x.val == null ? "—" : ind.f(x.val)}</td>${ind === INDICADORES.pop ? "" : `<td class="dir">${fmt(x.r.props.pop)}</td>`}</tr>`).join("");
  return `<div class="duas-uma mapa-e-tabela">
      <div class="coluna">
        <div class="mapa mapa-ras">
          <svg viewBox="0 0 800 560" role="img" aria-label="Mapa das Regiões Administrativas do DF">${paths}${divisas}${nomes}</svg>
          <div class="dica-mapa"></div>
        </div>
        ${legendaFaixas(cl, ind.unid)}
        <p class="pequeno mudo justo">Nomeadas no mapa ${nomeadas.length} das ${RAS.length} RAs: onde várias se aglomeram, fica o nome da maior, e as demais aparecem ao passar o cursor (ou tocar) e na tabela.</p>
      </div>
      <div class="tabela-rolavel" style="max-height:600px;overflow:auto">
        <table class="table tabela-ras"><thead><tr><th>Região Administrativa<br><span style="text-transform:none;letter-spacing:0">e código IBGE</span></th><th class="dir">${ind.cab || ind.nome}</th>${ind === INDICADORES.pop ? "" : `<th class="dir">População<br><span style="text-transform:none;letter-spacing:0">PDAD 2021</span></th>`}</tr></thead><tbody>${tabela}</tbody></table>
      </div>
    </div>`;
}

function vistaRas() {
  const quadra = S.escala === "quadra";
  if (quadra && INDICADORES[S.ind].soRa) S.ind = "pop";
  const ind = INDICADORES[S.ind];
  const comEsgoto = Object.values(D.ras).filter(v => v.esgoto != null).sort((a, b) => a.esgoto - b.esgoto);
  const menor = comEsgoto[0], maior = comEsgoto[comEsgoto.length - 1];
  const opcoes = Object.entries(INDICADORES).filter(([, v]) => !(quadra && v.soRa))
    .map(([k, v]) => `<option value="${k}"${k === S.ind ? " selected" : ""}>${esc(quadra && v.nomeQ ? v.nomeQ : v.nome)}</option>`).join("");
  const explicacao = (quadra && ind.textoQ) || ind.texto;
  const fonte = ind === INDICADORES.pop || ind === INDICADORES.dens
    ? (quadra ? "Fonte: Censo 2022 (IBGE), por setor censitário." : "Fonte: população da PDAD 2021 e área da malha das RAs.")
    : `Fonte: Censo 2022 (IBGE), agregado ${quadra ? "por setor censitário" : "por subdistrito — no DF, o subdistrito é a Região Administrativa"}.`;
  return `<section class="secao">
    ${cabeca("VI · Brasília por Região Administrativa", "As condições de cada RA",
      `Não há contagem de casos por RA, mas há condição: ${fmt(menor.esgoto, 2)}% de esgotamento inadequado em ${esc(menor.nome)} contra ${fmt(maior.esgoto, 1)}% em ${esc(maior.nome)}. O índice soma esgoto, água, lixo, bueiros e pavimento do Censo 2022, e desce até a quadra.`)}
    <div class="filtros" style="justify-content:space-between">
      ${seg("escala", S.escala, [["ra", "Região Administrativa"], ["quadra", "Quadra (setor censitário)"]])}
      <label class="filtros" style="gap:8px"><span class="pequeno mudo">Indicador</span>
        <select class="select" id="ind-ras">${opcoes}</select></label>
    </div>
    <p class="texto justo" style="max-width:800px"><strong style="font-weight:600">${esc(quadra && ind.nomeQ ? ind.nomeQ : ind.nome)}.</strong> ${explicacao} <span class="mudo">${fonte}</span></p>
    ${quadra ? mapaQuadras(ind) : mapaRas(ind)}
    <div class="faixa justo" style="display:block;font-size:14px;line-height:1.65"><strong style="font-weight:600">Este mapa não exibe casos de dengue por RA.</strong> Não existe fonte pública com essa série: o InfoDengue opera apenas no nível municipal, o painel da SES-DF não expõe os dados de forma programática, o LIRAa é publicado como relatório fechado e os microdados do SINAN dependem do FTP do DATASUS. Repartir os casos do DF entre as RAs na proporção da população produziria um mapa apenas aparentemente informativo, que reproduziria o mapa populacional e esconderia a desigualdade intraurbana real — justamente o que se quer medir.</div>
  </section>`;
}

// ===================================================== VII ALARMES E CLIMA
function vistaClima() {
  const al = D.alarmes, cl = D.clima;
  const regras = al.regras.map(r => `<div class="regra"><b>${r.id}</b>
    <div class="regra-corpo"><strong>${esc(r.nome)}</strong><span>${esc(r.descricao)}</span>
      <span class="pequeno mudo num">Efeito medido ${r.lag} semanas depois: incidência ${fmt(r.lift, 2)} vezes a habitual (mediana) · ${fmt(r.episodios)} episódios${r.acimaDoNormal != null ? ` · ${pct(r.acimaDoNormal)} deles acima do normal` : ""}</span>
      <span class="pequeno mudo">Condição testada: <span class="cod">${esc(r.condicao)}</span></span></div>
    <span class="tag ${r.aprovada ? "tag-outline" : "tag-neutral"}">${r.aprovada ? "Aprovada" : "Reprovada"}</span></div>`).join("");
  const ativos = al.ativos.length ? al.ativos.map(a => `<div class="regra"><b>${a.id}</b>
    <div class="regra-corpo"><strong>${esc(a.municipio)}: ${esc(a.nome)}</strong>
      <span>Valor do gatilho: ${pct(a.valor)}. Aqui, depois de gatilhos assim, a incidência ${a.lag} semanas depois foi ${fmt(a.lift, 1)} vezes a habitual.</span>
      ${a.semana ? `<span class="pequeno mudo">Semana ${rotSemana(a.semana)} · olhe ${a.lag} semanas à frente</span>` : ""}</div>
    <span class="tag tag-outline">Ativo</span></div>`).join("") : "";
  // Onde cada regra aprovada mais se confirmou: o lift de cada município.
  const porMunicipio = Object.entries(al.porMunicipio || {}).filter(([, l]) => l.length).map(([id, lista]) => {
    const regra = al.regras.find(r => r.id === id);
    return `<div class="coluna" style="gap:8px">
      <h3>Onde a ${id} (${esc(regra ? regra.nome.toLowerCase() : id)}) mais se confirmou</h3>
      <p class="pequeno mudo" style="font-size:13px">Efeito medido em cada município, só onde houve 8 episódios ou mais: ${fmt(lista.length)} dos ${D.totalMunicipios}. É esta medida que o índice de transmissão da ficha usa quando o município tem histórico próprio.</p>
      <div class="tabela-rolavel" style="max-height:420px;overflow:auto"><table class="table">
        <thead><tr><th>Município</th><th class="dir">Episódios</th><th class="dir">Incidência depois (× a habitual)</th></tr></thead>
        <tbody>${lista.map(x => `<tr class="${x.cod === COD_FOCO ? "destaque" : ""}"><td>${esc(x.nome)}</td><td class="dir">${fmt(x.n)}</td><td class="dir">${fmt(x.lift, 2)}</td></tr>`).join("")}</tbody>
      </table></div></div>`;
  }).join("");
  const bsb = cl.municipios.find(m => m.cod === COD_FOCO);
  let leitura = "";
  if (bsb) {
    const favoravel = bsb.temp != null && bsb.temp >= FAIXA_AEDES[0] && bsb.temp <= FAIXA_AEDES[1];
    leitura = `Temperatura ${favoravel ? "dentro" : "fora"} da faixa favorável ao <em>Aedes aegypti</em> (${FAIXA_AEDES[0]} a ${FAIXA_AEDES[1]} °C)${bsb.dias >= DIAS_CHUVA_FREQUENTE ? ", com chuva frequente." : "."}`;
  }
  const maxCh = Math.max(1, ...cl.municipios.map(m => m.chuva14 || 0));
  const chuva = cl.municipios.slice().sort((a, b) => (b.chuva14 || 0) - (a.chuva14 || 0)).map(m => `<tr class="${m.cod === COD_FOCO ? "destaque" : ""}">
    <td>${esc(m.nome)}</td>
    <td><div style="display:flex;gap:10px;align-items:center"><span class="barra-prob fina"><b style="width:${((m.chuva14 || 0) / maxCh * 100).toFixed(1)}%"></b></span><span class="num sem-quebra" style="width:78px;text-align:right">${fmt(m.chuva14, 1)} mm</span></div></td>
    <td class="dir">${fmt(m.chuva7, 1)} mm</td><td class="dir">${m.dias == null ? "—" : m.dias}</td><td class="dir">${m.temp == null ? "—" : fmt(m.temp, 1) + " °C"}</td></tr>`).join("");
  const medicao = [al.base ? `${fmt(al.base.municipios)} municípios, ${fmt(al.base.semanas)} semanas cada` : "", al.medidoEm ? `medido em ${diaMesAno(al.medidoEm)}` : ""].filter(Boolean).join("; ");
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
        <p class="pequeno mudo justo" style="font-size:13px;margin-bottom:10px">Como se mede: um episódio é a semana em que a condição liga, sem contar de novo as semanas seguidas. O efeito de cada episódio é a incidência algumas semanas depois dividida pela mediana daquela época do ano no próprio município. Regras reprovadas aparecem aqui por transparência e nunca disparam alarme.${medicao ? ` Base: ${medicao}.` : ""}</p>
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
    ${porMunicipio}
    <div class="coluna" style="gap:8px">
      <h3>Clima previsto para os próximos 14 dias, por município</h3>
      <div class="tabela-rolavel"><table class="table" style="min-width:680px">
        <thead><tr><th>Município</th><th style="width:240px">Chuva em 14 dias</th><th class="dir">Em 7 dias</th><th class="dir">Dias com chuva</th><th class="dir">Temp. média</th></tr></thead>
        <tbody>${chuva}</tbody></table></div>
      <p class="pequeno mudo">Previsão do ${esc(cl.fonte.replace(/\s*forecast\s*$/i, ""))} coletada para a semana ${rotSemana(cl.semana)}. Dia com chuva é o que tem 1 mm ou mais, o mesmo critério da série observada; dias sem previsão ficam fora das somas e da média. Chuva e temperatura à frente dizem se o território fica receptivo ao mosquito, mas não entram no modelo, que prevê com o clima já observado.${faltam ? ` Sem previsão para ${faltam} ${faltam === 1 ? "município" : "municípios"}: ${cl.faltantes.map(esc).join(", ")}.` : ""}</p>
    </div>
  </section>`;
}

// ========================================================= VIII DICIONÁRIO
function corpoDicionario() {
  const q = semAcento(S.dicBusca.trim());
  const cols = D.dicionario.colunas.filter(c =>
    (!S.dicBloco || c.bloco === S.dicBloco) && (!S.dicPapel || c.papel === S.dicPapel)
    && (!q || semAcento(c.coluna + " " + c.descricao + " " + c.fonte).includes(q)));
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
        <input class="input" id="busca-dic" type="search" placeholder="Buscar coluna, descrição ou fonte" value="${esc(S.dicBusca)}" style="width:260px" aria-label="Buscar coluna, descrição ou fonte">
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
    <p class="pequeno mudo justo" style="max-width:800px">Nenhuma variável enxerga o futuro: médias móveis são deslocadas em uma semana, as anomalias sazonais e o canal endêmico usam apenas anos anteriores, e a dobra de validação corta pela data que o alvo observa. As colunas abaixo de 100% de preenchimento faltam por construção — o canal endêmico exige anos anteriores, e o primeiro ano da série não os tem.</p>
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

// O endereço é "#tela" ou "#tela/municipio". Nas abas que mostram um
// município, ele vem do endereço (sem nome, é Brasília); nas demais, a
// escolha anterior fica guardada para quando a pessoa voltar.
let apelidoPendente = null;
function lerEndereco() {
  const [tela, apelidoMun] = location.hash.slice(1).split("/");
  S.tela = VISTAS[tela] ? tela : "panorama";
  if (!TELAS_MUN.has(S.tela)) return;
  if (!D) { apelidoPendente = apelidoMun || null; return; }
  const m = apelidoMun ? porSlug(apelidoMun) : null;
  S.mun = m ? m.cod : COD_FOCO;
}
function escolherMun(cod) {
  if (!porCod(cod)) return;
  S.mun = cod;
  history.replaceState(null, "", enderecoDe(S.tela, cod));
  render();
}

function desenharAbas() {
  abas.innerHTML = TELAS.map(([id, r], i) =>
    `<a href="${D ? enderecoDe(id, S.mun) : "#" + id}"${S.tela === id ? ' aria-current="page"' : ""}><span>${ROMANOS[i]}</span>${r}</a>`).join("");
  const atual = abas.querySelector("[aria-current]");
  if (atual && abas.scrollWidth > abas.clientWidth) {
    abas.scrollLeft = atual.offsetLeft - abas.clientWidth / 2 + atual.offsetWidth / 2;
  }
}

function render() {
  desenharAbas();
  if (!D) return;
  conteudo.innerHTML = VISTAS[S.tela]();
  const nome = TELAS.find(t => t[0] === S.tela)[1], m = munAtual();
  const doMun = TELAS_MUN.has(S.tela) && m.cod !== COD_FOCO ? `${m.nome} · ` : "";
  document.title = S.tela === "panorama" ? `VIGIA-Dengue · ${doMun}Semana ${D.semanaRotulo}` : `${doMun}${nome} · VIGIA-Dengue`;
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
  const antes = S.tela;
  lerEndereco();
  render();
  if (S.tela !== antes) window.scrollTo(0, 0);
});

document.addEventListener("click", e => {
  const alvo = e.target.closest("[data-acao], .mapa path[data-cod]");
  if (!alvo || !D) return;
  if (alvo.matches("path[data-cod]")) { escolherMun(+alvo.dataset.cod); return; }
  const v = alvo.dataset.valor;
  switch (alvo.dataset.acao) {
    case "periodo": S.periodo = +v; break;
    case "periodo-serie": S.periodoSerie = +v; break;
    case "ordem": S.ordem = v; break;
    case "escala": S.escala = v; break;
    case "medida": S.medida = v; break;
    case "sel": escolherMun(+v); return;
    case "baixar-ranking": baixarRanking(); return;
    case "baixar-serie": baixarSerie(); return;
    default: return;
  }
  render();
});

document.addEventListener("change", e => {
  if (!D) return;
  if (e.target.matches("[data-mun]")) { S.relSe = null; escolherMun(+e.target.value); }
  else if (e.target.id === "ind-ras") { S.ind = e.target.value; render(); }
  else if (e.target.id === "rel-semana") { S.relSe = +e.target.value; render(); }
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
  // No mapa da RIDE o toque escolhe o município; nos das RAs e das quadras,
  // que não têm ficha, o toque mostra a dica — no celular não há cursor.
  const path = mapa && (e.pointerType === "mouse" || mapa.classList.contains("mapa-ras")) ? e.target.closest("path[data-k]") : null;
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

lerEndereco();
desenharAbas();
fetch("dados/painel.json", { cache: "no-cache" })
  .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
  .then(dados => {
    D = dados;
    if (apelidoPendente) { const m = porSlug(apelidoPendente); if (m) S.mun = m.cod; apelidoPendente = null; }
    RIDE = projetar(D.malha, 800, 620);
    RAS = projetar(D.malhaRas, 800, 560);
    document.getElementById("topo-semana").textContent = `Semana ${D.semanaRotulo} · ${periodoSemana(D.dataInicio)}`;
    const g = D.geradoEm;
    let rodape = `Boletim gerado em ${g.slice(8, 10)}/${g.slice(5, 7)}/${g.slice(0, 4)} às ${g.slice(11, 16)} (horário de Brasília), com dados até a semana ${D.semanaRotulo}.`;
    if (D.semanaMaisRecente > D.semana) {
      rodape += ` A semana ${rotSemana(D.semanaMaisRecente)} já tem dados de parte dos municípios e entra quando o território estiver completo.`;
    }
    const h = horasDesde(D.verificadoEm);
    if (h != null) rodape += ` A fonte (InfoDengue) foi verificada ${quando(h, D.verificadoEm)}.`;
    document.getElementById("rodape-gerado").textContent = rodape;
    render();
  })
  .catch(err => {
    conteudo.innerHTML = `<p class="carregando">Não foi possível carregar os dados da semana (${esc(err.message)}). Tente recarregar a página.</p>`;
  });
})();
