"""
筛选模块单元测试
"""

import pytest
from datetime import datetime

from core.filter.analyzer import AIFilterEngine, HotspotAnalyzer
from core.filter.sentiment import SentimentAnalyzer, SentimentType
from core.filter.classifier import CategoryClassifier


class TestAIFilterEngine:
    """AI筛选引擎测试"""
    
    def setup_method(self):
        self.engine = AIFilterEngine()
    
    def test_keyword_match_exact(self):
        """测试精确关键词匹配"""
        text = "这是关于人工智能和深度学习的文章"
        is_match, score, keywords = self.engine.keyword_match(text)
        
        assert is_match is True
        assert score > 0
        assert len(keywords) > 0
        assert "人工智能" in keywords or "深度学习" in keywords
    
    def test_keyword_match_fuzzy(self):
        """测试模糊关键词匹配"""
        text = "这是关于AI的文章"
        is_match, score, keywords = self.engine.keyword_match(text)
        
        assert is_match is True
        assert "AI" in keywords or "智能" in keywords
    
    def test_keyword_match_exclude(self):
        """测试排除词过滤"""
        text = "这是一个游戏AI作弊工具"
        is_match, score, keywords = self.engine.keyword_match(text)
        
        # 包含排除词应该返回False
        assert is_match is False
    
    def test_calculate_hot_score(self):
        """测试热度计算"""
        score_result = self.engine.calculate_hot_score(
            views=1000,
            interactions=500,
            publish_time=datetime.now(),
            keyword_score=3.0
        )
        
        assert score_result.total_score > 0
        assert score_result.is_hot is True or score_result.is_hot is False
    
    def test_filter_hotspot(self):
        """测试热点筛选"""
        hotspot_data = {
            "title": "OpenAI发布新模型",
            "summary": "这是一个关于大模型的重要突破",
            "url": "https://example.com/news/1",
            "views": 10000,
            "interactions": 5000
        }
        
        result = self.engine.filter_hotspot(hotspot_data)
        
        assert result is not None
        assert 'hot_score' in result
        assert 'keywords' in result
    
    def test_filter_hotspot_no_match(self):
        """测试不匹配的热点"""
        hotspot_data = {
            "title": "今天的天气很好",
            "summary": "这是一个普通的新闻",
            "url": "https://example.com/news/1",
            "views": 100,
            "interactions": 10
        }
        
        result = self.engine.filter_hotspot(hotspot_data)
        
        # 应该返回None（不匹配）
        assert result is None


class TestSentimentAnalyzer:
    """情感分析器测试"""
    
    def setup_method(self):
        self.analyzer = SentimentAnalyzer()
    
    def test_analyze_positive(self):
        """测试正面情感分析"""
        text = "这是一个优秀的成果，非常成功"
        result = self.analyzer.analyze(text)
        
        assert result['sentiment'] == SentimentType.POSITIVE.value
        assert result['positive_score'] > result['negative_score']
    
    def test_analyze_negative(self):
        """测试负面情感分析"""
        text = "这个项目失败了，存在问题"
        result = self.analyzer.analyze(text)
        
        assert result['sentiment'] == SentimentType.NEGATIVE.value
        assert result['negative_score'] > result['positive_score']
    
    def test_analyze_neutral(self):
        """测试中性情感分析"""
        text = "这是一个普通的新闻报道"
        result = self.analyzer.analyze(text)
        
        assert result['sentiment'] == SentimentType.NEUTRAL.value
    
    def test_analyze_empty(self):
        """测试空文本"""
        result = self.analyzer.analyze("")
        
        assert result['sentiment'] == SentimentType.NEUTRAL.value
        assert result['confidence'] == 0.0


class TestCategoryClassifier:
    """分类器测试"""
    
    def setup_method(self):
        self.classifier = CategoryClassifier()
    
    def test_classify_technology(self):
        """测试技术分类"""
        text = "这篇论文提出了新的神经网络算法"
        category, confidence = self.classifier.classify(text)
        
        assert category == "技术"
        assert confidence > 0
    
    def test_classify_product(self):
        """测试产品分类"""
        text = "公司发布了新产品"
        category, confidence = self.classifier.classify(text)
        
        assert category == "产品"
    
    def test_classify_empty(self):
        """测试空文本"""
        category, confidence = self.classifier.classify("")
        
        assert category == "其他"
        assert confidence == 0.0
    
    def test_classify_multi(self):
        """测试多标签分类"""
        text = "这是一个关于人工智能技术的研究论文"
        results = self.classifier.classify_multi(text, top_k=2)

        assert len(results) <= 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


class TestHotspotAnalyzer:
    """热点综合分析器测试"""
    
    def setup_method(self):
        self.analyzer = HotspotAnalyzer()
    
    def test_analyze_hotspot(self):
        """测试综合分析"""
        hotspot_data = {
            "title": "OpenAI突破性进展",
            "summary": "这是一个革命性的创新，获得了广泛好评",
            "source": "测试来源",
            "url": "https://example.com/news/1",
            "views": 10000,
            "interactions": 5000,
            "publish_time": datetime.now()
        }
        
        result = self.analyzer.analyze(hotspot_data)
        
        assert result is not None
        assert 'hot_score' in result
        assert 'sentiment' in result
        assert 'category' in result
    
    def test_get_trend(self):
        """测试趋势计算"""
        hotspots = [
            {'crawl_time': datetime.now(), 'hot_score': 100},
            {'crawl_time': datetime.now(), 'hot_score': 150},
        ]
        
        trend = self.analyzer.get_trend(hotspots, days=7)
        
        assert isinstance(trend, list)
