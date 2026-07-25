# 小紫薯 - 腾讯云测试环境部署指南

> 适用范围：后端 API（Python FastAPI）部署到腾讯云轻量应用服务器 / 云托管

---

## 📦 已准备的部署文件

| 文件 | 说明 |
|------|------|
| `Dockerfile` | Docker 镜像构建（已适配腾讯云，端口 80） |
| `docker-compose.yml` | 本地或服务器上的容器编排 |
| `.env.test` | 测试环境配置模板 |
| `.dockerignore` | 排除 venv/缓存等不必要文件 |
| `deploy.sh` | 服务器一键部署脚本 |

---

## 🚀 方案一：腾讯云轻量应用服务器（推荐测试环境）

### 第一步：购买服务器

1. 访问 [腾讯云轻量应用服务器](https://cloud.tencent.com/product/lighthouse)
2. 选择配置：**2核2G** 即可（约 50元/月）
3. 选镜像：**Ubuntu 22.04 LTS**
4. 地域：选最近的（如上海）

### 第二步：配置安全组

在服务器控制台 → 防火墙，开放以下端口：

| 端口 | 协议 | 用途 |
|------|------|------|
| 22 | TCP | SSH 管理 |
| 80 | TCP | HTTP（云托管默认） |
| 8000 | TCP | API 测试端口 |
| 443 | TCP | HTTPS（配置 SSL 后） |

### 第三步：上传代码并部署

在本地执行以下命令：

```bash
# 1. 将 backend 目录打包上传到服务器
scp -r xunlongge/backend ubuntu@<服务器IP>:/home/ubuntu/xiaozishu/

# 2. SSH 登录服务器
ssh ubuntu@<服务器IP>

# 3. 进入项目目录
cd /home/ubuntu/xiaozishu/

# 4. 配置环境变量
cp .env.test .env
nano .env   # 填入微信 AppSecret 等配置

# 5. 一键部署
bash deploy.sh
```

### 第四步：验证部署

```bash
# 健康检查
curl http://<服务器IP>:8000/health

# 期望返回：
# {"status":"ok","service":"小紫薯 API","version":"1.0.0","environment":"testing"}

# 查看 API 文档
# 浏览器访问：http://<服务器IP>:8000/docs
```

---

## 🐳 方案二：微信云托管（推荐正式测试）

微信云托管与微信小程序天然集成，内网调用无需配置合法域名。

### 操作步骤

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)（使用 AppID: wx616f58ee521ab283）
2. 进入「云开发 → 云托管」
3. 点击「新建服务」，填写：
   - 服务名称：`xiaozishu-api`
   - 备注：小紫薯后端API
4. 选择「上传代码包」→ 上传 `backend/` 目录（压缩为 zip）
5. 配置环境变量（与 `.env.test` 内容一致）
6. 端口配置：**80**
7. 等待构建完成（约 3-5 分钟）

### 获取服务地址

部署完成后，云托管会提供：
- 内网地址（小程序内网访问，推荐）：`http://prod-xxxxxxxxxx.ap-shanghai.tencentcloudap.com`
- 外网地址（可选，需开启）

---

## 📱 配置小程序前端

部署完成后，需要更新前端 API 地址。

修改 `frontend/app.js`：

```javascript
// 第33行，修改 apiBaseUrl
apiBaseUrl: 'http://<你的服务器IP>:8000/api/v1',  // 轻量服务器
// 或
apiBaseUrl: 'https://<云托管提供的域名>/api/v1',  // 云托管
```

### 如果使用云托管内网模式

小程序调用云托管服务时可以直接使用 `wx.cloud.callContainer`，无需配置合法域名：

```javascript
// utils/request.js 中可替换为云托管专属调用
wx.cloud.callContainer({
  config: { env: 'prod-xxxxxxxxxx' },
  path: '/api/v1/health',
  method: 'GET',
  success: res => console.log(res)
});
```

---

## 🔧 环境变量说明

编辑服务器上的 `.env` 文件：

```bash
nano /home/ubuntu/xiaozishu/.env
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `WECHAT_APPID` | ✅ | 小程序 AppID（已预填：wx616f58ee521ab283） |
| `WECHAT_SECRET` | ✅ | 小程序 AppSecret（在微信公众平台获取） |
| `JWT_SECRET` | ✅ | JWT 密钥（deploy.sh 会自动生成） |
| `DATABASE_URL` | ⭕ | 数据库地址（默认 SQLite，测试环境够用） |
| `WECHAT_MCHID` | ⭕ | 微信支付商户号（不测试支付可留空） |

---

## 🔍 常用运维命令

```bash
# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f api

# 重启服务
docker-compose restart api

# 更新代码后重新部署
docker-compose down
docker build -t xiaozishu-api:latest .
docker-compose up -d

# 进入容器调试
docker exec -it xiaozishu-api bash
```

---

## 📋 部署检查清单

- [ ] 服务器已购买并获取公网 IP
- [ ] 安全组已开放 8000/80 端口
- [ ] `.env` 中已填入 `WECHAT_SECRET`
- [ ] `docker-compose up -d` 启动成功
- [ ] `/health` 接口返回正常
- [ ] 前端 `app.js` 中 `apiBaseUrl` 已更新
- [ ] 微信开发者工具「不校验合法域名」已开启（开发阶段）

---

*🍠 小紫薯 | 明明相代，代代相传*
