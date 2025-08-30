const qEl = document.getElementById('q');
const goBtn = document.getElementById('go');
const sortEl = document.getElementById('sort');
const noticeEl = document.getElementById('notice');
const resultsEl = document.getElementById('results');
const statsLink = document.getElementById('statsLink');

function debounce(fn, delay=300){
  let t=null;
  return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), delay); };
}

function renderResults(items){
  resultsEl.innerHTML='';
  if(!items || !items.length){
    resultsEl.innerHTML='<div class="notice">No results. Try different keywords.</div>'; return;
  }
  for(const r of items){
    const card=document.createElement('div');
    card.className='card';
    card.innerHTML=`
      <div class="title">
        <a href="${r.url}" target="_blank" rel="noopener">${r.title || '(untitled)'}</a>
        <span class="score">score ${r.score?.toFixed(2) ?? ''}</span>
      </div>
      <div class="meta">
        ${r.year ? `<span class="pill">${r.year}</span>` : ''}
        ${r.outlet ? `<span>${r.outlet}</span>` : ''}
      </div>
      <div class="authors">${
        (r.authors||[]).map((a,i)=>{
          const link = (r.author_links||[])[i] || '';
          return link ? `<a href="${link}" target="_blank" rel="noopener">${a}</a>` : `<span>${a}</span>`;
        }).join(', ')
      }</div>`;
    resultsEl.appendChild(card);
  }
}

async function doSearch(){
  const q=qEl.value.trim();
  const sort=sortEl.value;
  if(!q){ renderResults([]); return; }
  noticeEl.textContent='Searching…';
  try{
    const res=await fetch(`/api/search?q=${encodeURIComponent(q)}&sort=${encodeURIComponent(sort)}`);
    const data=await res.json();
    renderResults(data.results);
    noticeEl.textContent=`Showing ${data.results.length} results.`;
  }catch(e){
    noticeEl.textContent='Search failed (is the server running and index built?)';
  }
}

goBtn.addEventListener('click', doSearch);
qEl.addEventListener('input', debounce(doSearch, 400));
sortEl.addEventListener('change', doSearch);

statsLink.addEventListener('click', async (e)=>{
  e.preventDefault();
  try{
    const r=await fetch('/api/stats'); const d=await r.json();
    alert(d.ready? `Index ready. Documents: ${d.docs}` : 'Index not found. Run crawler + indexer.');
  }catch(e){ alert('Stats not available.'); }
});
