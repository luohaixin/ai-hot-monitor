"""
紧急热点检测引擎 - 识别需要立即关注的热点
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .config_loader import get_config
from .models import get_db, HotspotORM


@dataclass
class UrgentCheckResult:
    """紧急检测结果"""
    is_urgent: bool
    urgent_score: float
    urgent_reason: str
    matched_rules: List[str]


class UrgentHotspotDetector:
    """紧急热点检测器"""
    
    # 紧急关键词 - 表示突发、重要事件
    URGENT_KEYWORDS = [
        # 突发类
        "突发", "紧急", "速报", "刚刚", "立即", "即刻",
        "breaking", "urgent", "just now", "immediate",
        # 重要类
        "重磅", "重大", "重要", "震惊", "震撼", "爆炸",
        "重磅发布", "重大突破", "重大进展", "里程碑",
        # 预警类
        "预警", "警报", "危机", "风险", "暴跌", "暴涨",
        "崩盘", "熔断", "历史性", "史无前例",
        # 权威发布类
        "官方发布", "正式发布", "公告", "声明", "官宣",
        # AI领域特定
        "OpenAI发布", "GPT-5", "Claude", "Gemini",
        "Sora", "大模型发布", "AGI", "超级智能",
    ]
    
    # 权威来源 - 来自这些来源的消息更有可能是紧急的
    AUTHORITATIVE_SOURCES = [
        "机器之心", "量子位", "36氪", "品玩",
        "OpenAI Blog", "Google AI", "DeepMind",
        "Anthropic", "Meta AI", "Microsoft Research"
    ]
    
    def __init__(self):
        self.config = get_config()
        self.urgent_config = self.config.get('urgent_hotspot', {})
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式"""
        self.urgent_patterns = [
            re.compile(re.escape(kw), re.IGNORECASE) 
            for kw in self.URGENT_KEYWORDS
        ]
        # 保存原始关键词列表，用于匹配后获取原始关键词
        self._keyword_map = {
            id(pattern): kw for pattern, kw in zip(self.urgent_patterns, self.URGENT_KEYWORDS)
        }
    
    def check_urgent(self, hotspot_data: Dict) -> UrgentCheckResult:
        """
        检测是否为紧急热点
        
        评分规则：
        1. 热度分数超高 (>= 200) -> +50分
        2. 包含紧急关键词 -> 每个+10分
        3. 来自权威来源 -> +20分
        4. 短时间内热度飙升 -> +30分
        5. 包含突破/创新类词汇 + 高热度 -> +25分
        
        阈值：>= 60分为紧急热点
        """
        matched_rules = []
        urgent_score = 0.0
        
        # 规则1: 热度分数检查
        hot_score = hotspot_data.get('hot_score', 0)
        high_threshold = self.urgent_config.get('high_score_threshold', 200)
        if hot_score >= high_threshold:
            urgent_score += 50
            matched_rules.append(f"热度分数超高({hot_score:.1f})")
        elif hot_score >= high_threshold * 0.8:
            urgent_score += 30
            matched_rules.append(f"热度分数很高({hot_score:.1f})")
        
        # 规则2: 紧急关键词检查
        title = hotspot_data.get('title', '')
        summary = hotspot_data.get('summary', '')
        text = f"{title} {summary}"
        
        matched_keywords = []
        for pattern in self.urgent_patterns:
            if pattern.search(text):
                # 使用保存的原始关键词，避免从正则反推导致的转义问题
                keyword = self._keyword_map.get(id(pattern), '')
                if keyword and keyword not in matched_keywords:
                    matched_keywords.append(keyword)
                    urgent_score += 10
        
        if matched_keywords:
            matched_rules.append(f"包含紧急关键词({len(matched_keywords)}个)")
        
        # 规则3: 权威来源检查
        source = hotspot_data.get('source', '')
        if any(auth_source in source for auth_source in self.AUTHORITATIVE_SOURCES):
            urgent_score += 20
            matched_rules.append("来自权威来源")
        
        # 规则4: 突破创新类词汇 + 高热度
        breakthrough_keywords = ['突破', '创新', '首个', '第一', '领先', '里程碑', 'breakthrough']
        has_breakthrough = any(kw in text for kw in breakthrough_keywords)
        if has_breakthrough and hot_score >= 150:
            urgent_score += 25
            matched_rules.append("技术突破+高热度")
        
        # 判断是否为紧急热点
        threshold = self.urgent_config.get('urgent_threshold', 60)
        is_urgent = urgent_score >= threshold
        
        # 生成紧急原因
        if is_urgent:
            if matched_keywords:
                reason = f"检测到紧急关键词 [{', '.join(matched_keywords[:3])}]，"
            else:
                reason = ""
            reason += "；".join(matched_rules)
        else:
            reason = "未达到紧急阈值"
        
        return UrgentCheckResult(
            is_urgent=is_urgent,
            urgent_score=urgent_score,
            urgent_reason=reason,
            matched_rules=matched_rules
        )
    
    def mark_urgent_hotspot(self, hotspot_id: int) -> bool:
        """标记热点为紧急"""
        db = get_db()
        session = db.get_session()
        try:
            hotspot = session.query(HotspotORM).filter_by(id=hotspot_id).first()
            if not hotspot:
                return False
            
            # 检测紧急程度
            hotspot_data = {
                'title': hotspot.title,
                'summary': hotspot.summary or '',
                'source': hotspot.source,
                'hot_score': hotspot.hot_score,
                'views': hotspot.views,
                'interactions': hotspot.interactions
            }
            
            result = self.check_urgent(hotspot_data)
            
            if result.is_urgent:
                hotspot.is_urgent = True
                hotspot.urgent_score = result.urgent_score
                hotspot.urgent_reason = result.urgent_reason
                session.commit()
                logger.info(f"热点 {hotspot_id} 被标记为紧急: {result.urgent_reason}")
                return True
            
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"标记紧急热点失败: {e}")
            return False
        finally:
            session.close()
    
    def scan_and_mark_urgent(self, hours: int = 24) -> List[int]:
        """
        扫描最近的热点并标记紧急热点
        
        Returns:
            新标记的紧急热点ID列表
        """
        db = get_db()
        session = db.get_session()
        urgent_ids = []
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # 获取未标记为紧急的热点
            hotspots = session.query(HotspotORM).filter(
                HotspotORM.crawl_time >= since,
                HotspotORM.is_deleted == False,
                HotspotORM.is_urgent == False
            ).all()
            
            for hotspot in hotspots:
                hotspot_data = {
                    'title': hotspot.title,
                    'summary': hotspot.summary or '',
                    'source': hotspot.source,
                    'hot_score': hotspot.hot_score,
                    'views': hotspot.views,
                    'interactions': hotspot.interactions
                }
                
                result = self.check_urgent(hotspot_data)
                
                if result.is_urgent:
                    hotspot.is_urgent = True
                    hotspot.urgent_score = result.urgent_score
                    hotspot.urgent_reason = result.urgent_reason
                    urgent_ids.append(hotspot.id)
            
            session.commit()
            
            if urgent_ids:
                logger.info(f"扫描发现 {len(urgent_ids)} 个新的紧急热点")
            
            return urgent_ids
            
        except Exception as e:
            session.rollback()
            logger.error(f"扫描紧急热点失败: {e}")
            return []
        finally:
            session.close()
    
    def get_urgent_hotspots(
        self, 
        limit: int = 20, 
        include_acknowledged: bool = False,
        min_score: float = None
    ) -> List[HotspotORM]:
        """获取紧急热点列表"""
        db = get_db()
        session = db.get_session()
        
        try:
            query = session.query(HotspotORM).filter_by(
                is_urgent=True,
                is_deleted=False
            )
            
            if not include_acknowledged:
                query = query.filter_by(urgent_acknowledged=False)
            
            if min_score:
                query = query.filter(HotspotORM.urgent_score >= min_score)
            
            hotspots = query.order_by(
                HotspotORM.urgent_score.desc(),
                HotspotORM.crawl_time.desc()
            ).limit(limit).all()
            
            return hotspots
            
        finally:
            session.close()
    
    def acknowledge_urgent(self, hotspot_id: int) -> bool:
        """确认紧急热点（已读）"""
        db = get_db()
        session = db.get_session()
        
        try:
            hotspot = session.query(HotspotORM).filter_by(
                id=hotspot_id,
                is_urgent=True
            ).first()
            
            if not hotspot:
                return False
            
            hotspot.urgent_acknowledged = True
            session.commit()
            logger.info(f"紧急热点 {hotspot_id} 已确认")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"确认紧急热点失败: {e}")
            return False
        finally:
            session.close()
    
    def get_urgent_stats(self) -> Dict:
        """获取紧急热点统计"""
        db = get_db()
        session = db.get_session()
        
        try:
            # 总紧急热点数
            total_urgent = session.query(HotspotORM).filter_by(
                is_urgent=True,
                is_deleted=False
            ).count()
            
            # 未确认的紧急热点
            unacknowledged = session.query(HotspotORM).filter_by(
                is_urgent=True,
                is_deleted=False,
                urgent_acknowledged=False
            ).count()
            
            # 今日紧急热点
            today = datetime.utcnow().date()
            today_urgent = session.query(HotspotORM).filter(
                HotspotORM.is_urgent == True,
                HotspotORM.is_deleted == False,
                HotspotORM.crawl_time >= today
            ).count()
            
            # 平均紧急分数
            avg_score_result = session.query(
                HotspotORM.urgent_score
            ).filter_by(is_urgent=True, is_deleted=False).all()
            
            avg_score = sum(s[0] for s in avg_score_result) / len(avg_score_result) if avg_score_result else 0
            
            return {
                "total_urgent": total_urgent,
                "unacknowledged": unacknowledged,
                "today_urgent": today_urgent,
                "avg_urgent_score": round(avg_score, 2)
            }
            
        finally:
            session.close()


class UrgentPushService:
    """紧急热点推送服务"""
    
    def __init__(self):
        self.detector = UrgentHotspotDetector()
        self.config = get_config()
        self.urgent_config = self.config.get('urgent_hotspot', {})
    
    def push_urgent_hotspot(self, hotspot: HotspotORM, push_service) -> Dict[str, bool]:
        """
        推送紧急热点通知
        
        特点：
        1. 使用特殊标题前缀
        2. 高优先级
        3. 多渠道推送
        4. 包含紧急原因
        """
        title = f"🚨 紧急热点 - {hotspot.title[:50]}"
        
        content_parts = [
            f"⚠️ 紧急程度: {hotspot.urgent_score:.0f}/100",
            f"📊 热度分数: {hotspot.hot_score:.1f}",
            f"🏷️ 分类: {hotspot.category}",
            f"📰 来源: {hotspot.source}",
            "",
            f"📝 紧急原因: {hotspot.urgent_reason}",
            "",
            f"📄 {hotspot.summary[:200] if hotspot.summary else '无摘要'}...",
            "",
            f"🔗 {hotspot.url}"
        ]
        
        content = "\n".join(content_parts)
        
        # 获取启用的所有渠道
        channels = None  # None表示使用所有启用的渠道
        
        # 执行推送
        results = push_service.send(
            title=title,
            content=content,
            channels=channels,
            priority='high',
            tags='urgent,hotspot,alert'
        )
        
        # 更新推送时间
        if any(results.values()):
            db = get_db()
            session = db.get_session()
            try:
                hotspot.urgent_pushed_at = datetime.utcnow()
                session.commit()
            except:
                session.rollback()
            finally:
                session.close()
        
        return results
    
    def check_and_push_urgent(self, push_service) -> int:
        """
        检查并推送未确认的紧急热点
        
        Returns:
            推送的热点数量
        """
        # 获取未推送的紧急热点
        unacknowledged = self.detector.get_urgent_hotspots(
            limit=10,
            include_acknowledged=False
        )
        
        # 筛选出未推送或超过重复提醒间隔的
        now = datetime.utcnow()
        remind_interval = self.urgent_config.get('remind_interval_minutes', 30)
        
        hotspots_to_push = []
        for hotspot in unacknowledged:
            if hotspot.urgent_pushed_at is None:
                hotspots_to_push.append(hotspot)
            elif (now - hotspot.urgent_pushed_at).total_seconds() / 60 >= remind_interval:
                hotspots_to_push.append(hotspot)
        
        # 推送
        pushed_count = 0
        for hotspot in hotspots_to_push:
            results = self.push_urgent_hotspot(hotspot, push_service)
            if any(results.values()):
                pushed_count += 1
        
        if pushed_count > 0:
            logger.info(f"紧急热点推送完成: {pushed_count} 条")
        
        return pushed_count
