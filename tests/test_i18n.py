"""
多语言国际化功能测试
"""

import pytest
from core.i18n import I18nManager, LanguageCode, LanguageDetector


class TestI18nManager:
    """测试国际化管理器"""

    @pytest.fixture
    def i18n(self):
        """国际化管理器fixture"""
        manager = I18nManager()
        manager.set_language(LanguageCode.ZH_CN)
        return manager

    def test_translate_zh_cn(self, i18n):
        """测试简体中文翻译"""
        result = i18n.translate("common.confirm")
        assert result == "确认"

    def test_translate_en(self, i18n):
        """测试英文翻译"""
        i18n.set_language(LanguageCode.EN)
        result = i18n.translate("common.confirm")
        assert result == "Confirm"


class TestLanguageDetector:
    """测试语言检测器"""

    def test_detect_chinese(self):
        """检测中文"""
        result = LanguageDetector.detect_from_header("zh-CN,zh;q=0.9,en;q=0.8")
        assert result == LanguageCode.ZH_CN

    def test_detect_english(self):
        """检测英文"""
        result = LanguageDetector.detect_from_header("en-US,en;q=0.9")
        assert result == LanguageCode.EN
