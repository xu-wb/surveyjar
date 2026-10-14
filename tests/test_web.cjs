const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function workspace() {
  const app = {innerHTML: '', addEventListener() {}};
  const element = {style: {}, classList: {add() {}, remove() {}}, addEventListener() {}};
  const context = vm.createContext({
    document: {querySelector: s => s === '#app' ? app : element, querySelectorAll: () => [], body: element},
    window: {addEventListener() {}, scrollTo() {}},
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
