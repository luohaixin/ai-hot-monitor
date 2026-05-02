"""
热点预测模块 - 基于历史数据的热度趋势预测
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from loguru import logger

from ..models import HotspotORM
from ..config_loader import get_config


class TrendPredictor:
    """热点趋势预测器"""

    def __init__(self):
        self.config = get_config()

    def predict_category_trend(
        self,
        session,
        category: Optional[str] = None,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        预测特定分类的未来热度趋势

        Args:
            session: 数据库会话
            category: 分类名称，None表示全部
            hours_ahead: 预测多少小时后的趋势

        Returns:
            预测结果字典
        """
        query = session.query(HotspotORM).filter_by(is_deleted=False)
        if category:
            query = query.filter_by(category=category)

        items = query.order_by(HotspotORM.crawl_time.desc()).limit(200).all()

        if len(items) < 5:
            return {
                "prediction": None,
                "confidence": 0,
                "reason": "样本数量不足，需要至少5条数据"
            }

        scores = [h.hot_score for h in items]
        dates = [h.crawl_time for h in items if h.crawl_time]

        score_trend = self._analyze_trend(scores)
        time_pattern = self._analyze_time_pattern(dates)

        predicted_score = self._calculate_prediction(scores, score_trend, hours_ahead)

        confidence = min(0.95, 0.4 + len(items) * 0.005 + score_trend["stability"] * 0.2)

        return {
            "prediction": {
                "predicted_avg_score": round(predicted_score["avg_score"], 2),
                "predicted_max_score": round(predicted_score["max_score"], 2),
                "predicted_count": round(predicted_score["estimated_count"], 0),
                "trend": predicted_score["trend"],
                "category": category or "全部",
                "hours_ahead": hours_ahead,
            },
            "analysis": {
                "sample_count": len(items),
                "current_avg_score": round(sum(scores) / len(scores), 2),
                "current_max_score": max(scores),
                "score_trend": score_trend,
                "time_pattern": time_pattern,
            },
            "confidence": round(confidence, 2)
        }

    def predict_keyword_trend(
        self,
        session,
        keyword: str,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        预测特定关键词的未来热度

        Args:
            session: 数据库会话
            keyword: 关键词
            hours_ahead: 预测小时数

        Returns:
            预测结果
        """
        items = session.query(HotspotORM).filter(
            HotspotORM.is_deleted == False,
            (HotspotORM.title.contains(keyword) | HotspotORM.summary.contains(keyword))
        ).order_by(
            HotspotORM.crawl_time.desc()
        ).limit(100).all()

        if len(items) < 3:
            return {
                "prediction": None,
                "confidence": 0,
                "reason": f"关键词'{keyword}'的样本不足"
            }

        scores = [h.hot_score for h in items]
        score_trend = self._analyze_trend(scores)

        predicted_score = self._calculate_prediction(scores, score_trend, hours_ahead)

        return {
            "prediction": {
                "keyword": keyword,
                "predicted_avg_score": round(predicted_score["avg_score"], 2),
                "trend": predicted_score["trend"],
                "hours_ahead": hours_ahead,
            },
            "analysis": {
                "matching_items": len(items),
                "current_avg_score": round(sum(scores) / len(scores), 2),
            },
            "confidence": round(min(0.85, 0.3 + len(items) * 0.01), 2)
        }

    def _analyze_trend(self, scores: List[float]) -> Dict[str, Any]:
        """分析评分趋势"""
        if len(scores) < 2:
            return {"direction": "stable", "slope": 0, "stability": 0.5}

        n = len(scores)
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n

        numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        variance = sum((s - y_mean) ** 2 for s in scores) / n
        std_dev = math.sqrt(variance)

        stability = 1 / (1 + std_dev / max(y_mean, 1))

        if slope > y_mean * 0.05:
            direction = "rising"
        elif slope < -y_mean * 0.05:
            direction = "falling"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "slope": round(slope, 4),
            "stability": round(stability, 2),
            "variance": round(variance, 2)
        }

    def _analyze_time_pattern(self, dates: List[datetime]) -> Dict[str, Any]:
        """分析时间模式"""
        if not dates:
            return {"pattern": "unknown", "peak_hours": []}

        hour_counts = defaultdict(int)
        for d in dates:
            if d:
                hour_counts[d.hour] += 1

        if not hour_counts:
            return {"pattern": "unknown", "peak_hours": []}

        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [h for h, _ in sorted_hours[:3]]

        return {
            "pattern": "hourly" if len(hour_counts) > 1 else "sparse",
            "peak_hours": peak_hours,
            "total_hours_with_data": len(hour_counts)
        }

    def _calculate_prediction(
        self,
        scores: List[float],
        trend: Dict[str, Any],
        hours_ahead: int
    ) -> Dict[str, Any]:
        """计算预测值"""
        current_avg = sum(scores) / len(scores)
        current_max = max(scores)

        trend_multiplier = {
            "rising": 1.15,
            "stable": 1.0,
            "falling": 0.85
        }.get(trend["direction"], 1.0)

        hours_factor = 1 + (hours_ahead / 240) * 0.1

        predicted_avg = current_avg * trend_multiplier * hours_factor
        predicted_max = current_max * trend_multiplier * hours_factor

        estimated_count = len(scores) * (1.05 if trend["direction"] == "rising" else 0.95)

        return {
            "avg_score": min(predicted_avg, 500),
            "max_score": min(predicted_max, 1000),
            "estimated_count": estimated_count,
            "trend": trend["direction"]
        }

    def detect_emerging_topics(
        self,
        session,
        hours_window: int = 48
    ) -> List[Dict[str, Any]]:
        """
        检测新兴热点话题

        Args:
            session: 数据库会话
            hours_window: 检测时间窗口（小时）

        Returns:
            新兴话题列表
        """
        since = datetime.utcnow() - timedelta(hours=hours_window)

        recent_items = session.query(HotspotORM).filter(
            HotspotORM.is_deleted == False,
            HotspotORM.crawl_time >= since
        ).all()

        keyword_counts = defaultdict(lambda: {"count": 0, "total_score": 0, "items": []})

        for item in recent_items:
            if item.keywords:
                for kw in item.keywords.split(","):
                    kw = kw.strip()
                    if kw:
                        keyword_counts[kw]["count"] += 1
                        keyword_counts[kw]["total_score"] += item.hot_score
                        keyword_counts[kw]["items"].append(item.title)

        emerging = []
        for kw, data in keyword_counts.items():
            if data["count"] >= 2:
                avg_score = data["total_score"] / data["count"]
                velocity = data["count"] / hours_window

                emerging.append({
                    "keyword": kw,
                    "mention_count": data["count"],
                    "avg_score": round(avg_score, 2),
                    "velocity": round(velocity, 2),
                    "sample_titles": list(set(data["items"]))[:3],
                    "urgency": "high" if velocity > 0.1 and avg_score > 100 else "medium" if velocity > 0.05 else "low"
                })

        emerging.sort(key=lambda x: (x["velocity"], x["avg_score"]), reverse=True)

        return emerging[:10]


class HotspotForecaster:
    """热点预测服务封装"""

    def __init__(self):
        self.predictor = TrendPredictor()

    def get_forecast(
        self,
        session,
        forecast_type: str = "category",
        target: Optional[str] = None,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        获取预测结果

        Args:
            session: 数据库会话
            forecast_type: 预测类型 ("category" | "keyword")
            target: 目标值（分类名或关键词）
            hours_ahead: 预测小时数

        Returns:
            预测结果
        """
        try:
            if forecast_type == "category":
                return self.predictor.predict_category_trend(
                    session, target, hours_ahead
                )
            elif forecast_type == "keyword":
                if not target:
                    return {"error": "Keyword is required for keyword forecast"}
                return self.predictor.predict_keyword_trend(
                    session, target, hours_ahead
                )
            else:
                return {"error": f"Unknown forecast type: {forecast_type}"}
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return {"error": str(e)}

    def get_emerging_alerts(self, session) -> List[Dict[str, Any]]:
        """获取新兴热点警报"""
        try:
            return self.predictor.detect_emerging_topics(session)
        except Exception as e:
            logger.error(f"Emerging detection error: {e}")
            return []
