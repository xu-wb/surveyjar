// Parsing and preview do not write to the database.
let importBatch=null, importSource=null, importEditing=null, importModified=false;
const readingModes={auto:"自动识别",forced:"迫选题表格",matrix:"共用选项量表",form:"基础信息表（双列）",independent:"逐题独立选项",mixed:"混合问卷（逐表识别）"};
function importPage(){
  importEditing=null;importSource=null;importModified=false;
  app.innerHTML=heading('导入问卷','直接粘贴 Word 表格，或一行写完题目和选项。',btn('返回','back'))+`
  <div class="panel"><h2>选择文件，或直接粘贴</h2><p>支持 DOCX、TXT、JSON。Word 表格请连同表头一起复制；含多个【问卷名称】的文档会分开识别。</p>
  <label class="field">导入结构类型${select(readingModes,'auto','id="reading-mode"')}</label><p class="hint">适用于 DOCX 和横排 TXT。混合文档建议选择自动识别或混合问卷，DOCX 可在预览中逐表修改。混合 TXT 的不同表格之间请留一空行。JSON 和旧版模板保留文件内的结构。</p><div class="actions">${btn('选择文件','choosefile','primary')}${btn('下载横排 TXT 模板','txttemplate')}${btn('填入横排示例','import-example')}</div></div>
  <div class="panel"><label class="field">问卷名称（文本已有标题时优先采用文本标题）<input id="import-title" value="粘贴导入的问卷"></label>
  <label class="field" style="margin-top:18px">问卷内容<textarea id="import-text" class="import-text" placeholder="题目 | 没有 | 好几天 | 一半以上时间 | 几乎每天&#10;1.做事时提不起劲或没有兴趣 | 0 | 1 | 2 | 3"></textarea></label>
  <p class="hint">可用 Word 自带的制表符或 | 分列。也支持：题目　A.选项一　B.选项二。写「没有=0」明确分值；未标分时不计分。</p>
  ${btn('识别并预览','parse-paste','primary')}<p id="import-error" class="error" role="alert"></p></div>`;
}
function showImportPreview(data){
  importBatch=data;
  data.surveys.forEach(s=>validate(s));
  app.innerHTML=heading('核对导入内容',`识别到 ${data.surveys.length} 份问卷，共 ${data.surveys.reduce((n,s)=>n+s.questions.length,0)} 个条目。尚未保存到问卷库。`,btn('重新导入','import')+btn('保存勾选问卷','save-import','primary'))+
    `<div class="panel"><h2>需要核对的内容</h2>${data.readingLabel?`<p>识别为：${esc(data.readingLabel)}</p>`:''}${(data.errors||[]).map(e=>`<p class="error">${esc(e)}</p>`).join('')}${(data.warnings||[]).map(w=>`<p>${esc(w)}</p>`).join('')}</div>`+
    (data.tables||[]).map(t=>`<section class="panel"><h2>表格 ${Number(t.id)+1} · ${esc(t.title)}</h2><label class="field">读取方式${select(readingModes,t.mode,`data-table-mode="${t.id}"`)}</label><p>识别为：${esc(({forced:'迫选题表格',matrix:'共用选项量表',form:'基础信息表',independent:'逐题独立选项',unknown:'待确认'})[t.detected]||'待确认')} · ${t.count} 题</p><pre>${esc(t.preview.map(row=>row.join(' | ')).join('\n'))}</pre>${t.error?`<p class="error">${esc(t.error)}</p>`:''}</section>`).join('')+
    data.surveys.map((s,i)=>`<section class="panel"><div class="qtop"><label><input type="checkbox" data-import-index="${i}" checked> <strong>${esc(s.title)}</strong> · ${questionSummary(s.questions)}</label>${btn('调整题型与分组','edit-import:'+i)}${btn('预览作答','preview-import:'+i)}</div><p>${esc(s.description)}</p><details><summary>展开全部题目、选项和分值</summary><div class="table-wrap"><table class="import-table"><thead><tr><th>题目</th><th>选项及分值</th><th>计分</th></tr></thead><tbody>${s.questions.map(q=>`<tr><td>${q.groupTitle?esc(q.groupTitle)+' / ':''}${q.sourceNumber?esc(q.sourceNumber)+'. ':''}${esc(q.title)}${q.type==='forced'?`（${q.options.length} 选 ${q.chooseCount??1}）`:''}</td><td>${q.type==='substance'?'是否使用过；若是，填写使用时长（年）':q.type==='text'?'自由填写':['scale','number'].includes(q.type)?`${q.min} 至 ${q.max}`:q.options.map(o=>`${esc(o.label)}${q.scoring==='none'?'':` = ${o.score}`}`).join(' ／ ')}</td><td>${q.scoring==='none'?'不计分':'按明确分值'}</td></tr>`).join('')}</tbody></table></div></details></section>`).join('');
  if(data.errors?.length){document.querySelector('[data-action="save-import"]').disabled=true;document.querySelectorAll('[data-action^="edit-import:"], [data-action^="preview-import:"]').forEach(b=>b.disabled=true);}
}
async function readImportFile(file){
  importSource=null;
  if(file.name.toLowerCase().endsWith('.docx')){
    const bytes=new Uint8Array(await file.arrayBuffer());
    let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    importSource={format:'docx',data:btoa(binary),title:file.name.replace(/\.docx$/i,''),overrides:{},mode:document.querySelector('#reading-mode')?.value||'auto'};return api('import','POST',importSource);
  }
  const text=(await file.text()).replace(/^\uFEFF/,'');
  if(file.name.toLowerCase().endsWith('.json')){
    const value=JSON.parse(text);
    return {surveys:Array.isArray(value)?value:[value],warnings:['请核对题目、必填和计分设置后保存。']};
  }
  if(/^\[(单选|多选|量表|数字|文本)\|/m.test(text))return {surveys:[parseText(text)],warnings:['已按旧版逐行模板识别，请核对后保存。']};
  importSource={text,title:file.name.replace(/\.txt$/i,''),mode:document.querySelector('#reading-mode')?.value||'auto'};return api('import','POST',importSource);
}
async function importAction(action,i){
  if(action==='choosefile')document.querySelector('#file').click();
  if(action==='import-example')document.querySelector('#import-text').value=textTemplate;
  if(action==='parse-paste'){
    try{
      const text=document.querySelector('#import-text').value;
      const title=document.querySelector('#import-title').value.trim()||'粘贴导入的问卷';
      importSource={text,title,mode:document.querySelector('#reading-mode').value};
      const data=/^\[(单选|多选|量表|数字|文本)\|/m.test(text)?{surveys:[parseText(text)],warnings:['已按旧版模板识别。']}:await api('import','POST',importSource);
      showImportPreview(data);
    }catch(e){document.querySelector('#import-error').textContent=e.message;}
  }
  if(action==='edit-import'||action==='preview-import'){
    importEditing=i;edit=copy(importBatch.surveys[i]);delete edit.id;persistEdit();
    if(action==='preview-import')structureAction('preview-editor');else editor();
  }
  if(action==='import-preview'){
    if(edit&&importEditing!==null){validate(edit);importBatch.surveys[importEditing]=copy(edit);importModified=true;edit=null;}
    importEditing=null;localStorage.removeItem('questionnaire-editor');showImportPreview(importBatch);
  }
  if(action==='save-import'){
    if(importBatch.errors?.length)throw Error('请先解决读取错误，避免保存不完整问卷');
    const selected=[...document.querySelectorAll('[data-import-index]:checked')];
    if(!selected.length)throw Error('请至少勾选一份问卷');
    const button=document.querySelector('[data-action="save-import"]');button.disabled=true;
    try{
      for(const input of selected){
        const s=copy(importBatch.surveys[Number(input.dataset.importIndex)]);delete s.id;
        await api('surveys','POST',validate(s));input.checked=false;input.disabled=true;
      }
      await refresh();page='surveys';render();toast(`已保存 ${selected.length} 份问卷`);
    }finally{button.disabled=false;}
  }

}

app.addEventListener('change',async e=>{
  if(e.target.dataset.tableMode===undefined)return;
  const el=e.target;if(importModified&&!confirm('切换读取方式会重新解析整个源文档，并清除本次预览中的人工修改。是否继续？')){el.value=importBatch.tables.find(t=>t.id===el.dataset.tableMode).mode;return;}const previous=importSource.overrides[el.dataset.tableMode];importSource.overrides[el.dataset.tableMode]=el.value;el.disabled=true;
  try{showImportPreview(await api('import','POST',importSource));importModified=false;}catch(error){importSource.overrides[el.dataset.tableMode]=previous;el.value=importBatch.tables.find(t=>t.id===el.dataset.tableMode).mode;toast(error.message);el.disabled=false;}
});
