import unittest
from copy import deepcopy
from reporting import wide_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.survey = {'id': 1, 'title': 'BIS示例', 'scoreVersion': 2, 'dimensions': [{'id':'d','name':'维度一','method':'sum'}],
                       'questions':[{'id':'q','title':'题干','type':'single','scoring':'custom','reverse':True,'dimensionId':'d',
                                     'options':[{'label':str(n),'score':n} for n in range(1,6)]}]}
        self.response = {'id':1,'survey_id':1,'status':'submitted','survey':self.survey,'answers':{'q':'0'},
                         'participant':'S001','projectName':'项目','projectId':1,'batchId':1,'batchSurveyIds':[1,2]}

    def test_reverse_all_five_values(self):
        for choice in range(5):
            r=deepcopy(self.response);r['answers']['q']=str(choice)
            report=wide_report([r],[self.survey],{'surveyIds':[1]})
            self.assertEqual(report['rows'][0][5:],[choice+1,5-choice,5-choice,5-choice])
            self.assertFalse(any('题目ID' in h or '题型' in h for h in report['headers']))

    def test_merge_batch_and_separate_repeated_participant(self):
        b=deepcopy(self.response);b.update(id=2,survey_id=2);b['survey']['id']=2;b['survey']['title']='问卷二'
        c=deepcopy(self.response);c.update(id=3,batchId=2)
        report=wide_report([c,b,self.response],[self.survey],{'surveyIds':[1,2]})
        self.assertEqual(len(report['rows']),2)
        self.assertEqual(report['rows'][0][3],'已提交')
        self.assertEqual(report['rows'][1][3],'部分问卷未完成')

    def test_current_rules_never_overwrite_raw_or_snapshot(self):
        current=deepcopy(self.survey);current['questions'][0]['reverse']=False
        current['questions'][0]['options'][0]['score']=99
        before=deepcopy(self.response)
        result=wide_report([self.response],[current],{'surveyIds':[1],'basis':'current'})
        self.assertEqual(result['rows'][0][5:],[1,1,1])
        self.assertEqual(self.response,before)

    def test_empty_filter_and_drafts(self):
        r=deepcopy(self.response);r['status']='draft'
        with self.assertRaises(ValueError):wide_report([r],[],{'surveyIds':[1]})
        report=wide_report([r],[],{'surveyIds':[1],'includeDrafts':True})
        self.assertEqual(len(report['rows']),1)


if __name__ == '__main__':unittest.main()
