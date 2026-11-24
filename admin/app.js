'use strict';
const $ = id => document.getElementById(id);
let csrf = '', tab = 'overview', rows = [], editing = null;
const config = {
 contacts: { title:'Contacts', description:'The people behind every conversation.', columns:['name','email','phone','status'], fields:{ name:'text',email:'email',phone:'tel',role:'text',status:'text',source:'text',notes:'textarea' }, required:['name'] },
 deals: { title:'Deals', description:'Keep every opportunity moving forward.', columns:['title','value','currency','stage','probability'], fields:{title:'text',contact_id:'contact',value:'number',currency:'text',stage:'text',probability:'number',close_date:'date',notes:'textarea'},required:['title'] },
 activities: {title:'Activities',description:'Your notes, conversations and next steps.',columns:['kind','body','follow_up_at','completed'],fields:{contact_id:'contact',deal_id:'deal',kind:'text',body:'textarea',follow_up_at:'datetime-local',completed:'checkbox'},required:['body']},
 rag: { title:'Knowledge',description:'Trusted information for the BrightClean public assistant.',columns:['title','content','updated_at'],fields:{title:'text',url:'url',content:'textarea'},required:['title','content'] }
};
const labels = {contact_id:'Contact',deal_id:'Deal',follow_up_at:'Follow-up date',close_date:'Expected close date',updated_at:'Last updated',body:'Note',content:'Knowledge content',url:'Source URL',value:'Deal value',probability:'Probability (%)'};
const label = key => labels[key] || key.charAt(0).toUpperCase() + key.slice(1).replaceAll('_',' ');
function el(tag,text,cls) { const node=document.createElement(tag); if(text!==undefined) node.textContent=text; if(cls) node.className=cls; return node; }
async function api(path,method='GET',data) {
 const options={method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},credentials:'same-origin'};
 if(data!==undefined) options.body=JSON.stringify(data);
 const response=await fetch('/api/'+path,options);
 const result=await response.json();
 if(!response.ok) { if(response.status===401 && path!=='login') showLogin(); throw new Error(result.error || 'Request failed. Please try again.'); }
 return result;
}
function message(text,error=false) { $('message').textContent=text; $('message').hidden=false; $('message').style.color=error?'#a32b35':''; }
function showLogin() { csrf=''; rows=[]; $('workspace').hidden=true; $('login').hidden=false; $('editor').close(); $('table-body').replaceChildren(); $('stats').replaceChildren(); }
async function signedIn() {
 const session=await api('session'); csrf=session.csrf;
 $('username').textContent=session.username; $('classroom').hidden=!session.classroom;
 $('login-form').reset(); $('login-error').textContent=''; $('login').hidden=true; $('workspace').hidden=false;
 await navigate('overview');
}
$('login-form').addEventListener('submit',async event=>{
 event.preventDefault(); const button=event.submitter; button.disabled=true;
 try { const data=Object.fromEntries(new FormData(event.target)); const session=await api('login','POST',data); csrf=session.csrf; await signedIn(); }
 catch(error) { $('login-error').textContent=error.message; $('login-form').elements.password.value=''; }
 finally { button.disabled=false; }
});
$('logout').onclick=async()=>{ try { await api('logout','POST',{}); showLogin(); } catch(error){message(error.message,true);} };
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>navigate(button.dataset.tab));
async function navigate(next) {
 tab=next; $('message').hidden=true;
 document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
 $('page-title').textContent=tab==='overview'?'Overview':tab==='settings'?'Chatbot Settings':config[tab].title;
 $('overview').hidden=tab!=='overview'; $('records').hidden=tab==='overview'||tab==='settings'; $('settings').hidden=tab!=='settings';
 try {
  if(tab==='overview') {
   const counts=await api('summary'); $('stats').replaceChildren();
   for(const [key,title] of [['contacts','Total contacts'],['deals','Total deals'],['activities','Activities'],['knowledge','Knowledge articles']]) {
    const card=el('div',undefined,'stat');card.append(el('span',title),el('strong',String(counts[key])));$('stats').append(card);
   }
  } else if(tab==='settings') {
   await loadSettings();
  } else {
   $('list-title').textContent=config[tab].title; $('list-description').textContent=config[tab].description;
   $('knowledge-upload').hidden=tab!=='rag';
   $('add').textContent=tab==='rag'?'Add knowledge':'Add '+tab.slice(0,-1); $('search').value='';
   rows=[]; render(); const selected=tab; const result=await api(tab); if(tab===selected) {rows=result;render();}
  }
 } catch(error) { message(error.message,true); }
}
function render() {
 const cfg=config[tab]; if(!cfg) return;
 const head=el('tr');cfg.columns.forEach(key=>head.append(el('th',label(key))));head.append(el('th','Actions'));
 $('table-head').replaceChildren(head); $('table-body').replaceChildren();
 const query=$('search').value.toLowerCase();
 const filtered=rows.filter(row=>JSON.stringify(row).toLowerCase().includes(query));
 $('empty').hidden=filtered.length>0; $('empty').textContent=rows.length?'No matching records. Try a different search.':'No records yet. Add your first record to get started.';
 for(const row of filtered) {
  const tr=el('tr');
  for(const key of cfg.columns) {
   let value=row[key]??'—';
   if(key==='updated_at' && typeof value==='number') value=new Date(value*1000).toLocaleDateString();
   if(key==='completed') value=value?'Complete':'Open';
   if(key==='value') value=Number(value).toLocaleString(undefined,{maximumFractionDigits:2});
   if(key==='probability') value=value+'%';
   const td=el('td',String(value).length>150?String(value).slice(0,150)+'…':String(value));tr.append(td);
  }
  const actions=el('td'), edit=el('button','Edit','secondary'), remove=el('button','Delete','delete');
  if(row.url && row.url.startsWith('/api/uploads/')) { const source_link=el('a','Original','secondary'); source_link.href=row.url; source_link.target='_blank'; source_link.rel='noopener'; actions.append(source_link); }
  edit.setAttribute('aria-label','Edit '+(row.name||row.title||row.kind)); remove.setAttribute('aria-label','Delete '+(row.name||row.title||row.kind));
  edit.hidden=Boolean(row.upload_id); edit.onclick=()=>openEditor(row); remove.onclick=async()=>{
   if(!confirm('Delete this record? This cannot be undone.')) return;
   try { const route=row.upload_id?'uploads/'+row.upload_id:tab+'/'+(row.content_id||row.id); await api(route,'DELETE',{}); await navigate(tab); message('Record deleted.'); } catch(error) { message(error.message,true); }
  };
  actions.append(edit,remove);tr.append(actions);$('table-body').append(tr);
 }
}
$('search').oninput=render; $('refresh').onclick=()=>navigate(tab); $('add').onclick=()=>openEditor();
$('knowledge-upload').onsubmit=async event=>{
 event.preventDefault(); const file=$('knowledge-file').files[0], status=$('upload-status'), button=event.submitter; if(!file)return;
 status.textContent='Uploading and indexing…';button.disabled=true;
 try { const form=new FormData();form.append('file',file); const response=await fetch('/api/uploads',{method:'POST',headers:{'X-CSRF-Token':csrf},credentials:'same-origin',body:form}); const result=await response.json(); if(!response.ok)throw new Error(result.error||'Upload failed'); status.textContent=result.indexed?`Uploaded and vector-indexed ${result.original_filename}: ${result.chunk_count} chunks`:`Uploaded ${result.original_filename}: JSON search only. ${result.index_warning||'Vector indexing unavailable.'}`; event.target.reset(); await navigate('rag'); }
 catch(error){status.textContent=error.message;} finally{button.disabled=false;}
};
async function openEditor(row=null) {
 editing=row; const cfg=config[tab]; $('fields').replaceChildren(); $('form-error').textContent='';
 $('editor-title').textContent=(row?'Edit ':'New ')+(tab==='rag'?'knowledge item':tab.slice(0,-1));
 for(const [key,type] of Object.entries(cfg.fields)) {
  const fieldLabel=el('label',label(key)); let input;
  if(type==='contact'||type==='deal') {
   input=el('select'); const empty=el('option','None');empty.value='';input.append(empty);
   try { for(const linked of await api(type==='contact'?'contacts':'deals')) {const option=el('option',linked.name||linked.title);option.value=linked.id;input.append(option);} }
   catch(error) { message(error.message,true); return; }
  } else if(type==='textarea') input=el('textarea');
  else { input=el('input'); input.type=type; }
  input.name=key;input.id='field-'+key;input.required=cfg.required.includes(key);
  if(type==='checkbox') input.checked=Boolean(row?.[key]);
  else input.value=row?.[key] ?? ({currency:'USD',stage:'new',status:'lead',source:'admin',kind:'note',value:0,probability:0}[key]??'');
  if(type==='number') {input.min='0';input.step=key==='value'?'0.01':'1';if(key==='probability') input.max='100';}
  if(['name','title','email','phone','status','stage','currency','kind'].includes(key)) input.maxLength=key==='currency'?3:300;
  fieldLabel.append(input);$('fields').append(fieldLabel);
 }
 $('editor').showModal();
}
$('close').onclick=$('cancel').onclick=()=>$('editor').close();
$('edit-form').onsubmit=async event=>{
 event.preventDefault(); const button=event.submitter;button.disabled=true;
 try {
  const data={};for(const [key,type] of Object.entries(config[tab].fields)) {
   const input=event.target.elements[key];
   data[key]=type==='checkbox'?(input.checked?1:0):['contact','deal'].includes(type)?(input.value?Number(input.value):null):type==='number'?Number(input.value):input.value;
  }
  await api(tab+(editing?'/'+(editing.content_id||editing.id):''),editing?'PUT':'POST',data);
  $('editor').close();await navigate(tab);message('Record saved.');
 } catch(error) { $('form-error').textContent=error.message; } finally {button.disabled=false;}
};

let siteSettings=null, llmSettings=null, settingsPanel='appearance';
const fieldNames={primary_color:'Primary color',launcher_style:'Launcher style',launcher_size:'Launcher size',avatar_url:'Avatar URL',auto_open:'Open automatically',auto_open_delay_seconds:'Auto-open delay (seconds)',track_page_views:'Track page views',exclude_paths:'Excluded paths (one per line)',organization_name:'Organization name',website_name:'Website name',service_area:'Service area',website_url:'Website URL',privacy_url:'Privacy URL',consent_text:'Consent text',submit_label:'Submit button',enabled:'Enabled'};
function settingInput(key,value) {
 const wrap=el('label',fieldNames[key]||label(key)), input=key==='greeting'||key==='consent_text'||key==='description'?el('textarea'):el('input');
 if(typeof value==='boolean'){input.type='checkbox';input.checked=value;} else {input.value=Array.isArray(value)?value.join('\n'):value;input.type=key.includes('url')?'url':key==='email'?'email':key==='primary_color'?'color':key.includes('delay')?'number':'text';}
 input.name=key; wrap.append(input); return wrap;
}
async function loadSettings(){
 [siteSettings,llmSettings]=await Promise.all([api('settings'),api('llm')]); renderSettings();
}
function renderSettings(){
 const root=$('settings-fields');root.replaceChildren();document.querySelectorAll('[data-setting-panel]').forEach(b=>b.classList.toggle('active',b.dataset.settingPanel===settingsPanel));
 if(settingsPanel==='ai'){
  root.append(el('h2','AI Model'),el('p','Provider: OpenAI','muted'));
  const model=settingInput('model',llmSettings.model);model.querySelector('input').setAttribute('list','models');root.append(model);
  const list=el('datalist');list.id='models';llmSettings.model_options.forEach(x=>{const o=el('option');o.value=x;list.append(o);});root.append(list,settingInput('base_url',llmSettings.base_url));
  const key=settingInput('api_key','');key.querySelector('input').type='password';key.querySelector('input').placeholder='Leave blank to keep current';root.append(key);
  root.append(el('p',llmSettings.configured?'API key configured '+llmSettings.masked_key:'No API key configured','notice'));
  const runtime=llmSettings.runtime||{}, llmRuntime=runtime.llm||{}, vectorRuntime=runtime.pgvector||{};
  root.append(el('p',`Runtime: LLM ${llmRuntime.configured?'configured':'not configured'} · model list ${llmSettings.models_status||'cached'} · pgvector ${vectorRuntime.configured?'configured':'not configured'}${vectorRuntime.configured?` · ${vectorRuntime.embedding_model}/${vectorRuntime.embedding_dimension}`:''}`,'muted'));
  const actions=el('div',undefined,'form-actions'),test=el('button','Test connection','secondary'),clear=el('button','Clear API key','delete');test.type=clear.type='button';
  test.onclick=async()=>{try{const r=await api('llm/test','POST',{});llmSettings.model_options=r.model_options||llmSettings.model_options;llmSettings.models_status='live';renderSettings();message(r.message);}catch(e){message(e.message,true);}};
  clear.onclick=async()=>{if(confirm('Clear the saved API key?')){llmSettings=await api('llm','PUT',{model:root.querySelector('[name=model]').value,base_url:root.querySelector('[name=base_url]').value,clear_key:true});renderSettings();message('API key cleared. Restart chatbot to apply.');}};
  actions.append(test,clear);root.append(actions,el('p',llmSettings.restart_required?'Restart chatbot to apply saved AI changes.':'AI settings are active.','muted'));
 } else if(settingsPanel==='lead_form'){
  const value=siteSettings.lead_form; ['enabled','title','description','submit_label'].forEach(k=>root.append(settingInput(k,value[k])));root.append(el('h3','Fields'));
  ['name','email','phone','company','message'].forEach(name=>{const row=el('label',name);const use=el('input');use.type='checkbox';use.name='field_'+name;const found=value.fields.find(f=>f.name===name);use.checked=Boolean(found);const required=el('input');required.type='checkbox';required.name='required_'+name;required.checked=Boolean(found?.required);row.append(use,document.createTextNode(' Include · '),required,document.createTextNode(' Required'));root.append(row);});
 } else Object.entries(siteSettings[settingsPanel]).forEach(([k,v])=>root.append(settingInput(k,v)));
 updatePreview();
}
function updatePreview(){if(!siteSettings)return;const a=siteSettings.appearance;$('preview-title').textContent=a.title;$('preview-greeting').textContent=a.greeting;$('preview-card').style.borderColor=a.primary_color;$('preview-launcher').style.background=a.primary_color;$('preview-launcher').className=a.launcher_style+' '+a.launcher_size;}
document.querySelectorAll('[data-setting-panel]').forEach(b=>b.onclick=()=>{settingsPanel=b.dataset.settingPanel;renderSettings();});
$('settings-fields').addEventListener('input',event=>{if(settingsPanel==='appearance'&&event.target.name){siteSettings.appearance[event.target.name]=event.target.type==='checkbox'?event.target.checked:event.target.value;updatePreview();}});
$('settings-form').onsubmit=async event=>{
 event.preventDefault();$('settings-error').textContent='';
 try {
  const root=$('settings-fields');
  if(settingsPanel==='ai'){llmSettings=await api('llm','PUT',{model:root.querySelector('[name=model]').value,base_url:root.querySelector('[name=base_url]').value,api_key:root.querySelector('[name=api_key]').value});renderSettings();message('AI settings saved. Restart chatbot to apply.');return;}
  if(settingsPanel==='lead_form'){const section=siteSettings.lead_form;['enabled','title','description','submit_label'].forEach(k=>{const n=root.querySelector('[name='+k+']');section[k]=n.type==='checkbox'?n.checked:n.value;});section.fields=['name','email','phone','company','message'].filter(n=>root.querySelector('[name=field_'+n+']').checked).map(n=>({name:n,required:root.querySelector('[name=required_'+n+']').checked}));}
  else root.querySelectorAll('[name]').forEach(n=>{siteSettings[settingsPanel][n.name]=n.type==='checkbox'?n.checked:n.name==='auto_open_delay_seconds'?Number(n.value):n.name==='exclude_paths'?n.value.split('\n').map(x=>x.trim()).filter(Boolean):n.value;});
  siteSettings=await api('settings','PUT',siteSettings);renderSettings();message('Chatbot settings saved. Public widget refreshes on the next page load.');
 } catch(error){$('settings-error').textContent=error.message;}
};
signedIn().catch(()=>showLogin());
