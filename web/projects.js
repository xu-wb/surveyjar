let projects=[],batches=[],projectDraft=null;
function batchProgress(b){return b.surveys.filter((s,i)=>responses.some(r=>r.batchId===b.id&&r.batchIndex===i&&r.status==='submitted')).length;}
function projectsPage(){
  app.innerHTML=heading('项目与批量填写','为同一被试按顺序完成多份问卷，使用同一批次导出到一行。',btn('＋ 创建项目','project-new','primary'))+
    projects.map(p=>`<section class="panel"><div class="qtop"><h2>${esc(p.name)}</h2><div class="actions">${btn('批量填写','project-start:'+p.id,'primary')}${btn('编辑项目','project-edit:'+p.id)}</div></div><p>${p.surveyIds.map(id=>esc(surveys.find(s=>s.id===id)?.title||'已删除的问卷')).join(' → ')}</p></section>`).join('')+
    (!projects.length?'<div class="empty">先创建项目，再选择需要填写的问卷及顺序。</div>':'')+
    '<h2>被试作答批次</h2>'+batches.map(b=>{const n=batchProgress(b);return `<div class="panel qtop"><div><strong>${esc(b.participant)} · ${esc(b.projectName)}</strong><p>批次 ${b.id} · 已完成 ${n} / ${b.surveys.length}</p></div>${n<b.surveys.length?btn('继续本批次','batch-next:'+b.id,'primary'):'<span class="tag">已完成</span>'}</div>`}).join('');
}
function projectEditor(){
  const d=projectDraft;
  app.innerHTML=heading('编辑项目','问卷按下方顺序填写；已开始的批次保留开始时的题目和计分设置。',btn('保存项目','project-save','primary'))+
  `<div class="panel"><label class="field">项目名称<input id="project-name" value="${esc(d.name)}"></label></div><div class="panel"><h2>选择问卷</h2>${surveys.map(s=>`<label class="answer-option"><input type="checkbox" data-project-survey="${s.id}" ${d.surveyIds.includes(s.id)?'checked':''}> ${esc(s.title)}</label>`).join('')}</div><div class="panel"><h2>填写顺序</h2>${d.surveyIds.map((sid,i)=>`<div class="qtop"><span>${i+1}. ${esc(surveys.find(s=>s.id===sid)?.title||'已删除')}</span><div class="actions">${btn('↑','project-up:'+i)}${btn('↓','project-down:'+i)}</div></div>`).join('')}</div>`;
}
function projectStart(id){
  const p=projects.find(x=>x.id===id);
  app.innerHTML=heading(esc(p.name),'填写被试编号后，依次完成项目中的问卷。')+`<div class="panel"><label class="field">被试编号<input id="batch-participant" placeholder="例如 S001"></label><p>${p.surveyIds.length} 份问卷 · 同一编号再次开始会建立新的测量批次。</p>${btn('开始本次填写','batch-create:'+id,'primary')}</div>`;
}
async function continueBatch(id){
  await refresh();const b=batches.find(x=>x.id===id);
  if(!b)throw Error('未找到批次');
  const index=b.surveys.findIndex((s,i)=>!responses.some(r=>r.batchId===id&&r.batchIndex===i&&r.status==='submitted'));
  if(index<0){document.body.classList.add('answer-mode');window.scrollTo(0,0);app.innerHTML=`<div class="panel success"><span class="tag">全部完成</span><h1 style="margin-top:25px">感谢你的参与</h1><p>本次所有问卷已保存，请告知研究人员。</p>${btn('返回工作台','back')}</div>`;return;}
  const draft=responses.find(r=>r.batchId===id&&r.batchIndex===index&&r.status==='draft');
  run=draft?copy(draft):{survey_id:b.surveys[index].id,survey:copy(b.surveys[index]),answers:{},status:'draft',batchId:id,batchIndex:index,projectId:b.projectId,projectName:b.projectName,participant:b.participant};
  delete run.result;delete run.updated;filling();
}
function isBatchParticipantQuestion(q){
  return Boolean(run.batchId)&&q.type==='text'&&['编号','被试编号','受试者编号','参与者编号'].includes(q.title.replace(/[\s：:*＊]/g,''));
}
function syncBatchParticipant(){
  if(!run.batchId)return;
  const batch=batches.find(b=>b.id===run.batchId);
  if(batch)run.participant=batch.participant;
  run.survey.questions.filter(isBatchParticipantQuestion).forEach(q=>{run.answers[q.id]=run.participant;});
}
function participantFields(){
  if(run.batchId){const b=batches.find(x=>x.id===run.batchId);return `<div class="panel"><strong>${esc(run.projectName)} · 被试 ${esc(run.participant)}</strong><p>第 ${run.batchIndex+1} / ${b?.surveys.length||'?'} 份问卷 · 批次 ${run.batchId}</p></div>`;}
  return `<div class="panel"><label class="field">被试编号（选填；批量完成多问卷请使用项目）<input data-participant value="${esc(run.participant||'')}" placeholder="例如 S001"></label></div>`;
}
app.addEventListener('input',e=>{if(e.target.id==='project-name')projectDraft.name=e.target.value;if(e.target.hasAttribute('data-participant')){run.participant=e.target.value;if(run.preview)return;localStorage.setItem('questionnaire-answer',JSON.stringify(run));clearTimeout(timer);timer=setTimeout(()=>queueSave().catch(err=>toast(err.message)),600);}});
app.addEventListener('change',e=>{if(e.target.dataset.projectSurvey!==undefined){const id=Number(e.target.dataset.projectSurvey);if(e.target.checked)projectDraft.surveyIds.push(id);else projectDraft.surveyIds=projectDraft.surveyIds.filter(x=>x!==id);projectEditor();}});
app.addEventListener('click',async e=>{
  const a=e.target.closest('[data-action]')?.dataset.action;if(!a||!a.startsWith('project-')&&!a.startsWith('batch-'))return;
  const [action,value]=a.split(':');const id=Number(value);
  try{
    if(action==='project-new'){projectDraft={name:'',surveyIds:[]};projectEditor();}
    if(action==='project-edit'){projectDraft=copy(projects.find(p=>p.id===id));projectEditor();}
    if(action==='project-up'||action==='project-down'){const next=id+(action==='project-up'?-1:1),list=projectDraft.surveyIds;if(next>=0&&next<list.length)[list[id],list[next]]=[list[next],list[id]];projectEditor();}
    if(action==='project-save'){await api('projects','POST',projectDraft);await refresh();page='projects';render();toast('项目已保存');}
    if(action==='project-start')projectStart(id);
    if(action==='batch-create'){
      const participant=document.querySelector('#batch-participant').value.trim();
      const existing=batches.find(b=>b.projectId===id&&b.participant===participant&&batchProgress(b)<b.surveys.length);
      if(existing){await continueBatch(existing.id);toast('已继续该被试未完成的批次');return;}
      const button=e.target.closest('button');button.disabled=true;
      try{const b=await api('batches','POST',{projectId:id,participant});await continueBatch(b.id);}finally{button.disabled=false;}
    }
    if(action==='batch-next')await continueBatch(id);
  }catch(err){toast(err.message);}
});
