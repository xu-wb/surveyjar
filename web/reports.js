let reportSelection={surveyIds:null,projectId:'',includeDrafts:false,basis:'snapshot'},reportData=null;
function reportSurveyChoices(){const choices=new Map(surveys.map(s=>[s.id,s.title]));responses.forEach(r=>{if(!choices.has(r.survey_id))choices.set(r.survey_id,r.survey.title+'（问卷已删除）')});return [...choices];}
function results(){
  const choices=reportSurveyChoices();if(reportSelection.surveyIds===null)reportSelection.surveyIds=choices.map(([id])=>id);
  const filtered=responses.filter(r=>reportSelection.surveyIds.includes(r.survey_id)&&(!reportSelection.projectId||String(r.projectId)===reportSelection.projectId)&&(reportSelection.includeDrafts||r.status==='submitted'));
  app.innerHTML=heading('收集结果与导出','所有问卷合并为一张宽表：每行一个被试的一次项目作答，每列一道题。',btn('预览宽表','report-preview')+btn('导出合并宽表 CSV','report-export','primary'))+
  `<div class="panel"><h2>筛选问卷</h2><div class="actions">${btn('全选','report-all')}${btn('清空','report-clear')}</div><div class="report-surveys">${choices.map(([id,title])=>`<label><input type="checkbox" data-report-survey="${id}" ${reportSelection.surveyIds.includes(id)?'checked':''}>${esc(title)}</label>`).join('')}</div><div class="fields"><label class="field">项目${select({'':'全部项目',...Object.fromEntries(projects.map(p=>[p.id,p.name]))},reportSelection.projectId,'data-report-key="projectId"')}</label><label class="field">计分依据${select({snapshot:'作答时的计分规则',current:'当前反向与维度规则（保留原始分值）'},reportSelection.basis,'data-report-key="basis"')}</label><label><input type="checkbox" data-report-key="includeDrafts" ${reportSelection.includeDrafts?'checked':''}> 包含草稿</label></div><p class="hint">先列原始分；仅反向题紧邻增加反向转换分列；随后为各维度分及问卷总分。缺失值留空。计分依据切换只影响本次导出，不覆盖历史答卷。</p><p class="hint">非计分文本和普通选项不进入分数表。MCQ 没有原始量表分数，使用 1/2 记录选择（非得分），含义写在列名；物质使用导出0/1与使用年数。</p></div><div id="report-preview"></div><div class="panel table-wrap"><table><thead><tr><th>被试</th><th>项目／批次</th><th>问卷</th><th>状态</th><th>操作</th></tr></thead><tbody>${filtered.map(r=>`<tr><td>${esc(r.participant||'未填写编号')}</td><td>${esc(r.projectName||'单独填写')} / ${r.batchId||'—'}</td><td>${esc(r.survey.title)}</td><td>${r.status==='submitted'?'已提交':'草稿'}</td><td>${btn(r.status==='draft'?'继续填写':'查看详情',(r.status==='draft'?'resume:':'detail:')+r.id)}</td></tr>`).join('')||'<tr><td colspan="5">当前筛选条件下暂无答卷</td></tr>'}</tbody></table></div>`;
}
function renderReport(data){document.querySelector('#report-preview').innerHTML=`<div class="panel"><h2>宽表预览 · ${data.rows.length} 行</h2><div class="table-wrap report-table"><table><thead><tr>${data.headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${data.rows.slice(0,20).map(row=>`<tr>${row.map(v=>`<td>${esc(v??'')}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="hint">预览最多显示20行，导出包含全部筛选结果。</p>${data.warnings.map(w=>`<p class="hint">${esc(w)}</p>`).join('')}</div>`;}
app.addEventListener('change',e=>{
  const el=e.target;
  if(el.dataset.reportSurvey!==undefined){const id=Number(el.dataset.reportSurvey);reportSelection.surveyIds=el.checked?[...reportSelection.surveyIds,id]:reportSelection.surveyIds.filter(x=>x!==id);results();}
  if(el.dataset.reportKey){reportSelection[el.dataset.reportKey]=el.type==='checkbox'?el.checked:el.value;results();}
});
app.addEventListener('click',async e=>{
  const action=e.target.closest('[data-action]')?.dataset.action;if(!action?.startsWith('report-'))return;
  try{
    if(action==='report-all'||action==='report-clear'){reportSelection.surveyIds=action==='report-all'?reportSurveyChoices().map(([id])=>id):[];results();return;}
    reportData=await api('report','POST',reportSelection);renderReport(reportData);
    if(action==='report-export')download('项目问卷合并宽表.csv',csvText([reportData.headers,...reportData.rows]),'text/csv');
  }catch(err){toast(err.message);}
});
