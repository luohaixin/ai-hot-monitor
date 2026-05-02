#!/bin/bash
# AI热点监控工具 - 一键启动脚本 (V3.1.14)
# 自动检测Python版本并启动服务

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI热点监控工具 V3.1.14 - 一键启动    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检测最佳Python版本
detect_python() {
    # macOS优先使用系统Python 3.9（避免Homebrew的Python 3.14）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [ -f "/usr/bin/python3" ]; then
            # 检查版本
            VERSION=$(/usr/bin/python3 --version 2>&1 | grep -o '[0-9]\.[0-9]' | head -1)
            if [[ "$VERSION" == "3.9" ]] || [[ "$VERSION" == "3.8" ]]; then
                echo "/usr/bin/python3"
                return
            fi
        fi
    fi
    
    # 尝试python3
    if command -v python3 &> /dev/null; then
        echo "python3"
        return
    fi
    
    # 尝试python
    if command -v python &> /dev/null; then
        echo "python"
        return
    fi
    
    echo ""
}

PYTHON=$(detect_python)

if [ -z "$PYTHON" ]; then
    echo -e "${RED}错误: 未找到 Python${NC}"
    echo "请安装Python 3.8或更高版本: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}✓ 使用 Python: $PYTHON${NC}"
PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}✓ 版本: $PYTHON_VERSION${NC}"
echo ""

# 检查依赖是否已安装
check_dependencies() {
    if ! $PYTHON -c "import fastapi" 2>/dev/null; then
        echo -e "${YELLOW}⚠ 依赖未安装，正在安装...${NC}"
        echo ""
        $PYTHON -m pip install -r requirements.txt
        echo ""
        echo -e "${GREEN}✓ 依赖安装完成${NC}"
        echo ""
    fi
}

check_dependencies

# 检查前端是否已构建
check_frontend() {
    if [ ! -d "client/dist" ]; then
        echo -e "${YELLOW}⚠ 前端未构建，正在构建...${NC}"
        echo ""
        cd client
        if ! command -v npm &> /dev/null; then
            echo -e "${RED}错误: 未找到 npm，请先安装 Node.js${NC}"
            echo "下载地址: https://nodejs.org/"
            exit 1
        fi
        npm install
        npm run build
        cd ..
        echo ""
        echo -e "${GREEN}✓ 前端构建完成${NC}"
        echo ""
    fi
}

check_frontend

# 加载环境变量
if [ -f ".env" ]; then
    echo -e "${YELLOW}加载环境变量...${NC}"
    export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true
fi

# 检查配置文件
echo -e "${CYAN}📋 配置检查:${NC}"
if [ -f "config/config.yaml" ]; then
    echo -e "${GREEN}  ✓ 配置文件已加载${NC}"
else
    echo -e "${YELLOW}  ⚠ 配置文件不存在，将使用默认配置${NC}"
fi

# 检查环境变量配置
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo -e "${GREEN}  ✓ AI服务已配置 (OpenRouter)${NC}"
else
    echo -e "${YELLOW}  ⚠ AI服务未配置 (设置 OPENROUTER_API_KEY 启用)${NC}"
fi

if [ -n "$EMAIL_SMTP_SERVER" ]; then
    echo -e "${GREEN}  ✓ 邮件服务已配置 ($EMAIL_SMTP_SERVER)${NC}"
else
    echo -e "${YELLOW}  ⚠ 邮件服务未配置${NC}"
fi
echo ""

# 检测本机IP地址
detect_local_ip() {
    local ip=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ip=$(ifconfig | grep -E 'inet\s' | grep -v '127.0.0.1' | awk '{print $2}' | head -1)
    else
        # Linux
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' || \
             ip route get 1 2>/dev/null | awk '{print $7}' | head -1 || \
             echo "")
    fi
    echo "$ip"
}

LOCAL_IP=$(detect_local_ip)
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# 启动应用
echo -e "${GREEN}🚀 启动应用...${NC}"
echo ""
echo -e "${BLUE}📱 访问地址:${NC}"

if [ "$HOST" = "0.0.0.0" ] || [ "$HOST" = "::" ]; then
    echo -e "${GREEN}  ✓ 服务模式: 局域网/公网可访问${NC}"
    echo ""
    echo "  🌐 本地访问:    http://localhost:${PORT}"
    if [ -n "$LOCAL_IP" ]; then
        echo "  🌐 局域网访问:  http://${LOCAL_IP}:${PORT}"
    fi
    echo "  🌐 API文档:     http://localhost:${PORT}/docs"
    echo ""
    echo -e "${YELLOW}  💡 局域网内其他设备可使用 http://${LOCAL_IP}:${PORT} 访问${NC}"
else
    echo -e "${YELLOW}  ✓ 服务模式: 仅本地访问 (host=${HOST})${NC}"
    echo ""
    echo "  🌐 本地访问:    http://localhost:${PORT}"
    echo "  🌐 API文档:     http://localhost:${PORT}/docs"
fi
echo ""
echo -e "${CYAN}📊 主要功能:${NC}"
echo "  • 实时热点监控 (自动抓取各平台AI热点)"
echo "  • AI内容分析 (真实性/相关性/重要性评估)"
echo "  • 全网搜索 (Bing/HackerNews/搜狗/微博/B站)"
echo "  • 监控词管理 (精确/模糊/排除匹配)"
echo "  • 邮件/WebSocket通知推送"
echo "  • 数据导出 (CSV/JSON)"
echo ""
echo -e "${CYAN}🎛️  监控控制 (在设置-常规页面):${NC}"
echo "  • 查看监控运行状态"
echo "  • 启动/停止/重启监控服务"
echo "  • 设置监控间隔 (默认30分钟)"
echo ""
echo -e "${YELLOW}💡 提示: 首次使用请在设置页面配置AI服务和通知选项${NC}"
echo ""
echo -e "${RED}按 Ctrl+C 停止服务${NC}"
echo ""

$PYTHON main.py
