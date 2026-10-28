"""Application-owned Q&A history. Knowledge retrieval belongs to the separate service."""
import json
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import text

logger=logging.getLogger(__name__)

def _ensure_table(db):
    # Compatible with both deployed MySQL and local SQLite; do not use SQLite datetime('now').
    db.execute(text('''CREATE TABLE IF NOT EXISTS qa_history (
        id VARCHAR(40) PRIMARY KEY, user_openid VARCHAR(128) NOT NULL,
        school_name VARCHAR(200) DEFAULT '', question TEXT NOT NULL, answer TEXT NOT NULL,
        sources TEXT, tokens_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''))

def save_qa_history(db,user_openid,school_name,question,answer,sources):
    record_id='QA'+uuid.uuid4().hex[:12].upper()
    created=datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        _ensure_table(db)
        db.execute(text('''INSERT INTO qa_history
            (id,user_openid,school_name,question,answer,sources,created_at)
            VALUES (:id,:user,:school,:question,:answer,:sources,:created)'''),
            {'id':record_id,'user':user_openid,'school':school_name,'question':question,'answer':answer,
             'sources':json.dumps(sources,ensure_ascii=False),'created':created})
        db.commit()
        return {'id':record_id,'created_at':created.isoformat()+'Z'}
    except Exception:
        db.rollback()
        logger.warning('School wiki history save failed',exc_info=True)
        return None

def get_qa_history(db,user_openid,limit=20):
    _ensure_table(db)
    rows=db.execute(text('''SELECT id,school_name,question,answer,sources,created_at
        FROM qa_history WHERE user_openid=:user ORDER BY created_at DESC,id DESC LIMIT :limit'''),
        {'user':user_openid,'limit':limit}).mappings().all()
    result=[]
    for row in rows:
        try:
            sources=json.loads(row['sources'] or '[]')
        except (ValueError,TypeError):
            sources=[]
        result.append({'id':row['id'],'school_name':row['school_name'],'question':row['question'],
                       'answer':row['answer'],'answer_preview':row['answer'][:100],
                       'sources':sources if isinstance(sources,list) else [],'created_at':str(row['created_at'])})
    return result
