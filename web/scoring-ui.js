function prepareScoring(s){
  if(s.scoreVersion!==2){
    s.questions.forEach(q=>{
      if(['single','multi','forced'].includes(q.type)&&['forward','reverse'].includes(q.scoring))q.options.forEach((o,i)=>o.score=i+1);
      if(q.scoring==='reverse'){q.scoring='forward';q.reverse=true;}
    });
    s.scoreVersion=2;
  }
  s.dimensions=s.dimensions||[];s.totalMethod=s.totalMethod||'sum';s.scoreMode=s.scoreMode||'auto';
}
function scoringSettings(){
  return `<section class="panel"><h2>计分与维度</h2><div class="fields"><label class="field">问卷计分模式${select({auto:'自动计算',raw:'仅收集原始数据（特殊算法）'},edit.scoreMode,'data-survey="scoreMode"')}</label><label class="field">总分规则${select({sum:'所有计分题求和',mean:'所有计分题平均分',none:'不计算总分（仅维度）'},edit.totalMethod,'data-survey="totalMethod"')}</label></div><p class="hint">先按原始分值与反向设置计算题目分，再按所属维度汇总。总分直接按题目汇总，不对维度重复求和。计分题未答全时，对应维度与总分留空；不把缺失当 0 分。</p>${edit.dimensions.map(dimensionCard).join('')}<div class="actions" style="margin-top:14px">${btn('＋ 添加维度','add-dimension')}</div><p class="hint">在每个维度中直接勾选包含的计分题，也可在题目下方选择所属维度，两处同步。每道题属于一个维度，勾选到新维度会从原维度移出。原始数据模式仍保存已配置的原始分值，但不计算反向后得分、维度分或总分。</p></section>`;
}
function itemScoring(q,i){
  if(['text','substance'].includes(q.type))return q.type==='substance'?`<p class="hint">每个类别只问是否使用过。选择「是」后填写时长（年，可填小数），选择「否」则隐藏并清除时长。本题不计分。</p>`:'';
  return `<div class="fields" style="margin-top:15px"><label class="field">所属维度${select({'':'不分配维度',...Object.fromEntries(edit.dimensions.map(d=>[d.id,d.name]))},q.dimensionId||'',`data-q="${i}" data-key="dimensionId"`)}</label><label><input type="checkbox" data-q="${i}" data-key="reverse" ${q.reverse?'checked':''}> 反向计分（保留原始分）</label></div><p class="hint" data-score-preview="${i}">${itemScorePreview(q)}</p>`;
}
function substanceAnswer(q,v={}){
  v=v&&typeof v==='object'?v:{};
  return `<div class="actions">${[['no','否，未使用过'],['yes','是，使用过']].map(([value,label])=>`<label class="answer-option"><input type="radio" data-answer="${esc(q.id)}" data-part="used" name="${esc(q.id)}" value="${value}" ${v.used===value?'checked':''}>${label}</label>`).join('')}</div><div data-duration-box="${esc(q.id)}" ${v.used==='yes'?'':'hidden'} style="margin-top:15px"><label class="field">使用时长（年，可填小数）<input type="number" min="0.001" step="any" data-answer="${esc(q.id)}" data-part="duration" value="${esc(v.duration??'')}" ${v.used==='yes'?'':'disabled'} placeholder="例如 2 或 0.5"></label></div>`;
}
function getAnswerValue(el,id){
  if(el.dataset.part){
    const old=run.answers[id];const v=old&&typeof old==='object'?{...old}:{used:'',duration:''};v[el.dataset.part]=el.value;
    if(v.used==='no')v.duration='';
    const box=document.querySelector(`[data-duration-box="${id}"]`);box.hidden=v.used!=='yes';
    const duration=box.querySelector('input');duration.disabled=v.used!=='yes';if(v.used==='no')duration.value='';return v;
  }
  return el.type==='checkbox'?[...document.querySelectorAll('[data-answer="'+id+'"]:checked')].map(x=>x.value):el.value;
}
function scoreDisplay(result){
  if(result.scoreMode==='raw')return '仅收集原始数据';
  if(result.totalMethod==='none')return '不计算总分';
  return result.total==null?'未计算（无计分题或存在缺失）':String(result.total);
}
function dimensionResults(result){
  if(result.scoreMode==='raw')return '<p>已保留原始回答与已配置的原始分值，供导出后使用专门算法分析。</p>';
  return (result.dimensions||[]).map(d=>`<div class="panel"><h2>${esc(d.name)}：${d.score??'未计算'}</h2><span class="hint">${d.method==='mean'?'平均分':'求和'} · 已答 ${d.answered} / ${d.items} 道计分题</span></div>`).join('');
}
function rawItem(r,q){
  const d=r.result.details.find(x=>x.id===q.id)||{};
  if('rawScore' in d)return d;
  // Historical answer snapshots provide raw scores without rewriting stored results.
  const v=r.answers[q.id];let raw=null,parts=[];
  if(v!==undefined&&v!==null&&v!==''&&q.scoring!=='none'){
    if(['single','multi','forced'].includes(q.type)){
      parts=(Array.isArray(v)?v:[v]).map(i=>q.scoring==='custom'?Number(q.options[Number(i)].score):Number(i)+1);raw=parts.length?parts.reduce((a,b)=>a+b,0):null;
    }else if(['scale','number'].includes(q.type))raw=q.scoring==='custom'?Number(q.mapping?.[String(Number(v))]??0):Number(v);
  }
  return {...d,rawScore:raw,rawOptionScores:parts,reverse:q.scoring==='reverse'||!!q.reverse};
}
function csvText(rows){return rows.map(row=>row.map(value=>{let v=value??'';if(typeof v==='string'&&/^[=+@-]/.test(v))v="'"+v;return '"'+String(v).replace(/"/g,'""')+'"'}).join(',')).join('\r\n');}
function scoringAction(action,i){
  if(action==='add-dimension'){edit.dimensions.push({id:uid(),name:'新维度',method:'sum'});persistEdit();editor();}
  if(action==='remove-dimension'){const id=edit.dimensions[i].id;edit.dimensions.splice(i,1);edit.questions.forEach(q=>{if(q.dimensionId===id)q.dimensionId=''});persistEdit();editor();}
}

function dimensionCard(d,i){
  const eligible=edit.questions.map((q,index)=>({q,index})).filter(({q})=>!['text','substance'].includes(q.type)&&q.scoring!=='none');
  return `<section class="dimension-card"><div class="dimension-fields"><label class="field">维度名称<input data-dimension="${i}" data-key="name" value="${esc(d.name)}" placeholder="例如：注意力维度"></label><label class="field">计算方法${select({sum:'求和',mean:'平均分'},d.method,`data-dimension="${i}" data-key="method"`)}</label>${btn('删除维度','remove-dimension:'+i)}</div><fieldset class="dimension-members"><legend>包含的题目 · <span data-dimension-count="${i}">${eligible.filter(({q})=>q.dimensionId===d.id).length}</span> 题</legend><div class="dimension-question-list">${eligible.map(({q,index})=>`<label><input type="checkbox" data-member-dim="${i}" data-member-q="${index}" ${q.dimensionId===d.id?'checked':''}><span>第 ${index+1} 题 · ${esc(q.title)}</span></label>`).join('')||'<p class="hint">暂无计分题，请先在题目中设置计分方式。</p>'}</div></fieldset></section>`;
}
function syncDimensionControls(){
  document.querySelectorAll('[data-key="dimensionId"]').forEach(el=>{
    const value=edit.questions[Number(el.dataset.q)].dimensionId||'';
    el.innerHTML='<option value="">不分配维度</option>'+edit.dimensions.map(d=>`<option value="${esc(d.id)}">${esc(d.name)}</option>`).join('');el.value=value;
  });
  document.querySelectorAll('[data-member-dim]').forEach(el=>{el.checked=edit.questions[Number(el.dataset.memberQ)].dimensionId===edit.dimensions[Number(el.dataset.memberDim)].id;});
  document.querySelectorAll('[data-dimension-count]').forEach(el=>{const id=edit.dimensions[Number(el.dataset.dimensionCount)].id;el.textContent=edit.questions.filter(q=>q.dimensionId===id&&!['text','substance'].includes(q.type)&&q.scoring!=='none').length;});
}

function itemScorePreview(q){
 if(q.scoring==='none')return '本题不计分；若需要原始分，请先设置计分方式。';
 if(['single','multi','forced'].includes(q.type)){
  const vals=q.options.map(o=>Number(o.score));const reversed=q.reverse||q.scoring==='reverse';
  return (reversed?'反向转换预览：':'原始分值：')+vals.map(v=>reversed?`${v} → ${Math.max(...vals)+Math.min(...vals)-v}`:v).join('，');
 }
 return q.reverse?'反向转换：最小值 + 最大值 − 原始分':'正向计分';
}
function updateScorePreview(i){const el=document.querySelector(`[data-score-preview="${i}"]`);if(el)el.textContent=itemScorePreview(edit.questions[i]);}
