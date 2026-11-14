import type {PlantScene,SceneState} from './scene';
import uPlot from 'uplot';
type Row=Record<string,any>;
type Stage=SceneState&{run_id:string|null};
const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const escape=(v:any)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
$('close-drawer').onclick=()=>$<HTMLDialogElement>('drawer').close();
const route=location.pathname,wall=route==='/wall',mobile=route==='/m',compute=route==='/compute';
let key='',sid=new URLSearchParams(location.search).get('session')||(!wall&&!mobile?localStorage.getItem('p7-inside-session'):null)||'';
let state:Stage={chapter:0,selected_fastener:'B1',cursor:3,cutaway:true,isolate:false,bright:false,paused:false,run_id:null};
let data:Row|null=null,job:Row|null=null,scene:PlantScene|null=null,es:EventSource|null=null,plot:uPlot|null=null,passport:Row|null=null,revision=-1,after=0,saveTimer:number,telemetryTimer:number,refreshTimer:number;
let pendingSubmission:{id:string,body:string}|null=null;
let submitting=false, advancing=false, replayMode=false, mobileInferenceReady=true, persistChain=Promise.resolve(), tokenInputs={input:2,output:8,volume:1000};
let mobileOwnJob=false;let clipMissing=false;const currentScenario=()=>$<HTMLSelectElement>('scenario').value;
const chapters=[['THE LINE','A shift in the signal.','Something changed<br>on Line 3.','Four assembly lines. One change worth investigating.'],['INSIDE THE VEHICLE','Make the joint visible.','Look beneath<br>the surface.','Station 40 · Bracket B7 · Four stable fastener identities.'],['REPLAY THE EVIDENCE','Requirement. Observation.','Follow the<br>evidence.','One time cursor. Separate sources. Explicit uncertainty.'],['SCOPE THE CONTAINMENT','Trace every unit.','From one joint<br>to a cohort.','Inspection scope comes from the same retrieved unit records.'],['THE DECISION','Prepare the next move.','Evidence before<br>action.','A suspected cause, a reviewable response and clear open checks.']];
async function api(path:string,options:RequestInit={}){const r=await fetch(path,{signal:AbortSignal.timeout(15000),...options,headers:{'Content-Type':'application/json',...(key?{'X-Presenter-Key':key}:{}),...options.headers}});if(!r.ok){let m;try{m=(await r.json()).detail}catch{m=r.statusText}throw new Error(typeof m==='string'?m:JSON.stringify(m));}return r.json();}
function toast(t:string){$('toast').textContent=t;$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,6500);}
function drawer(title:string,html:string,label='SOURCE EVIDENCE'){ $('drawer-title').textContent=title;$('drawer-label').textContent=label;$('drawer-content').innerHTML=html;if(!$<HTMLDialogElement>('drawer').open)$<HTMLDialogElement>('drawer').showModal();}
function sourceButton(id:string,text:string){return `<button class="source-link" data-source="${escape(id)}">${text} ↗</button>`;}
function attachSources(){document.querySelectorAll<HTMLButtonElement>('[data-source]').forEach(b=>b.onclick=()=>{const evidence=job?.evidence?.find((e:Row)=>e.source_id===b.dataset.source);const fact=evidence||data?.[b.dataset.source!];if(!fact&&b.dataset.source?.startsWith('docs/')){api('/api/stage/documents').then(d=>drawer(b.textContent||'Requirement',`<pre>${escape(JSON.stringify(d.find((x:Row)=>x.id===b.dataset.source),null,2))}</pre>`)).catch(e=>toast(String(e)));return;}drawer(b.textContent||'Evidence',`<pre>${escape(JSON.stringify(fact??'Run the local investigation to retrieve this source.',null,2))}</pre>`);});}
function shiftRows(){return data?.shifts.filter((r:Row)=>r.line===3)||[];}
function renderPanel(){
 if(mobile){$('chapter-label').textContent='MOBILE EVIDENCE · INDEPENDENT QUESTIONS';$('panel-title').textContent=mobileOwnJob?'Your local investigation.':'Follow the investigation.';$('panel').innerHTML=`<p class="note">Read only stage evidence. Your questions do not change the presenter’s session.</p>${job?.answer?`<p>${escape(job.answer.leading_explanation)}</p>`:'<p>The presenter has not completed an investigation yet.</p>'}<div class="metrics-inline"><div><strong>${data?.cohort.length??'—'}</strong><small>Units in inspection cohort</small></div><div><strong>${data?.exception_count??'—'}</strong><small>Recorded angle exceptions</small></div></div>${sourceButton('MES-TOOL-TRENDS','Tool evidence')}${sourceButton('MAINTENANCE-L3','Recorded maintenance')}${sourceButton('docs/work_instructions/WI-L3-S40.md','Assembly requirement')}<button class="source-link" id="mobile-passport">Open the example unit passport ↗</button><p class="pending">Visual sequence unvalidated. No physical action or Quality release is applied.</p>`;attachSources();$('mobile-passport').onclick=()=>openUnit('P7-20261110-32-0021');return;}
 const chapter=state.chapter;const [label,title]=chapters[chapter];$('chapter-label').textContent=`0${chapter+1} / ${label}`;$('panel-title').textContent=title;
 const rows=shiftRows(),change=rows.length?rows[1].fpy_pct-rows[0].fpy_pct:null;
 let html='';
 if(chapter===0)html=`<div class="stat"><strong>${change===null?'…':change>0?'+'+change:change}</strong><span>percentage points<small>First pass yield · Line 3</small></span></div><div class="small-chart">${rows.map((r:Row)=>`<div><i style="height:${(r.fpy_pct-85)*4}px;${r.shift===2?'background:#004bdf':''}"></i><b>${r.fpy_pct}%</b><span>Shift ${r.shift}</span></div>`).join('')}</div><p>10 November 2026<br>Shift 2 · 14:00 to 22:00 UTC</p><p>Enter Station 40. Open the assembly. Ask the local investigation to test what changed.</p>${sourceButton('shifts','Inspect the yield query')}<p class="note">Measured values in this story come from a fictional plant dataset. Findings appear only after completed tools or a selected captured replay.</p>`;
 if(chapter===1)html=`<div class="eyebrow">ILLUSTRATIVE COMPONENT B7</div><p>A fixture bracket beneath the SUV body. Four fasteners connect the physical view to individual tool records.</p><div class="label-row"><span>Selected fastener</span><b>${state.selected_fastener}</b></div><div class="label-row"><span>Requirement</span><b>40 Nm · 38 to 42 Nm</b></div><div class="label-row"><span>Recorded angle limits</span><b>78° to 102°</b></div><button class="source-link" id="open-fastener">Open ${state.selected_fastener} readings ↗</button>${sourceButton('docs/work_instructions/WI-L3-S40.md','Read the assembly requirement')}<p class="note">This fictional component specifically requires 1 → 3 → 2 → 4. It is not a universal automotive fastening rule.</p><p>Drag to orbit. Use cutaway to reveal the joint, or isolate the bracket for inspection.</p>`;
 if(chapter===2)html=`<div class="eyebrow">REQUIRED · WI REVISION C, STEP 6</div><div class="sequence"><b>1</b>→<b>3</b>→<b>2</b>→<b>4</b></div><p>The instruction establishes the requirement. Tool records establish measured values. Video can support visible contact order.</p><div class="pending">${clipMissing?'Source gap: clip missing.':job?.video?.observation?'Model hypothesis: '+escape(job.video.observation):'Observed sequence: unverified. The local vision model is unavailable or has not completed a pixel evaluation.'}</div><p class="note">The visible tool motion is a manually authored synthetic animation. It is not a model detection or a camera recording.</p><div class="label-row"><span>Selected unit</span><b>…32 0021</b></div><button class="source-link" id="open-fastener">Inspect aligned tool record ↗</button>${sourceButton('S40-SYNTHETIC-VIDEO','Inspect video availability')}`;
 if(chapter===3){const n=data?.cohort.length??0,ex=data?.exception_count??0;html=`<div class="metrics-inline"><div><strong>${n}</strong><small>Needs inspection</small></div><div><strong>${ex}</strong><small>Recorded angle exceptions</small></div></div><p>${escape(data?.scope||'Retrieving unit genealogy…')}</p><p class="note">Recorded nonconformance means a stored tool result exceeds its limit. Actual joint condition remains insufficiently evidenced for every unit.</p><div class="legend"><span><i></i>Review</span><span><i class="amber"></i>Angle exception</span><span><i class="blue"></i>Simulated hold</span></div><button class="primary" id="prepare" style="width:100%" ${job?.status==='completed'?'':'disabled'}>Prepare containment ↗</button><p class="muted">Completed local result required. Draft first, then explicit simulation confirmation. Shipped units enter a simulated review state only.</p>${sourceButton('MES-COHORT','Inspect the exact cohort query')}`;}
 if(chapter===4){html=job?.answer?`<div class="eyebrow">D4 · SUSPECTED CAUSE</div><p class="decision-text">${escape(job.answer.leading_explanation)}</p><button class="source-link" id="decision-detail">Evidence, alternatives and open checks ↗</button><div class="pending">D6 onward pending. No permanent correction or effectiveness verification has been completed by this demo.</div><a class="link-button" href="/api/stage/jobs/${job.run_id}/export/brief" download>Evidence brief ↓</a><a class="link-button" href="/api/stage/jobs/${job.run_id}/export/8d" download>8D draft ↓</a><button class="source-link" id="scenario-arithmetic">Test a scenario ↗</button>`:`<p>Run the local investigation to assemble an evidence backed explanation and inspection scope.</p><div class="pending">No cause, corrective action or effectiveness claim is accepted while the evidence is incomplete.</div>`;}
 $('panel').innerHTML=html;attachSources();
 $('open-fastener')?.addEventListener('click',()=>openFastener(state.selected_fastener));$('prepare')?.addEventListener('click',prepareHold);$('decision-detail')?.addEventListener('click',()=>{const a=job!.answer;drawer('A decision with open checks',`<p class="decision-text">${escape(a.leading_explanation)}</p><h3>Supporting evidence</h3>${a.supporting_evidence.map((id:string)=>sourceButton(id,escape(id))).join('')}<h3>Alternative explanations</h3><ul>${a.alternatives.map((x:string)=>`<li>${escape(x)}</li>`).join('')}</ul><p class="note">The separate Line 2 conveyor record is also available for inspection. Its recorded drive scope does not establish a Line 3 cause.</p>${sourceButton('CONVEYOR-CONTROL','Inspect the conveyor alternative')}<h3>Uncertainties</h3><ul>${a.uncertainties.map((x:string)=>`<li>${escape(x)}</li>`).join('')}</ul><h3>Verification steps</h3><ul>${a.verification_steps.map((x:string)=>`<li>${escape(x)}</li>`).join('')}</ul><p class="pending">D4 remains suspected. Permanent correction and effectiveness verification remain pending.</p>`,'MODEL HYPOTHESIS · SOURCE REVIEW REQUIRED');attachSources();});$('scenario-arithmetic')?.addEventListener('click',scenarioArithmetic);
}
function renderGenealogy(){
 if(!data)return;const counts=data.counts;const holds=(window as any).p7holds||{};
 $('genealogy').innerHTML=['work_in_progress','finished_goods','shipped'].map(group=>`<div class="gene-group"><h3>${({work_in_progress:'Work in progress',finished_goods:'Finished goods',shipped:'Shipped'} as Row)[group]} <span>${counts[group]||0}</span></h3><div class="unit-grid">${data!.cohort.filter((r:Row)=>r.lifecycle===group).map((r:Row)=>`<button aria-label="Inspect ${r.unit_id}" title="${r.unit_id} · ${r.assessment}" class="${r.outside_limit_bolts?'exception':''} ${holds[r.unit_id]?'hold':''}" data-unit="${r.unit_id}"></button>`).join('')||'<p class="muted">No units in this group.</p>'}</div></div>`).join('');
 document.querySelectorAll<HTMLButtonElement>('[data-unit]').forEach(b=>b.onclick=()=>openUnit(b.dataset.unit!));
}
async function openUnit(id:string){try{const p=await api(`/api/stage/unit/${id}?scenario=${currentScenario()}`);drawer(id,`<p>Tool ${escape(p.torque[0]?.tool_id)} · ${escape(p.unit.supplier_lot)} · ${escape(p.unit.status)}</p><p class="note">Synthetic station history. Shipping status is not a Quality release or a confirmed joint condition.</p><h3>Fastener records</h3><div class="table-wrap"><table><tr><th>ID</th><th>UTC timestamp</th><th>Nm</th><th>Angle</th></tr>${p.torque.map((r:Row)=>`<tr><td>B${r.bolt}</td><td>${escape(r.timestamp)}</td><td>${r.actual_nm}</td><td>${r.angle_deg}°</td></tr>`).join('')}</table></div><h3>Station history</h3><pre>${escape(JSON.stringify(p.history,null,2))}</pre><h3>Recorded defects</h3><pre>${escape(JSON.stringify(p.defects,null,2))}</pre>`,'UNIT PASSPORT · READ ONLY SYNTHETIC MES');}catch(e){toast(String(e))}}
async function openFastener(id:string){try{const v=await api(`/api/stage/component/${id}?scenario=${currentScenario()}`);drawer(`${id} · its actual source record`,`<pre>${escape(JSON.stringify(v,null,2))}</pre>`);}catch(e){toast(String(e))}}
async function loadData(){data=await api('/api/stage/data?scenario='+currentScenario());passport=await api('/api/stage/unit/P7-20261110-32-0021?scenario='+currentScenario());renderPanel();renderGenealogy();renderPlot();}
function renderPlot(){if(!passport||state.chapter!==2)return;plot?.destroy();const parent=$('plot'),width=parent.clientWidth;if(width<100)return;const base=Date.parse('2026-11-10T14:42:38Z')/1000;const x=passport.torque.map((r:Row)=>Date.parse(r.timestamp+'Z')/1000-base);const values=passport.torque.map((r:Row)=>r.angle_deg);const torque=passport.torque.map((r:Row)=>r.actual_nm);plot=new uPlot({width,height:parent.clientHeight||100,padding:[10,10,0,0],cursor:{show:true,drag:{x:false,y:false}},legend:{show:false},scales:{x:{time:false,min:0,max:10},y:{min:75,max:115},nm:{min:37,max:43}},axes:[{show:false},{size:32,font:'9px Arial',stroke:'#718397',grid:{stroke:'#e5ebf3'},values:(_u,vals)=>vals.map(v=>v+'°')},{scale:'nm',side:1,size:27,font:'9px Arial',stroke:'#596d7b',grid:{show:false},values:(_u,vals)=>vals.map(v=>String(v))}],series:[{}, {stroke:'#004bdf',width:2,points:{size:5}},{scale:'nm',stroke:'#647888',width:1.5,points:{size:4}}]},[x,values,torque],parent);syncCursor();}
function syncCursor(){const t=state.cursor;scene?.setTime(t);$<HTMLInputElement>('cursor').value=t.toFixed(2);$('cursor-label').textContent=new Date(Date.parse('2026-11-10T14:42:38Z')+t*1000).toISOString().slice(11,19)+' UTC';if(plot)plot.setCursor({left:plot.valToPos(t,'x'),top:plot.valToPos(102,'y')});
 const clip=$<HTMLVideoElement>('clip');if(!clipMissing&&Number.isFinite(clip.duration)&&Math.abs(clip.currentTime-t)>.15)clip.currentTime=Math.min(t,clip.duration);
 const record=passport?.torque.find((r:Row)=>Math.abs(Date.parse(r.timestamp+'Z')-(Date.parse('2026-11-10T14:42:38Z')+t*1000))<510);
 $('alignment').textContent=record?`B${record.bolt} · ${record.actual_nm} Nm · ${record.angle_deg}° · recorded source sample ±0.5s. Synthetic authored alignment, not validated camera synchronization.`:'Source gap: no tool measurement at this cursor. No interpolation or clamp force inferred.';
}
function render(){
 if(compute)return;document.body.dataset.currentChapter=String(state.chapter);const c=chapters[state.chapter];$('title').innerHTML=c[2];$('subtitle').textContent=c[3];$('breadcrumb').textContent=state.chapter===0?'PLANT 7 / GENERAL ASSEMBLY':`PLANT 7 / LINE 3 / STATION 40 / ${state.isolate?'BRACKET B7':'SUV ASSEMBLY'}`;
 if(state.chapter!==2)$<HTMLVideoElement>('clip').pause();$('timeline').hidden=state.chapter!==2;$('genealogy').hidden=state.chapter!==3;document.body.classList.toggle('dark-scene',state.chapter>0&&!state.bright);
 $('scene-label').textContent=state.chapter===0?'LINE 3 · STATION 40':`B7 · ${state.selected_fastener} · READ ONLY EVIDENCE`;

 document.querySelectorAll<HTMLButtonElement>('[data-chapter]').forEach(b=>{const active=Number(b.dataset.chapter)===state.chapter;b.classList.toggle('active',active);b.setAttribute('aria-current',String(active));});
 $<HTMLButtonElement>('back').disabled=state.chapter===0||advancing;
 scene?.update(state);renderValue();renderPanel();renderGenealogy();if(state.chapter===2)setTimeout(renderPlot,50);updateRunStatus();
}
function change(patch:Partial<Stage>){if(wall||mobile)return;state={...state,...patch};render();save(true);}
function save(immediate=false){
 clearTimeout(saveTimer);
 const persist=()=>{if(!sid||!key)return;const snapshot=JSON.stringify(state),session=sid;
  persistChain=persistChain.catch(()=>{}).then(async()=>{await api('/api/stage/sessions/'+session,{method:'PATCH',body:snapshot,keepalive:true})}).catch(e=>toast('Your step could not be saved. '+String(e)));
 };
 if(immediate)persist();else saveTimer=window.setTimeout(persist,200);
}
function updateRunStatus(){
 const busy=submitting||!!job&&['running','queued'].includes(job.status);
 $<HTMLButtonElement>('investigate').disabled=busy||(!key&&!mobile)||(mobile&&!mobileInferenceReady);
 $('replay').hidden=mobile||wall||!['failed','canceled'].includes(job?.status);
 const replay=job?.mode==='captured_replay';$('mode').className='badge '+(replay?'replay':job?'live':'');
 $('mode').textContent=replay?'RECORDED WALKTHROUGH · NO LIVE INFERENCE':job?'LIVE LOCAL · SYNTHETIC DATA':replayMode?'RECORDED WALKTHROUGH AVAILABLE':'SYNTHETIC PLANT · LIVE LOCAL AI';
 if(job){
  const failure=job.events?.filter((e:Row)=>e.type==='error').at(-1)?.label;
  $('run-status').textContent=['failed','canceled'].includes(job.status)?`Investigation ${job.status}. ${failure||'You can retry or choose the labelled recorded walkthrough.'}`:
   `${replay?'Recorded run · ':''}${job.status==='completed'?'Evidence ready':job.status==='queued'?'Waiting for a local model slot':'Investigating locally…'}${job.first_evidence_s!=null?` · first evidence ${job.first_evidence_s.toFixed(2)}s`:''}${job.completion_s!=null?` · ${job.completion_s.toFixed(2)}s total`:''} · Vision unavailable`;
 }
 const labels=['Enter Station 40 →','Follow the evidence →','Trace affected units →','See the decision & value →','Start again →'];
 let label=labels[state.chapter],hint=['The local investigation starts as you enter.','The clip and tool records play together.','One query defines every unit in scope.','A reviewable decision and the measured local workload.','A fresh walkthrough, ready for the next audience.'][state.chapter];
 if(state.chapter===0&&replayMode){label='Start recorded walkthrough →';hint='Recorded telemetry/document result. No live inference will run.';}
 if(state.chapter>=2&&state.chapter<=3&&job?.status!=='completed'){
  if(busy){label='Investigating locally…';hint='Evidence is arriving. This step continues when the checks finish.';}
  else {label=job?'Retry local investigation →':'Run the investigation →';hint='A completed result is required before showing a decision.';}
 }
 $<HTMLButtonElement>('back').disabled=state.chapter===0||advancing;
 const button=$<HTMLButtonElement>('next');button.textContent=label;button.setAttribute('aria-label',label);button.disabled=advancing||submitting||((state.chapter===2||state.chapter===3)&&busy);$('next-hint').textContent=hint;
}
async function startJob(replay=false){
 if(submitting||job&&['running','queued'].includes(job.status))return false;
 submitting=true;updateRunStatus();
 try{
  if(mobile)mobileOwnJob=true;if(!sid)throw new Error('The demo session is reconnecting. Please reload.');
  const q=$<HTMLTextAreaElement>('mobile-question')?.value;
  const body={scenario:currentScenario(),question:q||'Investigate the Line 3 Station 40 shift change. Compare tools, maintenance, supplier lots and conveyor alternatives, and propose inspection scope.',replay};
  const signature=JSON.stringify(body);if(pendingSubmission?.body!==signature)pendingSubmission={id:Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join(''),body:signature};
  const r=await api(`/api/stage/sessions/${sid}/jobs`,{method:'POST',body:JSON.stringify({...body,request_id:pendingSubmission!.id})});pendingSubmission=null;
  es?.close();after=0;job={...r,events:[],evidence:[]};updateRunStatus();$('activity').replaceChildren();
  if(!mobile){state.run_id=r.run_id;save(true);}
  if(r.status==='completed')await refreshJob(r.run_id);else connectEvents(r.run_id);
  return true;
 }catch(e){toast(String(e));$('run-status').textContent='Unable to start. '+String(e);return false;}
 finally{submitting=false;updateRunStatus();}
}
async function refreshJob(rid:string){
 const value=await api('/api/stage/jobs/'+rid);
 if(job?.run_id!==rid)return;
 job=value;if(value.data)data=value.data;
 if(!['queued','running'].includes(value.status))es?.close();
 renderPanel();renderGenealogy();renderValue();updateRunStatus();
}
function connectEvents(rid:string){
 es?.close();const source=new EventSource(`/api/stage/jobs/${rid}/events?after=${after}`);es=source;
 source.onmessage=m=>{try{
  if(job?.run_id!==rid){source.close();return;}const e=JSON.parse(m.data);if(e.id<=after)return;after=e.id;
  job.status=e.status||job.status;if(e.type==='query_started')job.status='running';
  job.events.push(e);if(e.type==='evidence'&&!job.evidence.some((x:Row)=>x.source_id===e.evidence.source_id))job.evidence.push(e.evidence);
  if(e.label){const line=document.createElement('div');line.textContent=e.label;$('activity').prepend(line);while($('activity').childElementCount>8)$('activity').lastElementChild?.remove();}
  if(e.type==='done'){source.close();void refreshJob(rid).catch(e=>toast('Reconnecting to the saved result. '+String(e)));}
  updateRunStatus();
 }catch(e){source.close();toast('Reconnecting to saved evidence.');}};
 source.onerror=()=>{void refreshJob(rid).catch(()=>{$('run-status').textContent='Connection interrupted. Saved evidence will resume when the connection returns.';});};
}
async function restartStory(){
 es?.close();clearTimeout(saveTimer);await persistChain;
 if(job&&['queued','running'].includes(job.status))await api('/api/stage/jobs/'+job.run_id,{method:'DELETE'});
 const s=await api(`/api/stage/sessions/${sid}/reset`,{method:'POST',body:'{}'});state=s.stage;job=null;after=0;(window as any).p7holds={};$('activity').replaceChildren();
 $<HTMLSelectElement>('scenario').value='hero';await loadData();render();$('run-status').textContent=replayMode?'Recorded walkthrough ready. No live inference.':'Ready. The local investigation starts as you enter Station 40.';
}
async function advance(){
 if(advancing||wall||mobile||$<HTMLDialogElement>('drawer').open)return;advancing=true;updateRunStatus();
 try{
  if(state.chapter===4){await restartStory();return;}
  if(state.chapter===0){if(!job&&!(await startJob(replayMode)))return;change({chapter:1,cutaway:true,isolate:false,selected_fastener:'B1'});}
  else if(state.chapter===1){change({chapter:2,cursor:3});const clip=$<HTMLVideoElement>('clip');clip.currentTime=3;if(!clipMissing)void clip.play().catch(()=>{});}
  else if(job?.status==='completed')change({chapter:state.chapter+1});
  else if(!job||['failed','canceled'].includes(job.status))await startJob(replayMode);
 }catch(e){toast('Please retry this step. '+String(e));}
 finally{advancing=false;updateRunStatus();}
}
function renderValue(){
 const el=$('token-value');el.hidden=state.chapter!==4||!job?.answer||mobile;
 if(el.hidden)return;
 const usage=job?.token_economics,prompt=usage?.prompt_tokens,output=usage?.completion_tokens,known=usage?.usage_complete;
 const number=(n:number|null|undefined)=>n==null?'—':n.toLocaleString('en-GB');
 const basis=job?.mode==='captured_replay'?'RECORDED RUN · NO LIVE TOKENS GENERATED':'THIS INVESTIGATION · SERVER-REPORTED TOKENS';
 el.innerHTML=`<div class="eyebrow">THE VALUE OF KEEPING AI LOCAL</div><h2>One Fury.<br>The investigation stays local.</h2><p class="value-basis">${basis}</p><div class="token-metrics"><div><strong>${number(prompt)}</strong><span>input tokens processed</span></div><div><strong>${number(output)}</strong><span>tokens generated</span></div><div><strong>${job?.completion_s?.toFixed(2)??'—'}s</strong><span>${job?.mode==='captured_replay'?'recorded':'measured'} investigation</span></div></div><div class="value-chain"><span>SQL worker</span><i>→</i><span>Evidence synthesis</span><i>→</i><span>Second audit</span></div><p class="value-scope">${known?'Actual generation-call usage.':'Token usage incomplete; no cost extrapolation available.'} Embedding and reranking tokens excluded. Repeated context is counted on each call.</p><div class="cost-model"><div class="flex"><b>What would metered API use cost?</b><span>Illustrative assumptions · USD</span></div><div class="cost-inputs"><label>Input / 1M tokens $<input id="price-input" type="number" min="0" max="10000" step="0.1" value="${tokenInputs.input}"></label><label>Output / 1M tokens $<input id="price-output" type="number" min="0" max="10000" step="0.1" value="${tokenInputs.output}"></label><label>Investigations<input id="price-volume" type="number" min="1" max="1000000" step="1" value="${tokenInputs.volume}"></label></div><div class="cost-result"><strong id="cloud-equivalent">—</strong><span>illustrative token charge<br><small>No model API token bill for the local run.</small></span></div><p>Editable arithmetic, not a provider quote or a savings claim. Hardware, electricity, operations and model equivalence are excluded. Remote viewers receive evidence.</p></div>`;
 const calculate=()=>{
  const a=$<HTMLInputElement>('price-input'),b=$<HTMLInputElement>('price-output'),v=$<HTMLInputElement>('price-volume');
  const valid=[a,b,v].every(x=>x.value!==''&&x.checkValidity()&&Number.isFinite(x.valueAsNumber));
  if(valid)tokenInputs={input:a.valueAsNumber,output:b.valueAsNumber,volume:v.valueAsNumber};
  $('cloud-equivalent').textContent=valid&&known?'$'+((prompt*tokenInputs.input+output*tokenInputs.output)*tokenInputs.volume/1e6).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
 };
 for(const id of ['price-input','price-output','price-volume'])$(id).oninput=calculate;calculate();
}
async function prepareHold(){if(!job)return;try{const draft=await api(`/api/stage/sessions/${sid}/containment`,{method:'POST',body:JSON.stringify({run_id:job.run_id})});drawer('Review the containment draft',`<div class="pending">SIMULATION ONLY · No MES, shipment, robot or PLC write</div><p>${draft.unit_ids.length} units will enter simulated hold in this demo session.</p><p>${escape(draft.reason)}</p><div class="hold-list">${draft.unit_ids.map(escape).join('<br>')}</div><label for="approver">Demo approver</label><input id="approver" placeholder="Presenter or Quality reviewer name" maxlength="80"><p>Physical condition, Quality disposition and vision sequence validation remain unresolved. The underlying MES is read only.</p><button class="primary" id="confirm-hold">Confirm simulation · apply demo hold</button>`,'DRAFT CONTAINMENT · HUMAN REVIEW');$('confirm-hold').onclick=async()=>{const name=$<HTMLInputElement>('approver').value.trim();if(name.length<2){toast('Enter the demo approver name.');return;}try{await api(`/api/stage/sessions/${sid}/confirm`,{method:'POST',body:JSON.stringify({draft_id:draft.draft_id,approved_by:name,confirmation:'SIMULATE HOLD'})});const s=await api('/api/stage/sessions/'+sid);(window as any).p7holds=s.holds;renderGenealogy();drawer('Simulated hold applied',`<div class="pending">DEMO STATE ONLY</div><p>${draft.unit_ids.length} units · approved within this session by ${escape(name)}.</p><p>${escape(draft.reason)}</p><h3>Unresolved</h3><p>Actual unit condition. Quality disposition and release. Vision sequence validation.</p><div class="hold-list">${draft.unit_ids.map(escape).join('<br>')}</div>`,'TRACEABLE DEMO APPROVAL');}catch(e){toast(String(e))}};}catch(e){toast(String(e))}}
function scenarioArithmetic(){drawer('Compare an illustrative inspection choice',`<p>Scenario arithmetic. Editable assumptions, not a physical simulation or measured outcome.</p><label>Units to inspect<input id="calc-n" type="number" min="0" value="${data?.cohort.length||0}"></label><label>Minutes per unit<input id="calc-min" type="number" min="0" value="4"></label><label>Inspectors<input id="calc-people" type="number" min="1" value="2"></label><div class="stat"><strong id="calc-output"></strong><span>illustrative hours</span></div><p>Units × minutes ÷ inspectors ÷ 60. Excludes logistics, rework and approvals. No yield recovery is predicted.</p>`,'SCENARIO ARITHMETIC');const calc=()=>{$('calc-output').textContent=(Number($<HTMLInputElement>('calc-n').value)*Number($<HTMLInputElement>('calc-min').value)/Math.max(1,Number($<HTMLInputElement>('calc-people').value))/60).toFixed(1)};for(const id of ['calc-n','calc-min','calc-people'])$(id).oninput=calc;calc();}
function fallback(){$('scene').classList.add('webgl-fallback');const el=$('fallback');el.hidden=false;el.innerHTML=`<svg viewBox="0 0 900 600" role="img" aria-label="Fallback SUV cutaway illustration"><path d="M130 380L150 240 290 220 370 125 620 125 735 245 790 280 800 380Z" fill="#92acc5" stroke="#425e77" stroke-width="6"/><path d="M305 225L383 145H600L690 225Z" fill="#d9e6f1"/><g fill="#25394b"><circle cx="270" cy="378" r="65"/><circle cx="650" cy="378" r="65"/></g><rect x="400" y="275" width="180" height="100" rx="8" fill="#497da6" stroke="#d2e0ee" stroke-width="7"/></svg><div style="position:absolute;left:43%;top:35%">${[1,2,3,4].map(i=>`<button data-bolt="B${i}">B${i}</button>`).join('')}</div>`;el.querySelectorAll<HTMLButtonElement>('[data-bolt]').forEach(b=>b.onclick=()=>{change({selected_fastener:b.dataset.bolt!});openFastener(b.dataset.bolt!)});$('footer-status').textContent='WebGL unavailable · functional 2D source inspection';}
async function computeView(){document.body.classList.add('compute-layout');$('panel-title').textContent='Observed local compute';$('chapter-label').textContent='HP ZGX FURY · MEASURED APPLICATION STATE';const t=await api('/api/telemetry'),s=await api('/api/stage/status');$('panel').innerHTML=`<div class="compute-grid"><div class="compute-card"><h3>Device memory</h3><strong>${t.gpu.used_gb?.toFixed(1)??'Unknown'} GB</strong><p>Observed device use · ${t.gpu.total_gb?.toFixed(1)} GB reported capacity. Includes cache and other allocations.</p></div><div class="compute-card"><h3>Application queue</h3><strong>${s.jobs.filter((j:Row)=>j.status==='running').length} running</strong><p>${s.jobs.filter((j:Row)=>j.status==='queued').length} queued · ${s.concurrency_limit} investigation workers · ${s.queue_capacity} request capacity</p></div><div class="compute-card"><h3>Generated token rate</h3><strong>${t.total_tokens_per_second?.toFixed(1)??'Unknown'}</strong><p>Observed server generation tokens per second. Replay does not call models or increment this counter.</p></div></div><div class="compute-card"><h3>Local endpoint destinations</h3>${t.models.map((m:Row)=>`<div class="label-row"><span>${escape(m.role)} · ${escape(m.model)}</span><b>${m.healthy?'Healthy':'Unavailable'} · 127.0.0.1:${m.port}</b></div>`).join('')}<p>No new model downloads or serving configuration changes were required for the visual upgrade.</p></div><div class="compute-card"><h3>Measured requests and queue states</h3><pre>${escape(JSON.stringify(s.jobs,null,2))}</pre><div class="flex">${[1,8,20].map(n=>`<button data-load="${n}">Submit ${n} varied real requests</button>`).join('')}</div><p>Submitted requests are not simultaneous decodes. Bounded queue concurrency is two investigations. Completion and failure states remain separate.</p></div><div class="compute-card"><h3>Local request audit</h3><pre>${escape(JSON.stringify(s.external_audit,null,2))}</pre><p>Only the tested application and browser scope is described. NIC byte counts cannot establish privacy. Browser rendering occurs on the viewer device. Z Runtime, FOX, OpenShift and Omniverse are not integrated.</p></div>`;
 document.querySelectorAll<HTMLButtonElement>('[data-load]').forEach(b=>b.onclick=async()=>{if(!key||!sid){toast('Start a local presenter session first.');return;}const qs=['Compare shift yield on Line 3','Compare angle results by tool','Review recorded maintenance evidence','Inspect supplier lot controls','Compare conveyor alternatives'];let submitted=0;for(let i=0;i<Number(b.dataset.load);i++){try{await api(`/api/stage/sessions/${sid}/jobs`,{method:'POST',body:JSON.stringify({question:qs[i%qs.length],scenario:'hero'})});submitted++;}catch(e){toast(String(e));break;}}toast(`${submitted} real requests submitted. Inspect actual running, queued and outcome states.`);});}
async function pollStage(){
 if(!sid)return;
 try{
  if(!wall&&!mobile){if(job&&['queued','running'].includes(job.status))await refreshJob(job.run_id);return;}
  const value=await api('/api/stage/sessions/'+sid);
  const changed=value.revision!==revision;revision=value.revision;(window as any).p7holds=value.holds;state=value.stage;
  if(state.run_id&&(!mobile||!mobileOwnJob)&&(state.run_id!==job?.run_id||['queued','running'].includes(job?.status))){job=await api('/api/stage/jobs/'+state.run_id);if(job?.data)data=job.data;}
  else if(!state.run_id&&(!mobile||!mobileOwnJob))job=null;
  if(changed||job?.status==='completed'){if(mobile)renderPanel();else render();}
 }catch{$('run-status').textContent='Reconnecting. Your saved investigation is preserved.';}
}
async function init(){
 if(mobile)document.body.classList.add('mobile-layout');if(wall)document.body.classList.add('wall-layout');
 if(!mobile&&!wall){
  key=sessionStorage.getItem('p7-demo-key')||'';sid=sessionStorage.getItem('p7-demo-session')||'';
  let restored=false;
  if(sid&&key){try{const saved=await api('/api/stage/sessions/'+sid);await api('/api/stage/sessions/'+sid,{method:'PATCH',body:JSON.stringify(saved.stage)});state=saved.stage;(window as any).p7holds=saved.holds;restored=true;}catch{key='';sid='';}}
  if(!restored){const fresh=await api('/api/stage/demo-session',{method:'POST',body:'{}'});sid=fresh.session_id;key=fresh.session_key;state=fresh.stage;sessionStorage.setItem('p7-demo-key',key);sessionStorage.setItem('p7-demo-session',sid);}
 }
 if(!sid&&(wall||mobile)){const active=await api('/api/stage/current');sid=active.session_id||'';}
 if(sid&&(wall||mobile)){try{const saved=await api('/api/stage/sessions/'+sid);state=saved.stage;(window as any).p7holds=saved.holds;}catch{sid='';}}
 if(state.run_id){try{job=await api('/api/stage/jobs/'+state.run_id);if(job?.status==='queued'||job?.status==='running'){after=job.events?.at(-1)?.id||0;if(!wall&&!mobile)connectEvents(state.run_id);}}catch{state.run_id=null;}}
 if(compute){await computeView();setInterval(()=>computeView().catch(()=>{}),4000);return;}
 if(mobile){$('panel').insertAdjacentHTML('afterend','<label for="mobile-question">Your question for the local model</label><textarea class="inline-question" id="mobile-question">What does the Station 40 evidence show?</textarea>');$('investigate').hidden=false;}
 if(job?.scenario)$<HTMLSelectElement>('scenario').value=job.scenario;
 await loadData();if(job?.data)data=job.data;
 if(!mobile){try{const {PlantScene}=await import('./scene');scene=new PlantScene($('scene'),id=>{if(wall)return;if(id==='L3-S40'){if(state.chapter===0)void advance();}else{change({selected_fastener:id});void openFastener(id);}},state);scene.renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fallback();});}catch{fallback();}}
 try{const health=await api('/api/health');mobileInferenceReady=health.telemetry_investigation_ready;if(mobile&&!mobileInferenceReady){$('investigate').textContent='Live questions unavailable on this installation';$<HTMLTextAreaElement>('mobile-question').disabled=true;}replayMode=new URLSearchParams(location.search).get('walkthrough')==='recorded'||(!health.telemetry_investigation_ready&&health.captured_local_replay);if(!job)$('run-status').textContent=replayMode?'Models are not ready. Start a clearly labelled recorded walkthrough.':'Ready. Enter Station 40 to start the local investigation.';}catch{$('run-status').textContent='Readiness check unavailable. Retry the first step when connected.';}
 render();setInterval(()=>void pollStage(),2000);
 $('next').onclick=()=>void advance();$('back').onclick=()=>{if(!advancing)change({chapter:Math.max(0,state.chapter-1)});};
 $('investigate').onclick=()=>void startJob();$('replay').onclick=async()=>{if(await startJob(true)){replayMode=true;render();}};
 $('reset').onclick=()=>void restartStory().catch(e=>toast(String(e)));
 $('play-clip').onclick=()=>{const clip=$<HTMLVideoElement>('clip');if(clipMissing){toast('No compatible clip is available.');return;}if(clip.paused){if(clip.currentTime>=clip.duration-.1)clip.currentTime=0;void clip.play().catch(e=>toast(String(e)));}else clip.pause();};
 const clip=$<HTMLVideoElement>('clip');clip.onplay=()=>{$('play-clip').textContent='Pause evidence Ⅱ';};clip.onpause=()=>{$('play-clip').textContent='Play evidence ▷';};
 clip.ontimeupdate=()=>{if(!clip.paused){state.cursor=clip.currentTime;syncCursor();save();}};
 clip.onended=()=>{state.cursor=3;syncCursor();save();};
 $<HTMLInputElement>('cursor').oninput=e=>{clip.pause();state.cursor=Number((e.target as HTMLInputElement).value);syncCursor();save();};
 clip.onerror=()=>{clipMissing=true;$('alignment').textContent='Source gap: synthetic clip not available. Tool records remain inspectable.';};
 $('why').onclick=()=>drawer('The workload behind the walkthrough',`<p>Fury runs the SQL worker, evidence synthesis, a second audit, embedding and reranking locally. The browser draws the factory.</p><p>At the final step, inspect the generation tokens actually reported for this investigation and change the illustrative API rates and volume. This is a workload comparison, not total ownership cost.</p><p>Vision remains unavailable; the clip is synthetic. A recorded walkthrough is labelled throughout and never calls a model.</p><a class="link-button" href="/compute" target="_blank" rel="noopener">Inspect measured compute ↗</a><a class="link-button" href="/wall?session=${sid}" target="_blank" rel="noopener">Open a following display ↗</a><a class="link-button" href="/m?session=${sid}" target="_blank" rel="noopener">Open mobile evidence ↗</a>`,'LOCAL AI · MEASURED WORKLOAD');
 document.addEventListener('keydown',e=>{if(wall||mobile||e.repeat||['INPUT','TEXTAREA','SELECT'].includes((e.target as HTMLElement).tagName)||$<HTMLDialogElement>('drawer').open)return;if(e.key==='ArrowRight'||(e.key===' '&&!['BUTTON','A'].includes((e.target as HTMLElement).tagName))){e.preventDefault();void advance();}if(e.key==='ArrowLeft')change({chapter:Math.max(0,state.chapter-1)});});
 window.addEventListener('resize',()=>{clearTimeout(refreshTimer);refreshTimer=window.setTimeout(renderPlot,150);});
 window.addEventListener('online',()=>void pollStage());
 (window as any).p7={get state(){return state},get scene(){return scene},get job(){return job},get data(){return data},get sid(){return sid},setTime:(t:number)=>{state.cursor=t;syncCursor()},change,openFastener};
}
init().catch(e=>{toast(String(e));$('run-status').textContent='Connection or readiness issue. Reload to recover your saved session. '+String(e);});
