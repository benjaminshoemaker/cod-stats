/* Monitoring: Sentry (error reporting + feedback widget) and Vercel analytics.
   The Sentry bundle is loaded synchronously from each page's <head>, so init runs
   before page render code below. Everything is still gated to the deployed site
   so local dev sessions and Playwright runs don't send events or burn quota. */
const DEPLOYED = location.hostname === 'mapfive.app' || /\.vercel\.app$/.test(location.hostname);
if (DEPLOYED && window.Sentry) {
  Sentry.init({
    dsn: "https://31fc37624c1589dbbe233db42c843560@o4511651597975552.ingest.us.sentry.io/4511651631398912",
    integrations: [
      Sentry.feedbackIntegration({
        colorScheme: "light",
        showBranding: false,
        autoInject: true,
        isNameRequired: false,
        isEmailRequired: true,        // reporter must leave an email
        enableScreenshot: true,       // reporter can attach/annotate a screenshot
        triggerLabel: "Send feedback",
        formTitle: "Send feedback",
        submitButtonLabel: "Send feedback",
        messagePlaceholder: "What happened, and what did you expect? Mention the player or page if it helps.",
      }),
    ],
    tracesSampleRate: 0,             // no performance tracing, conserve free quota
    allowUrls: [/mapfive\.app/, /\.vercel\.app/],
  });
}
if (DEPLOYED) {
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  const va = document.createElement('script');
  va.defer = true; va.src = '/_vercel/insights/script.js';
  document.head.appendChild(va);
}

/* shared helpers */
const D = window.APP_DATA || null;
if (!D && Array.from(document.scripts).some(s => /(^|\/)data\.js(\?|$)/.test(s.getAttribute('src') || s.src || ''))) {
  document.body.insertAdjacentHTML('afterbegin',
    '<div class="note" style="margin:1rem">Sorry, the data failed to load. ' +
    'Try a hard refresh (Cmd/Ctrl+Shift+R); if it persists, use the feedback button.</div>');
  console.error('APP_DATA missing: data.js failed to load');
}
function qs(name){return new URLSearchParams(location.search).get(name);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function setCanonical(url){
  let link = document.querySelector('link[rel="canonical"]');
  if(!link){
    link = document.createElement('link');
    link.rel = 'canonical';
    document.head.appendChild(link);
  }
  link.href = url;
}
function yr(date){return date?String(date).slice(0,4):'';}
function playerLookupKey(name){
  return String(name || '').replace(/\s*\(.*?\)\s*/g, '').trim().toLowerCase();
}
function uniquePlayerIndex(names, keyFn){
  const out = new Map(), collisions = new Set();
  names.forEach(name => {
    const key = keyFn(name);
    if(!key || collisions.has(key)) return;
    if(out.has(key) && out.get(key) !== name){
      out.delete(key);
      collisions.add(key);
    }else{
      out.set(key, name);
    }
  });
  return out;
}
const PLAYER_NAMES = Object.keys((D && D.players) || {});
const PLAYER_BY_LOWER = uniquePlayerIndex(PLAYER_NAMES, name => String(name).trim().toLowerCase());
const PLAYER_BY_LOOKUP = uniquePlayerIndex(PLAYER_NAMES, playerLookupKey);
function canonicalPlayerName(name){
  const raw = String(name || '').trim();
  if(!raw) return null;
  if(Object.prototype.hasOwnProperty.call((D && D.players) || {}, raw)) return raw;
  const lowerMatch = PLAYER_BY_LOWER.get(raw.toLowerCase());
  if(lowerMatch) return lowerMatch;
  if(/\([^)]*\)/.test(raw)) return null;
  return PLAYER_BY_LOOKUP.get(playerLookupKey(raw)) || null;
}
function playerRecord(name){
  const canonical = canonicalPlayerName(name);
  return canonical && D ? D.players[canonical] : null;
}

/* localStorage can throw (private browsing, storage disabled); degrade to defaults */
function getPref(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function setPref(k,v){try{localStorage.setItem(k,v);}catch(e){}}

function deltaPill(d){
  if(d>0) return `<span class="pill up">▲ ${d}</span>`;
  if(d<0) return `<span class="pill down">▼ ${Math.abs(d)}</span>`;
  return `<span class="pill flat">–</span>`;
}
function teamBadge(team, cls=''){
  if(!team) return '<span class="small faint">—</span>';
  const logo = D && D.teamLogos && D.teamLogos[team];
  const img = logo && logo.src
    ? `<img class="team-logo" src="${esc(logo.src)}" alt="" title="${esc(team)}" decoding="async" onerror="this.remove()">`
    : '';
  return `<span class="team-badge${cls ? ' '+esc(cls) : ''}">${img}<span>${esc(team)}</span></span>`;
}
function roleRows(player, games){
  const rows = (player && player.role_by_game) || [];
  if(!games) return rows;
  const wanted = new Set(games);
  return rows.filter(r => wanted.has(r.game));
}
function roleSummary(player, games){
  const roles = [...new Set(roleRows(player, games).map(r => r.role).filter(r => r && r !== 'Unknown'))];
  if(roles.length === 0) return 'Unknown';
  if(roles.length === 1) return roles[0];
  return 'Mixed';
}
function roleForGame(player, game){
  const row = ((player && player.role_by_game) || []).find(r => r.game === game);
  return row ? row.role : 'Unknown';
}
function rolePill(role){
  const r = role || 'Unknown';
  return `<span class="pill role role-${esc(r.toLowerCase())}">${esc(r)}</span>`;
}
function roleDisputeUrl(player, game, currentRole){
  const title = `[Role dispute] ${player} - ${game}`;
  const body = [
    `Player: ${player}`,
    `Season: ${game}`,
    `Current role: ${currentRole || 'Unknown'}`,
    '',
    'Proposed role: ',
    'Evidence URL: ',
    'Timestamp / notes: '
  ].join('\n');
  const p = new URLSearchParams({
    template: 'role_dispute.yml',
    title,
    labels: 'role-data',
    body
  });
  return `https://github.com/benjaminshoemaker/cod-stats/issues/new?${p.toString()}`;
}
function roleDisputeLink(player, game, currentRole){
  return `<a class="role-dispute small" href="${roleDisputeUrl(player, game, currentRole)}" target="_blank" rel="noopener">Dispute</a>`;
}
function playerLink(name){
  const raw = String(name || '').trim();
  const canonical = canonicalPlayerName(raw);
  if(!canonical) return esc(raw);
  return `<a href="player.html?p=${encodeURIComponent(canonical)}">${esc(canonical)}</a>`;
}
function gameLink(game){return `<a href="game.html?g=${encodeURIComponent(game)}">${esc(game)}</a>`;}
function fmtInt(v){return v==null||!Number.isFinite(+v)?'<span class="faint">–</span>':Number(v).toLocaleString();}
function fmtKd(v){return v==null||!Number.isFinite(+v)?'<span class="faint">–</span>':Number(v).toFixed(3);}
function attrString(attrs={}){
  return Object.entries(attrs)
    .filter(([,v]) => v !== false && v != null)
    .map(([k,v]) => v === true ? esc(k) : `${esc(k)}="${esc(v)}"`)
    .join(' ');
}
function scrollRegionAttrs(label, extraClass='', extraAttrs={}){
  if(extraClass && typeof extraClass === 'object'){
    extraAttrs = extraClass;
    extraClass = '';
  }
  const cls = `scroll-x${extraClass ? ' '+extraClass : ''}`;
  return attrString({
    class: cls,
    tabindex: '0',
    role: 'region',
    'aria-label': label,
    'data-scroll-region': true,
    ...extraAttrs
  });
}
function tableCaption(label){
  return `<caption class="sr-only">${esc(label)}</caption>`;
}
function scrollHint(text='Scroll sideways to see all columns.'){
  return `<p class="scrollhint small muted">${esc(text)}</p>`;
}
function dataTableSurface({label, caption, className='', tableClass='data', tableAttrs={}, wrapperClass='', hint='auto', head='', body='', rows='', foot='', html=null }={}){
  const content = body || rows || '';
  const inner = html == null ? `${head}<tbody>${content}</tbody>${foot}` : html;
  const table = `<table ${attrString({class: tableClass, ...tableAttrs})}>${tableCaption(caption || label)}${inner}</table>`;
  const hintText = hint === false ? '' : scrollHint(typeof hint === 'string' && hint !== 'auto' ? hint : undefined);
  return `<div ${scrollRegionAttrs(label, wrapperClass || className)}>${hintText}${table}</div>`;
}
const SCROLL_REGION_SELECTOR = '.scroll-x, [data-scroll-region], .tabulator-tableholder';
const scrollRegionState = new WeakMap();
function scrollRegionLabel(el){
  const labelledBy = el.getAttribute('aria-labelledby');
  if(labelledBy) return '';
  if(el.getAttribute('aria-label')) return '';
  const table = el.querySelector('table');
  const caption = table && table.querySelector('caption');
  if(caption && caption.textContent && caption.textContent.trim()) return caption.textContent.trim();
  if(el.closest('#table')) return 'Leaderboard table';
  return 'Scrollable data table';
}
function updateScrollRegionState(el){
  const max = Math.max(0, el.scrollWidth - el.clientWidth);
  const x = Math.max(0, Math.min(el.scrollLeft, max));
  const overflow = max > 1;
  el.dataset.overflowX = overflow ? 'true' : 'false';
  el.dataset.atStart = x <= 1 ? 'true' : 'false';
  el.dataset.atEnd = x >= max - 1 ? 'true' : 'false';
}
function mountHorizontalTableScroll(el){
  if(!el || scrollRegionState.has(el)) return;
  if(!el.matches(SCROLL_REGION_SELECTOR)) return;
  el.classList.add('scroll-region');
  if(el.tabIndex < 0) el.tabIndex = 0;
  if(!el.getAttribute('role')) el.setAttribute('role', 'region');
  const label = scrollRegionLabel(el);
  if(label) el.setAttribute('aria-label', label);

  scrollRegionState.set(el, true);
  const step = () => Math.max(80, Math.floor(el.clientWidth * 0.8));
  const setLeft = x => {
    const max = Math.max(0, el.scrollWidth - el.clientWidth);
    el.scrollLeft = Math.max(0, Math.min(max, x));
    updateScrollRegionState(el);
  };
  const scrollBy = dx => setLeft(el.scrollLeft + dx);
  const onScroll = () => updateScrollRegionState(el);
  const onKeydown = e => {
    if(e.altKey || e.ctrlKey || e.metaKey) return;
    if(e.key === 'ArrowRight'){ e.preventDefault(); scrollBy(step()); }
    if(e.key === 'ArrowLeft'){ e.preventDefault(); scrollBy(-step()); }
    if(e.key === 'Home'){ e.preventDefault(); setLeft(0); }
    if(e.key === 'End'){ e.preventDefault(); setLeft(el.scrollWidth); }
  };
  const onWheel = e => {
    if(!e.shiftKey || Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    const max = Math.max(0, el.scrollWidth - el.clientWidth);
    if(max <= 1) return;
    const next = Math.max(0, Math.min(max, el.scrollLeft + e.deltaY));
    if(next === el.scrollLeft) return;
    e.preventDefault();
    el.scrollLeft = next;
  };
  el.addEventListener('scroll', onScroll, {passive:true});
  el.addEventListener('keydown', onKeydown);
  el.addEventListener('wheel', onWheel, {passive:false});
  updateScrollRegionState(el);
  requestAnimationFrame(()=>updateScrollRegionState(el));
}
function enhanceScrollRegions(root=document){
  const scope = root instanceof Element ? root : document;
  if(scope.matches && scope.matches(SCROLL_REGION_SELECTOR)) mountHorizontalTableScroll(scope);
  scope.querySelectorAll?.(SCROLL_REGION_SELECTOR).forEach(mountHorizontalTableScroll);
}
function wireTabulatorHeaderA11y(root){
  const scope = root instanceof Element ? root : document.querySelector(root);
  if(!scope) return;
  scope.querySelectorAll('.tabulator-col[tabulator-field]').forEach(col=>{
    if(!col.getAttribute('tabindex')) col.setAttribute('tabindex','0');
    col.setAttribute('role','button');
    if(col.dataset.tableSurfaceKeydown) return;
    col.dataset.tableSurfaceKeydown = 'true';
    col.addEventListener('keydown',e=>{
      if(e.key==='Enter'||e.key===' '){
        e.preventDefault();
        col.querySelector('.tabulator-col-content')?.click();
      }
    });
  });
}
function markTabulatorSort(table, root){
  const scope = root instanceof Element ? root : document.querySelector(root);
  if(!scope || !table || typeof table.getSorters !== 'function') return;
  const s = table.getSorters()[0];
  scope.querySelectorAll('.tabulator-col[tabulator-field]').forEach(col=>{
    if(s && col.getAttribute('tabulator-field')===s.field)
      col.setAttribute('aria-sort', s.dir==='asc' ? 'ascending' : 'descending');
    else col.removeAttribute('aria-sort');
  });
}
function enhanceTabulatorSurface(table, root, label){
  const scope = root instanceof Element ? root : document.querySelector(root);
  if(!scope) return;
  if(label) scope.querySelectorAll('.tabulator-tableholder').forEach(holder=>{
    if(!holder.getAttribute('aria-label')) holder.setAttribute('aria-label', label);
  });
  enhanceScrollRegions(scope);
  wireTabulatorHeaderA11y(scope);
  markTabulatorSort(table, scope);
}
function mountTabulatorSurface(selector, config={}){
  if(!window.Tabulator) throw new Error('Tabulator missing: include vendor/tabulator.min.js before app.js');
  const {
    label='Interactive data table',
    onBuilt,
    onRenderComplete,
    onDataSorted,
    ...tabulatorOptions
  } = config;
  const root = selector instanceof Element ? selector : document.querySelector(selector);
  const table = new Tabulator(selector, tabulatorOptions);
  const enhance = () => enhanceTabulatorSurface(table, root, label);
  table.on('tableBuilt', () => {
    enhance();
    if(onBuilt) onBuilt(table);
  });
  table.on('renderComplete', () => {
    enhance();
    if(onRenderComplete) onRenderComplete(table);
  });
  table.on('dataSorted', () => {
    markTabulatorSort(table, root);
    if(onDataSorted) onDataSorted(table);
  });
  return table;
}
const TableSurface = {
  attrs: attrString,
  scrollRegionAttrs,
  tableCaption,
  scrollHint,
  dataTable: dataTableSurface,
  enhanceScrollRegions,
  wireTabulatorHeaderA11y,
  markTabulatorSort,
  enhanceTabulator: enhanceTabulatorSurface,
  mountTabulator: mountTabulatorSurface,
};
window.TableSurface = TableSurface;
window.scrollRegionAttrs = scrollRegionAttrs;
window.tableCaption = tableCaption;
window.enhanceScrollRegions = enhanceScrollRegions;
if(document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ()=>enhanceScrollRegions());
} else {
  enhanceScrollRegions();
}
new MutationObserver(records=>{
  for(const rec of records) for(const node of rec.addedNodes) {
    if(node.nodeType === 1) enhanceScrollRegions(node);
  }
}).observe(document.documentElement, {childList:true, subtree:true});
function skillBucket(stats, split='overall'){
  if(!stats) return null;
  return split === 'overall' ? stats.overall : (stats.splits && stats.splits[split]) || null;
}
function skillValue(player, field, split='overall'){
  const b = skillBucket(player && player.skillStats, split);
  return b && b[field] != null ? b[field] : null;
}
function anchorLink(id, label){
  return `<a class="anchor-link" href="#${esc(id)}" aria-label="Link to ${esc(label)}">#</a>`;
}
function pageToc(items){
  return `<nav class="page-toc" aria-label="On this page">
    <span class="page-toc-title">On this page</span>
    ${items.map(([href,label])=>`<a href="#${esc(href)}">${esc(label)}</a>`).join('')}
  </nav>`;
}
function scrollToHashTarget(){
  if(!location.hash) return;
  let id = location.hash.slice(1);
  try { id = decodeURIComponent(id); } catch(e) {}
  const target = document.getElementById(id);
  if(target) requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
}
window.addEventListener('hashchange', scrollToHashTarget);

/* Short season labels, shared by the chart pages (heatmap, trajectory) so a new
   title only needs adding once. Look up via D.meta.seasonOrder with a fallback
   to the full name, so an unmapped new season can never render "undefined". */
window.GAME_ABBR = {'Call of Duty 4':'CoD4','Modern Warfare 2':'MW2','Black Ops':'BO','Modern Warfare 3':'MW3','Black Ops 2':'BO2','Ghosts':'GH','Advanced Warfare':'AW','Black Ops 3':'BO3','Infinite Warfare':'IW','World War II':'WWII','Black Ops 4':'BO4','Modern Warfare':'MW19','Black Ops Cold War':'CW','Vanguard':'VG','Modern Warfare II':'MW2·22','Modern Warfare III':'MW3·24','Black Ops 6':'BO6','Black Ops 7':'BO7'};

/* event -> season lookup, shared by the chart pages (heatmap, trajectory) */
window.EVENT2GAME = {};
if(D && Array.isArray(D.games)) for(const g of D.games) for(const e of g.events) window.EVENT2GAME[e.event]=g.game;

/* interpolate two #rrggbb colors — shared by the sequential ramps (heatmap, map) */
window.mixHex = (a,b,t)=>{
  const pa=[1,3,5].map(i=>parseInt(a.slice(i,i+2),16)), pb=[1,3,5].map(i=>parseInt(b.slice(i,i+2),16));
  return '#'+pa.map((v,i)=>Math.round(v+(pb[i]-v)*t).toString(16).padStart(2,'0')).join('');
};


/* Column show/hide dropdown for the leaderboard. Builds a button + checkbox panel
   inside #colmenu, driven by Tabulator's column visibility. `cols` is [{field,label}]
   (the toggleable columns); checkbox state mirrors current visibility. onChange fires
   after each toggle so the caller can persist state (URL/prefs). */
function mountColumnMenu(table, cols, onChange){
  const host = document.getElementById('colmenu');
  if(!host) return;
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'colmenu-btn';
  btn.setAttribute('aria-haspopup','true'); btn.setAttribute('aria-expanded','false');
  btn.innerHTML = 'Columns <span aria-hidden="true">▾</span>';
  const panel = document.createElement('div');
  panel.className = 'colmenu-panel'; panel.hidden = true;
  panel.innerHTML = cols.map(c=>{
    const col = table.getColumn(c.field);
    const on = col ? col.isVisible() : true;
    return `<label class="colmenu-item"><input type="checkbox" data-field="${esc(c.field)}"${on?' checked':''}> ${esc(c.label)}</label>`;
  }).join('');
  host.append(btn, panel);

  const close = (refocus)=>{ if(panel.hidden) return;
    panel.hidden = true; btn.setAttribute('aria-expanded','false');
    if(refocus) btn.focus(); };
  const open  = ()=>{ panel.hidden = false; btn.setAttribute('aria-expanded','true'); };
  btn.addEventListener('click', e=>{ e.stopPropagation(); panel.hidden ? open() : close(); });
  panel.addEventListener('click', e=>e.stopPropagation());
  panel.addEventListener('change', e=>{
    const field = e.target.dataset.field; if(!field) return;
    const col = table.getColumn(field); if(!col) return;
    e.target.checked ? col.show() : col.hide();
    table.redraw(true);   // re-run fitColumns so remaining columns fill the freed width
    if(onChange) onChange();
  });
  document.addEventListener('click', ()=>close(false));
  document.addEventListener('keydown', e=>{ if(e.key==='Escape') close(true); });
}

/* Header nav lives in assets/nav.js, mounted at the top of <body> before first
   paint (avoids the layout shift of injecting it here). Pages' mountNav('...')
   calls hit its already-mounted guard and are no-ops. */
function mountFoot(){
  const dataNote = D && D.meta
    ? ` · ${D.meta.numEvents} events across ${D.meta.seasonOrder.length} seasons · raw totals match the wiki exactly · data as of ${D.meta.asOf}`
    : '';
  document.body.insertAdjacentHTML('beforeend',
    `<footer class="site-foot">Reconstructed from the
      <a href="https://cod-esports.fandom.com/wiki/List_of_Most_Major_Tournament_Wins_by_Player" target="_blank" rel="noopener">Call of Duty Esports Wiki</a>
      · major = Tier &ldquo;Major&rdquo;/&ldquo;Premier&rdquo;, 1st place${dataNote}.</footer>`);
}
