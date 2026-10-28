# 高校知识图谱独立服务

此模块拥有独立的API、Docker镜像、依赖、数据、健康检查和发布周期。它不依赖小紫薯数据库、用户身份、微信SDK或本机8027工作台进程。小紫薯只调用固定的只读接口；不读取本目录数据，不向知识服务发送openid、令牌或历史会话。

当前检索为确定性规则，不调用语言模型。对话中的“AI”沿用产品模块名称，页面明确显示实际模式。没有模型密钥或调用费用。

## 与 Semantica 工作台的边界

- Semantica 高校工作台（原8027）：用于本体建模、图谱编辑及人工核验。
- 本模块（本地8028，容器8080）：发布经审核的公开图谱快照，为小程序提供查询服务。小程序不能访问工作台管理/编辑接口。
- 小紫薯后端：鉴别用户、转发查询、保存问答及来源。小程序仍通过现有微信云托管调用应用后端。
- 服务可独立扩容、更新及回滚。其离线只影响高校百科，不应影响小紫薯其他模块；请求超时8秒，可通过后端配置调整。

本模块没有复制Semantica实现代码，也不要求安装其完整依赖；采用同一nodes/edges图谱数据和OWL高校本体。后续可在本服务内部替换检索/存储，保持`/v1`契约不变。

## 数据及版本

`data/university_ontology.ttl`：高校本体，27类、25个对象属性、18个数据属性。

`data/university_graph.json`：首批人工核验的香港中文大学（深圳）公开样例，25个业务对象、5个官网来源、30条业务关系及25条来源关系。核验日期2026-10-26；不是高校全量数据或最新招生承诺。目前没有录取分数位次、具体招生计划人数、教师任课、成绩、课表、项目经费或当前审批状态。

数据不含本机路径、账号或内部记录。学校列表由已收录图谱生成；原高校百科的未核验静态排名与模板回答不再作为官方事实。尚未接入的学校会显示未收录，不能用本校事实回答另一所学校的问题。

服务启动时验证公开可见性、节点唯一性、关系端点和来源引用。无有效证据或含内部数据时拒绝启动；不会以空图“健康”运行。`/health`返回图谱内容SHA256的前16位版本，升级后可核对实际载入版本。进程内使用不可变快照，更换数据需重启服务。

## 本地独立运行

```powershell
cd university-knowledge
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn service:app --host 127.0.0.1 --port 8028
```

或者在本目录执行 `docker compose up -d --build`，再访问 `http://127.0.0.1:8028/health`。Compose只启动知识服务，不启动或修改小紫薯后端。文件系统只读、数据目录只读、非root运行，日志轮转；默认只发布到宿主127.0.0.1。

## 对接应用后端

在小紫薯后端部署环境配置（不要写到小程序代码）：

| 环境变量 | 含义 |
|---|---|
| `UNIVERSITY_KG_URL` | 后端可访问的服务地址；本机开发为`http://127.0.0.1:8028` |
| `UNIVERSITY_KG_SERVICE_TOKEN` | 两个服务配置相同的服务间访问令牌；通过环境注入 |
| `UNIVERSITY_KG_TIMEOUT` | 后端查询超时秒数，默认8 |

服务间地址应使用部署环境的内网DNS/内部入口。两个独立Docker服务可加入同一个专用外部网络，通过`http://university-knowledge:8080`连接；云托管分别发布知识服务与应用服务，按平台规则配置服务间内网路由。容器里的127.0.0.1是其自身，不能填桌面8027/8028作为云端地址。

知识服务使用`UNIVERSITY_KG_SERVICE_TOKEN`验证`X-Knowledge-Token`。本机默认可留空；生产部署设置随机令牌并限制网络入口，不向小程序下发令牌。`/health`不需要令牌。应用后端未设置服务URL时返回503，超时返回504，服务异常返回503；不泄漏上游地址/令牌，也不回退到模板冒充图谱答案。

## API契约

| 接口 | 用途 |
|---|---|
| `GET /health` | 独立就绪状态、版本、节点/关系数 |
| `GET /v1/schools` | 已接入高校和别名 |
| `GET /v1/knowledge?school_name=...&topic=...` | all/admissions/teaching/research分类，支持q/year/province |
| `POST /v1/ask` | `{question, school_name}`，返回answer/facts/sources/caveats/graph_version/evidence_status |

小程序调用现有`/api/v1/school-wiki/*`网关，新增`GET /knowledge`。来源包括官网URL、页面定位和核验日期，小程序可复制来源链接。回答中的`evidence_status`区分supported与insufficient；`answer_mode=knowledge_graph_rules`不能解读成语言模型已连接。

## 发布与运维

1. 在Semantica编辑工作区核验新增事实，导出公开业务节点及其来源；不得直接发布带内部信息的完整工作区。
2. 更新本模块数据快照与OWL，并运行`python -m unittest -v test_knowledge`；失效来源、缺失年份/地区和未公开状态需明确记录，禁止推测填补。
3. 在独立服务的发布流水线构建镜像，记录镜像标签和graph_version。代码镜像与数据快照独立于应用后端发布。
4. 更换快照时先备份旧版本，再原子替换文件并重启本服务；检查`/health`和至少一个带来源的课程问题、一个未收录年份问题。
5. 监控容器健康、重启次数、错误率、响应耗时以及服务版本。Docker healthcheck标记异常，需由宿主/云平台告警策略通知运维；本仓库不声称已配置线上告警。
6. 回滚时恢复此前镜像及匹配的数据快照，仅重启知识服务；应用后端保持运行。不要删除旧快照或用户问答历史。

小紫薯后端自身发布时只需配置服务URL/令牌。用户问答历史留在应用数据库；失败时不伪报保存成功，匿名使用不保存。历史写入兼容MySQL和SQLite，查询严格按当前用户隔离。

## 验证命令

```powershell
# 独立服务目录，安装本模块依赖后
python -m pip install -r requirements-dev.txt
python -m unittest -v test_knowledge
# 原应用backend目录，使用应用依赖
python -m unittest -v test_school_wiki_knowledge
# 仓库根目录
node --test scripts/test-school-wiki.mjs
```

以上为代码及本地验证。GitHub代码更新、线上云服务发布、配置注入、微信小程序上传/审核是不同步骤；本次提交不会自动完成后面三项。
