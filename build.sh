#!/bin/bash
# AI热点监控工具 - 构建脚本 (V3.1)
# 支持前端构建、后端依赖安装、完整部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI热点监控工具 V3.1 - 构建脚本      ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检测操作系统
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

echo -e "${BLUE}检测到操作系统: $OS${NC}"
echo ""

# 函数：检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 函数：安装前端依赖
install_frontend_deps() {
    echo -e "${YELLOW}[1/6] 安装前端依赖...${NC}"
    
    if [ -d "client" ]; then
        cd client
        
        if command_exists npm; then
            echo "使用 npm 安装依赖..."
            npm install
        elif command_exists yarn; then
            echo "使用 yarn 安装依赖..."
            yarn install
        elif command_exists pnpm; then
            echo "使用 pnpm 安装依赖..."
            pnpm install
        else
            echo -e "${RED}错误: 未找到 npm/yarn/pnpm，请先安装 Node.js${NC}"
            exit 1
        fi
        
        cd ..
        echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
    else
        echo -e "${YELLOW}⚠ 未找到 client 目录，跳过前端依赖安装${NC}"
    fi
    echo ""
}

# 函数：构建前端
build_frontend() {
    echo -e "${YELLOW}[2/6] 构建前端项目...${NC}"
    
    if [ -d "client" ]; then
        cd client
        
        if command_exists npm; then
            npm run build
        elif command_exists yarn; then
            yarn build
        elif command_exists pnpm; then
            pnpm build
        fi
        
        cd ..
        echo -e "${GREEN}✓ 前端构建完成${NC}"
        echo -e "${BLUE}  构建输出: client/dist/${NC}"
    else
        echo -e "${YELLOW}⚠ 未找到 client 目录，跳过前端构建${NC}"
    fi
    echo ""
}

# 函数：安装后端依赖
install_backend_deps() {
    echo -e "${YELLOW}[3/6] 安装后端依赖...${NC}"
    
    if command_exists pip; then
        pip install -r requirements.txt
    elif command_exists pip3; then
        pip3 install -r requirements.txt
    else
        echo -e "${RED}错误: 未找到 pip，请先安装 Python${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
    echo ""
}

# 函数：初始化数据库
init_database() {
    echo -e "${YELLOW}[4/6] 初始化数据库...${NC}"
    
    # 创建必要的目录
    mkdir -p data logs translations
    
    # 运行数据库初始化（如果Python可用）
    if command_exists python; then
        python -c "from core.models import init_database; init_database()" || true
    elif command_exists python3; then
        python3 -c "from core.models import init_database; init_database()" || true
    fi
    
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"
    echo ""
}

# 函数：创建环境配置示例
create_env_example() {
    echo -e "${YELLOW}[5/6] 创建环境配置示例...${NC}"
    
    if [ ! -f ".env.example" ]; then
        cat > .env.example << 'EOF'
# AI热点监控工具 - 环境变量配置示例
# 复制此文件为 .env 并填入实际值

# ==================== AI服务配置 ====================
# OpenRouter API Key (必需，用于AI分析)
# 获取地址: https://openrouter.ai/
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx

# ==================== 邮件服务配置 ====================
# SMTP服务器配置 (可选，用于邮件通知)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM_NAME=AI热点监控

# ==================== 社交媒体API配置 ====================
# Twitter API Key (可选，用于Twitter数据源)
# 获取地址: https://twitterapi.io/
TWITTER_API_KEY=your_twitter_api_key

# ==================== 数据库配置 ====================
# 数据库路径 (可选，默认使用 data/hotspots.db)
# DATABASE_URL=sqlite:///data/hotspots.db

# ==================== WebSocket配置 ====================
# WebSocket心跳间隔（秒）
WS_PING_INTERVAL=25

# ==================== 应用配置 ====================
# 调试模式 (开发时设为true)
DEBUG=false
# 监听端口
PORT=8000
# 监听地址
HOST=0.0.0.0
EOF
        echo -e "${GREEN}✓ 已创建 .env.example${NC}"
    else
        echo -e "${BLUE}  .env.example 已存在，跳过创建${NC}"
    fi
    echo ""
}

# 函数：显示完成信息
show_completion() {
    echo -e "${YELLOW}[6/6] 构建完成!${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  AI热点监控工具 V3.1 构建成功!       ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}使用说明:${NC}"
    echo "  1. 复制 .env.example 为 .env 并配置环境变量"
    echo "  2. 运行启动脚本: ./start.sh"
    echo "  3. 或使用 Python 直接启动: python main.py"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo "  - 前端界面: http://localhost:8000"
    echo "  - API文档: http://localhost:8000/docs"
    echo "  - 健康检查: http://localhost:8000/api/v1/health"
    echo ""
    echo -e "${BLUE}新增功能 (V3.1):${NC}"
    echo "  ✓ WebSocket 实时通知系统"
    echo "  ✓ OpenRouter AI 内容分析"
    echo "  ✓ 社交媒体数据源 (Twitter/Bing/HN/搜狗/B站/微博)"
    echo "  ✓ 邮件通知服务"
    echo "  ✓ React + Vite 前端重构"
    echo ""
}

# 主执行流程
main() {
    # 检查必要命令
    if ! command_exists python && ! command_exists python3; then
        echo -e "${RED}错误: 未找到 Python，请先安装 Python 3.8+${NC}"
        exit 1
    fi
    
    # 执行构建步骤
    install_frontend_deps
    build_frontend
    install_backend_deps
    init_database
    create_env_example
    show_completion
}

# 处理命令行参数
case "${1:-}" in
    --frontend-only)
        install_frontend_deps
        build_frontend
        ;;
    --backend-only)
        install_backend_deps
        init_database
        ;;
    --help|-h)
        echo "AI热点监控工具 V3.1 - 构建脚本"
        echo ""
        echo "用法: ./build.sh [选项]"
        echo ""
        echo "选项:"
        echo "  --frontend-only    仅构建前端"
        echo "  --backend-only     仅安装后端依赖"
        echo "  --help, -h         显示此帮助信息"
        echo ""
        echo "无选项时执行完整构建流程"
        ;;
    *)
        main
        ;;
esac
