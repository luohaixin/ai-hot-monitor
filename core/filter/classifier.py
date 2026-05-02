"""
分类器模块 - 自动分类热点
"""

from typing import Dict, List, Tuple
from collections import defaultdict
from loguru import logger


class CategoryClassifier:
    """热点分类器"""
    
    CATEGORIES = {
        "技术": {
            "keywords": ["算法", "模型", "框架", "代码", "开源", "论文", "研究", "架构", 
                        "优化", "训练", "推理", "部署", "API", "SDK", "工具库", "GitHub"],
            "weight": 1.0
        },
        "政策": {
            "keywords": ["政策", "法规", "监管", "标准", "政府", "工信部", "网信办", 
                        "立法", "合规", "规范", "指引", "发布", "出台", "国家"],
            "weight": 1.0
        },
        "产品": {
            "keywords": ["发布", "上线", "产品", "应用", "平台", "工具", "服务", "功能",
                        "版本", "更新", "升级", "推出", "亮相", "Demo", "测试版"],
            "weight": 1.0
        },
        "论文": {
            "keywords": ["论文", "ArXiv", "期刊", "会议", "CVPR", "NeurIPS", "ICML", 
                        "ICLR", "AAAI", "ACL", "EMNLP", "顶会", "发表", "引用", "SOTA"],
            "weight": 1.0
        },
        "行业应用": {
            "keywords": ["医疗", "金融", "教育", "自动驾驶", "机器人", "制造", "零售",
                        "客服", "营销", "安防", "农业", "能源", "物流", "交通"],
            "weight": 1.0
        },
        "投资融资": {
            "keywords": ["融资", "投资", "估值", "上市", "IPO", "并购", "收购", 
                        "轮融资", "独角兽", "资本", "VC", "PE", "股价", "市值"],
            "weight": 1.0
        },
        "人才动态": {
            "keywords": ["人才", "招聘", "求职", "跳槽", "离职", "加入", "任命", 
                        "专家", "学者", "教授", "博士", "研究员", "工程师"],
            "weight": 1.0
        }
    }
    
    def __init__(self):
        self.categories = self.CATEGORIES.copy()
    
    def classify(self, text: str) -> Tuple[str, float]:
        """
        对文本进行分类
        
        Returns:
            (分类名称, 置信度)
        """
        if not text:
            return "其他", 0.0
        
        text = text.lower()
        scores = defaultdict(float)
        
        for category, config in self.categories.items():
            weight = config.get("weight", 1.0)
            keywords = config.get("keywords", [])
            
            for keyword in keywords:
                if keyword in text:
                    scores[category] += weight
        
        if not scores:
            return "其他", 0.0
        
        # 获取最高分分类
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        # 计算置信度
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0
        
        return best_category, round(confidence, 2)
    
    def classify_multi(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        多标签分类，返回top_k个分类
        """
        if not text:
            return [("其他", 0.0)]
        
        text = text.lower()
        scores = defaultdict(float)
        
        for category, config in self.categories.items():
            weight = config.get("weight", 1.0)
            keywords = config.get("keywords", [])
            
            for keyword in keywords:
                if keyword in text:
                    scores[category] += weight
        
        if not scores:
            return [("其他", 0.0)]
        
        # 排序并返回top_k
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        total = sum(s[1] for s in sorted_scores)
        
        result = []
        for category, score in sorted_scores[:top_k]:
            confidence = score / total if total > 0 else 0.0
            result.append((category, round(confidence, 2)))
        
        return result
    
    def batch_classify(self, texts: List[str]) -> List[Tuple[str, float]]:
        """批量分类"""
        return [self.classify(text) for text in texts]
    
    def get_category_keywords(self, category: str) -> List[str]:
        """获取分类的关键词"""
        if category in self.categories:
            return self.categories[category].get("keywords", [])
        return []
    
    def add_category(self, name: str, keywords: List[str], weight: float = 1.0):
        """添加新分类"""
        self.categories[name] = {
            "keywords": keywords,
            "weight": weight
        }
        logger.info(f"添加新分类: {name}")
    
    def update_keywords(self, category: str, keywords: List[str]):
        """更新分类关键词"""
        if category in self.categories:
            self.categories[category]["keywords"] = keywords
            logger.info(f"更新分类关键词: {category}")
