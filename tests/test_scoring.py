import unittest
from copy import deepcopy
from scoring import score


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.survey = {'scoreVersion': 2, 'totalMethod': 'sum',
            'dimensions': [{'id': 'd', 'name': '示例维度', 'method': 'mean'}],
            'questions': [
                {'id': 'a', 'title': '正向', 'type': 'single', 'scoring': 'forward',
                 'dimensionId': 'd', 'options': [{'score': n} for n in [0, 1, 2, 3]]},
                {'id': 'b', 'title': '反向', 'type': 'single', 'scoring': 'forward',
                 'reverse': True, 'dimensionId': 'd', 'options': [{'score': n} for n in [0, 1, 2, 3]]}]}

    def test_raw_reverse_dimension_and_total(self):
        result, _ = score(self.survey, {'a': '2', 'b': '0'})
        self.assertEqual([d['rawScore'] for d in result['details']], [2, 0])
        self.assertEqual([d['score'] for d in result['details']], [2, 3])
        self.assertEqual(result['dimensions'][0]['score'], 2.5)
        self.assertEqual(result['total'], 5)

    def test_missing_not_zero_and_mean(self):
        result, _ = score(self.survey, {'a': '0'})
        self.assertIsNone(result['total'])
        self.assertIsNone(result['dimensions'][0]['score'])
        self.survey['totalMethod'] = 'mean'
        result, _ = score(self.survey, {'a': '0', 'b': '0'})
        self.assertEqual(result['total'], 1.5)

    def test_raw_mode_keeps_raw_but_no_aggregates(self):
        self.survey['scoreMode'] = 'raw'
        result, _ = score(self.survey, {'a': '2', 'b': '0'})
        self.assertEqual(result['details'][1]['rawScore'], 0)
        self.assertIsNone(result['details'][1]['score'])
        self.assertIsNone(result['total'])
        self.assertIsNone(result['dimensions'][0]['score'])

    def test_substance_followup(self):
        survey = {'questions': [{'id': 's', 'title': '烟草制品', 'type': 'substance', 'scoring': 'none', 'required': True}]}
        self.assertTrue(score(survey, {'s': {'used': 'yes', 'duration': ''}})[1])
        self.assertFalse(score(survey, {'s': {'used': 'yes', 'duration': '0.5'}})[1])
        answers = {'s': {'used': 'no', 'duration': '3'}}
        self.assertFalse(score(survey, answers)[1])
        self.assertEqual(answers['s']['duration'], '')
        with self.assertRaises(ValueError):
            score(survey, {'s': {'used': 'yes', 'duration': '-1'}})

    def test_legacy_reverse_preserved(self):
        s = deepcopy(self.survey)
        del s['scoreVersion']
        s['questions'][1].update(scoring='reverse', reverse=False)
        result, _ = score(s, {'a': '0', 'b': '0'})
        self.assertEqual(result['total'], 5)

    def test_single_and_multi_answer_shapes(self):
        for answer in (['0'], ['0', '1'], [], {}, True):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                score(self.survey, {'a': answer})
        self.survey['questions'][0]['type'] = 'multi'
        with self.assertRaises(ValueError):
            score(self.survey, {'a': '0'})
        self.assertEqual(score(self.survey, {'a': ['0', '1']})[0]['details'][0]['rawScore'], 1)
        self.assertIsNone(score(self.survey, {'a': []})[0]['details'][0]['rawScore'])


if __name__ == '__main__':
    unittest.main()
