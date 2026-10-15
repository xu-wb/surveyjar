const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function workspace(globals = {}) {
  const app = {innerHTML: '', addEventListener() {}};
  const element = {style: {}, classList: {add() {}, remove() {}}, addEventListener() {}};
  const context = vm.createContext({
    document: {querySelector: s => s === '#app' ? app : element, querySelectorAll: () => [], body: element},
    window: {addEventListener() {}, scrollTo() {}},
    ...globals,
  });
  for (const name of ['app.js', 'projects.js', 'structure.js', 'scoring-ui.js']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../web', name), 'utf8'), context);
  }
  return {context, app};
}

test('JSON import rejects IDs that can inject HTML or selectors', () => {
  const {context} = workspace();
  for (const id of ['q"><img src=x onerror=alert(1)>', 'q" onclick="alert(1)', 'q 1', 123]) {
    context.survey = {title: '测试', questions: [{id, title: '文本', type: 'text', scoring: 'none'}]};
    assert.throws(() => vm.runInContext('validate(survey)', context), /题目 ID/);
  }
  context.survey = {title: '测试', questions: [{id: 'q_1-2', title: '文本', type: 'text', scoring: 'none'}]};
  assert.doesNotThrow(() => vm.runInContext('validate(survey)', context));
});

test('answer and substance renderers escape IDs before creating HTML', () => {
  const {context, app} = workspace();
  context.probe = 'q"><img src=x onerror=alert(1)>';
  vm.runInContext(`
    renderAnswerGroups=()=>{};
    progress=()=>{};
    run={survey:{title:'测试',questions:[{id:probe,title:'文本',type:'text'}]},answers:{}};
    filling();
  `, context);
  assert.ok(!app.innerHTML.includes('<img'));
  assert.ok(app.innerHTML.includes('&quot;&gt;&lt;img'));
  const html = vm.runInContext('substanceAnswer({id:probe})', context);
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&quot;&gt;&lt;img'));
});

test('clearing answers during the first save updates the created draft before exit', async () => {
  const writes = [];
  let finishFirst;
  let notifyStarted;
  const started = new Promise(resolve => { notifyStarted = resolve; });
  const {context} = workspace({
    localStorage: {removeItem() {}, setItem() {}},
    saveResponse: async (url, method, payload) => {
      writes.push(payload);
      if (writes.length === 1) {
        notifyStarted();
        await new Promise(resolve => { finishFirst = resolve; });
      }
      return {id: 1};
    },
  });
  const first = vm.runInContext(`
    api=saveResponse;
    run={survey_id:1,survey:{questions:[{id:'q1',type:'text',title:'备注'}]},answers:{q1:'待清空'}};
    queueSave();
  `, context);
  await started;
  const last = vm.runInContext("run.answers.q1=''; queueSave()", context);
  finishFirst();
  await Promise.all([first, last]);
  assert.equal(writes.length, 2);
  assert.equal(writes[1].id, 1);
  assert.equal(writes[1].answers.q1, '');
});

test('untouched individual and batch forms do not create drafts', async () => {
  let writes = 0;
  const {context} = workspace({
    localStorage: {removeItem() {}},
    saveResponse: async () => { writes++; return {id: 1}; },
  });
  await vm.runInContext(`
    api=saveResponse;
    run={survey:{questions:[{id:'q1',type:'text',title:'备注'}]},answers:{}};
    queueSave();
  `, context);
  await vm.runInContext(`
    run={batchId:1,participant:'S001',survey:{questions:[{id:'q1',type:'text',title:'被试编号'}]},answers:{q1:'S001'}};
    queueSave();
  `, context);
  assert.equal(writes, 0);
});

test('preview checks answers without a participant ID or saving a response', async () => {
  const messages = [];
  const {context} = workspace({messages});
  context.document.getElementById = () => ({
    classList: {toggle() {}}, querySelector: () => ({hidden: true}),
  });
  await vm.runInContext(`
    toast=message=>messages.push(message);
    api=()=>{throw Error('预览不应保存答卷')};
    run={preview:true,survey:{questions:[{id:'q1',type:'text',required:true}]},answers:{q1:'已填写'}};
    submit({preventDefault(){}});
  `, context);
  assert.deepEqual(messages, ['预览检查通过，未保存答卷']);
  assert.equal(vm.runInContext('participantFields()', context), '');
});
