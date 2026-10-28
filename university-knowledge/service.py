"""Independently deployable university knowledge API. No end-user identifiers accepted."""
import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from knowledge import KnowledgeGraph, TOPICS

@asynccontextmanager
async def lifespan(app):
    path=os.environ.get('UNIVERSITY_GRAPH_PATH',str(Path(__file__).parent/'data/university_graph.json'))
    app.state.graph=KnowledgeGraph(path)
    yield

app=FastAPI(title='高校知识图谱独立服务',version='1.0.0',lifespan=lifespan)
def authorize(x_knowledge_token: str=Header(default='')):
    expected=os.environ.get('UNIVERSITY_KG_SERVICE_TOKEN','')
    if expected and not hmac.compare_digest(expected,x_knowledge_token):
        raise HTTPException(401,'知识服务认证失败')

class AskRequest(BaseModel):
    question:str=Field(min_length=1,max_length=1000)
    school_name:str=Field(default='',max_length=100)

@app.get('/health')
def health():
    return {'status':'ok','service':'university-knowledge','graph_version':app.state.graph.version,
            'nodes':len(app.state.graph.nodes),'edges':len(app.state.graph.edges),'mode':'knowledge_graph_rules'}

@app.get('/v1/schools',dependencies=[Depends(authorize)])
def schools():
    items=app.state.graph.schools()
    return {'schools':items,'total':len(items),'graph_version':app.state.graph.version,'answer_mode':'knowledge_graph_rules'}

@app.get('/v1/knowledge',dependencies=[Depends(authorize)])
def catalog(school_name:str=Query(...,max_length=100),topic:str='all',q:str=Query('',max_length=200),
            year:int|None=Query(None,ge=1900,le=2100),province:str=Query('',max_length=20)):
    if topic not in TOPICS:
        raise HTTPException(422,'不支持的知识分类')
    return app.state.graph.catalog(school_name,topic,q,year,province)

@app.post('/v1/ask',dependencies=[Depends(authorize)])
def ask(body:AskRequest):
    if not body.question.strip():
        raise HTTPException(422,'请输入问题')
    return app.state.graph.answer(body.question,body.school_name)
