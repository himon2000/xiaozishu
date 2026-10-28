"""Gateway integration tests: only a temporary in-memory user history database is used."""
import os
os.environ.update(WECHAT_APPID='test-app',WECHAT_SECRET='test-secret',JWT_SECRET='unit-test-only-secret',DATABASE_URL='sqlite://')
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'university-knowledge'))
from service import app as knowledge_app
from routers import school_wiki
from services import university_knowledge_client as gateway
from services.school_wiki_service import save_qa_history,get_qa_history

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        self.db=sessionmaker(bind=self.engine)()
        self.upstream=TestClient(knowledge_app)
        self.upstream.__enter__()
        self.app=FastAPI()
        self.app.include_router(school_wiki.router)
        self.app.dependency_overrides[school_wiki.get_db]=lambda:self.db
        self.app.dependency_overrides[school_wiki.get_current_user_optional]=lambda:SimpleNamespace(openid='user-a')
        self.app.dependency_overrides[school_wiki.get_current_user]=lambda:SimpleNamespace(openid='user-a')
        self.client=TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.upstream.__exit__(None,None,None)
        self.db.close()
        self.engine.dispose()

    def proxy(self,path,method='GET',payload=None,params=None):
        self.assertNotIn('openid',json.dumps(payload or {}))
        response=self.upstream.request(method,path,json=payload,params=params)
        response.raise_for_status()
        return response.json()

    def test_miniapp_gateway_history_and_public_fact_contract(self):
        with patch.object(school_wiki,'knowledge_request',side_effect=self.proxy):
            schools=self.client.get('/api/v1/school-wiki/schools').json()['data']['schools']
            self.assertEqual(len(schools),1)
            response=self.client.post('/api/v1/school-wiki/ask',json={
                'question':'数据科学与大数据技术有哪些课程？','school_name':schools[0]['name']})
            self.assertEqual(response.status_code,200)
            data=response.json()['data']
            self.assertEqual(data['evidence_status'],'supported')
            self.assertTrue(data['history_saved'])
            self.assertTrue(data['sources'])
            history=self.client.get('/api/v1/school-wiki/history').json()['data']['records']
            self.assertEqual(history[0]['answer'],data['answer'])
            self.assertEqual(history[0]['sources'],data['sources'])
            self.assertTrue(history[0]['created_at'])
            graph=self.client.get('/api/v1/school-wiki/knowledge',params={'school_name':schools[0]['name'],'topic':'teaching'}).json()['data']
            self.assertTrue(any(n['type']=='Course' for n in graph['nodes']))
            self.assertEqual(self.client.post('/api/v1/school-wiki/ask',json={'question':' '*4}).status_code,422)

    def test_history_is_user_scoped_and_legacy_sources_tolerated(self):
        save_qa_history(self.db,'user-a','A','q','answer',[])
        save_qa_history(self.db,'user-b','B','q2','private answer',[])
        self.assertEqual(len(get_qa_history(self.db,'user-a')),1)
        self.assertEqual(get_qa_history(self.db,'no-user'),[])

    def test_unconfigured_and_failed_upstream_never_fall_back_to_templates(self):
        settings=SimpleNamespace(university_kg_url='',university_kg_service_token='',university_kg_timeout=1)
        with patch.object(gateway,'get_settings',return_value=settings):
            with self.assertRaises(HTTPException) as error:gateway.knowledge_request('/v1/schools')
            self.assertEqual(error.exception.status_code,503)
        settings.university_kg_url='http://independent-knowledge'
        with patch.object(gateway,'get_settings',return_value=settings),patch.object(gateway.httpx,'Client') as factory:
            factory.return_value.__enter__.return_value.request.side_effect=httpx.ReadTimeout('no service')
            with self.assertRaises(HTTPException) as error:gateway.knowledge_request('/v1/ask','POST',{'question':'test'})
            self.assertEqual(error.exception.status_code,504)

if __name__=='__main__':unittest.main()
