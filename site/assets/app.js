/* Sentry: JS error monitoring + feedback widget (loaded via CDN in each page <head>) */
if (window.Sentry) {
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
    allowUrls: [/cod-stats-one\.vercel\.app/, /localhost/, /127\.0\.0\.1/],
  });
}

/* shared helpers */
const D = window.APP_DATA;

function qs(name){return new URLSearchParams(location.search).get(name);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmt(n,d=2){return (n==null||isNaN(n))?'–':Number(n).toFixed(d);}
function yr(date){return date?String(date).slice(0,4):'';}

function deltaHtml(d){
  if(d>0) return `<span class="delta up">▲ ${d}</span>`;
  if(d<0) return `<span class="delta down">▼ ${Math.abs(d)}</span>`;
  return `<span class="delta flat">–</span>`;
}
function deltaPill(d){
  if(d>0) return `<span class="pill up">▲ ${d}</span>`;
  if(d<0) return `<span class="pill down">▼ ${Math.abs(d)}</span>`;
  return `<span class="pill flat">–</span>`;
}
function playerLink(name){return `<a href="player.html?p=${encodeURIComponent(name)}">${esc(name)}</a>`;}
function gameLink(game){return `<a href="game.html?g=${encodeURIComponent(game)}">${esc(game)}</a>`;}

/* horizontal bar row */
function barRow(label,value,max,opts={}){
  const pct=max>0?Math.max(2,(value/max)*100):0;
  const cls=opts.cls||'';
  const valTxt=opts.valTxt!=null?opts.valTxt:value;
  const lab=opts.link?gameLink(label):esc(label);
  return `<div class="barline"><div class="lab">${lab}</div>
    <div class="bar-track" style="flex:1"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div>
    <div class="val">${valTxt}</div></div>`;
}

/* build header nav, marking active */
function mountNav(active){
  const links=[['index.html','Leaderboard'],['games.html','Seasons'],['methodology.html','Why weight?']];
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
