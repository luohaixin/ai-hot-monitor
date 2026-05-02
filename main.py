"""
AI热点监控工具 - 主程序入口 (V3.1)
集成爬虫、API、数据库初始化、WebSocket、邮件通知等功能
"""

import os
import sys
from pathlib import Path

# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
project_root = Path(__file__).parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# 添加项目路径
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger
import uvicorn

from core.config_loader import get_config
from core.models import init_database, get_db
from api.routes import router
from core.crawler.social_sources import SocialSourceAggregator
from core.websocket import websocket_manager
from core.ai_service import get_ai_service
from core.email_service import get_email_service, EmailConfig

# Socket.io 集成
try:
    import socketio
    from socketio import ASGIApp
    SOCKET_IO_AVAILABLE = True
except ImportError:
    SOCKET_IO_AVAILABLE = False
    logger.warning("socket.io 未安装，WebSocket功能将不可用")

# 初始化数据库（支持通过环境变量配置测试数据库）
def _init_db():
    """初始化数据库，支持测试模式"""
    import os
    test_db = os.environ.get('TEST_DB_PATH')
    if test_db:
        return init_database(test_db, force=True)
    return init_database()

# 延迟初始化数据库
db_manager = None


def setup_logging():
    """配置日志"""
    config = get_config()
    log_config = config.logging_config
    
    log_file = log_config.get('file', 'logs/app.log')
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}')
    
    # 确保日志目录存在
    log_path = Path(log_file)
    log_dir = log_path.parent
    if not log_dir or str(log_dir) == '.':
        log_dir = Path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format=log_format,
        colorize=True
    )
    logger.add(
        log_file,
        level=log_level,
        format=log_format,
        rotation=log_config.get('rotation', '1 day'),
        retention=log_config.get('retention', '30 days'),
        encoding='utf-8'
    )


def create_fastapi_app(social_sources=None, ai_service=None, email_service=None, websocket_manager=None) -> FastAPI:
    """创建FastAPI应用"""
    global db_manager
    
    # 初始化数据库
    if db_manager is None:
        db_manager = _init_db()
    
    config = get_config()
    app_config = config.get('app', {})
    
    app = FastAPI(
        title=app_config.get('name', 'AI热点监控工具'),
        description="AI领域热点监控与分析平台 V3.1",
        version=app_config.get('version', '3.1.0'),
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 将服务实例附加到app状态
    app.state.social_sources = social_sources
    app.state.ai_service = ai_service
    app.state.email_service = email_service
    app.state.websocket_manager = websocket_manager
    
    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由 - 确保API路由优先注册
    app.include_router(router)
    
    # 静态文件和前端页面
    web_dir = project_root / "web" / "dist"
    client_dir = project_root / "client" / "dist"
    
    # 优先使用新的React前端
    frontend_dir = client_dir if client_dir.exists() else web_dir
    
    if frontend_dir.exists():
        # 挂载静态文件到/static路径
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        # 挂载assets目录以支持前端相对路径引用
        assets_dir = frontend_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # 根路径返回前端页面
        @app.get("/", response_class=HTMLResponse)
        async def root():
            """根路径返回前端页面"""
            with open(frontend_dir / "index.html", "r", encoding="utf-8") as f:
                return f.read()

        # 通配符路由处理前端页面
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def frontend_page(request: Request, path: str):
            """前端页面通配符路由 - 处理所有非API路由"""
            from fastapi import HTTPException
            
            # 排除API路径，返回404
            if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("socket.io"):
                raise HTTPException(status_code=404, detail="Not Found")

            # 尝试查找对应的子目录index.html
            subdir_index = frontend_dir / path / "index.html"
            if subdir_index.exists():
                with open(subdir_index, "r", encoding="utf-8") as f:
                    return f.read()

            # 默认返回根index.html（前端路由模式）
            index_file = frontend_dir / "index.html"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    return f.read()

            return None
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            """根路径返回前端页面"""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AI热点监控工具 V3.1</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #333; }
                    .api-link { display: inline-block; margin: 10px 10px 0 0; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
                    .api-link:hover { background: #0056b3; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 AI热点监控工具 V3.1 API服务</h1>
                    <p>服务运行正常！</p>
                    <p>请使用以下链接访问功能：</p>
                    <a href="/docs" class="api-link">📚 API文档</a>
                    <a href="/api/v1/dashboard" class="api-link">📊 仪表盘数据</a>
                    <a href="/api/v1/hot/top" class="api-link">🔥 热点榜单</a>
                </div>
            </body>
            </html>
            """

    return app


def create_app():
    """创建应用（带WebSocket支持）"""
    # 设置日志
    setup_logging()
    logger.info("=" * 50)
    logger.info("AI热点监控工具 V3.1 启动中...")
    logger.info("=" * 50)

    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('translations', exist_ok=True)

    # 初始化数据库
    db = init_database()
    logger.info("✅ 数据库初始化完成")

    # 初始化默认用户
    try:
        from core.auth import init_default_users
        init_default_users()
        logger.info("✅ 默认用户初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ 默认用户初始化失败（可能已存在）: {e}")

    # 初始化社交媒体数据源
    try:
        social_sources = SocialSourceAggregator(
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            enable_bing=True,
            enable_hackernews=True,
            enable_sogou=True,
            enable_bilibili=True,
            enable_weibo=True
        )
        logger.info("✅ 社交媒体数据源初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ 社交媒体数据源初始化失败: {e}")
        social_sources = None

    # 初始化AI服务
    # 优先检查配置文件中的设置
    from core.config_loader import get_config
    config = get_config()
    ai_config = config.ai_service_config
    
    # 根据 provider 选择对应的环境变量
    provider = ai_config.get('provider', 'openrouter')
    if provider in ['moonshot', 'kimi']:
        ai_api_key = os.getenv("MOONSHOT_API_KEY") or ai_config.get('api_key')
        provider_name = "Moonshot (Kimi)"
    else:
        ai_api_key = os.getenv("OPENROUTER_API_KEY") or ai_config.get('api_key')
        provider_name = "OpenRouter"
    
    if ai_api_key:
        ai_service = get_ai_service(ai_api_key, provider)
        logger.info(f"✅ AI服务初始化完成 (提供商: {provider_name}, 模型: {ai_service.openrouter.model})")
    else:
        ai_service = None
        logger.warning(f"⚠️ {provider_name} API Key未设置，AI分析功能不可用")

    # 初始化邮件服务
    email_config = None
    if os.getenv("EMAIL_SMTP_SERVER"):
        email_config = EmailConfig(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            username=os.getenv("EMAIL_USERNAME", ""),
            password=os.getenv("EMAIL_PASSWORD", ""),
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
            from_name=os.getenv("EMAIL_FROM_NAME", "AI热点监控")
        )
    email_service = get_email_service(email_config)
    if email_config:
        logger.info("✅ 邮件服务配置加载完成")
    else:
        logger.warning("⚠️ 邮件服务未配置")

    # 创建FastAPI应用（传入服务实例）
    fastapi_app = create_fastapi_app(social_sources, ai_service, email_service, websocket_manager)
    logger.info("✅ FastAPI应用创建完成")

    # 集成Socket.io
    if SOCKET_IO_AVAILABLE and websocket_manager.get_socket_io():
        sio = websocket_manager.get_socket_io()
        # 创建ASGI应用，将Socket.io和FastAPI组合
        app = ASGIApp(sio, fastapi_app)
        logger.info("✅ WebSocket服务初始化完成")
    else:
        app = fastapi_app
        logger.warning("⚠️ WebSocket服务未启用")

    # 启动监控服务（根据配置）
    try:
        from core.monitor_service import get_monitor_service
        monitor = get_monitor_service()
        monitor.initialize(enable_detail_crawl=True)
        
        # 获取监控间隔配置
        app_config = get_config()
        monitor_config = app_config.general_config
        auto_start = monitor_config.get('auto_start', False)
        interval = monitor_config.get('monitor_interval', 30)
        
        if auto_start:
            monitor.start(interval_minutes=interval)
            logger.info(f"✅ 定时监控服务已自动启动，间隔: {interval}分钟")
        else:
            logger.info("⏸️ 定时监控服务未自动启动（可在设置中手动启动）")
    except Exception as e:
        logger.warning(f"⚠️ 监控服务初始化失败: {e}")

    logger.info("✨ 应用启动完成!")
    
    return app


# 全局应用实例
app = create_app()


if __name__ == "__main__":
    config = get_config()
    app_config = config.get('app', {})
    
    host = app_config.get('host', '127.0.0.1')
    port = app_config.get('port', 8000)
    
    logger.info(f"🌐 启动服务器: http://localhost:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=config.get('app', {}).get('debug', False),
        log_level="info"
    )
