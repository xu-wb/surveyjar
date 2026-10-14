"""Offline questionnaire app. Python standard library only."""
import json
import math
import re
import base64
import sqlite3
import webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from import_questionnaire import parse_docx, parse_text
from scoring import score
from reporting import wide_report

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DB = DATA / 'questionnaires.sqlite3'
VERSION = (ROOT / 'VERSION').read_text().strip()


def validate_survey(survey):
    if not isinstance(survey, dict) or not isinstance(survey.get('title'), str) or not survey['title'].strip():
        raise ValueError('请填写问卷名称')
    if not isinstance(survey.get('questions'), list) or not survey['questions']:
        raise ValueError('请至少添加一道题')
    if not isinstance(survey.get('description', ''), str):
        raise ValueError('问卷说明应为文本')
    if survey.get('scoreMode', 'auto') not in ('auto', 'raw') or survey.get('totalMethod', 'sum') not in ('sum', 'mean', 'none'):
        raise ValueError('无效计分规则')
    dimensions = survey.get('dimensions', [])
    if not isinstance(dimensions, list):
        raise ValueError('维度应为列表')
    dimension_ids, names = set(), set()
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            raise ValueError('无效维度')
        did, name = dimension.get('id'), dimension.get('name')
        if not isinstance(did, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', did) or did in dimension_ids:
            raise ValueError('维度 ID 无效或重复')
        if not isinstance(name, str) or not name.strip() or name.strip() in names or dimension.get('method', 'sum') not in ('sum', 'mean'):
            raise ValueError('维度名称或计算方法无效')
        dimension_ids.add(did)
        names.add(name.strip())
    ids = set()
    for q in survey['questions']:
        if not isinstance(q, dict):
            raise ValueError('无效题目')
        qid = q.get('id')
        if not isinstance(qid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', qid) or qid in ids:
            raise ValueError('题目 ID 无效或重复，只能包含字母、数字、下划线和连字符')
        ids.add(qid)
        if not isinstance(q.get('title'), str) or not q['title'].strip():
            raise ValueError('请填写题目内容')
        if q.get('type') not in ('single', 'multi', 'forced', 'number', 'scale', 'text', 'substance'):
            raise ValueError('未知题型')
        if q.get('scoring') not in ('none', 'forward', 'reverse', 'custom'):
            raise ValueError('未知计分方式')
        if type(q.get('required', False)) is not bool or type(q.get('reverse', False)) is not bool:
            raise ValueError('必填和反向设置应为布尔值')
        if q.get('dimensionId') and q['dimensionId'] not in dimension_ids:
            raise ValueError('题目引用了不存在的维度')
        if q.get('groupId') and (not isinstance(q.get('groupTitle'), str) or not q['groupTitle'].strip()):
            raise ValueError('请填写分组的问题标题')
        if q['type'] in ('single', 'multi', 'forced'):
            options = q.get('options')
            if not isinstance(options, list) or not options:
                raise ValueError('请选择题目选项')
            for option in options:
                if not isinstance(option, dict) or not isinstance(option.get('label'), str) or not option['label'].strip():
                    raise ValueError('选项内容不能为空')
                if type(option.get('score')) not in (int, float) or not math.isfinite(option['score']):
                    raise ValueError('选项分值应为有限数字')
            count = q.get('chooseCount', 1)
            if q['type'] == 'forced' and (type(count) is not int or not 1 <= count < len(options)):
                raise ValueError('迫选题的选择数量须为整数且小于选项数量')
        if q['type'] in ('number', 'scale'):
            lo, hi = q.get('min'), q.get('max')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in (lo, hi)) or lo >= hi:
                raise ValueError('数字范围不正确')
            if q['type'] == 'scale' and (not float(lo).is_integer() or not float(hi).is_integer() or hi - lo > 20):
                raise ValueError('量表应使用整数，且最多 21 个刻度')
            mapping = q.get('mapping', {})
            if not isinstance(mapping, dict) or any(type(v) not in (int, float) or not math.isfinite(v) for v in mapping.values()):
                raise ValueError('映射分值应为有限数字')
        if q['type'] in ('text', 'substance') and q['scoring'] != 'none':
            raise ValueError('文本和物质使用题不计分')

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    DB.parent.mkdir(exist_ok=True)
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS surveys(id INTEGER PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS responses(id INTEGER PRIMARY KEY, survey_id INTEGER NOT NULL,
          status TEXT NOT NULL, body TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY, body TEXT NOT NULL);
        ''')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def send_json(self, obj, status=200):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def allow_write(self):
        host = self.headers.get('Host')
        if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}') or self.headers.get('Origin') not in (None, 'http://' + host):
            self.send_json({'error': '只允许本地工作台写入数据'}, 403)
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if not path.startswith('/api/'):
            return super().do_GET()
        with connect() as db:
            if path == '/api/surveys':
                return self.send_json([dict(id=r['id'], **json.loads(r['body'])) for r in db.execute('SELECT * FROM surveys ORDER BY id DESC')])
            if path == '/api/responses':
                return self.send_json([dict(id=r['id'], survey_id=r['survey_id'], status=r['status'], updated=r['updated'], **json.loads(r['body'])) for r in db.execute('SELECT * FROM responses ORDER BY id DESC')])
            if path in ('/api/projects', '/api/batches'):
                table = 'projects' if path.endswith('projects') else 'batches'
                return self.send_json([dict(id=r['id'], **json.loads(r['body'])) for r in db.execute(f'SELECT * FROM {table} ORDER BY id DESC')])
        self.send_json({'error': '未找到'}, 404)

    def do_POST(self):
        if not self.allow_write():
            return
        if self.headers.get_content_type() != 'application/json':
            return self.send_json({'error': '请求应使用 application/json'}, 415)
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if not isinstance(body, dict):
                raise ValueError('请求内容应为 JSON 对象')
            if self.path == '/api/import':
                if body.get('format') == 'docx':
                    return self.send_json(parse_docx(base64.b64decode(body['data']), body.get('title', '导入问卷'), body.get('overrides'), body.get('mode', 'auto')))
                return self.send_json(parse_text(body['text'], body.get('title', '粘贴导入的问卷'), body.get('mode', 'auto')))
            with connect() as db:
                if self.path == '/api/report':
                    records = [dict(id=r['id'], survey_id=r['survey_id'], status=r['status'], updated=r['updated'], **json.loads(r['body'])) for r in db.execute('SELECT * FROM responses ORDER BY id DESC')]
                    surveys = [dict(id=r['id'], **json.loads(r['body'])) for r in db.execute('SELECT * FROM surveys')]
                    return self.send_json(wide_report(records, surveys, body))
                if self.path == '/api/projects':
                    if not body.get('name', '').strip() or not body.get('surveyIds'):
                        raise ValueError('请填写项目名称并选择问卷')
                    if len(set(body['surveyIds'])) != len(body['surveyIds']):
                        raise ValueError('项目不能重复包含同一问卷')
                    pid = body.pop('id', None)
                    if pid:
                        db.execute('UPDATE projects SET body=? WHERE id=?', (json.dumps(body, ensure_ascii=False), pid))
                    else:
                        pid = db.execute('INSERT INTO projects(body) VALUES(?)', (json.dumps(body, ensure_ascii=False),)).lastrowid
                    return self.send_json({'id': pid})
                if self.path == '/api/batches':
                    participant = body.get('participant', '').strip()
                    if not participant:
                        raise ValueError('请填写被试编号')
                    project = db.execute('SELECT * FROM projects WHERE id=?', (body['projectId'],)).fetchone()
                    if not project:
                        raise ValueError('项目不存在')
                    config = json.loads(project['body'])
                    queue = []
                    for sid in config['surveyIds']:
                        row = db.execute('SELECT body FROM surveys WHERE id=?', (sid,)).fetchone()
                        if not row:
                            raise ValueError('项目中的问卷已被删除，请重新编辑项目')
                        queue.append(dict(id=sid, **json.loads(row['body'])))
                    batch = {'projectId': project['id'], 'projectName': config['name'], 'participant': participant, 'surveys': queue}
                    bid = db.execute('INSERT INTO batches(body) VALUES(?)', (json.dumps(batch, ensure_ascii=False),)).lastrowid
                    return self.send_json(dict(id=bid, **batch))
                if self.path == '/api/surveys':
                    validate_survey(body)
                    sid = body.pop('id', None)
                    if sid:
                        db.execute('UPDATE surveys SET body=? WHERE id=?', (json.dumps(body, ensure_ascii=False), sid))
                    else:
                        sid = db.execute('INSERT INTO surveys(body) VALUES(?)', (json.dumps(body, ensure_ascii=False),)).lastrowid
                    return self.send_json({'id': sid})
                if self.path == '/api/responses':
                    if body.get('status') not in ('draft', 'submitted'):
                        raise ValueError('答卷状态应为 draft 或 submitted')
                    db.execute('BEGIN IMMEDIATE')
                    if body.get('batchId'):
                        row = db.execute('SELECT body FROM batches WHERE id=?', (body['batchId'],)).fetchone()
                        if not row:
                            raise ValueError('作答批次不存在')
                        batch = json.loads(row['body'])
                        body['survey'] = batch['surveys'][int(body['batchIndex'])]
                        if body['survey_id'] != body['survey']['id']:
                            raise ValueError('批次问卷不匹配')
                        for key in ('projectId', 'projectName', 'participant'):
                            body[key] = batch[key]
                        body['batchSurveyIds'] = [s['id'] for s in batch['surveys']]
                        for previous in db.execute('SELECT id,body FROM responses WHERE survey_id=?', (body['survey_id'],)):
                            previous_body = json.loads(previous['body'])
                            if previous_body.get('batchId') == body['batchId'] and previous_body.get('batchIndex') == body['batchIndex']:
                                body['id'] = previous['id']
                                break
                    old = db.execute('SELECT * FROM responses WHERE id=?', (body['id'],)).fetchone() if body.get('id') else None
                    if body.get('id') and not old:
                        raise ValueError('答卷不存在')
                    if old:
                        if old['status'] == 'submitted':
                            raise ValueError('已提交的答卷不可覆盖')
                        snapshot = json.loads(old['body'])
                        if old['survey_id'] != body['survey_id'] or snapshot.get('batchId') != body.get('batchId'):
                            raise ValueError('答卷所属问卷或批次不匹配')
                        body['survey'] = snapshot['survey']
                    elif not body.get('batchId'):
                        row = db.execute('SELECT body FROM surveys WHERE id=?', (body['survey_id'],)).fetchone()
                        if not row:
                            raise ValueError('问卷不存在')
                        body['survey'] = json.loads(row['body'])
                    result, missing = score(body['survey'], body['answers'])
                    if body['status'] == 'submitted' and missing:
                        return self.send_json({'error': '请完成必填题：' + '、'.join(missing)}, 400)
                    rid = body.pop('id', None)
                    sid, status = body.pop('survey_id'), body.pop('status')
                    body['result'] = result
                    raw = json.dumps(body, ensure_ascii=False)
                    if rid:
                        db.execute('UPDATE responses SET body=?,status=?,updated=CURRENT_TIMESTAMP WHERE id=?', (raw, status, rid))
                    else:
                        rid = db.execute('INSERT INTO responses(survey_id,status,body) VALUES(?,?,?)', (sid, status, raw)).lastrowid
                    return self.send_json({'id': rid, 'result': result})
        except (ValueError, KeyError, TypeError, IndexError) as e:
            return self.send_json({'error': str(e)}, 400)
        self.send_json({'error': '未找到'}, 404)

    def do_DELETE(self):
        if not self.allow_write():
            return
        parsed = urlparse(self.path)
        sid = int(parse_qs(parsed.query)['id'][0])
        with connect() as db:
            if parsed.path == '/api/surveys':
                db.execute('DELETE FROM surveys WHERE id=?', (sid,))
            elif parsed.path == '/api/responses':
                db.execute('DELETE FROM responses WHERE id=?', (sid,))
            else:
                return self.send_json({'error': '未找到'}, 404)
        self.send_json({'ok': True})

if __name__ == '__main__':
    init_db()
    address = 'http://127.0.0.1:8765'
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('SurveyJar ' + VERSION + ' 已启动：' + address + '\n关闭此窗口即可停止。数据保存在 ' + str(DB))
    webbrowser.open(address)
    server.serve_forever()
