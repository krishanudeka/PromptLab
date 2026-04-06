const API = 'http://localhost:8000';
let prompts=[], selectedPromptId=null, selectedVersions=[], ollamaOnline=false, charts={};

// ---- Utilities ----
function toast(msg, type='success') {
  const c={success:'var(--accent)',error:'var(--danger)',warn:'var(--warn)'};
  document.getElementById('toast-dot').style.background=c[type]||c.success;
  document.getElementById('toast-msg').textContent=msg;
  const t=document.getElementById('toast'); t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3200);
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function sc(s){if(s==null)return'var(--muted)';return s>=7?'var(--accent)':s>=4?'var(--warn)':'var(--danger)';}
function fmt(v,dp=1){return v!=null?v.toFixed(dp):'--';}
function fmtDate(d){if(!d)return'--';return new Date(d).toLocaleDateString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});}
function killChart(k){if(charts[k]){charts[k].destroy();delete charts[k];}}

// Issue 4: rank badge HTML
function rankBadge(rank) {
  if(rank==null) return '<span class="rank-badge rank-n">--</span>';
  const cls = rank===1?'rank-1':rank===2?'rank-2':rank===3?'rank-3':'rank-n';
  const label = rank===1?'#1':rank===2?'#2':rank===3?'#3':`#${rank}`;
  return `<span class="rank-badge ${cls}">${label}</span>`;
}

function cOpts({max,yLabel,grouped}={}) {
  return {
    responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
    plugins:{
      legend:{labels:{color:'rgba(255,255,255,.4)',font:{family:"'IBM Plex Mono'",size:11},boxWidth:10,padding:10}},
      tooltip:{backgroundColor:'#1e222c',borderColor:'rgba(255,255,255,.1)',borderWidth:1,titleColor:'#e8eaf0',bodyColor:'rgba(255,255,255,.55)',titleFont:{family:"'IBM Plex Mono'",size:11},bodyFont:{family:"'IBM Plex Mono'",size:11}}
    },
    scales:{
      x:{ticks:{color:'rgba(255,255,255,.3)',font:{family:"'IBM Plex Mono'",size:10}},grid:{color:'rgba(255,255,255,.05)'}},
      y:{min:0,...(max?{max}:{}),ticks:{color:'rgba(255,255,255,.3)',font:{family:"'IBM Plex Mono'",size:10}},grid:{color:'rgba(255,255,255,.05)'},title:yLabel?{display:true,text:yLabel,color:'rgba(255,255,255,.25)',font:{size:10,family:"'IBM Plex Mono'"}}:undefined}
    },
    ...(grouped?{barPercentage:.75,categoryPercentage:.8}:{})
  };
}

// ---- Ollama status ----
async function checkOllama() {
  const pill=document.getElementById('status-pill'),txt=document.getElementById('status-text');
  pill.className='status-pill checking'; txt.textContent='Checking...';
  try {
    const r=await fetch(`${API}/health`,{signal:AbortSignal.timeout(4000)});
    const d=await r.json(); ollamaOnline=d.ollama==='ok';
  } catch { ollamaOnline=false; }
  pill.className=`status-pill ${ollamaOnline?'online':'offline'}`;
  txt.textContent=ollamaOnline?'Ollama online':'Ollama offline';
  ['offline-banner','exp-offline-banner'].forEach(id=>{
    const el=document.getElementById(id); if(el) el.classList.toggle('show',!ollamaOnline);
  });
}

// ---- Navigation ----
function showPage(p) {
  document.querySelectorAll('.page').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(el=>el.classList.remove('active'));
  document.getElementById('page-'+p).classList.add('active');
  const m={dashboard:0,prompts:1,experiments:2,history:3};
  document.querySelectorAll('.nav-tab')[m[p]].classList.add('active');
  if(p==='prompts'&&selectedPromptId) loadPromptDetail(selectedPromptId);
  if(p==='experiments') populateExpSelect();
  if(p==='dashboard') loadDashboard();
  if(p==='history') loadHistory();
}

function switchSection(s) {
  document.querySelectorAll('.section').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.inner-tab').forEach(el=>el.classList.remove('active'));
  document.getElementById('section-'+s).classList.add('active');
  const m={versions:0,compare:1,pstats:2,'add-version':3};
  document.querySelectorAll('.inner-tab')[m[s]].classList.add('active');
  if(s==='compare') loadCompare();
  if(s==='pstats') loadPromptStatsCharts();
}

// ---- Prompts ----
async function loadPrompts() {
  try {
    const r=await fetch(`${API}/prompts`); if(!r.ok) return;
    prompts=await r.json(); renderSidebar(); populateExpSelect(); populateHistoryFilter();
  } catch {}
}

function renderSidebar() {
  document.getElementById('sidebar-prompts').innerHTML=prompts.map(p=>`
    <div class="prompt-item${selectedPromptId===p.id?' active':''}" onclick="selectPrompt(${p.id},'${esc(p.name)}')">
      <div><div class="prompt-item-name">${esc(p.name)}</div><div class="prompt-item-meta">#${p.id}</div></div>
      <span class="version-badge">${p.version_count}v</span>
    </div>`).join('');
}

function selectPrompt(id, name) {
  selectedPromptId=id; showPage('prompts');
  document.getElementById('no-prompt-selected').style.display='none';
  document.getElementById('new-prompt-form').style.display='none';
  document.getElementById('prompt-detail').style.display='block';
  document.getElementById('prompt-detail-title').textContent=name;
  document.getElementById('prompt-actions').style.display='flex';
  renderSidebar();
  loadPromptDetail(id);
  loadPromptStatStrip(id);
}

// Issue 1: load per-prompt stats strip from /stats/{prompt_id}
async function loadPromptStatStrip(id) {
  ['ps-versions','ps-experiments','ps-best','ps-score'].forEach(k=>document.getElementById(k).textContent='--');
  try {
    const r=await fetch(`${API}/stats/${id}`); if(!r.ok) return;
    const d=await r.json();
    document.getElementById('ps-versions').textContent=d.version_count||0;
    document.getElementById('ps-experiments').textContent=d.experiment_count||0;
    if(d.best_version) {
      document.getElementById('ps-best').textContent=`v${d.best_version.version_number}`;
      document.getElementById('ps-score').textContent=d.best_version.avg_score.toFixed(1);
    } else {
      document.getElementById('ps-best').textContent='none';
      document.getElementById('ps-score').textContent='--';
    }
  } catch {}
}

// Issue 1: per-prompt trend charts rendered in "This prompt stats" tab
async function loadPromptStatsCharts() {
  if(!selectedPromptId) return;
  try {
    const r=await fetch(`${API}/stats/${selectedPromptId}`); if(!r.ok) return;
    const d=await r.json();
    const trend=d.trend||[];
    const labels=trend.map(t=>`#${t.experiment_id}`);
    const scores=trend.map(t=>t.avg_score!=null?parseFloat(t.avg_score.toFixed(2)):null);
    const lats=trend.map(t=>t.avg_latency!=null?parseFloat(t.avg_latency.toFixed(2)):null);

    killChart('ps-s'); killChart('ps-l');
    charts['ps-s']=new Chart(document.getElementById('chart-ps-score'),{type:'line',data:{labels,datasets:[{label:'Avg score',data:scores,borderColor:'rgba(126,232,162,.8)',backgroundColor:'rgba(126,232,162,.08)',fill:true,tension:.4,pointBackgroundColor:'rgba(126,232,162,1)',pointRadius:4,spanGaps:true}]},options:cOpts({max:10,yLabel:'Score'})});
    charts['ps-l']=new Chart(document.getElementById('chart-ps-latency'),{type:'line',data:{labels,datasets:[{label:'Avg latency (s)',data:lats,borderColor:'rgba(56,189,248,.8)',backgroundColor:'rgba(56,189,248,.08)',fill:true,tension:.4,pointBackgroundColor:'rgba(56,189,248,1)',pointRadius:4,spanGaps:true}]},options:cOpts({yLabel:'Seconds'})});
  } catch {}
}

async function loadPromptDetail(id) {
  try {
    const r=await fetch(`${API}/prompts/${id}/versions`); if(!r.ok) return;
    selectedVersions=await r.json(); renderVersionsList();
  } catch {}
}

// Issue 4: rank column in version list
function renderVersionsList() {
  const el=document.getElementById('versions-list');
  if(!selectedVersions.length){el.innerHTML='<div class="empty"><div class="empty-title">No versions yet</div><div class="empty-sub">Add a version to get started</div></div>';return;}
  el.innerHTML=`<div style="display:grid;grid-template-columns:30px 50px 1fr 100px 70px 60px;gap:10px;padding:8px 0;color:var(--muted);font-size:10px;font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)">
    <span>Rank</span><span>Ver</span><span>Content</span><span>Avg score</span><span>Runs</span><span>ID</span>
  </div>`
  +selectedVersions.map(v=>`
    <div class="version-row">
      ${rankBadge(v.rank)}
      <span class="version-tag">v${v.version_number}</span>
      <span style="font-family:var(--font-mono);font-size:12px;color:var(--muted);overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;line-clamp:2;-webkit-box-orient:vertical">${esc(v.content)}</span>
      <div class="score-bar">
        <span class="score-num" style="color:${sc(v.avg_score)}">${fmt(v.avg_score)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${v.avg_score!=null?v.avg_score*10:0}%"></div></div>
      </div>
      <span style="font-size:12px;color:var(--muted);font-family:var(--font-mono)">${v.run_count||0}</span>
      <span style="font-size:11px;color:var(--muted);font-family:var(--font-mono)">#${v.id}</span>
    </div>`).join('');
}

async function loadCompare() {
  if(!selectedPromptId) return;
  try {
    const r=await fetch(`${API}/prompts/${selectedPromptId}/compare`);
    const data=await r.json();
    const labels=data.map(d=>`v${d.version}`);

    killChart('cs');
    charts['cs']=new Chart(document.getElementById('chart-compare-score'),{type:'bar',data:{labels,datasets:[{label:'Composite',data:data.map(d=>d.avg_score),backgroundColor:'rgba(126,232,162,.35)',borderColor:'rgba(126,232,162,.8)',borderWidth:1,borderRadius:5}]},options:cOpts({max:10,yLabel:'Score'})});

    killChart('cd');
    charts['cd']=new Chart(document.getElementById('chart-compare-dims'),{type:'bar',data:{labels,datasets:[
      {label:'Clarity',data:data.map(d=>d.avg_clarity||0),backgroundColor:'rgba(56,189,248,.5)',borderColor:'rgba(56,189,248,.9)',borderWidth:1,borderRadius:4},
      {label:'Relevance',data:data.map(d=>d.avg_relevance||0),backgroundColor:'rgba(244,114,182,.5)',borderColor:'rgba(244,114,182,.9)',borderWidth:1,borderRadius:4},
      {label:'Grammar',data:data.map(d=>d.avg_grammar||0),backgroundColor:'rgba(126,232,162,.5)',borderColor:'rgba(126,232,162,.9)',borderWidth:1,borderRadius:4},
      {label:'Depth',data:data.map(d=>d.avg_depth||0),backgroundColor:'rgba(251,191,36,.5)',borderColor:'rgba(251,191,36,.9)',borderWidth:1,borderRadius:4}
    ]},options:cOpts({max:10,yLabel:'Score',grouped:true})});

    const ml=Math.max(...data.map(d=>d.avg_latency||0),1);
    document.getElementById('compare-latency-bars').innerHTML=data.map(d=>`
      <div class="compare-bar">
        <div class="compare-label">v${d.version}</div>
        <div class="compare-track"><div class="compare-fill" style="width:${((d.avg_latency||0)/ml)*100}%"><span style="font-size:11px;color:rgba(255,255,255,.8);font-family:var(--font-mono)">${fmt(d.avg_latency,2)}s</span></div></div>
        <div class="compare-score">${d.run_count} runs</div>
      </div>`).join('');
  } catch { toast('Could not load compare data','error'); }
}

// ---- Prompt CRUD ----
function showNewPromptForm() {
  showPage('prompts'); selectedPromptId=null;
  document.getElementById('no-prompt-selected').style.display='none';
  document.getElementById('prompt-detail').style.display='none';
  document.getElementById('prompt-actions').style.display='none';
  document.getElementById('new-prompt-form').style.display='block';
  document.getElementById('prompt-detail-title').textContent='New prompt';
  renderSidebar();
}

async function createPrompt() {
  const name=document.getElementById('new-prompt-name').value.trim();
  if(!name){toast('Enter a prompt name','error');return;}
  try {
    const r=await fetch(`${API}/prompts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    const p=await r.json(); toast('Prompt created!');
    document.getElementById('new-prompt-name').value='';
    await loadPrompts(); selectPrompt(p.id,p.name);
  } catch { toast('Error creating prompt','error'); }
}

async function addVersion() {
  const content=document.getElementById('new-version-content').value.trim();
  if(!content||!selectedPromptId){toast('Enter version content','error');return;}
  try {
    await fetch(`${API}/prompts/${selectedPromptId}/versions`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});
    toast('Version saved!'); document.getElementById('new-version-content').value='';
    await loadPrompts(); await loadPromptDetail(selectedPromptId);
    await loadPromptStatStrip(selectedPromptId);
    renderSidebar(); switchSection('versions');
  } catch { toast('Error saving version','error'); }
}

// ---- Experiments ----
function populateExpSelect() {
  document.getElementById('exp-prompt-select').innerHTML='<option value="">Select a prompt...</option>'+prompts.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
}

async function runExperiment() {
  if(!ollamaOnline){toast('Ollama is offline — start it first','error');return;}
  const promptId=parseInt(document.getElementById('exp-prompt-select').value);
  const inputText=document.getElementById('exp-input').value.trim();
  if(!promptId||!inputText){toast('Select a prompt and enter input','error');return;}

  const btn=document.getElementById('run-btn');
  btn.disabled=true; btn.innerHTML='<span class="spinner"></span> Running...';
  document.getElementById('exp-empty').style.display='none';
  document.getElementById('exp-results-card').style.display='none';

  try {
    const r=await fetch(`${API}/experiments/run`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt_id:promptId,input_text:inputText})});
    if(!r.ok) {
      const err=await r.json();
      toast(err?.detail?.message||err?.detail||'Experiment failed','error');
      document.getElementById('exp-empty').style.display='block';
      if(err?.detail?.error==='ollama_offline'){ollamaOnline=false;checkOllama();}
    } else {
      const data=await r.json();
      // Always render — even if all results are errors, show them
      renderExpResults(data);
      const allFailed = data.results.every(r=>r.error);
      toast(allFailed ? 'Experiment ran — LLM output was too short or eval failed' : 'Experiment complete!', allFailed?'warn':'success');
      loadDashboard();
      if(selectedPromptId===promptId){ loadPromptStatStrip(promptId); loadPromptDetail(promptId); }
    }
  } catch(e) { toast('Network error — is the API running? '+e.message,'error'); document.getElementById('exp-empty').style.display='block'; }
  btn.disabled=false; btn.innerHTML='Run experiment';
}

function renderExpResults(data) {
  document.getElementById('exp-results-card').style.display='block';

  // Issue 3: best_version is now { version, score } — use .version not .version_id
  const bestVer = data.best_version?.version;

  document.getElementById('exp-results').innerHTML=data.results.map(r=>{
    const isBest = r.version === bestVer && !r.error;
    const s=r.scores||{};
    return `
    <div class="result-card${isBest?' best-card':''}${r.error?' failed-card':''}">
      <div class="result-header">
        <span class="version-tag">v${r.version}${isBest?' &#9733; best':''}</span>
        <div style="display:flex;align-items:center;gap:8px">
          ${r.error?`<span class="error-badge">${r.error_type==='eval_failed'?'Eval failed':'LLM failed'}</span>`:''}
          <span class="latency-badge">${r.latency.toFixed(2)}s</span>
          ${!r.error?`<span style="font-family:var(--font-mono);font-size:16px;font-weight:600;color:${sc(r.score)}">${fmt(r.score)}</span>`:''}
        </div>
      </div>
      <div class="output-text">${esc(r.output)}</div>
      ${!r.error?`<div class="score-breakdown">
        <div class="score-dim"><div class="score-dim-label">Clarity</div><div class="score-dim-val" style="color:var(--accent2)">${fmt(s.clarity)}</div></div>
        <div class="score-dim"><div class="score-dim-label">Relevance</div><div class="score-dim-val" style="color:var(--accent3)">${fmt(s.relevance)}</div></div>
        <div class="score-dim"><div class="score-dim-label">Grammar</div><div class="score-dim-val" style="color:var(--accent)">${fmt(s.grammar)}</div></div>
        <div class="score-dim"><div class="score-dim-label">Depth</div><div class="score-dim-val" style="color:var(--warn)">${fmt(s.depth)}</div></div>
      </div>`:`<div style="font-size:11px;color:var(--danger);font-family:var(--font-mono);margin-top:6px;">LLM did not generate output.</div>`}
    </div>`;
  }).join('');

  const good=data.results.filter(r=>!r.error&&r.score!=null&&r.score>0);
  if(good.length>0) {
    killChart('es');
    charts['es']=new Chart(document.getElementById('chart-exp-scores'),{type:'bar',data:{
      labels:good.map(r=>`v${r.version}`),
      datasets:[
        {label:'Clarity',   data:good.map(r=>r.scores?.clarity||0),   backgroundColor:'rgba(56,189,248,.5)',  borderColor:'rgba(56,189,248,.9)',  borderWidth:1,borderRadius:4},
        {label:'Relevance', data:good.map(r=>r.scores?.relevance||0), backgroundColor:'rgba(244,114,182,.5)', borderColor:'rgba(244,114,182,.9)', borderWidth:1,borderRadius:4},
        {label:'Grammar',   data:good.map(r=>r.scores?.grammar||0),   backgroundColor:'rgba(126,232,162,.5)', borderColor:'rgba(126,232,162,.9)', borderWidth:1,borderRadius:4},
        {label:'Composite', data:good.map(r=>r.score),                backgroundColor:'rgba(251,191,36,.5)',   borderColor:'rgba(251,191,36,.9)',  borderWidth:1,borderRadius:4},
      ]},options:cOpts({max:10,yLabel:'Score',grouped:true})});
  }
}

// ---- History ----
function populateHistoryFilter() {
  document.getElementById('history-filter').innerHTML='<option value="">All prompts</option>'+prompts.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
}

async function loadHistory() {
  const fid=document.getElementById('history-filter').value;
  const el=document.getElementById('history-list');
  el.innerHTML='<div style="color:var(--muted);padding:16px 0;font-size:13px">Loading...</div>';
  try {
    const r=await fetch(fid?`${API}/experiments?prompt_id=${fid}`:`${API}/experiments`);
    const data=await r.json();
    if(!data.length){el.innerHTML='<div class="empty" style="padding:30px 0"><div class="empty-title">No experiments yet</div></div>';return;}
    const pm={};prompts.forEach(p=>pm[p.id]=p.name);
    el.innerHTML=data.map(e=>`
      <div class="history-row" onclick="viewExpDetail(${e.id})">
        <span style="font-family:var(--font-mono);color:var(--muted);font-size:12px">#${e.id}</span>
        <span style="overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${esc(e.input_text)}</span>
        <span style="font-size:12px;color:var(--accent2)">${esc(pm[e.prompt_id]||'#'+e.prompt_id)}</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--muted)">${e.result_count} results</span>
        <span style="font-size:11px;color:var(--muted)">${fmtDate(e.created_at)}</span>
      </div>`).join('');
  } catch { el.innerHTML='<div style="color:var(--danger);padding:16px 0">Could not load history</div>'; }
}

async function viewExpDetail(id) {
  document.getElementById('history-card').style.display='none';
  document.getElementById('exp-detail').style.display='block';
  document.getElementById('exp-detail-title').textContent=`Experiment #${id}`;
  const content=document.getElementById('exp-detail-content');
  content.innerHTML='<div style="color:var(--muted);font-size:13px">Loading...</div>';
  try {
    const [mainRes, debugRes] = await Promise.all([
      fetch(`${API}/experiments/${id}`),
      fetch(`${API}/debug/experiments/${id}`)
    ]);
    const data = await mainRes.json();
    const dbg  = await debugRes.json();

    const bestVer = data.best_version?.version;
    const resultCount = data.results?.length || 0;
    const dbResultCount = dbg.result_count || 0;

    // Debug info strip — always shown so we can diagnose issues
    const debugStrip = `
      <div style="background:rgba(56,189,248,.06);border:1px solid rgba(56,189,248,.2);border-radius:8px;padding:12px 16px;margin-bottom:16px;font-family:var(--font-mono);font-size:11px;color:var(--muted);line-height:1.9">
        <div style="color:var(--accent2);font-weight:500;margin-bottom:6px">DEBUG — experiment #${id}</div>
        DB result rows: <span style="color:${dbResultCount>0?'var(--accent)':'var(--danger)'}">${dbResultCount}</span> &nbsp;|&nbsp;
        API results returned: <span style="color:${resultCount>0?'var(--accent)':'var(--danger)'}">${resultCount}</span> &nbsp;|&nbsp;
        input_text: <span style="color:${data.input_text?'var(--accent)':'var(--danger)'}">${data.input_text?'present':'MISSING'}</span> &nbsp;|&nbsp;
        created_at: <span style="color:${data.created_at?'var(--accent)':'var(--danger)'}">${data.created_at?'present':'MISSING'}</span><br>
        ${dbg.results?.map(r=>`row #${r.id}: version_id=${r.version_id} score=${r.score} output="${(r.output||'').substring(0,50)}"`).join('<br>')||'no rows in DB'}
      </div>`;

    if(resultCount === 0 && dbResultCount === 0) {
      content.innerHTML = debugStrip + `
        <div class="card">
          <div class="card-title" style="color:var(--danger)">No results saved</div>
          <div style="font-size:13px;color:var(--muted);line-height:1.9">
            This experiment ran when error-skipping was still active.<br>
            Run a new experiment — results will now always be saved.
          </div>
        </div>`;
      return;
    }

    content.innerHTML = debugStrip + `
      <div class="card" style="margin-bottom:16px">
        <div class="card-title">Input</div>
        <div class="output-text" style="max-height:none">${esc(data.input_text||'(empty — old experiment)')}</div>
        <div style="font-size:12px;color:var(--muted);font-family:var(--font-mono);margin-top:8px">${fmtDate(data.created_at)}</div>
      </div>`
    +(data.results||[]).sort((a,b)=>(b.score||0)-(a.score||0)).map((r,idx)=>{
      const s=r.scores||{}; const isBest=r.version===bestVer;
      const isErr=r.error||false;
      return `
      <div class="result-card${isBest?' best-card':''}${isErr?' failed-card':''}">
        <div class="result-header">
          <div style="display:flex;align-items:center;gap:8px">
            ${!isErr?rankBadge(idx+1):''}
            <span class="version-tag">v${r.version}${isBest?' &#9733; best':''}</span>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            ${isErr?'<span class="error-badge">LLM failed</span>':''}
            <span class="latency-badge">${fmt(r.latency,2)}s</span>
            ${!isErr?`<span style="font-family:var(--font-mono);font-size:16px;font-weight:600;color:${sc(r.score)}">${fmt(r.score)}</span>`:''}
          </div>
        </div>
        <div class="output-text">${esc(r.output||'')}</div>
        ${!isErr?`<div class="score-breakdown">
          <div class="score-dim"><div class="score-dim-label">Clarity</div><div class="score-dim-val" style="color:var(--accent2)">${fmt(s.clarity)}</div></div>
          <div class="score-dim"><div class="score-dim-label">Relevance</div><div class="score-dim-val" style="color:var(--accent3)">${fmt(s.relevance)}</div></div>
          <div class="score-dim"><div class="score-dim-label">Grammar</div><div class="score-dim-val" style="color:var(--accent)">${fmt(s.grammar)}</div></div>
          <div class="score-dim"><div class="score-dim-label">Depth</div><div class="score-dim-val" style="color:var(--warn)">${fmt(s.depth)}</div></div>
        </div>`:''}
      </div>`;
    }).join('');
  } catch(e) { content.innerHTML=`<div style="color:var(--danger)">Error: ${e.message}</div>`; }
}

function closeExpDetail() {
  document.getElementById('history-card').style.display='block';
  document.getElementById('exp-detail').style.display='none';
}

// ---- Dashboard (always global, uses /stats) ----
async function loadDashboard() {
  try {
    const r=await fetch(`${API}/stats`); const s=await r.json();
    document.getElementById('stat-prompts').textContent=s.total_prompts||'--';
    document.getElementById('stat-versions').textContent=s.total_versions||'--';
    document.getElementById('stat-experiments').textContent=s.total_experiments||'--';
    document.getElementById('stat-avg-score').textContent=s.avg_score!=null?s.avg_score.toFixed(1):'--';
  } catch {
    document.getElementById('stat-prompts').textContent=prompts.length||'--';
    document.getElementById('stat-versions').textContent=prompts.reduce((a,p)=>a+(p.version_count||0),0)||'--';
  }

  try {
    const r=await fetch(`${API}/experiments`); const exps=await r.json();
    const last10=exps.slice(0,10).reverse();
    const td=await Promise.all(last10.map(async e=>{
      try {
        const rd=await fetch(`${API}/experiments/${e.id}`); const d=await rd.json();
        const s2=(d.results||[]).map(r=>r.score).filter(x=>x!=null);
        const lt=(d.results||[]).map(r=>r.latency).filter(Boolean);
        return{id:e.id,avgScore:s2.length?s2.reduce((a,b)=>a+b,0)/s2.length:null,avgLatency:lt.length?lt.reduce((a,b)=>a+b,0)/lt.length:null};
      } catch { return{id:e.id,avgScore:null,avgLatency:null}; }
    }));

    killChart('st'); killChart('lt');
    charts['st']=new Chart(document.getElementById('chart-score-trend'),{type:'line',data:{labels:td.map(d=>`#${d.id}`),datasets:[{label:'Avg score',data:td.map(d=>d.avgScore!=null?parseFloat(d.avgScore.toFixed(2)):null),borderColor:'rgba(126,232,162,.8)',backgroundColor:'rgba(126,232,162,.08)',fill:true,tension:.4,pointBackgroundColor:'rgba(126,232,162,1)',pointRadius:4,spanGaps:true}]},options:cOpts({max:10,yLabel:'Score'})});
    charts['lt']=new Chart(document.getElementById('chart-latency-trend'),{type:'line',data:{labels:td.map(d=>`#${d.id}`),datasets:[{label:'Avg latency (s)',data:td.map(d=>d.avgLatency!=null?parseFloat(d.avgLatency.toFixed(2)):null),borderColor:'rgba(56,189,248,.8)',backgroundColor:'rgba(56,189,248,.08)',fill:true,tension:.4,pointBackgroundColor:'rgba(56,189,248,1)',pointRadius:4,spanGaps:true}]},options:cOpts({yLabel:'Seconds'})});
  } catch {}

  const el=document.getElementById('recent-prompts-list');
  if(!prompts.length){el.innerHTML='<div class="empty"><div class="empty-title">No prompts yet</div></div>';return;}
  el.innerHTML=prompts.slice(0,5).map(p=>`
    <div style="display:flex;align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid var(--border)">
      <div>
        <div style="font-weight:500">${esc(p.name)}</div>
        <div style="font-size:12px;color:var(--muted);font-family:var(--font-mono)">#${p.id} &middot; ${p.version_count}v &middot; ${p.experiment_count||0} experiments</div>
      </div>
      <button class="btn btn-secondary" style="font-size:12px;padding:6px 14px" onclick="selectPrompt(${p.id},'${esc(p.name)}')">Open</button>
    </div>`).join('')+(prompts.length>5?`<div style="text-align:center;padding:12px;color:var(--muted);font-size:12px">+${prompts.length-5} more</div>`:'');
}

// ---- Init ----
(async()=>{
  await checkOllama();
  await loadPrompts();
  loadDashboard();
  setInterval(checkOllama, 30000);
})();
