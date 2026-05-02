"""
紧急热点检测器测试
"""

import pytest
from datetime import datetime

from core.urgent_detector import UrgentHotspotDetector, UrgentCheckResult


class TestUrgentHotspotDetector:
    """测试紧急热点检测器"""
    
    @pytest.fixture
    def detector(self):
        return UrgentHotspotDetector()
    
    def test_init(self, detector):
        """测试初始化"""
        assert detector is not None
        assert len(detector.URGENT_KEYWORDS) > 0
        assert len(detector.AUTHORITATIVE_SOURCES) > 0
    
    def test_check_urgent_with_high_score(self, detector):
        """测试高热度分数触发紧急"""
        hotspot_data = {
            'title': '测试标题 突发 重大',
            'summary': '测试摘要 突破 震惊',
            'source': '测试来源',
            'hot_score': 250,
            'views': 10000,
            'interactions': 500
        }
        
        result = detector.check_urgent(hotspot_data)
        
        # 高热度 + 多个紧急关键词应该触发紧急
        assert result.is_urgent is True
        assert result.urgent_score >= 60
        assert '热度分数超高' in result.matched_rules[0]
    
    def test_check_urgent_with_urgent_keywords(self, detector):
        """测试紧急关键词触发"""
        hotspot_data = {
            'title': '重大突破！OpenAI发布GPT-5',
            'summary': '这是一个人工智能的重大里程碑事件',
            'source': '机器之心',
            'hot_score': 150,
            'views': 5000,
            'interactions': 300
        }
        
        result = detector.check_urgent(hotspot_data)
        
        assert result.is_urgent is True
        assert result.urgent_score >= 60
        assert '重大突破' in result.matched_rules[0] or '紧急关键词' in result.urgent_reason
    
    def test_check_urgent_with_authoritative_source(self, detector):
        """测试权威来源加分"""
        hotspot_data = {
            'title': '突发：OpenAI发布重要更新',
            'summary': '重要更新内容',
            'source': '机器之心',
            'hot_score': 180,
            'views': 8000,
            'interactions': 400
        }
        
        result = detector.check_urgent(hotspot_data)
        
        assert result.is_urgent is True
        assert any('权威来源' in rule for rule in result.matched_rules)
    
    def test_check_urgent_with_breakthrough(self, detector):
        """测试技术突破+高热度触发"""
        hotspot_data = {
            'title': '中国团队实现重大技术突破',
            'summary': '这是一个历史性时刻',
            'source': '某科技媒体',
            'hot_score': 160,
            'views': 6000,
            'interactions': 350
        }
        
        result = detector.check_urgent(hotspot_data)
        
        assert result.is_urgent is True
        assert any('技术突破' in rule for rule in result.matched_rules)
    
    def test_check_not_urgent(self, detector):
        """测试非紧急热点"""
        hotspot_data = {
            'title': '普通的AI技术文章',
            'summary': '这是一篇普通的技术文章',
            'source': '普通博客',
            'hot_score': 50,
            'views': 100,
            'interactions': 10
        }
        
        result = detector.check_urgent(hotspot_data)
        
        assert result.is_urgent is False
        assert result.urgent_score < 60
    
    def test_multiple_urgent_keywords(self, detector):
        """测试多个紧急关键词"""
        hotspot_data = {
            'title': '突发！紧急发布！重磅消息震惊业界 里程碑',
            'summary': '这是一个紧急且重要的事件 突破',
            'source': '机器之心',  # 权威来源额外加20分
            'hot_score': 140,
            'views': 3000,
            'interactions': 200
        }

        result = detector.check_urgent(hotspot_data)

        assert result.is_urgent is True
        # 应该匹配多个紧急关键词 + 权威来源
        assert result.urgent_score >= 60  # 至少6个关键词(60分) + 权威来源(20分)


class TestUrgentCheckResult:
    """测试紧急检测结果数据类"""
    
    def test_dataclass_creation(self):
        """测试数据类创建"""
        result = UrgentCheckResult(
            is_urgent=True,
            urgent_score=75.0,
            urgent_reason="测试原因",
            matched_rules=["规则1", "规则2"]
        )
        
        assert result.is_urgent is True
        assert result.urgent_score == 75.0
        assert result.urgent_reason == "测试原因"
        assert len(result.matched_rules) == 2


class TestUrgentKeywords:
    """测试紧急关键词列表"""
    
    def test_urgent_keywords_coverage(self):
        """测试紧急关键词覆盖范围"""
        detector = UrgentHotspotDetector()
        
        # 检查是否包含各类关键词
        keywords = detector.URGENT_KEYWORDS
        
        # 突发类
        assert any(kw in keywords for kw in ['突发', '紧急', 'breaking'])
        
        # 重要类
        assert any(kw in keywords for kw in ['重磅', '重大', '里程碑'])
        
        # AI领域特定
        assert any(kw in keywords for kw in ['OpenAI发布', 'GPT-5', 'AGI'])


class TestAuthoritativeSources:
    """测试权威来源列表"""
    
    def test_authoritative_sources(self):
        """测试权威来源列表"""
        detector = UrgentHotspotDetector()
        
        sources = detector.AUTHORITATIVE_SOURCES
        
        # 检查是否包含主要AI媒体
        assert '机器之心' in sources
        assert '量子位' in sources
        assert '36氪' in sources
