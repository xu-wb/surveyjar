import io
import unittest
from zipfile import ZipFile

from import_questionnaire import parse_docx, parse_text
from scoring import score
from reporting import wide_report


class StructureTests(unittest.TestCase):
    def test_mixed_text_keeps_forms_and_matrix_in_one_survey(self):
        s = parse_text('【混合问卷】\n项目 | 内容\n姓名 |\n\n题目 | 从不 | 总是\n心情平静 | 0 | 3', mode='mixed')['surveys'][0]
        self.assertEqual([q['type'] for q in s['questions']], ['text', 'single'])
        self.assertEqual(s['questions'][1]['options'][1]['score'], 3)

    def test_explicit_independent_does_not_consume_first_question_as_header(self):
        result = parse_text('【问卷甲】\n喜欢的颜色 | 红 | 蓝\n【问卷乙】\n活动 | 阅读=0 | 散步=1 | 运动=2', mode='independent')
        self.assertEqual(len(result['surveys']), 2)
        self.assertEqual(result['surveys'][0]['questions'][0]['title'], '喜欢的颜色')
        self.assertEqual(result['surveys'][1]['questions'][0]['options'][2]['score'], 2)

    def test_form_groups_preserve_independent_answers_and_export(self):
        s = parse_text('物质使用 | 使用时长（年）\n烟草 |\n酒精 |', mode='form')['surveys'][0]
        a, b = s['questions']
        self.assertEqual(a['groupId'], b['groupId'])
        self.assertNotEqual(a['id'], b['id'])
        answers = {a['id']: {'used': 'no'}, b['id']: {'used': 'yes', 'duration': 2}}
        _, missing = score(s, answers)
        self.assertEqual(missing, [])
        r = {'id': 1, 'survey_id': 1, 'status': 'submitted', 'survey': s, 'answers': answers}
        report = wide_report([r], [], {'surveyIds': [1]})
        self.assertIn('物质使用 / 烟草', str(report))
        self.assertIn('物质使用 / 酒精', str(report))

    def test_docx_default_and_per_table_override(self):
        xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>'
        for row in [('问题一', '甲', '乙'), ('问题二', '丙', '丁')]:
            xml += '<w:tr>' + ''.join('<w:tc><w:p><w:r><w:t>'+cell+'</w:t></w:r></w:p></w:tc>' for cell in row) + '</w:tr>'
        xml += '</w:tbl></w:body></w:document>'
        data = io.BytesIO()
        with ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', xml)
        for kwargs in ({'mode': 'independent'}, {'mode': 'matrix', 'overrides': {'0': 'independent'}}):
            result = parse_docx(data.getvalue(), **kwargs)
            self.assertFalse(result['errors'])
            self.assertEqual(len(result['surveys'][0]['questions']), 2)

    def test_forced_three_choose_two_scoring_and_export(self):
        s = parse_text('题号 | 选项甲 | 选项乙 | 选项丙\n1 | 甲 | 乙 | 丙', mode='forced')['surveys'][0]
        q = s['questions'][0]
        q['chooseCount'] = 2
        answers = {q['id']: ['0', '2']}
        self.assertEqual(score(s, answers)[1], [])
        self.assertTrue(score(s, {q['id']: ['0']})[1])
        self.assertTrue(score(s, {q['id']: ['0', '1', '2']})[1])
        with self.assertRaises(ValueError):
            score(s, {q['id']: ['0', '0']})
        with self.assertRaises(ValueError):
            score(s, {q['id']: ['0', '9']})
        r = {'id': 1, 'survey_id': 1, 'status': 'submitted', 'survey': s, 'answers': answers}
        self.assertIn('1、3', str(wide_report([r], [], {'surveyIds': [1]})))
        s.update(scoreMode='auto', scoreVersion=2)
        q['scoring'] = 'custom'
        for option, points in zip(q['options'], [1, 3, 5]):
            option['score'] = points
        self.assertEqual(score(s, answers)[0]['total'], 6)

    def test_binary_choice_backwards_compatible(self):
        s = parse_text('1 | 甲 | 乙', mode='forced')['surveys'][0]
        q = s['questions'][0]
        self.assertEqual(score(s, {q['id']: '1'})[1], [])
        with self.assertRaises(ValueError):
            score(s, {q['id']: ['1']})


if __name__ == '__main__':
    unittest.main()
