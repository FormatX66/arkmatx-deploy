(()=>{
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const apiBase=(params.get('api')||'').replace(/\/+$/,'');
  const apiUrl=path=>`${apiBase}/api${path}`;
  let liveApi=false;
  let hostTestsEnabled=false;
  const demoProjects=[{id:'demo',name:'Demo Website',repository:'',site_url:'',status:'ready'}];
  let demoTasks=[];

  async function request(path,options={}){
    if(!liveApi)throw new Error('Arkmatx backend is not online.');
    const response=await fetch(apiUrl(path),{
      cache:'no-store',
      ...options,
      headers:{'Content-Type':'application/json',...(options.headers||{})},
    });
    const data=await response.json().catch(()=>({}));
    if(!response.ok){
      const detail=data.detail;
      const message=typeof detail==='object'?(detail.message||JSON.stringify(detail)):(detail||`HTTP ${response.status}`);
      throw new Error(message);
    }
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

  function describeHostResult(data){
    const parts=[`${String(data.status||'unknown').toUpperCase()}: ${data.message||'Test complete.'}`];
    if(data.protocol&&data.protocol!=='auto')parts.push(`${data.protocol} on port ${data.port}`);
    if(data.capabilities?.length)parts.push(`Available: ${data.capabilities.join(', ')}`);
    if(data.host_key?.sha256)parts.push(`SSH key: SHA256:${data.host_key.sha256}`);
    if(data.alternatives?.length)parts.push(`Also reachable: ${data.alternatives.map(x=>`${x.protocol}:${x.port}`).join(', ')}`);
    parts.push('Password discarded; nothing was changed.');
    return parts.join(' · ');
  }

  async function testHost(event){
    event.preventDefault();
    const password=$('hostPassword').value;
    const portValue=$('hostPort').value.trim();
    const payload={
      domain:$('hostDomain').value.trim(),
      username:$('hostUser').value.trim(),
      password,
      protocol:$('hostProtocol').value,
      port:portValue?Number(portValue):null,
    };
    const button=$('hostTestButton');
    if(!liveApi||!hostTestsEnabled){
      $('hostPassword').value='';
      setResult($('hostResult'),'The interface is ready, but this preview has no network-enabled Arkmatx backend. No credentials were sent.','warn');
      return;
    }
    button.disabled=true;button.classList.add('loading');
    setResult($('hostResult'),'Testing one read-only connection…','');
    try{
      const data=await request('/hosts/test',{method:'POST',body:JSON.stringify(payload)});
      setResult($('hostResult'),describeHostResult(data),data.authenticated?'good':(data.status==='reachable'?'warn':'bad'));
    }catch(error){
      setResult($('hostResult'),`${error.message} Password discarded; nothing was changed.`,'bad');
    }finally{
      $('hostPassword').value='';
      button.disabled=false;button.classList.remove('loading');
    }
  }

  async function loadProjects(){try{renderProjects(liveApi?(await request('/projects')).items:demoProjects)}catch{renderProjects(demoProjects)}}
  async function loadTasks(){try{renderTasks(liveApi?(await request('/tasks')).items:demoTasks)}catch{renderTasks(demoTasks)}}
  async function loadConnectors(){try{renderConnectors(liveApi?(await request('/connectors')).items:[{name:'BoxBrain',status:'preview-safe'},{name:'Brain Connect',status:'adapter-ready'}])}catch{renderConnectors([{name:'BoxBrain',status:'offline'},{name:'Brain Connect',status:'adapter-ready'}])}}

  $('commandForm').addEventListener('submit',event=>{event.preventDefault();runCommand($('commandInput').value);});
  document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>runCommand(button.dataset.command)));
  $('hostForm').addEventListener('submit',testHost);
  $('refreshProjects').addEventListener('click',loadProjects);

  (async()=>{
    const health=document.querySelector('.health');
    const state=$('hostTestState');
    try{
      const r=await fetch(apiUrl('/health'),{cache:'no-store'});if(!r.ok)throw new Error();
      const data=await r.json();
      liveApi=true;hostTestsEnabled=Boolean(data.host_authentication_tests);
      $('healthText').textContent=hostTestsEnabled?'HOST TEST READY':'API ONLINE';
      health.classList.add(hostTestsEnabled?'ok':'warn');
      state.textContent=hostTestsEnabled?'Backend online. Read-only connection testing is enabled.':'Backend online, but network connection tests are disabled by policy.';
      state.classList.add(hostTestsEnabled?'ready':'off');
      $('hostTestButton').disabled=!hostTestsEnabled;
    }catch{
      $('healthText').textContent='PREVIEW ONLY';health.classList.add('warn');
      state.textContent='Static preview only. Connect this interface to the Arkmatx backend to run a real host login test.';
      state.classList.add('off');$('hostTestButton').disabled=true;
    }
    await Promise.all([loadProjects(),loadTasks(),loadConnectors()]);
    if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{});
  })();
})();
