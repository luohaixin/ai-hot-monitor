# AI热点监控工具 - 项目记忆 (V3.1)

## 项目概述

AI热点监控工具是一个基于Python + FastAPI的实时热点监控与分析平台，支持多渠道数据抓取、AI内容分析、实时通知推送。

**版本**: V3.1.19\
**架构**: Python + FastAPI + SQLAlchemy + React + Vite

**最近更新** (V3.1.19):

- 优化抓取性能：AI分析并发化（速度提升5倍）+ 快速模式（速度提升10-20倍）
- 新增 Kimi (Moonshot) API 支持，国内访问更稳定
- 新增定时监控服务管理与状态显示功能
- 完善设置模块所有选项卡功能（常规/通知/邮件/安全/数据）
- 新增全网搜索数据源筛选功能

***

## 核心功能模块

### 1. 数据源抓取 (Crawler)

- **传统数据源**: 机器之心、36氪、GitHub、掘金、CSDN、InfoQ等
- **新增数据源** (V3.1.5新增):
  - 机器之心英文版 (syncedreview\.com)
  - 新智元 (aiera.com.cn)
  - 量子位 (qbitai.com)
  - GitHub AI-Agents话题 (github.com/topics/ai-agents)
- **社交媒体数据源** (V3.1新增):
  - Twitter/X (需API Key)
  - Bing 搜索
  - HackerNews
  - 搜狗搜索
  - Bilibili
  - 微博热搜

### 2. AI分析服务 (V3.1新增)

- **OpenRouter集成**: 支持多种AI模型 (DeepSeek/Claude/GPT)
- **功能**:
  - Query Expansion (关键词扩展)
  - 内容真实性判断
  - 相关性分析 (0-100分)
  - 重要程度分级 (urgent/high/medium/low)
  - AI摘要生成

### 3. WebSocket实时通知 (V3.1新增)

- Socket.io 实现实时双向通信
- 支持关键词订阅
- 新热点实时推送
- 紧急热点提醒
- 心跳检测机制

### 4. 邮件通知服务 (V3.1新增)

- SMTP支持
- 热点邮件推送
- 批量邮件发送
- HTML邮件模板

### 5. 前端界面

- **技术栈**: React + TypeScript + Vite + TailwindCSS + Framer Motion
- **功能**:
  - 仪表盘数据可视化 (Recharts图表)
  - 热点列表与筛选
  - **热点详情弹窗** (V3.1.3新增) - 点击查看完整标题、摘要、关键词、统计数据
  - 监控词管理 (精确/模糊/排除)
  - 全网搜索 (多数据源聚合)
  - 设置管理

***

## 项目结构

```
ai-hot-monitor/
├── api/                    # API路由
│   └── routes.py          # API端点定义
├── client/                # React前端 (V3.1)
│   ├── src/
│   │   ├── components/    # 组件
│   │   │   └── Layout.tsx
│   │   ├── pages/         # 页面
│   │   │   ├── Dashboard.tsx    # 仪表盘
│   │   │   ├── Hotspots.tsx     # 热点列表
│   │   │   ├── Keywords.tsx     # 监控词管理
│   │   │   ├── Search.tsx       # 全网搜索
│   │   │   └── Settings.tsx     # 设置
│   │   ├── hooks/         # 自定义Hooks
│   │   │   └── useWebSocket.tsx
│   │   ├── styles/        # 样式
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── config/                # 配置文件
│   └── config.yaml
├── core/                  # 核心模块
│   ├── ai_service.py      # AI服务 (V3.1)
│   ├── email_service.py   # 邮件服务 (V3.1)
│   ├── websocket.py       # WebSocket服务 (V3.1)
│   ├── crawler/           # 爬虫模块
│   │   └── social_sources.py  # 社交媒体源 (V3.1)
│   └── ...
├── web/                   # 旧前端 (Astro) - 保留兼容
├── main.py               # 主入口
├── requirements.txt      # Python依赖
├── .env                  # 环境变量配置
├── build.sh             # 构建脚本
└── start.sh             # 启动脚本
```

***

## API接口概览

### 热点相关

| 接口                          | 方法   | 描述            |
| --------------------------- | ---- | ------------- |
| `/api/v1/dashboard`         | GET  | 仪表盘数据         |
| `/api/v1/hot/list`          | GET  | 热点列表 (支持分页筛选) |
| `/api/v1/hot/top`           | GET  | 热门榜单          |
| `/api/v1/hot/trend`         | GET  | 趋势数据          |
| `/api/v1/hotspots/search`   | POST | 全网搜索 (V3.1)   |
| `/api/v1/hotspots/trending` | GET  | 热门内容 (V3.1)   |

### AI分析 (V3.1)

| 接口                          | 方法   | 描述                      |
| --------------------------- | ---- | ----------------------- |
| `/api/v1/ai/analyze`        | POST | 内容分析 (真实性/相关性/重要度)      |
| `/api/v1/ai/expand-keyword` | GET  | 关键词扩展 (Query Expansion) |
| `/api/v1/ai/summary`        | POST | 生成摘要                    |

### 监控词管理

| 接口                        | 方法   | 描述                          |
| ------------------------- | ---- | --------------------------- |
| `/api/v1/keywords`        | GET  | 获取监控词配置                     |
| `/api/v1/keywords/add`    | POST | 添加监控词 (exact/fuzzy/exclude) |
| `/api/v1/keywords/remove` | POST | 移除监控词                       |

### 爬虫控制

| 接口                               | 方法   | 描述     |
| -------------------------------- | ---- | ------ |
| `/api/v1/crawler/run`            | POST | 手动触发抓取 |
| `/api/v1/crawler/status`         | GET  | 爬虫状态   |
| `/api/v1/crawler/task/{task_id}` | GET  | 任务进度   |

### 推送与通知

| 接口                     | 方法   | 描述            |
| ---------------------- | ---- | ------------- |
| `/api/v1/push/test`    | POST | 测试推送          |
| `/api/v1/push/now`     | POST | 立即推送          |
| `/api/v1/email/test`   | POST | 测试邮件 (V3.1)   |
| `/api/v1/email/status` | GET  | 邮件服务状态 (V3.1) |

### 系统状态

| 接口                         | 方法  | 描述                 |
| -------------------------- | --- | ------------------ |
| `/api/v1/health`           | GET | 健康检查               |
| `/api/v1/system/status`    | GET | 系统整体状态 (V3.1)      |
| `/api/v1/websocket/status` | GET | WebSocket状态 (V3.1) |

***

## 环境变量配置

创建 `.env` 文件在项目根目录：

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
EMAIL_FROM_NAME=AI热点监控

# ==================== 社交媒体API配置 ====================
# Twitter API Key (可选，用于Twitter数据源)
# 获取地址: https://twitterapi.io/
TWITTER_API_KEY=your_twitter_api_key

# ==================== 应用配置 ====================
DEBUG=false
PORT=8000
HOST=0.0.0.0
```

***

## 快速开始

### 方式一：使用脚本（推荐）

```bash
# 1. 进入项目目录
cd ai-hot-monitor

# 2. 完整构建（安装依赖+构建前端）
./build.sh

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENROUTER_API_KEY 等配置

# 4. 启动服务
./start.sh
```

### 方式二：手动部署

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 安装前端依赖并构建
cd client
npm install
npm run build
cd ..

# 3. 配置环境变量
# 创建 .env 文件并配置

# 4. 启动服务
python main.py
```

### 方式三：开发模式

```bash
# 终端1：启动后端
cd ai-hot-monitor
python main.py

# 终端2：启动前端开发服务器
cd ai-hot-monitor/client
npm run dev
```

***

## 访问地址

服务启动后，可通过以下地址访问：

| 地址                                           | 说明              |
| -------------------------------------------- | --------------- |
| <http://localhost:8000>                      | 前端界面            |
| <http://localhost:8000/docs>                 | API文档 (Swagger) |
| <http://localhost:8000/redoc>                | API文档 (ReDoc)   |
| <http://localhost:8000/api/v1/health>        | 健康检查            |
| <http://localhost:8000/api/v1/system/status> | 系统状态            |

***

## 功能启用状态

### ✅ 已启用功能

- 基础热点抓取与展示
- 仪表盘数据可视化
- 热点列表与筛选
- 监控词管理
- 社交媒体搜索 (Bing/HackerNews/搜狗/Bilibili/微博)
- React前端界面

### ⚠️ 需配置后启用

| 功能            | 所需配置                          | 配置位置             |
| ------------- | ----------------------------- | ---------------- |
| AI分析          | `OPENROUTER_API_KEY`          | .env             |
| 邮件通知          | `EMAIL_SMTP_*`                | .env             |
| Twitter数据源    | `TWITTER_API_KEY`             | .env             |
| WebSocket实时通知 | `pip install python-socketio` | requirements.txt |


## 技术栈详情

### 后端

| 技术              | 版本     | 用途             |
| --------------- | ------ | -------------- |
| Python          | 3.8+   | 运行时            |
| FastAPI         | 0.105+ | Web框架          |
| SQLAlchemy      | 2.0+   | ORM            |
| SQLite          | -      | 数据库            |
| python-socketio | 5.9+   | WebSocket (可选) |
| APScheduler     | 3.10+  | 定时任务           |
| Loguru          | -      | 日志             |
| httpx           | -      | HTTP客户端        |

### 前端

| 技术               | 版本    | 用途           |
| ---------------- | ----- | ------------ |
| React            | 19    | UI框架         |
| TypeScript       | 5.9+  | 类型系统         |
| Vite             | 7.2+  | 构建工具         |
| TailwindCSS      | 4.1+  | CSS框架        |
| Framer Motion    | 12.3+ | 动画           |
| Socket.io-client | 4.8+  | WebSocket客户端 |
| Recharts         | 2.15+ | 图表           |
| Axios            | 1.13+ | HTTP客户端      |
| date-fns         | 4.1+  | 日期处理         |
| Lucide React     | 0.56+ | 图标           |

### AI服务

| 服务              | 模型                          | 用途                     |
| --------------- | --------------------------- | ---------------------- |
| Moonshot (Kimi) | moonshot-v1-8k              | **默认模型**，8K上下文，长文本理解优秀 |
| Moonshot (Kimi) | moonshot-v1-32k             | 32K上下文，适合长文档分析         |
| OpenRouter      | deepseek/deepseek-chat      | 备用模型1，性价比高             |
| OpenRouter      | anthropic/claude-3.5-sonnet | 备用模型2，理解能力强            |
| OpenRouter      | openai/gpt-4o               | 备用模型3，综合能力优秀           |

***

## 新增功能 (V3.1)

1. **WebSocket实时通知系统**
   - Socket.io 集成
   - 实时热点推送
   - 关键词订阅机制
2. **OpenRouter AI分析**
   - 内容真实性判断 (is\_real)
   - 相关性评分 (0-100分)
   - 重要程度分级 (urgent/high/medium/low)
   - 关键词扩展 (Query Expansion)
   - AI摘要生成
3. **社交媒体数据源扩展**
   - Twitter/X API (twitterapi.io)
   - Bing 搜索 (网页爬虫)
   - HackerNews (Algolia API)
   - 搜狗搜索 (网页爬虫)
   - Bilibili (API)
   - 微博热搜 (网页爬虫)
4. **邮件通知服务**
   - SMTP协议支持
   - HTML邮件模板
   - 批量发送能力
   - 热点数据格式化
5. **前端重构**
   - React + Vite 架构
   - TailwindCSS 样式
   - Framer Motion 动画
   - 响应式设计 (适配移动端)
   - 深色模式支持

***

## 开发计划

### 近期计划 (高优先级)

- [ ] ~~前端开发服务器代理配置优化~~ (已部分修复 MIME 类型问题)
- [ ] 完善错误处理和加载状态
- [ ] 添加更多前端单元测试
- [x] **修复前端AI配置默认模型不一致问题** - ✅ 已统一为 `moonshot-v1-8k`（与后端配置一致）
- [x] **完善多语言i18n集成** - ✅ 已集成 react-i18next，支持简体中文/繁体中文/英文，添加 LanguageSwitcher 组件

### 中期计划

- [ ] 更多数据源集成 (Reddit, LinkedIn, Product Hunt)
- [ ] **热点趋势预测功能优化** - 当前只是简单趋势分析，未使用真正的ML模型，可集成sklearn/tensorflow实现时间序列预测
- [ ] 用户系统完善 (JWT认证)
- [ ] 数据导出功能优化

### 长期计划

- [ ] 移动端 App (React Native/Flutter)
- [ ] 机器学习热点推荐
- [ ] ~~多语言国际化 (i18n)~~ (已移至近期计划)
- [ ] 云原生部署支持 (Docker/K8s)

### 待解决问题/已知限制

- [x] **MCP协议功能启用** - ✅ 已启用（Python 3.14.4 满足 >= 3.10 要求，MCP SDK 1.27.0 已安装并验证通过）
- [x] **部分数据源已启用** - ✅ Playwright 已安装 (v1.58.0)，CSDN、掘金、36氪、开源中国、思否AI、知乎等数据源已启用并支持 JS 渲染抓取
- [ ] **Twitter数据源** - 需要API Key，默认未启用，需配置`TWITTER_API_KEY`环境变量
- [ ] **环境变量安全** - `.env`文件包含真实API Key和邮箱密码，应从版本控制中移除，创建`.env.example`模板

***

## 相关文档

- **详细设计文档**: `/开发文档.md`
- **API文档**: <http://localhost:8000/docs>
- **前端源码**: `client/src/`
- **后端源码**: `core/`, `api/`

***

## 更新日志

### V3.1.19 (2026-04-23)

- AI分析并发化优化，速度提升5倍以上
- 新增快速扫描模式，速度提升10-20倍
- 修复抓取进度统计显示异常问题

### V3.1.18 (2026-04-23)

- 新增 Kimi (Moonshot) API 支持，国内访问更稳定
- 支持多AI提供商切换（Moonshot/OpenRouter）
- 自动模型切换机制：Kimi → OpenRouter备用模型

### V3.1.17 (2026-04-23)

- 修复扫描进度卡住问题（抓取后立即更新进度）
- 完善OpenRouter API错误处理（429/404自动重试和模型切换）

### V3.1.16 (2026-04-23)

- 修复点击停止监控后页面崩溃问题
- 修复监控服务初始化失败的变量作用域bug
- 添加爬取任务诊断日志

### V3.1.15 (2026-04-22)

- 修复定时监控执行次数统计不准确问题
- 修复OpenRouter API编码错误

### V3.1.14 (2026-04-22)

- 一键启动脚本全面升级，添加配置检查和功能提示
- 新增定时监控服务管理与状态显示功能
- 新增监控管理API端点（启动/停止/重启/更新间隔）

### V3.1.13 (2026-04-22)

- 完善设置模块所有选项卡功能（常规/通知/邮件/安全/数据）
- 新增设置相关API端点
- Settings.tsx完全重写，支持状态管理和API调用

### V3.1.12 (2026-04-22)

- 修复微博热搜获取失败问题

### V3.1.11 (2026-04-22)

- 修复全网搜索多数据源结果获取失败问题（Bing/搜狗/微博）

### V3.1.10 (2026-04-22)

- 新增全网搜索数据源筛选功能

### V3.1.9 (2026-04-22)

- 全网搜索添加详情弹窗功能

### V3.1.8 (2026-04-22)

- 修复扫描进度重复计数问题
- 优化HackerNews并发控制和超时机制

### V3.1.7 (2026-04-22)

- 修复通知铃铛点击无反应问题
- 修复扫描后页面无法加载数据问题

### V3.1.6 (2026-04-22)

- AI服务功能真正集成到数据处理流程
- 后端新增AI配置管理API
- 数据库模型新增AI分析字段

### V3.1.5 (2026-04-22)

- 新增机器之心英文版、新智元、量子位、GitHub AI-Agents数据源
- 优化热度计算算法

### V3.1.4 (2026-04-22)

- 修复"立即扫描"按钮无响应问题
- 集成社交媒体源到爬虫引擎
- 修复依赖安装问题

### V3.1.3 (2026-04-21)

- 修复热点详情弹窗中"查看原文"链接失效问题
- 为Hotspots页面添加热点详情弹窗功能

### V3.1.2 (2026-04-21)

- 修复WebSocket连接失败问题
- 修复ASGIApp state属性访问错误

### V3.1.1 (2026-04-21)

- 修复前端MIME类型错误
- 更新项目文档

### V3.1 (2026-04-21)

- 新增WebSocket实时通知系统
- 新增OpenRouter AI分析服务
- 新增社交媒体数据源
- 新增邮件通知服务
- 重构前端为React + Vite

***

## 最近重要变更

| 日期         | 版本      | 变更内容                             |
| ---------- | ------- | -------------------------------- |
| 2026-04-23 | V3.1.19 | AI分析并发化优化，新增快速扫描模式               |
| 2026-04-23 | V3.1.18 | 新增 Kimi (Moonshot) API 支持        |
| 2026-04-23 | V3.1.17 | 修复扫描进度卡住问题，完善API错误处理             |
| 2026-04-23 | V3.1.16 | 修复监控服务相关问题                       |
| 2026-04-22 | V3.1.14 | 新增定时监控服务管理与状态显示                  |
| 2026-04-22 | V3.1.13 | 完善设置模块所有选项卡功能                    |
| 2026-04-22 | V3.1.12 | 修复微博热搜获取失败                       |
| 2026-04-22 | V3.1.11 | 修复全网搜索多数据源结果获取失败                 |
| 2026-04-22 | V3.1.10 | 新增全网搜索数据源筛选功能                    |
| 2026-04-21 | V3.1    | 项目重构：React前端、WebSocket、AI分析、邮件通知 |

***

**维护者**: AI热点监控团队
**最后更新**: 2026-04-23 (V3.1.19)
