"""
多语言国际化支持模块 (i18n)
支持: 简体中文(zh-CN)、英文(en)、繁体中文(zh-TW)
"""

import json
import os
from typing import Dict, Optional, Any
from enum import Enum
from pathlib import Path

from loguru import logger


class LanguageCode(str, Enum):
    """语言代码枚举"""
    ZH_CN = "zh-CN"  # 简体中文
    EN = "en"        # 英文
    ZH_TW = "zh-TW"  # 繁体中文
    JA = "ja"        # 日文
    KO = "ko"        # 韩文


# 默认语言
DEFAULT_LANGUAGE = LanguageCode.ZH_CN


class I18nManager:
    """国际化管理器"""
    
    def __init__(self, translations_dir: Optional[str] = None):
        """
        初始化国际化管理器
        
        Args:
            translations_dir: 翻译文件目录路径
        """
        if translations_dir is None:
            # 默认使用项目目录下的 translations
            translations_dir = Path(__file__).parent.parent / "translations"
        
        self.translations_dir = Path(translations_dir)
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._current_language: LanguageCode = DEFAULT_LANGUAGE
        
        # 加载翻译文件
        self._load_translations()
    
    def _load_translations(self):
        """加载所有翻译文件"""
        if not self.translations_dir.exists():
            logger.warning(f"翻译目录不存在: {self.translations_dir}")
            # 创建翻译目录和默认翻译文件
            self._create_default_translations()
            return
        
        for lang_file in self.translations_dir.glob("*.json"):
            try:
                lang_code = lang_file.stem
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self._translations[lang_code] = json.load(f)
                logger.debug(f"已加载翻译文件: {lang_code}")
            except Exception as e:
                logger.error(f"加载翻译文件失败 {lang_file}: {e}")
    
    def _create_default_translations(self):
        """创建默认翻译文件"""
        self.translations_dir.mkdir(parents=True, exist_ok=True)
        
        # 简体中文翻译
        zh_cn = {
            "app": {
                "name": "AI热点监控工具",
                "description": "智能监控AI领域热点资讯"
            },
            "common": {
                "confirm": "确认",
                "cancel": "取消",
                "save": "保存",
                "delete": "删除",
                "edit": "编辑",
                "add": "添加",
                "search": "搜索",
                "refresh": "刷新",
                "loading": "加载中...",
                "success": "成功",
                "error": "错误",
                "warning": "警告",
                "info": "信息",
                "yes": "是",
                "no": "否",
                "submit": "提交",
                "close": "关闭",
                "back": "返回",
                "next": "下一步",
                "previous": "上一步"
            },
            "nav": {
                "dashboard": "仪表盘",
                "hotspots": "热点列表",
                "realtime": "实时流",
                "urgent": "紧急热点",
                "keywords": "监控词",
                "settings": "设置",
                "logout": "退出登录"
            },
            "hotspot": {
                "title": "标题",
                "source": "来源",
                "category": "分类",
                "sentiment": "情感",
                "hot_score": "热度",
                "views": "浏览量",
                "interactions": "互动量",
                "publish_time": "发布时间",
                "crawl_time": "抓取时间",
                "summary": "摘要",
                "keywords": "关键词",
                "ai_analysis": "AI分析",
                "is_urgent": "紧急热点",
                "urgent_score": "紧急分数",
                "urgent_reason": "紧急原因"
            },
            "category": {
                "technology": "技术",
                "policy": "政策",
                "product": "产品",
                "paper": "论文",
                "industry": "行业应用",
                "other": "其他"
            },
            "sentiment": {
                "positive": "正面",
                "negative": "负面",
                "neutral": "中性"
            },
            "auth": {
                "login": "登录",
                "logout": "退出",
                "username": "用户名",
                "password": "密码",
                "login_success": "登录成功",
                "login_failed": "登录失败",
                "unauthorized": "未授权",
                "forbidden": "禁止访问",
                "invalid_token": "无效的令牌",
                "session_expired": "会话已过期"
            },
            "crawler": {
                "status": "爬虫状态",
                "running": "运行中",
                "stopped": "已停止",
                "last_run": "上次运行",
                "next_run": "下次运行",
                "trigger": "触发抓取",
                "data_sources": "数据源"
            },
            "push": {
                "channels": "推送渠道",
                "test": "测试推送",
                "settings": "推送设置",
                "enabled": "已启用",
                "disabled": "已禁用"
            },
            "export": {
                "title": "导出数据",
                "format": "格式",
                "csv": "CSV",
                "excel": "Excel",
                "json": "JSON",
                "download": "下载",
                "select_fields": "选择字段",
                "date_range": "日期范围",
                "filters": "筛选条件"
            },
            "messages": {
                "created": "创建成功",
                "updated": "更新成功",
                "deleted": "删除成功",
                "operation_failed": "操作失败",
                "confirm_delete": "确认删除？",
                "no_data": "暂无数据",
                "load_error": "加载失败"
            }
        }
        
        # 英文翻译
        en = {
            "app": {
                "name": "AI Hotspot Monitor",
                "description": "Intelligent monitoring of AI industry hotspots"
            },
            "common": {
                "confirm": "Confirm",
                "cancel": "Cancel",
                "save": "Save",
                "delete": "Delete",
                "edit": "Edit",
                "add": "Add",
                "search": "Search",
                "refresh": "Refresh",
                "loading": "Loading...",
                "success": "Success",
                "error": "Error",
                "warning": "Warning",
                "info": "Info",
                "yes": "Yes",
                "no": "No",
                "submit": "Submit",
                "close": "Close",
                "back": "Back",
                "next": "Next",
                "previous": "Previous"
            },
            "nav": {
                "dashboard": "Dashboard",
                "hotspots": "Hotspots",
                "realtime": "Realtime",
                "urgent": "Urgent",
                "keywords": "Keywords",
                "settings": "Settings",
                "logout": "Logout"
            },
            "hotspot": {
                "title": "Title",
                "source": "Source",
                "category": "Category",
                "sentiment": "Sentiment",
                "hot_score": "Hot Score",
                "views": "Views",
                "interactions": "Interactions",
                "publish_time": "Publish Time",
                "crawl_time": "Crawl Time",
                "summary": "Summary",
                "keywords": "Keywords",
                "ai_analysis": "AI Analysis",
                "is_urgent": "Urgent",
                "urgent_score": "Urgent Score",
                "urgent_reason": "Urgent Reason"
            },
            "category": {
                "technology": "Technology",
                "policy": "Policy",
                "product": "Product",
                "paper": "Paper",
                "industry": "Industry",
                "other": "Other"
            },
            "sentiment": {
                "positive": "Positive",
                "negative": "Negative",
                "neutral": "Neutral"
            },
            "auth": {
                "login": "Login",
                "logout": "Logout",
                "username": "Username",
                "password": "Password",
                "login_success": "Login successful",
                "login_failed": "Login failed",
                "unauthorized": "Unauthorized",
                "forbidden": "Forbidden",
                "invalid_token": "Invalid token",
                "session_expired": "Session expired"
            },
            "crawler": {
                "status": "Crawler Status",
                "running": "Running",
                "stopped": "Stopped",
                "last_run": "Last Run",
                "next_run": "Next Run",
                "trigger": "Trigger Crawl",
                "data_sources": "Data Sources"
            },
            "push": {
                "channels": "Push Channels",
                "test": "Test Push",
                "settings": "Push Settings",
                "enabled": "Enabled",
                "disabled": "Disabled"
            },
            "export": {
                "title": "Export Data",
                "format": "Format",
                "csv": "CSV",
                "excel": "Excel",
                "json": "JSON",
                "download": "Download",
                "select_fields": "Select Fields",
                "date_range": "Date Range",
                "filters": "Filters"
            },
            "messages": {
                "created": "Created successfully",
                "updated": "Updated successfully",
                "deleted": "Deleted successfully",
                "operation_failed": "Operation failed",
                "confirm_delete": "Confirm delete?",
                "no_data": "No data",
                "load_error": "Failed to load"
            }
        }
        
        # 繁体中文翻译
        zh_tw = {
            "app": {
                "name": "AI熱點監控工具",
                "description": "智能監控AI領域熱點資訊"
            },
            "common": {
                "confirm": "確認",
                "cancel": "取消",
                "save": "儲存",
                "delete": "刪除",
                "edit": "編輯",
                "add": "新增",
                "search": "搜尋",
                "refresh": "重新整理",
                "loading": "載入中...",
                "success": "成功",
                "error": "錯誤",
                "warning": "警告",
                "info": "資訊",
                "yes": "是",
                "no": "否",
                "submit": "提交",
                "close": "關閉",
                "back": "返回",
                "next": "下一步",
                "previous": "上一步"
            },
            "nav": {
                "dashboard": "儀表板",
                "hotspots": "熱點列表",
                "realtime": "即時流",
                "urgent": "緊急熱點",
                "keywords": "監控詞",
                "settings": "設定",
                "logout": "登出"
            },
            "hotspot": {
                "title": "標題",
                "source": "來源",
                "category": "分類",
                "sentiment": "情感",
                "hot_score": "熱度",
                "views": "瀏覽量",
                "interactions": "互動量",
                "publish_time": "發布時間",
                "crawl_time": "抓取時間",
                "summary": "摘要",
                "keywords": "關鍵詞",
                "ai_analysis": "AI分析",
                "is_urgent": "緊急熱點",
                "urgent_score": "緊急分數",
                "urgent_reason": "緊急原因"
            },
            "category": {
                "technology": "技術",
                "policy": "政策",
                "product": "產品",
                "paper": "論文",
                "industry": "產業應用",
                "other": "其他"
            },
            "sentiment": {
                "positive": "正面",
                "negative": "負面",
                "neutral": "中性"
            },
            "auth": {
                "login": "登入",
                "logout": "登出",
                "username": "使用者名稱",
                "password": "密碼",
                "login_success": "登入成功",
                "login_failed": "登入失敗",
                "unauthorized": "未授權",
                "forbidden": "禁止存取",
                "invalid_token": "無效的令牌",
                "session_expired": "工作階段已過期"
            },
            "crawler": {
                "status": "爬蟲狀態",
                "running": "執行中",
                "stopped": "已停止",
                "last_run": "上次執行",
                "next_run": "下次執行",
                "trigger": "觸發抓取",
                "data_sources": "資料來源"
            },
            "push": {
                "channels": "推播管道",
                "test": "測試推播",
                "settings": "推播設定",
                "enabled": "已啟用",
                "disabled": "已停用"
            },
            "export": {
                "title": "匯出資料",
                "format": "格式",
                "csv": "CSV",
                "excel": "Excel",
                "json": "JSON",
                "download": "下載",
                "select_fields": "選擇欄位",
                "date_range": "日期範圍",
                "filters": "篩選條件"
            },
            "messages": {
                "created": "建立成功",
                "updated": "更新成功",
                "deleted": "刪除成功",
                "operation_failed": "操作失敗",
                "confirm_delete": "確認刪除？",
                "no_data": "暫無資料",
                "load_error": "載入失敗"
            }
        }
        
        # 保存翻译文件
        self._save_translation(LanguageCode.ZH_CN.value, zh_cn)
        self._save_translation(LanguageCode.EN.value, en)
        self._save_translation(LanguageCode.ZH_TW.value, zh_tw)
        
        # 加载到内存
        self._translations = {
            LanguageCode.ZH_CN.value: zh_cn,
            LanguageCode.EN.value: en,
            LanguageCode.ZH_TW.value: zh_tw
        }
    
    def _save_translation(self, lang_code: str, data: dict):
        """保存翻译文件"""
        file_path = self.translations_dir / f"{lang_code}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"翻译文件已创建: {file_path}")
        except Exception as e:
            logger.error(f"保存翻译文件失败: {e}")
    
    def set_language(self, language: LanguageCode):
        """设置当前语言"""
        self._current_language = language
        logger.debug(f"语言已切换为: {language}")
    
    def get_language(self) -> LanguageCode:
        """获取当前语言"""
        return self._current_language
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        return [
            {"code": lang.value, "name": self._get_language_name(lang)}
            for lang in LanguageCode
        ]
    
    def _get_language_name(self, lang: LanguageCode) -> str:
        """获取语言显示名称"""
        names = {
            LanguageCode.ZH_CN: "简体中文",
            LanguageCode.EN: "English",
            LanguageCode.ZH_TW: "繁體中文",
            LanguageCode.JA: "日本語",
            LanguageCode.KO: "한국어"
        }
        return names.get(lang, lang.value)
    
    def translate(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        翻译键值为当前语言的文本
        
        Args:
            key: 翻译键值，使用点号分隔，如 "common.confirm"
            default: 默认文本，如果翻译不存在则返回此值
            **kwargs: 用于格式化翻译文本的参数
        
        Returns:
            翻译后的文本
        """
        lang_code = self._current_language.value
        translation = self._translations.get(lang_code, {})
        
        # 遍历键值路径
        keys = key.split('.')
        value = translation
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # 尝试从默认语言获取
                if lang_code != DEFAULT_LANGUAGE.value:
                    return self._translate_from_default(key, default, **kwargs)
                return default or key
        
        # 格式化翻译文本
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return default or key
    
    def _translate_from_default(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """从默认语言获取翻译"""
        translation = self._translations.get(DEFAULT_LANGUAGE.value, {})
        keys = key.split('.')
        value = translation
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default or key
        
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return default or key
    
    def t(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """translate的简写形式"""
        return self.translate(key, default, **kwargs)


# 全局国际化管理器实例
_i18n_manager: Optional[I18nManager] = None


def get_i18n() -> I18nManager:
    """获取国际化管理器实例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def set_language(language: LanguageCode):
    """设置当前语言（便捷函数）"""
    get_i18n().set_language(language)


def translate(key: str, default: Optional[str] = None, **kwargs) -> str:
    """翻译函数（便捷函数）"""
    return get_i18n().translate(key, default, **kwargs)


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """翻译函数简写（便捷函数）"""
    return get_i18n().translate(key, default, **kwargs)


# 语言检测
class LanguageDetector:
    """语言检测器"""
    
    @staticmethod
    def detect_from_header(accept_language: str) -> LanguageCode:
        """
        从HTTP Accept-Language头检测语言
        
        Args:
            accept_language: HTTP Accept-Language 头值
        
        Returns:
            检测到的语言代码
        """
        if not accept_language:
            return DEFAULT_LANGUAGE
        
        # 解析语言优先级列表
        languages = []
        for lang in accept_language.split(','):
            parts = lang.strip().split(';')
            code = parts[0].strip()
            q = 1.0
            if len(parts) > 1 and parts[1].startswith('q='):
                try:
                    q = float(parts[1][2:])
                except ValueError:
                    q = 1.0
            languages.append((code, q))
        
        # 按优先级排序
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # 匹配语言
        lang_map = {
            'zh-CN': LanguageCode.ZH_CN,
            'zh': LanguageCode.ZH_CN,
            'zh-TW': LanguageCode.ZH_TW,
            'zh-HK': LanguageCode.ZH_TW,
            'en': LanguageCode.EN,
            'en-US': LanguageCode.EN,
            'en-GB': LanguageCode.EN,
            'ja': LanguageCode.JA,
            'ja-JP': LanguageCode.JA,
            'ko': LanguageCode.KO,
            'ko-KR': LanguageCode.KO,
        }
        
        for code, _ in languages:
            if code in lang_map:
                return lang_map[code]
        
        return DEFAULT_LANGUAGE
