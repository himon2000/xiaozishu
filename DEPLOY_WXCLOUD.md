# 小紫薯 × 微信云托管 部署手册

> 适用版本：2026-04 | AppID: `wx776c4b107e04e36a`（测试号）

---

## 一、准备工作

### 1.1 开通微信云托管

1. 打开 **[微信公众平台](https://mp.weixin.qq.com)**，登录小程序账号（AppID: `wx616f58ee521ab283`）
2. 左侧菜单 → **开发** → **云开发**
3. 首次进入，点击「**开通**」，选择区域（建议选广州或上海）
4. 进入云开发控制台后，点击顶部「**云托管**」标签
5. 若提示未开通，点击「**立即开通**」 → 选择**按量计费**（测试阶段免费）

> ✅ 开通完成后，记录页面顶部的「**环境ID**」（格式如：`prod-8a3b4c`）

---

## 二、部署后端服务

### 2.1 创建服务

1. 云托管控制台 → 左侧「**服务管理**」→「**新建服务**」
2. 填写：
   - **服务名称**：`xiaozishu-api`（注意：后续填入前端代码）
   - **备注**：小紫薯后端API
3. 点击「**确认**」

### 2.2 上传代码部署

**方式A：直接上传代码包（推荐新手）**

1. 将 `xunlongge/backend/` 目录压缩为 `backend.zip`（**注意**：压缩时直接选中 backend 目录内的所有文件，不要包含外层 backend 文件夹）
2. 在服务详情页，点击「**新建版本**」
3. 上传方式选「**代码包**」→ 上传 `backend.zip`
4. 填写部署参数：
   - **端口**：`80`
   - **CPU**：0.25 核（测试够用）
   - **内存**：512 MB
   - **最小副本数**：1
5. 点击「**确认**」，等待约 2~3 分钟构建完成

**方式B：命令行上传（需要安装 @wxcloud/cli）**

```bash
# 安装 wxcloud CLI
npm install -g @wxcloud/cli

# 登录（会弹出二维码扫码）
wxcloud login

# 进入 backend 目录上传
cd xunlongge/backend
wxcloud deploy --env YOUR_ENV_ID --service xiaozishu-api
```

### 2.3 配置环境变量

1. 服务详情 → 「**配置**」→「**环境变量**」→「**新增**」
2. 依次添加以下变量：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `WECHAT_SECRET` | 小程序 AppSecret（公众平台→开发设置中获取） | `your_real_secret` |
| `JWT_SECRET` | JWT 密钥（自定义32位随机字符串） | `xzs_prod_secret_2026_xyz` |
| `ENVIRONMENT` | 运行环境标识 | `production` |
| `DEBUG` | 是否调试模式 | `false` |

> ⚠️ `WECHAT_SECRET` 必须填真实值，否则微信登录失败

### 2.4 验证后端部署

部署完成后，服务状态变为「**正常**」，复制「**公网域名**」（格式如：`https://xxx.ap-guangzhou.tencentscf.com`）

访问：`https://你的公网域名/health`，应返回：
```json
{"status": "ok", "service": "小紫薯API"}
```

访问：`https://你的公网域名/docs`，可查看完整 API 文档

---

## 三、配置前端连接云托管

### 3.1 修改 app.js（关键步骤）

打开 `xunlongge/frontend/app.js`，修改顶部配置：

```js
// 修改前（本地开发配置）
const CLOUD_ENV_ID = 'YOUR_ENV_ID';      // ← 替换为你的云托管环境ID
const CLOUD_SERVICE = 'xiaozishu-api';   // ← 对应步骤2.1创建的服务名称
const USE_CLOUD = false;                  // ← 改为 true

// 修改后（正式部署配置）
const CLOUD_ENV_ID = 'prod-8a3b4c';     // ← 你的真实环境ID
const CLOUD_SERVICE = 'xiaozishu-api';  // 服务名不变
const USE_CLOUD = true;                  // ← 开启云托管内网模式
```

### 3.2 云托管授权小程序

1. 云托管控制台 → 「**设置**」→「**微信凭证**」
2. 确认已绑定 AppID：`wx616f58ee521ab283`
3. 若未绑定，点击「**添加**」→ 扫码授权

### 3.3 在微信开发者工具中测试

1. 打开微信开发者工具，导入 `xunlongge/frontend`
2. 在「详情」→「本地设置」中确认：
   - 基础库版本 ≥ **2.23.0**（callContainer 要求）
   - 不勾选「不校验合法域名」（云托管走内网，无需配置合法域名）
3. 运行小程序，查看 Console 无 callContainer 报错

---

## 四、数据持久化（SQLite）

微信云托管容器重启后本地文件会丢失。有两种解决方案：

### 方案A：挂载云存储（简单，测试用）

在版本配置中的「**存储**」部分挂载 CFS（腾讯云文件存储）：
- 挂载路径：`/app/data`
- 这样 SQLite 文件会持久保存

### 方案B：迁移到云数据库（推荐生产）

将 SQLite 替换为腾讯云 MySQL（云托管内网可直连）：
1. 在云托管控制台开通「**云数据库 MySQL**」
2. 修改 `config.py`：
   ```python
   database_url: str = "mysql+pymysql://user:pass@内网域名:3306/xiaozishu"
   ```
3. 安装 `pymysql`：在 `requirements.txt` 添加 `pymysql==1.1.0`

---

## 五、上线前检查清单

- [ ] 云托管服务状态：正常
- [ ] 访问 `/health` 接口返回 200
- [ ] app.js 中 `USE_CLOUD = true`，`CLOUD_ENV_ID` 已填真实值
- [ ] 基础库版本 ≥ 2.23.0
- [ ] 小程序已授权给云托管环境
- [ ] `WECHAT_SECRET` 环境变量已配置
- [ ] （可选）SQLite 挂载存储或迁移 MySQL

---

## 六、费用参考

| 资源 | 规格 | 预估费用 |
|------|------|----------|
| 云托管计算 | 0.25核/512MB × 1副本 | ~¥0.1/小时（测试期可降为0） |
| 流量 | 内网调用免费 | ¥0 |
| 存储（CFS） | 10GB | ~¥2/月 |
| **月合计** | | **约 ¥5~20（视并发量）** |

> 💡 测试期间，将副本最小数设为 **0**，无流量时自动缩容至 0，完全免费。

---

## 七、常见问题

**Q: callContainer 报 "Cloud API isn't enabled"**
A: 检查 `wx.cloud.init()` 是否在 `onLaunch` 中调用，且基础库 ≥ 2.23.0

**Q: 后端获取不到 openid**
A: 确保请求经过 `wx.cloud.callContainer`（不是 `wx.request`），且 `USE_CLOUD = true`

**Q: 构建失败（pip 安装超时）**
A: Dockerfile 已配置腾讯云 pypi 加速源，若仍失败可检查 requirements.txt 中是否有冲突的版本

**Q: 服务不稳定/频繁重启**
A: 检查健康检查配置，确保 `/health` 接口在 20 秒内响应，或延长 `start-period` 参数

---

*最后更新：2026-04-10*
