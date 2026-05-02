"""
配置加载模块 - 支持热加载和配置管理
"""

import os
import threading
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ConfigLoader:
    """配置加载器 - 支持热加载"""

    _instance = None
    _config = None
    _observer = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = config_path or cls._get_default_config_path()
            cls._instance._load_config()
            cls._instance._setup_file_watcher()
        return cls._instance
    
    @staticmethod
    def _get_default_config_path() -> str:
        """获取默认配置文件路径"""
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "config" / "config.yaml")
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {self._config_path}")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "app": {
                "name": "AI热点监控工具",
                "version": "1.0.0",
                "host": "0.0.0.0",
                "port": 8000
            },
            "keywords": {
                "exact": ["人工智能", "机器学习", "深度学习"],
                "fuzzy": ["AI", "智能"],
                "exclude": ["游戏AI"]
            },
            "hot_score": {
                "weights": {"views": 0.4, "interactions": 0.4, "time_decay": 0.2},
                "threshold": 100
            },
            "data_sources": {},
            "push": {"enabled": False},
            "logging": {"level": "INFO"}
        }
    
    def _setup_file_watcher(self) -> None:
        """设置文件监听器，实现热加载"""
        try:
            class ConfigFileHandler(FileSystemEventHandler):
                def __init__(self, loader):
                    self.loader = loader
                
                def on_modified(self, event):
                    if event.src_path == self.loader._config_path:
                        logger.info("配置文件变更，重新加载...")
                        self.loader._load_config()
            
            self._observer = Observer()
            config_dir = os.path.dirname(self._config_path)
            self._observer.schedule(ConfigFileHandler(self), config_dir, recursive=False)
            self._observer.start()
            logger.info("配置文件热加载已启用")
        except Exception as e:
            logger.warning(f"配置文件热加载初始化失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号分隔的键路径"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    @property
    def keywords(self) -> Dict[str, List[str]]:
        """获取关键词配置"""
        return self._config.get('keywords', {})
    
    @property
    def data_sources(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self._config.get('data_sources', {})
    
    @property
    def hot_score_config(self) -> Dict[str, Any]:
        """获取热度计算配置"""
        return self._config.get('hot_score', {})
    
    @property
    def push_config(self) -> Dict[str, Any]:
        """获取推送配置"""
        return self._config.get('push', {})
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self._config.get('database', {})
    
    @property
    def sentiment_config(self) -> Dict[str, Any]:
        """获取情感分析配置"""
        return self._config.get('sentiment', {})
    
    @property
    def categories(self) -> List[Dict[str, Any]]:
        """获取分类配置"""
        return self._config.get('categories', [])
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get('logging', {})
    
    @property
    def system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self._config.get('system', {})
    
    @property
    def ai_service_config(self) -> Dict[str, Any]:
        """获取AI服务配置"""
        return self._config.get('ai_service', {
            'enabled': True,
            'model': 'moonshot-v1-8k',
            'provider': 'moonshot',
            'api_key': '',
            'min_relevance': 50,
            'temperature': 0.2,
            'max_tokens': 500,
            'require_keyword_mention': False
        })
    
    def reload(self) -> None:
        """手动重新加载配置"""
        self._load_config()
        logger.info("配置手动重载完成")
    
    def stop_watcher(self) -> None:
        """停止文件监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
    
    def update_keywords(self, keywords: Dict[str, List[str]]) -> bool:
        """更新关键词配置"""
        with self._lock:
            try:
                # 验证关键词格式
                required_keys = ['exact', 'fuzzy', 'exclude']
                for key in required_keys:
                    if key not in keywords:
                        keywords[key] = []
                    elif not isinstance(keywords[key], list):
                        return False

                # 更新配置
                self._config['keywords'] = keywords

                # 写回配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

                logger.info("关键词配置更新成功")
                return True
            except Exception as e:
                logger.error(f"关键词配置更新失败: {e}")
                return False
    
    def add_keyword(self, keyword_type: str, keyword: str) -> bool:
        """添加关键词"""
        with self._lock:
            try:
                if keyword_type not in ['exact', 'fuzzy', 'exclude']:
                    return False

                if keyword not in self._config['keywords'].get(keyword_type, []):
                    self._config['keywords'][keyword_type].append(keyword)

                    # 写回配置文件
                    with open(self._config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

                    logger.info(f"添加关键词成功: {keyword_type} - {keyword}")
                    return True
                return False
            except Exception as e:
                logger.error(f"添加关键词失败: {e}")
                return False
    
    def remove_keyword(self, keyword_type: str, keyword: str) -> bool:
        """移除关键词"""
        with self._lock:
            try:
                if keyword_type not in ['exact', 'fuzzy', 'exclude']:
                    return False

                if keyword in self._config['keywords'].get(keyword_type, []):
                    self._config['keywords'][keyword_type].remove(keyword)

                    # 写回配置文件
                    with open(self._config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

                    logger.info(f"移除关键词成功: {keyword_type} - {keyword}")
                    return True
                return False
            except Exception as e:
                logger.error(f"移除关键词失败: {e}")
                return False
    
    def update_ai_config(self, ai_config: Dict[str, Any]) -> bool:
        """更新AI服务配置"""
        with self._lock:
            try:
                # 验证配置字段
                valid_fields = ['enabled', 'model', 'provider', 'api_key', 'min_relevance', 
                               'temperature', 'max_tokens', 'require_keyword_mention']
                
                # 获取当前配置或创建默认配置
                if 'ai_service' not in self._config:
                    self._config['ai_service'] = {}
                
                # 更新配置字段
                for field in valid_fields:
                    if field in ai_config:
                        self._config['ai_service'][field] = ai_config[field]
                
                # 写回配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                
                logger.info("AI服务配置更新成功")
                return True
            except Exception as e:
                logger.error(f"AI服务配置更新失败: {e}")
                return False
    
    def update_general_config(self, general_config: Dict[str, Any]) -> bool:
        """更新通用配置"""
        with self._lock:
            try:
                # 确保general配置段存在
                if 'general' not in self._config:
                    self._config['general'] = {}
                
                # 更新配置字段
                valid_fields = ['monitor_interval', 'hot_score_threshold']
                for field in valid_fields:
                    if field in general_config:
                        self._config['general'][field] = general_config[field]
                
                # 同时更新热度阈值到hot_score配置
                if 'hot_score_threshold' in general_config:
                    if 'hot_score' not in self._config:
                        self._config['hot_score'] = {}
                    self._config['hot_score']['threshold'] = general_config['hot_score_threshold']
                
                # 写回配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                
                logger.info("通用配置更新成功")
                return True
            except Exception as e:
                logger.error(f"通用配置更新失败: {e}")
                return False
    
    def update_notification_config(self, notification_config: Dict[str, Any]) -> bool:
        """更新通知配置"""
        with self._lock:
            try:
                # 确保notifications配置段存在
                if 'notifications' not in self._config:
                    self._config['notifications'] = {}
                
                # 更新配置字段
                valid_fields = ['websocket_enabled', 'new_hotspot_push', 'urgent_reminder', 'daily_digest']
                for field in valid_fields:
                    if field in notification_config:
                        self._config['notifications'][field] = notification_config[field]
                
                # 写回配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                
                logger.info("通知配置更新成功")
                return True
            except Exception as e:
                logger.error(f"通知配置更新失败: {e}")
                return False
    
    def update_email_config(self, email_config: Dict[str, Any]) -> bool:
        """更新邮件配置"""
        with self._lock:
            try:
                # 确保email配置段存在
                if 'email' not in self._config:
                    self._config['email'] = {}
                
                # 更新配置字段
                valid_fields = ['smtp_server', 'smtp_port', 'use_tls', 'username', 'password', 'from_name']
                for field in valid_fields:
                    if field in email_config:
                        # 密码如果是掩码则不更新
                        if field == 'password' and email_config[field].startswith('********'):
                            continue
                        self._config['email'][field] = email_config[field]
                
                # 写回配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                
                logger.info("邮件配置更新成功")
                return True
            except Exception as e:
                logger.error(f"邮件配置更新失败: {e}")
                return False
    
    @property
    def general_config(self) -> Dict[str, Any]:
        """获取通用配置"""
        return self._config.get('general', {
            'monitor_interval': 30,
            'hot_score_threshold': 100
        })
    
    @property
    def notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        return self._config.get('notifications', {
            'websocket_enabled': True,
            'new_hotspot_push': True,
            'urgent_reminder': True,
            'daily_digest': False
        })
    
    @property
    def email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        return self._config.get('email', {
            'smtp_server': '',
            'smtp_port': 587,
            'use_tls': True,
            'username': '',
            'password': '',
            'from_name': 'AI热点监控'
        })


# 全局配置实例
def get_config() -> ConfigLoader:
    """获取配置加载器实例"""
    return ConfigLoader()
