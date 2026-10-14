import unittest
from import_questionnaire import Importer, parse_text

class TableReadingTests(unittest.TestCase):
    def test_numbered_choices_without_questionnaire_name(self):
        r = Importer('任意问卷')
        mode = r.table([['', '选择奖励方式'], ['1', '立即获得54美元', '117天后获得55美元'], ['2', '立即获得55美元', '61天后获得75美元']])
        self.assertEqual(mode, 'forced')
        q = r.finish()['surveys'][0]['questions'][0]
        self.assertEqual(q['options'][1]['label'], '117天后获得55美元')
        self.assertEqual(q['scoring'], 'none')
        self.assertEqual(q['choiceAttributes']['delayDays'], 117)

    def test_common_options_stay_matrix(self):
        r = Importer('量表')
        self.assertEqual(r.table([['题目', '从不', '总是'], ['1.我的状态', '0', '3']]), 'matrix')
        self.assertEqual(r.finish()['surveys'][0]['questions'][0]['options'][0]['score'], 0)

    def test_ambiguous_numeric_requires_choice(self):
        rows = [['题号', '选项A', '选项B'], ['1', '10', '20']]
        with self.assertRaises(ValueError):
            Importer('数字选项').table(rows)
        r = Importer('数字选项')
        self.assertEqual(r.table(rows, 'forced'), 'forced')

    def test_wrong_mode_does_not_guess(self):
        with self.assertRaises(ValueError):
            Importer('问卷').table([['', '合并标题'], ['1', '奖励甲', '奖励乙']], 'matrix')
        with self.assertRaises(ValueError):
            Importer('问卷').table([['1', '奖励甲', '奖励乙'], ['3', '奖励丙', '奖励丁']], 'forced')

    def test_pasted_numbered_rows(self):
        r = parse_text('题号\t选项 A\t选项 B\n1\t立即获得54美元\t117天后获得55美元')
        self.assertEqual(r['readingLabel'], '迫选题表格')

if __name__ == '__main__':
    unittest.main()
