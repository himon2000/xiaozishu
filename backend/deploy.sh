#!/bin/bash
# ================================================================
# 小紫薯 - 腾讯云轻量应用服务器一键部署脚本
# 适用：Ubuntu 20.04/22.04 LTS
# 运行方式：bash deploy.sh
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🍠 小紫薯 API - 腾讯云部署脚本${NC}"
echo "============================================"

# ── 1. 安装 Docker ────────────────────────────────────────────
echo -e "${YELLOW}[1/6] 检查 Docker 安装...${NC}"
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✅ Docker 安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker 已安装: $(docker --version)${NC}"
fi

# ── 2. 安装 Docker Compose ────────────────────────────────────
echo -e "${YELLOW}[2/6] 检查 Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo "安装 Docker Compose..."
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose 安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker Compose 已安装: $(docker-compose --version)${NC}"
fi

# ── 3. 配置环境变量 ────────────────────────────────────────────
echo -e "${YELLOW}[3/6] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    cp .env.test .env
    # 生成随机 JWT Secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
                 cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 64)
    sed -i "s/xiaozishu_test_jwt_secret_change_me_32chars/$JWT_SECRET/" .env
    echo -e "${GREEN}✅ .env 文件已创建，JWT_SECRET 已随机生成${NC}"
    echo -e "${YELLOW}⚠️  请编辑 .env 文件，填入微信小程序 WECHAT_SECRET${NC}"
else
    echo -e "${GREEN}✅ .env 已存在，跳过创建${NC}"
fi

# ── 4. 构建 Docker 镜像 ────────────────────────────────────────
echo -e "${YELLOW}[4/6] 构建 Docker 镜像...${NC}"
docker build -t xiaozishu-api:latest .
echo -e "${GREEN}✅ 镜像构建完成${NC}"

# ── 5. 启动服务 ────────────────────────────────────────────────
echo -e "${YELLOW}[5/6] 启动服务...${NC}"
docker-compose down 2>/dev/null || true
docker-compose up -d
echo -e "${GREEN}✅ 服务启动完成${NC}"

# ── 6. 健康检查 ────────────────────────────────────────────────
echo -e "${YELLOW}[6/6] 等待服务就绪...${NC}"
sleep 5
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务健康检查通过！${NC}"
        break
    fi
    echo "等待服务启动... ($i/10)"
    sleep 3
done

# ── 显示结果 ────────────────────────────────────────────────────
SERVER_IP=$(curl -s https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================"
echo -e "${GREEN}🎉 小紫薯 API 部署成功！${NC}"
echo "============================================"
echo -e "  API 地址:  http://${SERVER_IP}:8000"
echo -e "  健康检查:  http://${SERVER_IP}:8000/health"
echo -e "  接口文档:  http://${SERVER_IP}:8000/docs"
echo ""
echo -e "${YELLOW}下一步：${NC}"
echo "  1. 在腾讯云安全组开放 8000 端口"
echo "  2. 编辑 .env 填入 WECHAT_SECRET"
echo "  3. 在微信公众平台配置合法域名"
echo "  4. 修改小程序 utils/request.js 中的 BASE_URL"
echo "============================================"
