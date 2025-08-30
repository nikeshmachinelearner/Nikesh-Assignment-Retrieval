const textEl=document.getElementById('text');
const modelEl=document.getElementById('model');
const resultEl=document.getElementById('result');
const predictBtn=document.getElementById('predictBtn');
const metricsLink=document.getElementById('metricsLink');

function renderResult(payload){
  resultEl.style.display='block';
  if(payload.error){ resultEl.innerHTML=`<strong>Error:</strong> ${payload.error}`; return; }
  let html='<h3>Prediction</h3>';
  html+=`<p><strong>Label:</strong> ${payload.label}</p>`;
  if(payload.probabilities){
    html+='<table><tr><th>Class</th><th>Probability</th></tr>';
    for(const [c,p] of payload.probabilities){ html+=`<tr><td>${c}</td><td>${p.toFixed(3)}</td></tr>`; }
    html+='</table>';
  }
  if(payload.top_terms && payload.top_terms.length){
    html+=`<p><strong>Top indicative terms:</strong> ${payload.top_terms.join(', ')}</p>`;
  }
  resultEl.innerHTML=html;
}

predictBtn.addEventListener('click', async ()=>{
  const text=textEl.value.trim(); const model=modelEl.value;
  if(!text){ renderResult({error:'Please paste some text first.'}); return; }
  renderResult({label:'...', probabilities:null});
  try{
    const res=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,model})});
    const data=await res.json(); renderResult(data);
  }catch(e){ renderResult({error:'Server not reachable. Did you run python app.py ?'}); }
});

metricsLink.addEventListener('click', async (e)=>{
  e.preventDefault();
  try{
    const res=await fetch('/metrics'); const m=await res.json();
    if(m.error){ alert(m.error); return; }
    const nb=m.cv.nb, lr=m.cv.lr; const hnb=m.heldout.nb, hlr=m.heldout.lr, best=m.heldout.best_model;
    alert(
      `Docs per class: ${JSON.stringify(m.counts)}\n\n`+
      `CV — NB: mean=${nb.accuracy_mean.toFixed(3)} (±${nb.accuracy_std.toFixed(3)})\n`+
      `CV — LR: mean=${lr.accuracy_mean.toFixed(3)} (±${lr.accuracy_std.toFixed(3)})\n\n`+
      `Held-out — NB acc=${hnb.accuracy.toFixed(3)} | LR acc=${hlr.accuracy.toFixed(3)}\n`+
      `Best model: ${best.toUpperCase()}`
    );
  }catch(e){ alert('Metrics not available yet. Run: python train.py'); }
});
