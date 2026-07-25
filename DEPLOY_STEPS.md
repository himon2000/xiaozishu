# 小紫薯 · 部署操作指南（图文版）

> ⏱ 预计总耗时：15分钟
> 📦 AppID：`wx616f58ee521ab283`

---

## 第一阶段：获取凭证（3分钟）

### Step 1.1 获取 AppSecret

1. 打开 👉 **https://mp.weixin.qq.com**（微信公众平台）
2. 登录后，左侧菜单 → **开发** → **开发管理** → **开发设置**
3. 找到 **AppSecret** 行，点击「**重置**」
4. 用管理员微信扫码，验证后显示 AppSecret
5. **复制 AppSecret**（格式如：`a1b2c3d4e5f6...`）

> ⚠️ AppSecret 只显示一次，请立即保存！

---

## 第二阶段：开通云托管（5分钟）

### Step 2.1 进入云托管

**方式A**（推荐）：公众平台左侧 → **开发** → **云开发** → 顶部点「**云托管**」

**方式B**：直接访问 👉 **https://cloud.weixin.qq.com** → 扫码登录

---

### Step 2.2 开通云托管

1. 若提示「未开通」，点击「**立即开通**」
2. 选择地区：**广州**（或上海，推荐广州）
3. 计费方式：选「**按量计费**」（测试免费，有流量才计费）
4. 点击「**确认开通**」

---

### Step 2.3 复制环境ID

开通成功后，页面顶部会有环境ID，格式如：

```
环境ID：prod-8a3b4c5d
```

**复制这个环境ID**，后面要填入前端代码。

---

## 第三阶段：部署后端（7分钟）

### Step 3.1 创建服务

1. 云托管左侧菜单 → **服务管理** → **新建服务**
2. 填写：
   - **服务名称**：`xiaozishu-api`
   - **备注**：`小紫薯后端API`
3. 点击「**确认**」

---

### Step 3.2 上传代码包

> ⬇️ **上传包已准备在**：
> `xunlongge/backend/` 目录

1. 进入刚创建的 `xiaozishu-api` 服务
2. 点击「**新建版本**」
3. 上传方式选「**代码包**」
4. 将 `xunlongge/backend/` 内所有文件压缩为 `backend.zip`（注意：压缩时选中所有文件，不要包含外层 backend 文件夹）
5. 上传 `backend.zip`
6. 配置：
   - **端口**：`80`
   - **CPU**：`0.25核`
   - **内存**：`512MB`
   - **最小副本数**：`0`（无流量自动停止，测试免费）
7. 点击「**确认部署**」，等待约 **2~3分钟**

---

### Step 3.3 配置环境变量

1. 服务详情页 → **配置** → **环境变量** → **新增**
2. 依次添加：

| 变量名 | 值 |
|--------|-----|
| `WECHAT_SECRET` | ⬅️ 填入 Step 1.1 获取的 AppSecret |
| `JWT_SECRET` | `xzs_cloud_secret_2026_random_key` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |

3. 点击「**保存**」，服务会自动重启

---

### Step 3.4 验证部署成功

部署状态变为「**正常**」后，复制服务的「**公网域名**」（格式如：`https://xxx.ap-guangzhou.tencentscf.com`）

打开浏览器访问：
```
https://你的公网域名/health
```

应返回：
```json
{"status": "ok", "service": "小紫薯API"}
```

---

## 第四阶段：配置前端（2分钟）

### Step 4.1 修改 app.js

打开 `xunlongge/frontend/app.js`，修改顶部配置：

```js
// 改成这样：
const CLOUD_ENV_ID = '你的环境ID';    // ← 例：prod-8a3b4c5d
const CLOUD_SERVICE = 'xiaozishu-api';
const USE_CLOUD = true;               // ← 改为 true
```

---

### Step 4.2 微信开发者工具导入测试

1. 打开微信开发者工具
2. 导入项目：`xunlongge/frontend`
3. AppID：`wx616f58ee521ab283`
4. 不勾选「不校验合法域名」（云托管走内网，无需配置）
5. 点击「导入」

---

## ✅ 完成检查清单

- [ ] `/health` 接口返回 200
- [ ] `/docs` 可打开 API 文档
- [ ] `app.js` 中 `USE_CLOUD = true`，`CLOUD_ENV_ID` 已填真实值
- [ ] 微信开发者工具中无报错

---

## ❓ 遇到问题？

| 问题 | 解决方法 |
|------|---------|
| 构建失败 | 检查 requirements.txt 是否有冲突依赖 |
| health 返回 502 | 等待2分钟后重试，容器需要启动时间 |
| 找不到云托管入口 | 直接访问 cloud.weixin.qq.com |
| AppSecret 重置要管理员 | 联系小程序管理员扫码 |

---

*最后更新：2026-04-10*
