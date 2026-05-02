"""
情感分析模块 - 支持多种引擎
"""

from typing import Dict, List
from enum import Enum
from loguru import logger


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self, engine: str = "simple"):
        self.engine = engine
        self.positive_words = set()
        self.negative_words = set()
        self._init_dict()
    
    def _init_dict(self):
        """初始化情感词典"""
        # 正面情感词
        self.positive_words = {
            '优秀', '出色', '成功', '突破', '创新', '领先', '第一', '最佳', '卓越',
            '好评', '赞', '棒', '完美', '满意', '喜欢', '推荐', '支持', '肯定',
            '提升', '增长', '进步', '改善', '优化', '升级', '强大', '高效', '稳定',
            '获奖', '荣誉', '里程碑', '重要', '关键', '核心', '革命性', '颠覆',
            # AI领域正面词
            '准确', '智能', '自动化', '精准', '快速', '便捷', '高效能',
            '开源', '免费', '共享', '协作', '贡献', '社区活跃',
        }
        
        # 负面情感词
        self.negative_words = {
            '失败', '错误', '问题', '缺陷', 'bug', '崩溃', '故障',
            '差', '糟糕', '失望', '不满', '抱怨', '批评', '质疑', '争议',
            '下降', '下滑', '亏损', '裁员', '离职', '危机', '风险', '隐患',
            '落后', '过时', '淘汰', '局限', '瓶颈', '困境', '挑战', '困难',
            # AI领域负面词
            '偏见', '歧视', '隐私泄露', '安全风险', '滥用', '伪造',
            '失控', '担忧', '恐惧', '失业', '替代', '威胁',
        }
    
    def analyze(self, text: str) -> Dict:
        """
        分析文本情感
        
        Returns:
            {
                'sentiment': 'positive'/'negative'/'neutral',
                'confidence': 0.0-1.0,
                'positive_score': float,
                'negative_score': float
            }
        """
        if not text:
            return {
                'sentiment': SentimentType.NEUTRAL.value,
                'confidence': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
        
        if self.engine == "simple":
            return self._analyze_simple(text)
        else:
            return self._analyze_simple(text)
    
    def _analyze_simple(self, text: str) -> Dict:
        """简单规则情感分析"""
        text = text.lower()
        
        pos_count = sum(1 for word in self.positive_words if word in text)
        neg_count = sum(1 for word in self.negative_words if word in text)
        
        total = pos_count + neg_count
        if total == 0:
            return {
                'sentiment': SentimentType.NEUTRAL.value,
                'confidence': 0.5,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
        
        pos_ratio = pos_count / total
        neg_ratio = neg_count / total
        
        # 判断情感倾向
        if pos_count > neg_count:
            sentiment = SentimentType.POSITIVE.value
            confidence = min(pos_ratio * 1.5, 1.0)
        elif neg_count > pos_count:
            sentiment = SentimentType.NEGATIVE.value
            confidence = min(neg_ratio * 1.5, 1.0)
        else:
            sentiment = SentimentType.NEUTRAL.value
            confidence = 0.5
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'positive_score': round(pos_count, 2),
            'negative_score': round(neg_count, 2)
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """批量分析"""
        return [self.analyze(text) for text in texts]


class AdvancedSentimentAnalyzer(SentimentAnalyzer):
    """高级情感分析器（支持权重和否定词）"""
    
    def __init__(self):
        super().__init__("advanced")
        self.negation_words = {'不', '没', '无', '非', '莫', '勿', '未', '否', '不是', '没有'}
        self.degree_words = {
            '很': 1.5, '非常': 2.0, '极其': 2.5, '特别': 1.8,
            '稍微': 0.5, '有点': 0.6, '比较': 1.2, '十分': 1.6,
            '最': 2.0, '更': 1.3, '越': 1.3
        }
    
    def _analyze_simple(self, text: str) -> Dict:
        """增强版情感分析"""
        import re
        
        text = text.lower()
        sentences = re.split(r'[。！？.!?]', text)
        
        total_pos = 0
        total_neg = 0
        
        for sentence in sentences:
            pos_score, neg_score = self._analyze_sentence(sentence)
            total_pos += pos_score
            total_neg += neg_score
        
        total = total_pos + total_neg
        if total == 0:
            return {
                'sentiment': SentimentType.NEUTRAL.value,
                'confidence': 0.5,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
        
        pos_ratio = total_pos / total
        neg_ratio = total_neg / total
        
        if total_pos > total_neg:
            sentiment = SentimentType.POSITIVE.value
            confidence = min(pos_ratio, 1.0)
        elif total_neg > total_pos:
            sentiment = SentimentType.NEGATIVE.value
            confidence = min(neg_ratio, 1.0)
        else:
            sentiment = SentimentType.NEUTRAL.value
            confidence = 0.5
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'positive_score': round(total_pos, 2),
            'negative_score': round(total_neg, 2)
        }
    
    def _analyze_sentence(self, sentence: str) -> tuple:
        """分析单句情感"""
        pos_score = 0
        neg_score = 0
        
        # 检查程度词
        degree = 1.0
        for word, factor in self.degree_words.items():
            if word in sentence:
                degree = factor
                break
        
        # 检查否定词（反转后面的情感词）
        has_negation = any(word in sentence for word in self.negation_words)
        
        for word in self.positive_words:
            if word in sentence:
                score = 1.0 * degree
                if has_negation:
                    score = -score  # 否定反转
                pos_score += max(score, 0)
                neg_score += max(-score, 0)
        
        for word in self.negative_words:
            if word in sentence:
                score = 1.0 * degree
                if has_negation:
                    score = -score  # 否定反转
                neg_score += max(score, 0)
                pos_score += max(-score, 0)
        
        return pos_score, neg_score
