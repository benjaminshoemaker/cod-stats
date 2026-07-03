/* Header nav, mounted before first paint.
   Loaded as a blocking script at the top of <body> (and preloaded from <head>)
   so the header is in the DOM for the first frame — injecting it later from the
   page modules pushed the whole page down by the nav height (layout shift).
   Pages still call mountNav('...') from their module scripts; the guard below
   makes those calls no-ops, and the alias map keeps player/game pages
   highlighting their section (Leaderboard / Seasons) rather than themselves. */
function mountNav(active){
  if(document.querySelector('.site-head')) return;   // already mounted at parse time
  // "Insights" groups the charts and the derived-signature page in a dropdown.
  const VIZ=[['scatter.html','Peak vs Longevity'],['heatmap.html','Dominance heatmap'],['trajectory.html','Career trajectories'],['map.html','Similarity map'],['signatures.html','Signatures']];
  const vizActive=VIZ.some(([h])=>h===active);
  const drop=`<div class="navdrop${vizActive?' active':''}">
      <button type="button" class="navdrop-btn" aria-haspopup="true" aria-expanded="false">Insights <span aria-hidden="true">▾</span></button>
      <div class="navdrop-menu">${VIZ.map(([h,t])=>`<a href="${h}" class="${h===active?'active':''}">${t}</a>`).join('')}</div>
    </div>`;
  const before=[['index.html','Leaderboard']], after=[['games.html','Seasons'],['methodology.html','Why weight?'],['changelog.html','Changelog']];
  const lnk=([h,t])=>`<a href="${h}" class="${h===active?'active':''}">${t}</a>`;
  const nav=before.map(lnk).join('')+drop+after.map(lnk).join('');
  document.body.insertAdjacentHTML('afterbegin',
    `<a class="skip" href="#root">Skip to content</a>`+
    `<header class="site-head"><div class="inner">
      <a class="brand" href="index.html">CoD Major Wins <span class="dot">◆</span> Era-Adjusted</a>
      <nav class="nav">${nav}</nav>
    </div></header>`);
  // dropdown open/close (click to toggle, click-away + Esc to close)
  const dd=document.querySelector('.navdrop');
  if(dd){
    const b=dd.querySelector('.navdrop-btn');
    b.addEventListener('click',e=>{e.stopPropagation();const o=dd.classList.toggle('open');b.setAttribute('aria-expanded',o);});
    document.addEventListener('click',()=>{dd.classList.remove('open');b.setAttribute('aria-expanded','false');});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&dd.classList.contains('open')){
      dd.classList.remove('open');b.setAttribute('aria-expanded','false');b.focus();}});
  }
  // expose the nav's height so sticky table headers can sit just below it
  const setNavH=()=>{const el=document.querySelector('.site-head');
    if(el) document.documentElement.style.setProperty('--navh', el.offsetHeight+'px');};
  setNavH();
  window.addEventListener('resize', setNavH);
  window.addEventListener('load', setNavH);
}
{
  // detail pages highlight their section's entry, not their own filename
  const ALIAS={'player.html':'index.html','game.html':'games.html','':'index.html'};
  const page=location.pathname.split('/').pop();
  mountNav(Object.prototype.hasOwnProperty.call(ALIAS,page)?ALIAS[page]:page);
}
