// Groups change presentation only. Item IDs, scoring and answers stay independent.
function multipleChoice(q){return q.type==='multi'||(q.type==='forced'&&(q.chooseCount??1)>1)}
function questionSummary(qs){
  const count=qs.filter((q,i)=>!q.groupId||i===0||q.groupId!==qs[i-1].groupId).length;
  return count===qs.length?`${count} 道题目`:`${count} 道题目（${qs.length} 个条目）`;
}
function normalizeGroups(qs){
  let previous=null,current=null;
  const seen=new Set();
  qs.forEach(q=>{
    const original=q.groupId;
    if(original){if(original!==previous){current=seen.has(original)?uid():original;seen.add(original);}q.groupId=current;}
    previous=original;
  });
}
function structureToolbar(){
  return `<section class="panel"><h2>调整题目结构</h2><p>勾选连续条目，将它们归为一个问题。各子条目仍分别保存答案和计分。取消分组后恢复为独立问题。</p><label class="field">共同题目标题<input id="group-title" placeholder="例如：物质使用"></label><div class="actions">${btn('将勾选条目归为一题','group-items')}${btn('取消勾选条目的分组','ungroup-items')}</div>${importEditing!==null?'<p class="hint">修改完成后点击「返回导入预览」，再统一保存勾选问卷。</p>':''}</section>`;
}
function groupEditor(q,i){
  return q.groupId?`<label class="field">所属问题标题<input data-group-title="${i}" value="${esc(q.groupTitle)}"></label><p class="hint">当前为子条目。修改此标题会同步到同组条目。</p>`:'';
}
function displayQuestionLabel(qs,index){
  let number=0,sub=0;
  for(let i=0;i<=index;i++){
    const q=qs[i];
    if(!q.groupId||i===0||q.groupId!==qs[i-1].groupId){number++;sub=0;}
    sub++;
  }
  return qs[index].groupId?`${number}.${sub}`:`${number}.`;
}
function renderAnswerGroups(qs){
  let container=null,previous=null;
  qs.forEach((q,i)=>{
    if(!q.groupId){container=null;previous=null;return;}
    const panel=document.getElementById('answer-'+q.id);
    if(q.groupId!==previous){
      container=document.createElement('fieldset');container.className='panel question-group';
      const title=document.createElement('legend');
      title.textContent=displayQuestionLabel(qs,i).split('.')[0]+'. '+q.groupTitle;
      container.append(title);panel.before(container);
    }
    container.append(panel);previous=q.groupId;
  });
}
function structureAction(action){
  if(action==='preview-editor'){
    validate(edit);run={survey:copy(edit),answers:{},preview:true};filling();
    app.insertAdjacentHTML('afterbegin',`<div class="panel"><h2>作答预览</h2><p>可以试填并检查必填规则，答案不会保存。</p>${btn('返回编辑','preview-back')}</div>`);
    document.querySelector('#save-state').textContent='预览模式，不保存答案';
    document.querySelector('[type="submit"]').textContent='检查填写';document.querySelector('#answer-form > .actions .hint').textContent='仅用于检查，不保存答案。';return;
  }
  if(action==='preview-back'){run=null;document.body.classList.remove('answer-mode');editor();return;}
  const selected=[...document.querySelectorAll('[data-structure-select]:checked')].map(el=>Number(el.dataset.structureSelect));
  if(!selected.length)throw Error('请先勾选需要调整的条目');
  if(action==='group-items'){
    const title=document.querySelector('#group-title').value.trim();
    if(!title)throw Error('请填写共同题目标题');
    if(selected.length<2)throw Error('请至少勾选两个条目');
    if(selected.at(-1)-selected[0]+1!==selected.length)throw Error('请先用上下移动按钮将条目排在一起，再勾选连续条目');
    const id=uid();selected.forEach(i=>Object.assign(edit.questions[i],{groupId:id,groupTitle:title}));
  }else selected.forEach(i=>{delete edit.questions[i].groupId;delete edit.questions[i].groupTitle;});
  persistEdit();editor();
}
app.addEventListener('input',e=>{
  if(e.target.dataset.groupTitle===undefined)return;
  const q=edit.questions[Number(e.target.dataset.groupTitle)];
  edit.questions.filter(item=>item.groupId===q.groupId).forEach(item=>item.groupTitle=e.target.value);
  document.querySelectorAll('[data-group-title]').forEach(el=>{if(edit.questions[Number(el.dataset.groupTitle)].groupId===q.groupId)el.value=e.target.value;});
  persistEdit();
});
