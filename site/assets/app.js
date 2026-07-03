/* Monitoring — Sentry (error reporting + feedback widget) and Vercel analytics.
   The Sentry bundle itself is loaded (with SRI) from each page's <head>; init and
   the analytics injection are gated to the deployed site so local dev sessions and
   Playwright runs don't send events or burn quota. */
const DEPLOYED = /\.vercel\.app$/.test(location.hostname);
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
    tracesSampleRate: 0,             // no performance tracing — conserve free quota
    allowUrls: [/\.vercel\.app/],
  });
}
if (DEPLOYED) {
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  const va = document.createElement('script');
  va.defer = true; va.src = '/_vercel/insights/script.js';
  document.head.appendChild(va);
}

/* shared helpers */
const D = window.APP_DATA;
if (!D) {
  document.body.insertAdjacentHTML('afterbegin',
    '<div class="note" style="margin:1rem">Sorry — the data failed to load. ' +
    'Try a hard refresh (Cmd/Ctrl+Shift+R); if it persists, use the feedback button.</div>');
  throw new Error('APP_DATA missing — data.js failed to load');
}

function qs(name){return new URLSearchParams(location.search).get(name);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function yr(date){return date?String(date).slice(0,4):'';}

/* localStorage can throw (private browsing, storage disabled) — degrade to defaults */
function getPref(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function setPref(k,v){try{localStorage.setItem(k,v);}catch(e){}}

function deltaPill(d){
  if(d>0) return `<span class="pill up">▲ ${d}</span>`;
  if(d<0) return `<span class="pill down">▼ ${Math.abs(d)}</span>`;
  return `<span class="pill flat">–</span>`;
}
function playerLink(name){return `<a href="player.html?p=${encodeURIComponent(name)}">${esc(name)}</a>`;}
function gameLink(game){return `<a href="game.html?g=${encodeURIComponent(game)}">${esc(game)}</a>`;}


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
  panel.className = 'colmenu-panel'; panel.hidden = true; panel.setAttribute('role','menu');
  panel.innerHTML = cols.map(c=>{
    const col = table.getColumn(c.field);
    const on = col ? col.isVisible() : true;
    return `<label class="colmenu-item"><input type="checkbox" data-field="${esc(c.field)}"${on?' checked':''}> ${esc(c.label)}</label>`;
  }).join('');
  host.append(btn, panel);

  const close = ()=>{ panel.hidden = true; btn.setAttribute('aria-expanded','false'); };
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
  document.addEventListener('click', close);
  document.addEventListener('keydown', e=>{ if(e.key==='Escape') close(); });
}

/* build header nav, marking active */
function mountNav(active){
  const links=[['index.html','Leaderboard'],['scatter.html','Peak vs Longevity'],['games.html','Seasons'],['methodology.html','Why weight?'],['changelog.html','Changelog']];
  const nav=links.map(([h,t])=>`<a href="${h}" class="${h===active?'active':''}">${t}</a>`).join('');
  document.body.insertAdjacentHTML('afterbegin',
    `<header class="site-head"><div class="inner">
      <a class="brand" href="index.html">CoD Major Wins <span class="dot">◆</span> Era-Adjusted</a>
      <nav class="nav">${nav}</nav>
    </div></header>`);
  // expose the nav's height so sticky table headers can sit just below it
  const setNavH=()=>{const el=document.querySelector('.site-head');
    if(el) document.documentElement.style.setProperty('--navh', el.offsetHeight+'px');};
  setNavH();
  window.addEventListener('resize', setNavH);
  window.addEventListener('load', setNavH);
}
function mountFoot(){
  document.body.insertAdjacentHTML('beforeend',
    `<footer class="site-foot">Reconstructed from the
      <a href="https://cod-esports.fandom.com/wiki/List_of_Most_Major_Tournament_Wins_by_Player" target="_blank" rel="noopener">Call of Duty Esports Wiki</a>
      · major = Tier &ldquo;Major&rdquo;/&ldquo;Premier&rdquo;, 1st place · ${D.meta.numEvents} events across ${D.meta.seasonOrder.length} seasons ·
      raw totals match the wiki exactly · data as of ${D.meta.asOf}.</footer>`);
}
