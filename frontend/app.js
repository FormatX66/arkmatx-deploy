(()=>{
  const $=id=>document.getElementById(id);
  let liveApi=false;
  const demoProjects=[{id:'demo',name:'Demo Website',repository:'',site_url:'',status:'ready'}];
  let demoTasks=[];

  async function request(path,options={}){
    if(!liveApi)throw new Error('demo');
    const response=await fetch(`/api${path}`,{
      ...options,
      headers:{'Content-Type':'application/json',...(options.headers||{})},
    });
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
    return data;
  }

  function setResult(element,text,kind=''){
    element.textContent=text;element.className=`result ${kind}`.trim();
  }

  function renderProjects(items){
    $('projects').innerHTML=items.map(item=>`<article class="card"><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.repository||item.site_url||'No repository connected yet')}</small><span class="status">${escapeHtml(item.status.toUpperCase())}</span></article>`).join('');
  }

  function renderTasks(items){
    $('tasks').innerHTML=items.length?items.map(item=>{
      const approval=item.requires_confirmation&&item.status==='waiting-confirmation'
        ?`<form class="confirm" data-task="${item.id}"><input placeholder="Type ${item.confirmation_phrase}"><button>CONFIRM</button></form>`:'';
      return `<div class="list-item"><strong>${escapeHtml(item.intent.toUpperCase())}</strong><small>${escapeHtml(item.status)} · ${escapeHtml(item.details?.summary||'queued action')}</small>${approval}</div>`;
    }).join(''):'<div class="list-item"><small>No tasks yet.</small></div>';
    document.querySelectorAll('.confirm').forEach(form=>form.addEventListener('submit',approveTask));
  }

  function renderConnectors(items){
    $('connectors').innerHTML=items.map(item=>`<div class="list-item"><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.status||'unknown')}</small></div>`).join('');
  }

  function escapeHtml(value=''){
    return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  }

  async function runCommand(text){
    if(!text.trim())return;
    try{
      let data;
      if(liveApi){
        data=await request('/commands',{method:'POST',body:JSON.stringify({text})});
      }else{
        const action=(text.match(/deploy|ship|publish|rollback|undo|restore|preview|test|check|status|backup|clone/i)||[])[0]||'unknown';
        const destructive=/deploy|ship|publish|rollback|undo|restore|clone/i.test(action);
        const task={id:crypto.randomUUID(),intent:action,status:destructive?'waiting-confirmation':'queued',requires_confirmation:destructive,confirmation_phrase:/rollback|undo|restore/i.test(action)?'UNDO':'SHIP',details:{summary:text}};
        demoTasks.unshift(task);data={task,parsed:{summary:text}};
      }
      setResult($('commandResult'),`${data.parsed.summary} → ${data.task.status}`,'good');
      await loadTasks();
    }catch(error){setResult($('commandResult'),error.message,'bad')}
  }

  async function approveTask(event){
    event.preventDefault();const form=event.currentTarget;const id=form.dataset.task;const confirmation=form.querySelector('input').value;
    try{
      if(liveApi){await request(`/tasks/${id}/approve`,{method:'POST',body:JSON.stringify({confirmation})});}
      else{const task=demoTasks.find(x=>x.id===id);if(task&&confirmation.toUpperCase()===task.confirmation_phrase){task.status='queued';}else throw new Error('Wrong confirmation phrase');}
      await loadTasks();
    }catch(error){alert(error.message)}
  }

  async function detectHost(event){
    event.preventDefault();const payload={domain:$('hostDomain').value,username:$('hostUser').value,password:$('hostPassword').value||null,protocol:'auto'};
    try{
      let data;
      if(liveApi)data=await request('/hosts/detect',{method:'POST',body:JSON.stringify(payload)});
      else data={domain:payload.domain,probe_mode:'demo',credentials_saved:false,candidates:['ssh/sftp','ftp','ftps','cpanel','plesk','directadmin','https/api'].map((protocol,i)=>({protocol,port:[22,21,990,2083,8443,2222,443][i],status:'ready-to-test'}))};
      $('hostPassword').value='';
      setResult($('hostResult'),`${data.domain}: ${data.candidates.map(x=>`${x.protocol} ${x.port} (${x.status})`).join(' · ')}. Password discarded.`,'good');
    }catch(error){$('hostPassword').value='';setResult($('hostResult'),error.message,'bad')}
  }

  async function loadProjects(){try{renderProjects(liveApi?(await request('/projects')).items:demoProjects)}catch{renderProjects(demoProjects)}}
  async function loadTasks(){try{renderTasks(liveApi?(await request('/tasks')).items:demoTasks)}catch{renderTasks(demoTasks)}}
  async function loadConnectors(){try{renderConnectors(liveApi?(await request('/connectors')).items:[{name:'BoxBrain',status:'demo-safe'},{name:'Brain Connect',status:'adapter-ready'}])}catch{renderConnectors([{name:'BoxBrain',status:'offline'},{name:'Brain Connect',status:'adapter-ready'}])}}

  $('commandForm').addEventListener('submit',event=>{event.preventDefault();runCommand($('commandInput').value);});
  document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>runCommand(button.dataset.command)));
  $('hostForm').addEventListener('submit',detectHost);
  $('refreshProjects').addEventListener('click',loadProjects);

  (async()=>{
    try{const r=await fetch('/api/health',{cache:'no-store'});if(!r.ok)throw new Error();liveApi=true;$('healthText').textContent='API ONLINE';document.querySelector('.health').classList.add('ok');}
    catch{$('healthText').textContent='DEMO MODE';document.querySelector('.health').classList.add('bad');}
    await Promise.all([loadProjects(),loadTasks(),loadConnectors()]);
    if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{});
  })();
})();
