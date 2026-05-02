"""
WebSocket 实时通知系统
基于 Socket.io 实现实时热点推送
"""

import asyncio
import json
from typing import Dict, List, Set, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

from loguru import logger

# 尝试导入 socket.io
try:
    import socketio
    SOCKET_IO_AVAILABLE = True
except ImportError:
    SOCKET_IO_AVAILABLE = False
    logger.warning("socket.io 未安装，WebSocket功能将不可用")


@dataclass
class NotificationMessage:
    """通知消息"""
    type: str  # hotspot, alert, system
    title: str
    content: str
    importance: str = "low"  # low, medium, high, urgent
    data: Optional[dict] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


class WebSocketManager:
    """WebSocket 管理器 - 处理实时通知"""
    
    def __init__(self):
        self.sio = None
        self.connected_clients: Set[str] = set()
        self.keyword_subscribers: Dict[str, Set[str]] = {}  # keyword -> set of socket ids
        self.message_history: List[NotificationMessage] = []
        self.max_history = 100
        self._callbacks: Dict[str, List[Callable]] = {}
        
        if SOCKET_IO_AVAILABLE:
            self._init_socketio()
    
    def _init_socketio(self):
        """初始化 Socket.io"""
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            async_mode="asgi"
        )
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        
        @self.sio.event
        async def connect(sid, environ):
            """客户端连接"""
            self.connected_clients.add(sid)
            logger.info(f"WebSocket客户端连接: {sid}")
            
            # 发送连接成功消息
            await self.sio.emit("connected", {
                "sid": sid,
                "message": "连接成功"
            }, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            """客户端断开"""
            self.connected_clients.discard(sid)
            
            # 从所有关键词订阅中移除
            for keyword, subscribers in self.keyword_subscribers.items():
                subscribers.discard(sid)
            
            logger.info(f"WebSocket客户端断开: {sid}")
        
        @self.sio.event
        async def subscribe(sid, data):
            """订阅关键词"""
            keywords = data.get("keywords", []) if isinstance(data, dict) else []
            if isinstance(keywords, str):
                keywords = [keywords]
            
            for keyword in keywords:
                if keyword not in self.keyword_subscribers:
                    self.keyword_subscribers[keyword] = set()
                self.keyword_subscribers[keyword].add(sid)
                logger.debug(f"客户端 {sid} 订阅关键词: {keyword}")
            
            await self.sio.emit("subscribed", {
                "keywords": keywords,
                "message": f"已订阅 {len(keywords)} 个关键词"
            }, room=sid)
        
        @self.sio.event
        async def unsubscribe(sid, data):
            """取消订阅"""
            keywords = data.get("keywords", []) if isinstance(data, dict) else []
            if isinstance(keywords, str):
                keywords = [keywords]
            
            for keyword in keywords:
                if keyword in self.keyword_subscribers:
                    self.keyword_subscribers[keyword].discard(sid)
                    logger.debug(f"客户端 {sid} 取消订阅关键词: {keyword}")
            
            await self.sio.emit("unsubscribed", {
                "keywords": keywords
            }, room=sid)
        
        @self.sio.event
        async def ping(sid, data):
            """心跳检测"""
            await self.sio.emit("pong", {"timestamp": datetime.utcnow().isoformat()}, room=sid)
    
    async def notify_new_hotspot(self, hotspot_data: dict):
        """
        通知新热点
        
        Args:
            hotspot_data: 热点数据字典
        """
        if not self.sio:
            return
        
        # 获取关键词
        keywords = hotspot_data.get("keywords", "")
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
        
        # 构建消息
        message = NotificationMessage(
            type="hotspot",
            title="发现新热点",
            content=hotspot_data.get("title", ""),
            importance=hotspot_data.get("importance", "low"),
            data=hotspot_data
        )
        
        # 保存到历史
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # 广播给所有客户端
        await self.sio.emit("hotspot:new", message.to_dict())
        
        # 发送给订阅了相关关键词的客户端
        for keyword in keyword_list:
            if keyword in self.keyword_subscribers:
                for sid in self.keyword_subscribers[keyword]:
                    await self.sio.emit(
                        f"keyword:{keyword}",
                        message.to_dict(),
                        room=sid
                    )
        
        logger.debug(f"WebSocket推送新热点: {hotspot_data.get('title', '')[:50]}")
    
    async def notify_urgent_hotspot(self, hotspot_data: dict):
        """
        通知紧急热点
        
        Args:
            hotspot_data: 热点数据字典
        """
        if not self.sio:
            return
        
        message = NotificationMessage(
            type="urgent",
            title="🔥 紧急热点",
            content=hotspot_data.get("title", ""),
            importance="urgent",
            data=hotspot_data
        )
        
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # 紧急热点广播给所有客户端
        await self.sio.emit("hotspot:urgent", message.to_dict())
        
        logger.info(f"WebSocket推送紧急热点: {hotspot_data.get('title', '')[:50]}")
    
    async def send_notification(self, message: NotificationMessage):
        """
        发送通用通知
        
        Args:
            message: 通知消息
        """
        if not self.sio:
            return
        
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        await self.sio.emit("notification", message.to_dict())
        
        logger.debug(f"WebSocket发送通知: {message.title}")
    
    async def broadcast_system_message(self, message: str, level: str = "info"):
        """
        广播系统消息
        
        Args:
            message: 消息内容
            level: 消息级别 (info, warning, error)
        """
        if not self.sio:
            return
        
        notification = NotificationMessage(
            type="system",
            title=f"系统消息 [{level.upper()}]",
            content=message,
            importance=level if level in ["high", "urgent"] else "low"
        )
        
        await self.sio.emit("system:message", notification.to_dict())
        
        logger.info(f"WebSocket广播系统消息: {message}")
    
    def get_connection_stats(self) -> dict:
        """获取连接统计"""
        return {
            "connected_clients": len(self.connected_clients),
            "subscribed_keywords": len(self.keyword_subscribers),
            "total_subscriptions": sum(len(subs) for subs in self.keyword_subscribers.values()),
            "message_history": len(self.message_history)
        }
    
    def get_socket_io(self):
        """获取 Socket.io 服务器实例"""
        return self.sio


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """获取 WebSocket 管理器"""
    return websocket_manager


# 辅助函数
async def notify_hotspot_created(hotspot_data: dict):
    """热点创建通知"""
    await websocket_manager.notify_new_hotspot(hotspot_data)


async def notify_urgent_hotspot_detected(hotspot_data: dict):
    """紧急热点检测通知"""
    await websocket_manager.notify_urgent_hotspot(hotspot_data)


async def broadcast_crawl_complete(stats: dict):
    """抓取完成广播"""
    message = NotificationMessage(
        type="system",
        title="抓取完成",
        content=f"本次抓取完成，共发现 {stats.get('saved', 0)} 条热点",
        importance="low",
        data=stats
    )
    await websocket_manager.send_notification(message)
