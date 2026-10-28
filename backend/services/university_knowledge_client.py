"""Fixed-route server-to-server gateway; never connects the phone to desktop localhost."""
import httpx
from fastapi import HTTPException
from config import get_settings

def knowledge_request(path, method='GET', payload=None, params=None):
    settings=get_settings()
    if not settings.university_kg_url:
        raise HTTPException(503,'高校知识图谱服务尚未配置，请稍后重试')
    headers={}
    if settings.university_kg_service_token:
        headers['X-Knowledge-Token']=settings.university_kg_service_token
    try:
        with httpx.Client(timeout=settings.university_kg_timeout,trust_env=False) as client:
            response=client.request(method,settings.university_kg_url.rstrip('/')+path,
                                    headers=headers,json=payload,params=params)
            response.raise_for_status()
            result=response.json()
            if not isinstance(result,dict):
                raise ValueError('Invalid knowledge response')
            return result
    except httpx.TimeoutException:
        raise HTTPException(504,'高校知识图谱查询超时，请稍后重试') from None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code==422:
            raise HTTPException(422,'知识查询条件不符合要求') from None
        raise HTTPException(503,'高校知识图谱服务暂时不可用') from None
    except (httpx.HTTPError,ValueError):
        raise HTTPException(503,'高校知识图谱服务暂时不可用') from None
