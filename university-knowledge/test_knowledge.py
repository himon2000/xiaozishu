import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from knowledge import KnowledgeGraph
from service import app

ROOT=Path(__file__).parent
SCHOOL='香港中文大学（深圳）'

class KnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=KnowledgeGraph(ROOT/'data/university_graph.json')

    def test_official_course_and_track_evidence(self):
        result=self.graph.answer('数据科学与大数据技术有哪些课程和方向？',SCHOOL)
        self.assertEqual(result['evidence_status'],'supported')
        self.assertIn('机器学习',result['answer'])
        self.assertIn('计算方向',result['answer'])
        self.assertTrue(result['sources'])
        self.assertTrue(all(s['url'].startswith('https://') and s['locator'] for s in result['sources']))

    def test_year_isolation_and_not_plan(self):
        for year in [2006,2027]:
            result=self.graph.answer(f'{year}年广东综合评价有哪些专业？',SCHOOL)
            self.assertEqual(result['facts'],[])
        result=self.graph.answer('2026年广东招生计划人数',SCHOOL)
        self.assertEqual(result['evidence_status'],'insufficient')
        self.assertIn('不能替代',result['answer'])

    def test_province_and_admission_semantics(self):
        self.assertEqual(self.graph.answer('2026年北京综合评价招生专业',SCHOOL)['facts'],[])
        self.assertIn('统计学',self.graph.answer('2026年广东综合评价招生专业',SCHOOL)['answer'])
        self.assertEqual(self.graph.answer('比较2026和2027年广东招生专业',SCHOOL)['facts'],[])
        self.assertEqual(self.graph.answer('2026年广东普通高考招生专业',SCHOOL)['facts'],[])
        self.assertEqual(self.graph.answer('2026年报名资格和选科要求',SCHOOL)['facts'],[])
        self.assertEqual(self.graph.answer('2006年科研项目有哪些？',SCHOOL)['facts'],[])

    def test_no_school_substitution(self):
        self.assertEqual(self.graph.answer('复旦大学有什么课程？',SCHOOL)['facts'],[])
        self.assertEqual(self.graph.answer('有哪些课程？','复旦大学')['facts'],[])
        self.assertEqual(self.graph.answer('有什么课程？')['facts'],[])
        self.assertEqual(self.graph.answer('数据科学与大数据技术有哪些课程？','港中深')['evidence_status'],'supported')

    def test_no_missing_pi_or_model_invention(self):
        for question in ['项目负责人是谁？','录取概率多少？','今天天气怎么样？']:
            result=self.graph.answer(question,SCHOOL)
            self.assertEqual(result['facts'],[])
            self.assertEqual(result['answer_mode'],'knowledge_graph_rules')

    def test_typed_catalog_and_year_filter(self):
        records=self.graph.catalog(SCHOOL,'research')
        self.assertTrue(records['nodes'])
        self.assertFalse(any(n['type']=='Course' for n in records['nodes']))
        self.assertEqual(self.graph.catalog(SCHOOL,'admissions',year=2006)['total'],0)

    def test_fail_closed_invalid_evidence_and_private_data(self):
        original=json.loads((ROOT/'data/university_graph.json').read_text(encoding='utf-8'))
        for kind in ['private','evidence']:
            data=json.loads(json.dumps(original))
            if kind=='private': data['nodes'][0]['metadata']['visibility']='internal'
            else: data['edges'][0]['metadata']['evidence_ids']=['missing-source']
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'graph.json'
                path.write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaises(ValueError): KnowledgeGraph(path)

    def test_standalone_service_auth_validation_and_health(self):
        with patch.dict(os.environ,{'UNIVERSITY_KG_SERVICE_TOKEN':'test-only-secret'}),TestClient(app) as client:
            self.assertEqual(client.get('/health').status_code,200)
            self.assertEqual(client.get('/v1/schools').status_code,401)
            headers={'X-Knowledge-Token':'test-only-secret'}
            self.assertEqual(client.get('/v1/schools',headers=headers).json()['total'],1)
            self.assertEqual(client.post('/v1/ask',headers=headers,json={'question':' '}).status_code,422)
            self.assertEqual(client.post('/v1/ask',headers=headers,json={'question':'x'*1001}).status_code,422)
            self.assertEqual(client.post('/v1/ask',headers=headers,json={'question':'有哪些课程？','school_name':SCHOOL}).status_code,200)
            self.assertEqual(client.get('/v1/knowledge',headers=headers,params={'school_name':SCHOOL,'topic':'invalid'}).status_code,422)

if __name__=='__main__': unittest.main()
