# AI热点监控工具 V3.1.19

AI领域热点监控与分析平台，自动抓取多源AI资讯，通过AI筛选算法识别热点，支持多渠道推送提醒、WebSocket实时通知、Kimi/OpenRouter AI分析。

**版本**: V3.1.19  
**架构**: Python + FastAPI + React + Vite

## 核心功能

### 1. 热点数据采集模块
- **多源抓取**：支持机器之心、新智元、量子位、GitHub Trending等传统数据源
- **社交媒体源** (V3.1新增)：Bing搜索、HackerNews、搜狗、Bilibili、微博热搜
- **智能解析**：自动提取标题、摘要、链接、发布时间、浏览量等字段
- **定时任务**：支持10分钟~24小时自定义抓取间隔
- **快速模式**：跳过AI分析，速度提升10-20倍
- **失败降级**：抓取失败自动切换到示例数据，确保服务可用性

### 2. 智能分析引擎
- **关键词匹配**：精确匹配、模糊匹配、排除词过滤
- **AI分析** (V3.1新增)：
  - Kimi (Moonshot) 集成，国内访问稳定
  - OpenRouter备用，支持DeepSeek/Claude/GPT等多种模型
  - 自动模型切换：Kimi → OpenRouter备用模型
  - 内容真实性判断、相关性评分(0-100分)、重要程度分级
- **热度计算**：(浏览×0.4 + 互动×0.4) × 时间衰减因子
- **情感分析**：正面/负面/中性三分类
- **自动分类**：技术/政策/产品/论文/行业应用/投资融资/人才动态
- **AI摘要** (V3.1新增)：自动生成热点内容摘要
- **并发AI分析**：速度提升5倍以上

### 3. 实时监控告警系统
- **推送渠道**：企业微信、钉钉、飞书、邮件、Telegram、ntfy
- **WebSocket实时推送** (V3.1新增)：Socket.io实现双向实时通信
- **推送模式**：实时推送、每日汇总、阈值预警
- **失败重试**：支持2次重试，保证推送成功率≥95%
- **紧急热点**：自动检测紧急热点，支持即时推送和确认机制
- **邮件自动通知**：爬取完成后自动发送邮件通知（可配置）

### 4. 数据可视化界面
- 热点TOP10/20榜单
- 实时热点流（自动更新）
- 趋势图表（今日/7天/30天）
- 分类统计、来源分析
- 历史查询、导出功能(CSV/JSON)
- 深色主题（支持全局切换、自动跟随系统偏好）
- **热点详情弹窗**：点击查看完整标题、摘要、AI分析结果

### 5. 监控服务管理 (V3.1.14新增)
- **定时监控服务**：后台自动定时抓取
- **服务状态显示**：实时显示运行状态、运行时间、下次执行时间
- **灵活控制**：支持启动、停止、重启监控服务
- **动态调整**：可实时修改监控间隔，无需重启服务

### 6. 用户认证与权限管理 (P3)
- **JWT认证**：Access Token + Refresh Token 双令牌机制
- **RBAC权限**：viewer/operator/admin 三种角色
- **密码加密**：bcrypt 哈希存储
- **默认用户**：admin/admin123（管理员）、viewer/viewer123（只读）

### 7. 多语言支持 (P3)
- **支持语言**：简体中文 (zh-CN)、英文 (en)、繁体中文 (zh-TW)
- **自动检测**：HTTP Accept-Language 头
- **动态切换**：支持运行时语言切换

### 8. 数据导出 (P3)
- **支持格式**：CSV、Excel、JSON
- **筛选导出**：按来源、分类、日期等条件筛选
- **自定义字段**：选择需要导出的字段

## 快速开始

### 方式一：使用一键启动脚本（推荐）

```bash
# 进入项目目录
cd ai-hot-monitor

# 一键启动（自动检测Python、安装依赖、构建前端）
./start.sh
```

脚本会自动：
- ✅ 检测并使用正确的Python版本（macOS自动使用系统Python 3.9）
- ✅ 检查并安装Python依赖
- ✅ 检查并构建前端（如未构建）
- ✅ 启动服务

### 方式二：使用构建脚本（完整构建）

```bash
# 1. 进入项目目录
cd ai-hot-monitor

# 2. 完整构建（安装依赖+构建前端）
./build.sh

# 3. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 填入 MOONSHOT_API_KEY 等配置

# 4. 启动服务
./start.sh
```

### 方式三：手动部署（高级用户）

```bash
# 1. 安装后端依赖
# macOS用户请使用系统Python 3.9
/usr/bin/python3 -m pip install -r requirements.txt

# 2. 安装前端依赖并构建
cd client && npm install && npm run build && cd ..

# 3. （可选）配置环境变量
touch .env

# 4. 启动服务
/usr/bin/python3 main.py
```

### macOS多Python版本注意事项

如果你的macOS安装了多个Python版本，建议使用 `./start.sh` 脚本，它会自动检测并使用正确的Python版本。

### 方式四：开发模式（热更新）

```bash
# 终端1：启动后端（带热重载）
cd ai-hot-monitor && ./start.sh

# 终端2：启动前端开发服务器（热更新）
cd ai-hot-monitor/client && npm run dev
```

### 访问服务

服务启动后，可通过以下地址访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8000 | 前端界面 |
| http://localhost:8000/docs | API文档 (Swagger) |
| http://localhost:8000/redoc | API文档 (ReDoc) |
| http://localhost:8000/api/v1/health | 健康检查 |
| http://localhost:8000/api/v1/system/status | 系统状态 |

### 默认登录账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| viewer | viewer123 | 只读用户 |

### 环境变量配置

创建 `.env` 文件在项目根目录（可选，用于启用高级功能）：

```bash
# ==================== AI服务配置 ====================
# Moonshot (Kimi) API Key (推荐，国内访问稳定)
# 获取地址: https://platform.moonshot.cn/
MOONSHOT_API_KEY=sk-xxx

# OpenRouter API Key (备用，支持多种国外模型)
# 获取地址: https://openrouter.ai/
OPENROUTER_API_KEY=sk-or-v1-xxx

# ==================== 邮件服务配置 ====================
# SMTP服务器配置 (可选，用于邮件通知)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# ==================== 社交媒体API配置 ====================
# Twitter API Key (可选，用于Twitter数据源)
# 获取地址: https://twitterapi.io/
TWITTER_API_KEY=your_twitter_api_key

# ==================== 应用配置 ====================
DEBUG=false
PORT=8000
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成测试报告
pytest tests/ -v --html=test_report.html
```

## API接口

### 热点相关

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/dashboard | GET | 仪表盘数据 |
| /api/v1/hot/list | GET | 热点列表（支持分页、筛选） |
| /api/v1/hot/top | GET | 热门榜单 |
| /api/v1/hot/trend | GET | 趋势数据 |
| /api/v1/hotspots/search | POST | 全网搜索 (V3.1) |
| /api/v1/hotspots/trending | GET | 热门内容 (V3.1) |

### AI分析 (V3.1)

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/ai/analyze | POST | 内容分析 (真实性/相关性/重要度) |
| /api/v1/ai/expand-keyword | GET | 关键词扩展 (Query Expansion) |
| /api/v1/ai/summary | POST | 生成摘要 |
| /api/v1/ai/config | GET/POST | AI配置管理 |
| /api/v1/ai/models | GET | 获取可用模型列表 |

### 爬虫相关

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/crawler/run | POST | 手动触发抓取 |
| /api/v1/crawler/status | GET | 获取爬虫状态 |
| /api/v1/crawler/task/{task_id} | GET | 任务进度 |

### 监控服务 (V3.1.14)

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/monitor/status | GET | 获取监控服务状态 |
| /api/v1/monitor/start | POST | 启动监控服务 |
| /api/v1/monitor/stop | POST | 停止监控服务 |
| /api/v1/monitor/restart | POST | 重启监控服务 |
| /api/v1/monitor/update-interval | POST | 更新监控间隔 |

### 监控词管理

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/keywords | GET | 获取监控词配置 |
| /api/v1/keywords/add | POST | 添加监控词 (exact/fuzzy/exclude) |
| /api/v1/keywords/remove | POST | 移除监控词 |

### 推送与通知

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/push/test | POST | 测试推送 |
| /api/v1/push/now | POST | 立即推送 |
| /api/v1/email/test | POST | 测试邮件 (V3.1) |
| /api/v1/email/status | GET | 邮件服务状态 (V3.1) |

### 系统状态

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/health | GET | 健康检查 |
| /api/v1/system/status | GET | 系统整体状态 (V3.1) |
| /api/v1/websocket/status | GET | WebSocket状态 (V3.1) |

### 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/hot/realtime | GET | 实时热点流 |
| /api/v1/hot/detail/{id} | GET | 热点详情（含AI分析理由） |
| /api/v1/hot/stats | GET | 统计信息 |
| /api/v1/hot/history | GET | 历史查询 |
| /api/v1/config | GET | 获取配置 |
| /api/v1/config/reload | POST | 重新加载配置 |
| /api/v1/mcp/status | GET | MCP协议状态 |

## 配置说明

配置文件：`config/config.yaml`

### 关键词配置

```yaml
keywords:
  exact:    # 精确匹配（高权重）
    - "人工智能"
    - "深度学习"
    - "大模型"
    - "LLM"
    - "GPT"
  fuzzy:    # 模糊匹配
    - "AI"
    - "智能"
    - "算法"
  exclude:  # 排除词
    - "游戏AI"
    - "AI换脸"
    - "AI诈骗"
```

### AI服务配置

```yaml
ai_service:
  enabled: true
  provider: moonshot          # 可选: moonshot, openrouter
  model: moonshot-v1-8k       # 可选: moonshot-v1-8k, moonshot-v1-32k
  api_key: ""                 # 从环境变量读取优先
  min_relevance: 50           # 最小相关性阈值(0-100)
  temperature: 0.2            # AI温度参数
  max_tokens: 500             # 最大token数
  require_keyword_mention: true  # 是否要求提及关键词
```

### 推送配置

```yaml
push:
  enabled: true
  mode: "threshold"  # realtime / daily / threshold
  ntfy:              # 默认启用，免配置
    enabled: true
    server: "https://ntfy.sh"
    topic: "ai-hot-monitor"
  wecom:
    enabled: false
    webhook_url: ""
  dingtalk:
    enabled: false
    webhook_url: ""
    secret: ""
  feishu:
    enabled: false
    webhook_url: ""
  email:
    enabled: false
    smtp_server: ""
    username: ""
    password: ""
    recipients: []
    auto_notify: true           # 爬取后自动发送邮件
    min_hotspots_to_notify: 1   # 最少热点数才发送
    send_batch: true            # 批量发送模式
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
```

### 紧急热点配置

```yaml
urgent_hotspot:
  enabled: true
  urgent_threshold: 60          # 紧急阈值（0-100）
  high_score_threshold: 200     # 高频热点阈值
  remind_interval_minutes: 30   # 提醒间隔（分钟）
  auto_push: true               # 自动推送
  keywords:                     # 紧急关键词
    - "突发"
    - "紧急"
    - "重磅"
    - "突破"
    - "OpenAI发布"
    - "GPT-5"
    - "AGI"
```

### 热度评分配置

```yaml
hot_score:
  threshold: 100                # 热度阈值
  weights:
    views: 0.4                  # 浏览量权重
    interactions: 0.4           # 互动量权重
    time_decay: 0.2             # 时间衰减权重
  decay_factor: 0.95            # 时间衰减因子
```

### 数据源配置

```yaml
data_sources:
  jiqizhixin:                   # 机器之心
    enabled: true
    url: "https://www.jiqizhixin.com/articles"
    interval: 30                # 抓取间隔（分钟）
  zhihu:                        # 知乎AI
    enabled: false              # 需要登录，暂时禁用
    url: "https://www.zhihu.com/topic/19559450/hot"
    interval: 30
  kr36:                         # 36氪
    enabled: false              # 动态加载，需要Playwright
    url: "https://36kr.com/search/articles/人工智能"
    interval: 60
  github:                       # GitHub Trending
    enabled: true
    url: "https://github.com/trending?l=python&since=daily"
    interval: 120
```

## 项目结构

```
ai-hot-monitor/
├── api/                         # FastAPI接口层
│   └── routes.py                # 路由定义
├── client/                      # React前端 (V3.1)
│   ├── src/
│   │   ├── components/          # UI组件
│   │   ├── pages/               # 页面
│   │   │   ├── Dashboard.tsx    # 仪表盘
│   │   │   ├── Hotspots.tsx     # 热点列表
│   │   │   ├── Keywords.tsx     # 监控词管理
│   │   │   ├── Search.tsx       # 全网搜索
│   │   │   └── Settings.tsx     # 设置
│   │   ├── hooks/               # 自定义Hooks
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── config/
│   └── config.yaml              # 配置文件
├── core/                        # 核心业务层
│   ├── ai_service.py            # AI分析服务 (V3.1)
│   ├── auth.py                  # 用户认证与权限管理
│   ├── config_loader.py         # 配置加载
│   ├── email_service.py         # 邮件服务 (V3.1)
│   ├── email_notification_service.py  # 邮件通知自动化 (V3.1)
│   ├── models.py                # 数据模型（ORM + Pydantic）
│   ├── monitor_service.py       # 监控服务管理 (V3.1.14)
│   ├── websocket.py             # WebSocket服务 (V3.1)
│   └── crawler/                 # 抓取模块
│       ├── engine.py            # 爬虫引擎
│       ├── social_sources.py    # 社交媒体源 (V3.1)
│       └── parser.py            # 内容解析
├── data/                        # 数据库目录
├── logs/                        # 日志文件
├── web/                         # 旧前端 (Astro) - 保留兼容
├── tests/                       # 测试文件
├── translations/                # 多语言文件
├── build.sh                     # 构建脚本
├── start.sh                     # 启动脚本
├── main.py                      # 主入口
├── requirements.txt             # 依赖清单
├── PROJECT_MEMORY.md            # 项目记忆
└── README.md                    # 使用说明
```

## Docker部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 运行时 |
| FastAPI | 0.105+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM |
| SQLite | - | 数据库 |
| python-socketio | 5.9+ | WebSocket |
| APScheduler | 3.10+ | 定时任务 |
| Loguru | - | 日志 |
| httpx | - | HTTP客户端 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI框架 |
| TypeScript | 5.9+ | 类型系统 |
| Vite | 7.2+ | 构建工具 |
| TailwindCSS | 4.1+ | CSS框架 |
| Framer Motion | 12.3+ | 动画 |
| Socket.io-client | 4.8+ | WebSocket客户端 |
| Recharts | 2.15+ | 图表 |

### AI服务
| 服务 | 模型 | 用途 |
|------|------|------|
| Moonshot (Kimi) | moonshot-v1-8k | **默认模型**，国内访问稳定 |
| Moonshot (Kimi) | moonshot-v1-32k | 长文本模型 (32k上下文) |
| OpenRouter | deepseek/deepseek-chat | 备用模型1 |
| OpenRouter | anthropic/claude-3.5-sonnet | 备用模型2 |
| OpenRouter | openai/gpt-4o | 备用模型3 |

### 部署
- Docker + Docker Compose
- GitHub Actions (CI/CD)

## 开发规范

### 代码规范
- 使用类型注解
- 函数添加文档字符串
- 异常必须捕获并记录日志
- 配置不硬编码，放入config.yaml

### Git提交规范
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `test`: 测试
- `refactor`: 重构

## 版本迭代

- **V1.0.0**：核心功能（热点采集、AI筛选、推送、API）
- **V1.5.0**：体验优化（前端、部署、CI/CD）
- **V2.0.0**：高级功能（MCP协议、热点预测）
- **V2.1.0**：实时热点流
- **V2.2.0**：监控词管理界面
- **V2.3.0**：深色主题优化和AI分析理由展示
- **V2.4.0**：紧急热点监控功能
- **V3.0.0**：用户认证、多语言支持、数据导出
- **V3.1.0**：前端重构为React+Vite、WebSocket实时通知、OpenRouter AI分析、社交媒体数据源扩展、邮件通知服务
- **V3.1.5**：新增机器之心英文版/新智元/量子位/GitHub AI-Agents数据源、优化热度计算算法
- **V3.1.14**：新增定时监控服务管理与状态显示、完善设置模块所有选项卡功能
- **V3.1.17**：修复扫描进度卡住问题、修复OpenRouter API 429/404错误、添加AI分析并发化
- **V3.1.18**：新增Kimi (Moonshot) API支持，默认AI模型更换为Kimi
- **V3.1.19**：修复抓取进度统计显示异常、新增快速模式（速度提升10-20倍）

## 功能启用状态

### ✅ 已启用功能
- 基础热点抓取与展示
- 仪表盘数据可视化
- 热点列表与筛选（含详情弹窗）
- 监控词管理
- 社交媒体搜索 (Bing/HackerNews/搜狗/Bilibili/微博)
- React前端界面
- "立即扫描"手动触发抓取
- 社交媒体热门内容自动抓取（GitHub/HackerNews/微博/Bilibili）
- 定时监控服务（自动后台抓取）
- 快速扫描模式
- WebSocket实时通知
- 邮件自动通知

### ⚠️ 需配置后启用
| 功能 | 所需配置 | 配置位置 |
|------|----------|----------|
| AI分析 (Kimi) | `MOONSHOT_API_KEY` | .env |
| AI分析 (OpenRouter) | `OPENROUTER_API_KEY` | .env |
| 邮件通知 | `EMAIL_SMTP_*` | .env |
| Twitter数据源 | `TWITTER_API_KEY` | .env |
| WebSocket实时通知 | `pip install python-socketio` | 已包含在requirements.txt |

### 📝 数据源配置说明

当前配置的数据源（`config/config.yaml`）：

| 数据源 | 状态 | 说明 |
|--------|------|------|
| 机器之心 | ✅ 启用 | 中文AI资讯头部媒体 |
| 机器之心英文版 | ✅ 启用 | syncedreview.com，英文AI资讯 |
| 新智元 | ✅ 启用 | aiera.com.cn，AI产业资讯 |
| 量子位 | ✅ 启用 | qbitai.com，AI趋势报道 |
| GitHub Trending | ✅ 启用 | 静态页面，稳定可靠 |
| GitHub AI Agents | ✅ 启用 | github.com/topics/ai-agents话题 |
| HackerNews | ✅ 启用 | API接口，实时热门 |
| 微博热搜 | ✅ 启用 | 网页抓取，实时热门 |
| Bilibili | ✅ 启用 | API接口，热门视频 |
| Bing搜索 | ✅ 启用 | 搜索引擎 |
| 搜狗搜索 | ✅ 启用 | 搜索引擎 |
| InfoQ AI | ✅ 启用 | 技术资讯平台 |
| CSDN AI | ❌ 禁用 | 需要JavaScript渲染 |
| 掘金AI | ❌ 禁用 | 单页应用(SPA) |
| 36氪 | ❌ 禁用 | 动态加载内容 |
| 开源中国 | ❌ 禁用 | 页面结构变化 |
| 思否AI | ❌ 禁用 | 反爬拦截(468错误) |
| 知乎AI | ❌ 禁用 | 需要登录验证 |

如需抓取SPA网站（掘金/CSDN等），需安装Playwright：
```bash
pip install playwright
playwright install chromium
```

## 故障排查

### 问题1：前端构建失败
```bash
# 错误：TypeScript类型错误
# 解决：检查未使用的import并移除
```

### 问题2：WebSocket未启用
```bash
# 日志：socket.io 未安装，WebSocket功能将不可用
# 解决：pip install python-socketio
```

### 问题3：AI分析功能不可用
```bash
# 日志：OpenRouter API Key未设置
# 解决：在 .env 文件中设置 MOONSHOT_API_KEY 或 OPENROUTER_API_KEY
```

### 问题4：邮件服务未配置
```bash
# 日志：邮件服务未配置
# 解决：在 .env 文件中配置 EMAIL_SMTP_* 相关变量
```

### 问题5：端口被占用
```bash
# 错误：Address already in use
# 解决：修改 .env 中的 PORT 变量，或使用其他端口启动
PORT=8080 python main.py
```

### 问题6：ModuleNotFoundError（macOS多Python版本）
```bash
# 错误：ModuleNotFoundError: No module named 'fastapi'
# 原因：macOS有多个Python版本，pip安装的包与运行的Python不匹配
# 解决：使用系统Python 3.9
/usr/bin/python3 -m pip install -r requirements.txt
/usr/bin/python3 main.py
```

### 问题7：立即扫描按钮无响应
```bash
# 问题：点击"立即扫描"按钮没有反应
# 解决：已修复，更新代码后重新构建前端
cd client && npm run build
cd ..
/usr/bin/python3 main.py
```

### 问题8：扫描进度卡住（0/9长时间无变化）
```bash
# 问题：点击"立即扫描"后进度长时间卡在0
# 原因：AI分析是串行的，每个item需要2-5秒
# 解决：V3.1.19已修复，添加了快速模式
# 快速模式：POST /api/v1/crawler/run {"fast_mode": true}
```

### 问题9：抓取速度慢（10分钟以上）
```bash
# 问题：完整抓取需要10分钟或更久
# 解决1：使用快速模式（跳过AI分析，速度提升10-20倍）
# 解决2：AI分析已并发化（V3.1.19，速度提升5倍）
```

### 问题10：OpenRouter API 429/404错误
```bash
# 错误：429 Rate Limited 或 404 Model Not Found
# 解决：V3.1.17+已添加自动重试和模型切换机制
# 建议：配置 MOONSHOT_API_KEY 使用Kimi（国内稳定）
```

### 问题11：监控服务启动失败
```bash
# 错误：name 'config' is not defined
# 解决：V3.1.16已修复，请更新到最新版本
```

## 已知问题与限制

1. **MCP协议功能**：需要Python >= 3.10，当前在requirements.txt中被注释
2. **部分数据源被禁用**：CSDN、掘金、36氪等需要JavaScript渲染或存在反爬机制
3. **Twitter数据源**：需要API Key，默认未启用
4. **热点预测**：当前为简单趋势分析，未使用真正的ML模型

## 许可证

MIT License

## 联系

如有问题，请提交Issue或联系开发者。
