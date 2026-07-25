# 《驯龙阁》微信小程序 - 部署指南

> 《龙虾修仙传·驯龙阁》校园接力 O2O 知识服务平台
> 技术栈：微信小程序原生 + Python FastAPI + 微信云托管

---

## 📁 项目结构

```
xunlongge/
├── backend/                    # 后端 API（Python FastAPI）
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 配置管理
│   ├── models.py              # SQLAlchemy 数据模型
│   ├── dependencies.py        # 认证守卫
│   ├── routers/               # API 路由
│   │   ├── auth.py           # 登录/认证
│   │   ├── services.py       # 六大道法服务
│   │   ├── orders.py         # 订单全流程
│   │   ├── mentorships.py    # 师徒体系
│   │   └── levels.py         # 修为境界
│   ├── services/             # 业务逻辑服务
│   │   ├── wechat_auth.py    # 微信登录
│   │   ├── order_machine.py  # 订单状态机
│   │   ├── level_service.py  # 修为激励
│   │   ├── mentor_service.py # 师徒传承
│   │   └── payment_service.py# 微信支付
│   ├── utils/
│   │   ├── db.py             # 数据库会话
│   │   └── jwt_utils.py      # JWT 工具
│   ├── requirements.txt
│   ├── Dockerfile             # 云托管容器化
│   └── .env.example           # 环境变量模板
│
├── frontend/                  # 微信小程序前端
│   ├── app.js / app.json / app.wxss
│   ├── project.config.json
│   ├── sitemap.json
│   ├── pages/                 # 主包页面
│   │   ├── splash/            # 启动/登录
│   │   ├── home/              # 首页
│   │   ├── service-plaza/     # 服务广场
│   │   ├── service-detail/    # 服务详情
│   │   ├── order-confirm/     # 下单确认
│   │   ├── order-list/        # 订单列表
│   │   ├── order-detail/      # 订单详情
│   │   └── profile/           # 个人中心
│   ├── components/            # 自定义组件
│   │   └── level-badge/       # 境界徽章
│   ├── subpackages/           # 分包（Phase 2+）
│   │   └── mentor/
│   ├── services/              # API 调用层
│   └── utils/                 # 工具函数
│       ├── request.js         # HTTP 封装
│       ├── auth.js            # 认证工具
│       ├── payment.js         # 微信支付
│       └── format.js          # 格式化
│
└── README.md                  # 本文档
```

---

## 🚀 快速启动（本地开发）

### 1. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制配置（填入真实值）
cp .env.example .env

# 初始化数据库（SQLite）
python -c "from models import init_db; init_db()"

# 启动开发服务器
python main.py
# 或
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 2. 小程序前端启动

1. 下载并安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入 `frontend/` 目录为小程序项目
3. 在 `app.js` 中配置 `apiBaseUrl` 为本机 IP：
   ```javascript
   apiBaseUrl: 'http://192.168.x.x:8000/api/v1',
   ```
4. 编译运行

> ⚠️ 注意：微信开发者工具需开启「不校验合法域名」选项才能请求本地 HTTP 接口。

---

## 🐳 微信云托管部署（生产环境）

### 方式一：微信开发者工具一键部署

1. 在微信开发者工具中打开小程序项目
2. 点击「云开发」→「云托管」→「新建服务」
3. 选择「Python」运行环境
4. 上传 `backend/` 目录（不含 `__pycache__`）
5. 配置环境变量（`.env` 中的值）
6. 等待容器构建完成，获取服务地址

### 方式二：手动 Docker 部署

```bash
cd backend

# 构建镜像（推送到微信云托管仓库）
docker build -t xunlongge-api .

# 推送（需安装微信云开发 CLI）
tcb fn deploy --service xunlongge-api
```

### 3. 域名配置

1. 在 [微信公众平台](https://mp.weixin.qq.com/) 后台添加已备案域名
2. 配置请求合法域名：`https://your-domain.com/api/v1`
3. 在小程序 `app.js` 中配置：
   ```javascript
   apiBaseUrl: 'https://your-domain.com/api/v1',
   ```

---

## 🔧 关键配置项

### `.env` 文件（后端）

```env
# 微信小程序（必须）
WECHAT_APPID=wx_your_real_appid
WECHAT_SECRET=your_real_appsecret

# 微信支付（必须）
WECHAT_MCHID=your_mchid
WECHAT_MCHSERIALNO=your_serial_no
WECHAT_MCHAPIV3KEY=your_apiv3_key

# JWT（生产环境必须修改）
JWT_SECRET=your_random_32char_secret
```

### 小程序 `app.json`（必须）

```json
{
  "appid": "wx_your_real_appid"
}
```

### `frontend/app.js`（必须）

```javascript
apiBaseUrl: 'https://your-production-domain.com/api/v1',
env: 'production',
```

---

## 📋 MVP 功能检查清单

### ✅ Phase 1（已完成）

- [x] 微信登录（code2session）
- [x] 角色选择（散修/大虾/长老）
- [x] 学信网认证申请（大虾）
- [x] 六大道法服务发布 + 列表
- [x] 服务详情 + 大虾主页
- [x] 下单 + 微信支付调起
- [x] 订单状态机（pending→paid→assigned→in_progress→completed）
- [x] 课次日志记录
- [x] 修为积分 + 境界晋升
- [x] 排行榜

### ✅ Phase 2（已完成）

- [x] 同道相契 + 传承树
- [x] 秘境组队（多人拼团）
- [x] 藏经阁 UGC 发布 + 积分解锁
- [x] 订阅消息通知
- [x] 宗门指引（志愿咨询）
- [x] 下山历练（实习岗发布）

### ✅ Phase 3（年度分红池 + 高校百科 AI 问答）

- [x] **宗门宝库**：年度分红池展示
- [x] **分红领取**：化神期大虾按修为比例领取分红
- [x] **分红历史**：用户可查看历年分红记录
- [x] **高校百科**：宗门图志列表
- [x] **AI 问答**：智能问答助手（招生、专业、校园生活等）
- [x] **问答历史**：记录用户问答记录

---

## 🔒 安全注意事项

1. **JWT Secret**：生产环境务必使用随机 32+ 字符的密钥
2. **微信支付证书**：`apiclient_key.pem` 妥善保管，**不要提交到代码仓库**
3. **数据库**：生产环境建议使用 PostgreSQL，敏感字段（手机号）加密存储
4. **学信网认证**：截图需人工复核，防止伪造

---

## 📞 微信小程序注册

1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 注册小程序账号
3. 获取 `AppID` 和 `AppSecret`
4. 配置服务器域名白名单
5. 配置微信支付商户号

---

*本文档对应《驯龙阁》架构设计 v2.0*
*明明相代，代代相传 🐲*
# xiaozishu
明明相代电子化
