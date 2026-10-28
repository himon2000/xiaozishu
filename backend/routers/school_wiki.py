"""小程序高校百科网关：图谱独立运维，用户身份和问答历史留在应用侧。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from dependencies import get_db, get_current_user, get_current_user_optional
from services.university_knowledge_client import knowledge_request
from services.school_wiki_service import save_qa_history, get_qa_history

router=APIRouter(prefix='/api/v1/school-wiki',tags=['高校百科'])

class AskRequest(BaseModel):
    question:str=Field(min_length=1,max_length=1000)
    school_name:str=Field(default='',max_length=100)

@router.get('/schools')
def school_list():
    return {'code':0,'data':knowledge_request('/v1/schools')}

@router.get('')
def school_wiki_index():
    return school_list()

@router.get('/search')
def search_school_api(keyword:str=Query(...,min_length=1,max_length=100)):
    data=knowledge_request('/v1/schools')
    key=keyword.strip().casefold()
    matches=[s for s in data['schools'] if key and any(key in x.casefold() for x in [s['name']]+s.get('alias',[]))]
    return {'code':0,'data':{'found':bool(matches),'school':matches[0] if matches else None,
                           'schools':matches,'suggestions':[s['name'] for s in data['schools']]}}

@router.get('/knowledge')
def knowledge(school_name:str=Query(...,max_length=100),topic:str='all',q:str=Query('',max_length=200),
              year:int|None=Query(None,ge=1900,le=2100),province:str=Query('',max_length=20)):
    params={'school_name':school_name,'topic':topic,'q':q,'province':province}
    if year is not None:
        params['year']=year
    return {'code':0,'data':knowledge_request('/v1/knowledge',params=params)}

@router.post('/ask')
def ask_question(payload:AskRequest,db:Session=Depends(get_db),current_user=Depends(get_current_user_optional)):
    if not payload.question.strip():
        raise HTTPException(422,'请输入问题')
    # Only public query text and the selected school cross the service boundary.
    result=knowledge_request('/v1/ask',method='POST',payload={
        'question':payload.question.strip(),'school_name':payload.school_name})
    result['history_saved']=False
    if current_user:
        record=save_qa_history(db,current_user.openid,
            (result.get('school_info') or {}).get('name',payload.school_name),
            payload.question,result['answer'],result.get('sources',[]))
        result['history_saved']=record is not None
    return {'code':0,'data':result}

@router.get('/history')
def history(db:Session=Depends(get_db),current_user=Depends(get_current_user),limit:int=Query(20,ge=1,le=50)):
    records=get_qa_history(db,current_user.openid,limit)
    return {'code':0,'data':{'records':records,'total':len(records)}}

@router.get('/detail/{school_name}')
def school_detail(school_name:str):
    data=knowledge_request('/v1/schools')
    school=next((s for s in data['schools'] if school_name in [s['name']]+s.get('alias',[])),None)
    if not school:
        raise HTTPException(404,'该高校尚未接入知识图谱')
    graph=knowledge_request('/v1/knowledge',params={'school_name':school['name']})
    return {'code':0,'data':{'school':school,'knowledge':graph,'resources':[],'wiki_count':graph['total']}}
