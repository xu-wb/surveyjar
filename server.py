"""Offline questionnaire app. Python standard library only."""
import json
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
DATA.mkdir(exist_ok=True)
DB = DATA / 'questionnaires.sqlite3'

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

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
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
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
                    sid = body.pop('id', None)
                    if sid:
                        db.execute('UPDATE surveys SET body=? WHERE id=?', (json.dumps(body, ensure_ascii=False), sid))
                    else:
                        sid = db.execute('INSERT INTO surveys(body) VALUES(?)', (json.dumps(body, ensure_ascii=False),)).lastrowid
                    return self.send_json({'id': sid})
                if self.path == '/api/responses':
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
                    result, missing = score(body['survey'], body['answers'])
                    if body['status'] == 'submitted' and missing:
                        return self.send_json({'error': '请完成必填题：' + '、'.join(missing)}, 400)
                    rid = body.pop('id', None)
                    sid, status = body.pop('survey_id'), body.pop('status')
                    body['result'] = result
                    raw = json.dumps(body, ensure_ascii=False)
                    if rid:
                        old = db.execute('SELECT status FROM responses WHERE id=?', (rid,)).fetchone()
                        if old and old['status'] == 'submitted':
                            return self.send_json({'error': '已提交的答卷不可覆盖'}, 400)
                        db.execute('UPDATE responses SET body=?,status=?,updated=CURRENT_TIMESTAMP WHERE id=?', (raw, status, rid))
                    else:
                        rid = db.execute('INSERT INTO responses(survey_id,status,body) VALUES(?,?,?)', (sid, status, raw)).lastrowid
                    return self.send_json({'id': rid, 'result': result})
        except (ValueError, KeyError, TypeError, IndexError) as e:
            return self.send_json({'error': str(e)}, 400)
        self.send_json({'error': '未找到'}, 404)

    def do_DELETE(self):
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
    address = 'http://127.0.0.1:8765'
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('SurveyJar 已启动：' + address + '\n关闭此窗口即可停止。数据保存在 ' + str(DB))
    webbrowser.open(address)
    server.serve_forever()
