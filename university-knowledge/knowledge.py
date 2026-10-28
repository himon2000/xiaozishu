"""Read-only, source-backed university graph. No app DB, LLM, or Semantica UI dependency."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

LABELS = {'has_school':'设有学院','offers':'开设专业','jointly_offers':'联合培养',
          'lists_course':'课程介绍列示','has_specialization':'专修方向','publishes':'发布政策',
          'lists_major':'政策列示专业','lists_project':'官网列示科研项目','lists_platform':'官网列示科研平台'}
TOPICS = {'all':None,'admissions':{'Major','Specialization','AdmissionPolicy','AdmissionPlan','AdmissionResult'},
          'teaching':{'Major','Course','Specialization','ProgramVersion','CourseOffering'},
          'research':{'ResearchPlatform','ResearchProject','Person','Publication'}}
PROVINCES = '广东 浙江 上海 山东 福建 江苏 北京 天津 河北 河南 湖北 湖南 安徽 江西 四川 重庆 云南 贵州 广西 海南 辽宁 吉林 黑龙江 陕西 山西 甘肃 青海 宁夏 新疆 西藏 内蒙古'.split()
CAVEATS = ['未收录不代表该校没有该项。','招生政策不等于招生人数计划、报名资格或录取概率。',
           '课程介绍适用年级待核验；科研项目负责人、经费和当前状态未公开。']

class KnowledgeGraph:
    def __init__(self, path):
        raw=Path(path).read_bytes()
        data=json.loads(raw)
        self.version=hashlib.sha256(raw).hexdigest()[:16]
        self.nodes={}
        for n in data['nodes']:
            props={**n.get('metadata',{}),**n.get('properties',{})}
            if props.get('visibility')!='public':
                raise ValueError('Only reviewed public university data may be deployed')
            self.nodes[n['id']]={'id':n['id'],'type':n['type'],'name':n.get('content') or props.get('content',''), 'properties':props}
        if len(self.nodes)!=len(data['nodes']):
            raise ValueError('Duplicate node IDs')
        self.edges=data['edges']
        for e in self.edges:
            if e['source'] not in self.nodes or e['target'] not in self.nodes:
                raise ValueError('Dangling graph relationship')
            if not self.evidence(e):
                raise ValueError('Relationship without evidence')
        for n in list(self.nodes.values())+self.edges:
            ids=self.evidence(n)
            if n.get('type')!='SourceDocument' and not ids:
                raise ValueError('Public fact without evidence')
            for identifier in ids:
                source=self.nodes.get(identifier,{})
                if source.get('type')!='SourceDocument':
                    raise ValueError('Missing source document')
        for n in self.nodes.values():
            if n['type']=='SourceDocument':
                p=urlparse(n['properties'].get('url',''))
                if p.scheme!='https' or not p.hostname or not p.hostname.endswith(('.edu.cn','.edu.hk')):
                    raise ValueError('Expected an official university HTTPS source')

    @staticmethod
    def evidence(item):
        return list(dict.fromkeys(item.get('metadata',{}).get('evidence_ids',[])+item.get('properties',{}).get('evidence_ids',[])))

    def schools(self):
        return [{'name':n['name'],'id':n['id'],'alias':n['properties'].get('aliases',[]),
                 'location':n['properties'].get('campus',''),'knowledge_available':True,
                 'data_status':'official_source_sample'} for n in self.nodes.values() if n['type']=='University']

    def resolve(self, school):
        key=school.strip().casefold()
        if not key:
            return None
        return next((s for s in self.schools() if key in [s['name'].casefold()]+[a.casefold() for a in s['alias']]),None)

    def scope(self, school):
        selected=self.resolve(school)
        if not selected:
            return set()
        ids={selected['id']}
        while True:
            targets={e['target'] for e in self.edges if e['source'] in ids and self.nodes[e['target']]['type']!='SourceDocument'}
            if targets<=ids:
                return ids
            ids |= targets

    def sources(self, objects):
        ids={x for item in objects for x in self.evidence(item)}
        return [{'id':n['id'],'title':n['name'],'url':n['properties']['url'],
                 'locator':n['properties'].get('locator',''),'reviewed_on':n['properties'].get('retrieved_on',''),
                 'source_type':'official'} for n in self.nodes.values() if n['id'] in ids and n['type']=='SourceDocument']

    def catalog(self, school, topic='all', query='', year=None, province=''):
        ids=self.scope(school)
        allowed=TOPICS[topic]
        result=[n for n in self.nodes.values() if n['id'] in ids and (not allowed or n['type'] in allowed)
                and (not query or query.casefold() in json.dumps(n,ensure_ascii=False).casefold())]
        if year or province:
            policies=[n for n in result if n['type'] in {'AdmissionPolicy','AdmissionPlan','AdmissionResult'}
                      and (not year or str(n['properties'].get('year'))==str(year))
                      and (not province or province in n['properties'].get('provinces',[]))]
            eligible={n['id'] for n in policies}
            eligible|={e['target'] for e in self.edges if e['source'] in eligible and e['type']=='lists_major'}
            result=[n for n in result if n['id'] in eligible]
        selected={n['id'] for n in result}
        edges=[e for e in self.edges if e['source'] in selected and e['target'] in selected]
        return {'nodes':result,'edges':edges,'sources':self.sources(result+edges),'total':len(result),
                'graph_version':self.version,'caveats':CAVEATS}

    def answer(self, question, school_name=''):
        mentioned=[s for s in self.schools() if any(a.casefold() in question.casefold() for a in [s['name']]+s['alias'])]
        selected=self.resolve(school_name) if school_name else (mentioned[0] if len(mentioned)==1 else None)
        reason=''
        if school_name and not selected:
            reason='该高校尚未接入已核验的公开图谱。'
        elif not selected:
            reason='请选择已接入高校，再查询专业、课程、招生政策或科研项目。'
        elif mentioned and any(s['id']!=selected['id'] for s in mentioned):
            reason='问题中的高校与所选高校不一致，请分别查询。'
        elif selected and '大学' in question and not any(a.casefold() in question.casefold() for a in [selected['name']]+selected['alias']):
            reason='问题中出现了未确认的高校名称，请核对所选高校并使用完整名称，不能将其他高校的事实混用。'
        q=question.strip()
        ids=self.scope(selected['name']) if selected else set()
        scoped=[n for n in self.nodes.values() if n['id'] in ids]
        years=re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)',q)
        provinces=[p for p in PROVINCES if p in q]
        rels=set()
        if any(x in q for x in ['招生','综合评价','录取','选科']):
            rels={'lists_major'}
        elif any(x in q for x in ['科研项目','科研','项目','实验室','平台']):
            if '项目' in q or '科研' in q: rels.add('lists_project')
            if '实验室' in q or '平台' in q: rels.add('lists_platform')
        else:
            if '课程' in q or '学什么' in q: rels.add('lists_course')
            if '方向' in q: rels.add('has_specialization')
            if not rels and any(x in q for x in ['专业','学院','概况']): rels={'offers','jointly_offers','has_school'}
        if any(x in q for x in ['负责人','经费','成绩','实时','录取概率','分数','位次','任课','先修']):
            reason=reason or '当前图谱未收录该项问题所需的负责人、经费、成绩、任课或录取统计，无法确认。'
        if any(x in q for x in ['选科','学费','住宿费','报名条件','报名资格','报名时间','截止']):
            reason=reason or '当前图谱未收录足够的选科、收费或报名条件与时间信息，请核验当年完整官网通知。'
        if any(x in q for x in ['招生计划','招生人数','名额']):
            reason=reason or '当前图谱未收录具体招生人数计划，已收录的招生政策不能替代招生计划。'
        if len(set(years))>1 or len(provinces)>1:
            reason=reason or '请一次查询一个年份和一个省份，避免混用招生口径。'
        if years and rels and 'lists_major' not in rels:
            reason=reason or '当前课程或科研资料未标明该年份的适用范围，无法作为指定年份的事实返回。'
        candidates=[e for e in self.edges if e['source'] in ids and e['target'] in ids and e['type'] in rels]
        if 'lists_major' in rels:
            candidates=[e for e in candidates if (not years or str(self.nodes[e['source']]['properties'].get('year'))==years[0])
                        and (not provinces or provinces[0] in self.nodes[e['source']]['properties'].get('provinces',[]))]
            requested_types=[t for t in ['普通高考','普通批','强基计划','保送','自主招生','艺术类','音乐类','国际招生','综合评价'] if t in q]
            if requested_types:
                candidates=[e for e in candidates if all(t==self.nodes[e['source']]['properties'].get('admission_type') for t in requested_types)]
        anchors=[n for n in scoped if n['type'] not in {'University','School'} and n['name'] and n['name'] in q]
        if anchors:
            longest=max(len(n['name']) for n in anchors)
            anchor_ids={n['id'] for n in anchors if len(n['name'])==longest}
            candidates=[e for e in candidates if e['source'] in anchor_ids or e['target'] in anchor_ids]
        if not rels:
            reason=reason or '当前规则检索暂不支持该问题，请查询专业课程、专修方向、招生政策或公开科研项目。'
        if reason:
            candidates=[]
        source_objects=candidates+[self.nodes[e['source']] for e in candidates]+[self.nodes[e['target']] for e in candidates]
        sources=self.sources(source_objects)
        facts=[{'source':self.nodes[e['source']]['name'],'relation':LABELS.get(e['type'],e['type']),
                'target':self.nodes[e['target']]['name'],'evidence_ids':self.evidence(e)} for e in candidates]
        lines=[f"{selected['name']} · 官网知识图谱" if selected else '高校知识图谱']
        if facts:
            lines += [f"• {f['source']} → {f['relation']} → {f['target']}" for f in facts]
        else:
            lines += [reason or '当前图谱未找到符合年份、省份及专业条件的记录。']
        lines += ['','本次为知识图谱规则检索，未调用语言模型。']
        return {'answer':'\n'.join(lines),'sources':sources,'facts':facts,
                'school_info':selected,'answer_mode':'knowledge_graph_rules','graph_version':self.version,
                'evidence_status':'supported' if facts else 'insufficient','caveats':CAVEATS,
                'suggestions':['数据科学与大数据技术有哪些课程？','2026年广东综合评价有哪些专业？','有哪些公开科研项目？']}
