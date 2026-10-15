import gc
import io
import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import server


class ServerValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(gc.collect)
        self.db_patch = patch.object(server, 'DB', Path(self.temp.name) / 'test.sqlite3')
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        server.init_db()
        self.survey = {'title': '测试问卷', 'scoreVersion': 2, 'questions': [
            {'id': 'q1', 'title': '单选', 'type': 'single', 'required': True,
             'scoring': 'forward', 'options': [{'label': '甲', 'score': 1}, {'label': '乙', 'score': 2}]}]}

    def post(self, path, body, **headers):
        handler = object.__new__(server.Handler)
        handler.path = '/api/' + path
        handler.server = SimpleNamespace(server_port=8765)
        handler.rfile = io.BytesIO(json.dumps(body).encode())
        handler.headers = Message()
        for name, value in {'Host': '127.0.0.1:8765', 'Content-Type': 'application/json',
                            'Content-Length': str(len(handler.rfile.getvalue())), **headers}.items():
            handler.headers[name] = value
        result = []
        handler.send_json = lambda data, status=200: result.append((status, data))
        handler.do_POST()
        return result[0]

    def test_invalid_surveys_are_not_stored(self):
        bad_id = deepcopy(self.survey)
        bad_id['questions'][0]['id'] = 'q"><img src=x onerror=alert(1)>'
        duplicate = deepcopy(self.survey)
        duplicate['questions'].append(deepcopy(duplicate['questions'][0]))
        bad_options = deepcopy(self.survey)
        bad_options['questions'][0]['options'] = []
        for body in ({}, {'title': '空问卷', 'questions': []}, bad_id, duplicate, bad_options):
            with self.subTest(body=body):
                self.assertEqual(self.post('surveys', body)[0], 400)
        with sqlite3.connect(server.DB) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM surveys').fetchone()[0], 0)

    def test_answer_shape_and_status_are_checked_before_storage(self):
        status, created = self.post('surveys', self.survey)
        self.assertEqual(status, 200)
        body = {'participant': 'S001', 'survey_id': created['id'], 'survey': self.survey, 'status': 'submitted', 'answers': {'q1': '0'}}
        for changes in ({'answers': {'q1': ['0', '1']}}, {'answers': {'q1': []}}, {'status': 'other'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post('responses', {**body, **changes})[0], 400)
        with sqlite3.connect(server.DB) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM responses').fetchone()[0], 0)
        status, saved = self.post('responses', body)
        self.assertEqual(status, 200)
        self.assertEqual(saved['result']['total'], 1)
        self.assertEqual(self.post('responses', {**body, 'id': saved['id']})[0], 400)

    def test_client_cannot_replace_the_stored_question_type_or_draft_rules(self):
        sid = self.post('surveys', self.survey)[1]['id']
        forged = deepcopy(self.survey)
        forged['questions'][0]['type'] = 'multi'
        body = {'participant': 'S001', 'survey_id': sid, 'survey': forged, 'status': 'draft', 'answers': {'q1': ['0', '1']}}
        self.assertEqual(self.post('responses', body)[0], 400)
        body['answers'] = {'q1': '0'}
        rid = self.post('responses', body)[1]['id']
        changed = deepcopy(self.survey)
        changed['id'] = sid
        changed['questions'][0]['options'][0]['score'] = 99
        self.post('surveys', changed)
        status, submitted = self.post('responses', {**body, 'id': rid, 'status': 'submitted'})
        self.assertEqual(status, 200)
        self.assertEqual(submitted['result']['total'], 1)

    def test_distributed_templates_are_valid_survey_inputs(self):
        examples = server.ROOT / 'examples'
        surveys = [json.loads((examples / '问卷导入模板.json').read_text(encoding='utf-8'))]
        surveys += server.parse_text((examples / '问卷导入模板.txt').read_text(encoding='utf-8'))['surveys']
        for survey in surveys:
            with self.subTest(title=survey['title']):
                self.assertEqual(self.post('surveys', survey)[0], 200)

    def test_write_requests_reject_foreign_host_origin_and_plain_text(self):
        for headers in ({'Host': 'example.com:8765'}, {'Origin': 'https://example.com'},
                        {'Content-Type': 'text/plain'}):
            with self.subTest(headers=headers):
                self.assertIn(self.post('surveys', self.survey, **headers)[0], (403, 415))
        self.assertEqual(self.post('surveys', self.survey, Origin='http://127.0.0.1:8765')[0], 200)

    def test_delete_requests_also_reject_foreign_origins(self):
        handler = object.__new__(server.Handler)
        handler.server = SimpleNamespace(server_port=8765)
        handler.headers = {'Host': '127.0.0.1:8765', 'Origin': 'https://example.com'}
        result = []
        handler.send_json = lambda data, status=200: result.append(status)
        handler.do_DELETE()
        self.assertEqual(result, [403])

    def test_participant_required_on_submission_but_not_draft(self):
        sid = self.post('surveys', self.survey)[1]['id']
        body = {'survey_id': sid, 'status': 'submitted', 'answers': {'q1': '0'}}
        for participant in (None, '', '   '):
            status, result = self.post('responses', {**body, 'participant': participant})
            self.assertEqual(status, 400)
            self.assertEqual(result['error'], '请填写被试编号')
        status, draft = self.post('responses', {**body, 'status': 'draft'})
        self.assertEqual(status, 200)
        self.assertEqual(self.post('responses', {**body, 'id': draft['id'], 'participant': ' S001 '})[0], 200)
        with sqlite3.connect(server.DB) as db:
            stored = json.loads(db.execute('SELECT body FROM responses WHERE id=?', (draft['id'],)).fetchone()[0])
        self.assertEqual(stored['participant'], 'S001')

    def test_batch_responses_inherit_participant(self):
        sid = self.post('surveys', self.survey)[1]['id']
        pid = self.post('projects', {'name': '测试项目', 'surveyIds': [sid]})[1]['id']
        bid = self.post('batches', {'projectId': pid, 'participant': 'S002'})[1]['id']
        status, saved = self.post('responses', {'survey_id': sid, 'batchId': bid, 'batchIndex': 0,
                                               'status': 'submitted', 'answers': {'q1': '0'}})
        self.assertEqual(status, 200)
        with sqlite3.connect(server.DB) as db:
            stored = json.loads(db.execute('SELECT body FROM responses WHERE id=?', (saved['id'],)).fetchone()[0])
        self.assertEqual(stored['participant'], 'S002')
