"""Read the distributed examples and check their expected scoring behavior."""
import json
import unittest
from pathlib import Path

from import_questionnaire import parse_text
from scoring import score


EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class ExampleTests(unittest.TestCase):
    def test_text_template_sections_and_reverse_scoring(self):
        parsed = parse_text((EXAMPLES / '问卷导入模板.txt').read_text(encoding='utf-8'))
        surveys = parsed['surveys']
        self.assertEqual([s['title'] for s in surveys],
                         ['横排问卷示例', '共用选项示例', '表格粘贴示例'])
        self.assertEqual([len(s['questions']) for s in surveys], [4, 2, 2])
        self.assertFalse(parsed.get('errors'))
        self.assertEqual([q['type'] for q in surveys[0]['questions']],
                         ['single', 'single', 'multi', 'text'])
        survey = surveys[1]
        answers = {q['id']: '0' for q in survey['questions']}
        result, missing = score(survey, answers)
        self.assertFalse(missing)
        self.assertEqual([d['score'] for d in result['details']], [0, 3])
        self.assertEqual(result['total'], 3)
        self.assertEqual([o['score'] for o in surveys[2]['questions'][0]['options']],
                         [0, 1, 2, 3])

    def test_json_template_custom_and_reverse_scoring(self):
        survey = json.loads((EXAMPLES / '问卷导入模板.json').read_text(encoding='utf-8'))
        self.assertEqual([q['type'] for q in survey['questions']],
                         ['single', 'scale', 'number', 'text'])
        self.assertEqual(len({q['id'] for q in survey['questions']}), 4)
        result, missing = score(survey, {'q1': '2', 'q2': '1', 'q3': '2', 'q4': '示例回答'})
        self.assertFalse(missing)
        self.assertEqual([d['score'] for d in result['details'][:3]], [5, 5, 3])
        self.assertEqual(result['total'], 13)
