"""
数据模型定义 - 使用SQLAlchemy ORM
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel, Field, ConfigDict
import enum

Base = declarative_base()


class SentimentType(str, enum.Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CategoryType(str, enum.Enum):
    """热点分类"""
    TECHNOLOGY = "技术"
    POLICY = "政策"
    PRODUCT = "产品"
    PAPER = "论文"
    INDUSTRY = "行业应用"
    OTHER = "其他"


# ========== SQLAlchemy ORM 模型 ==========

class HotspotORM(Base):
    """热点数据表"""
    __tablename__ = "hotspots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)
    url = Column(String(1000), nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # 完整内容
    publish_time = Column(DateTime, nullable=True)
    crawl_time = Column(DateTime, default=datetime.utcnow)
    
    # 热度指标
    hot_score = Column(Float, default=0.0, index=True)
    views = Column(Integer, default=0)
    interactions = Column(Integer, default=0)
    
    # AI分析结果
    sentiment = Column(String(20), default=SentimentType.NEUTRAL.value)
    category = Column(String(50), default=CategoryType.OTHER.value)
    keywords = Column(String(500), nullable=True)  # 逗号分隔的关键词
    
    # AI深度分析字段（V3.1 AI集成新增）
    is_real = Column(Boolean, default=True)  # 内容真实性
    relevance = Column(Integer, default=50)  # 相关性评分 0-100
    relevance_reason = Column(Text, nullable=True)  # 相关性理由
    importance = Column(String(20), default="medium")  # 重要程度 urgent/high/medium/low
    ai_summary = Column(Text, nullable=True)  # AI生成的摘要
    keyword_mentioned = Column(Boolean, default=False)  # 是否明确提及关键词
    matched_keywords = Column(String(500), nullable=True)  # AI匹配的关键词列表
    
    # AI分析理由（新增）
    ai_analysis = Column(Text, nullable=True)  # AI分析理由的JSON字符串
    
    # 紧急热点标记
    is_urgent = Column(Boolean, default=False, index=True)
    urgent_reason = Column(String(200), nullable=True)  # 紧急原因
    urgent_score = Column(Float, default=0.0)  # 紧急程度分数
    urgent_pushed_at = Column(DateTime, nullable=True)  # 紧急推送时间
    urgent_acknowledged = Column(Boolean, default=False)  # 是否已确认
    
    # 状态
    is_pushed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)


class DataSourceORM(Base):
    """数据源状态表"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(String(1000), nullable=False)
    enabled = Column(Boolean, default=True)
    last_crawl_time = Column(DateTime, nullable=True)
    last_status = Column(String(20), default="pending")  # pending/success/failed
    fail_count = Column(Integer, default=0)
    total_items = Column(Integer, default=0)


class SystemLogORM(Base):
    """系统日志表"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserORM(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ========== Pydantic 数据模型 ==========

class HotspotBase(BaseModel):
    """热点基础模型"""
    title: str = Field(..., min_length=1, max_length=500, description="标题")
    source: str = Field(..., min_length=1, max_length=100, description="来源")
    url: str = Field(..., min_length=1, max_length=1000, description="链接")
    summary: Optional[str] = Field(None, max_length=5000, description="摘要")
    content: Optional[str] = Field(None, max_length=50000, description="完整内容")
    publish_time: Optional[datetime] = Field(None, description="发布时间")


class HotspotCreate(HotspotBase):
    """创建热点模型"""
    views: int = Field(0, ge=0, description="浏览量")
    interactions: int = Field(0, ge=0, description="互动量")


class HotspotUpdate(BaseModel):
    """更新热点模型"""
    hot_score: Optional[float] = Field(None, ge=0, description="热度分数")
    sentiment: Optional[SentimentType] = Field(None, description="情感")
    category: Optional[CategoryType] = Field(None, description="分类")
    is_pushed: Optional[bool] = Field(None, description="是否已推送")


class AIAnalysisDetail(BaseModel):
    """AI分析详情"""
    matched_keywords: List[str] = Field(default_factory=list, description="匹配的关键词")
    keyword_match_reason: str = Field("", description="关键词匹配理由")
    sentiment_reason: str = Field("", description="情感分析理由")
    category_reason: str = Field("", description="分类理由")
    hot_score_reason: str = Field("", description="热度评分理由")
    views_score: float = Field(0.0, description="浏览量得分")
    interaction_score: float = Field(0.0, description="互动量得分")
    time_decay_factor: float = Field(0.0, description="时间衰减因子")
    keyword_bonus: float = Field(0.0, description="关键词匹配加分")


class HotspotResponse(HotspotBase):
    """热点响应模型"""
    id: int
    crawl_time: datetime
    hot_score: float
    views: int
    interactions: int
    sentiment: str
    category: str
    keywords: Optional[str]
    content: Optional[str] = None  # 完整内容
    is_pushed: bool
    ai_analysis: Optional[AIAnalysisDetail] = None
    
    # AI深度分析字段（V3.1 AI集成新增）
    is_real: bool = True
    relevance: int = 50
    relevance_reason: Optional[str] = None
    importance: str = "medium"
    ai_summary: Optional[str] = None
    keyword_mentioned: bool = False
    matched_keywords: Optional[str] = None
    
    # 紧急热点字段
    is_urgent: bool = False
    urgent_reason: Optional[str] = None
    urgent_score: float = 0.0
    urgent_pushed_at: Optional[datetime] = None
    urgent_acknowledged: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class HotspotFilter(BaseModel):
    """热点筛选条件"""
    source: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_hot_score: Optional[float] = None
    max_hot_score: Optional[float] = None
    keyword: Optional[str] = None
    is_urgent: Optional[bool] = None
    sort_by: Optional[str] = Field(None, description="排序字段: hot_score|crawl_time|publish_time|views|interactions")
    sort_order: Optional[str] = Field("desc", description="排序方向: asc|desc")


class TrendData(BaseModel):
    """趋势数据"""
    date: str
    count: int
    avg_hot_score: float


class CategoryStats(BaseModel):
    """分类统计"""
    category: str
    count: int
    percentage: float


class SourceStats(BaseModel):
    """数据源统计"""
    source: str
    count: int
    last_update: Optional[datetime]


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_hotspots: int
    today_hotspots: int
    top_categories: List[CategoryStats]
    trend_7d: List[TrendData]
    hot_sources: List[SourceStats]


# ========== 数据库管理类 ==========

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/hotspots.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._create_tables()
    
    def _create_tables(self):
        """创建数据表"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库实例
db_manager = None

def init_database(db_path: str = "data/hotspots.db", force: bool = False) -> DatabaseManager:
    """初始化数据库
    
    Args:
        db_path: 数据库路径
        force: 是否强制重新初始化（用于测试）
    """
    global db_manager
    if db_manager is not None and not force:
        return db_manager
    db_manager = DatabaseManager(db_path)
    return db_manager

def get_db() -> DatabaseManager:
    """获取数据库管理器"""
    global db_manager
    if db_manager is None:
        db_manager = init_database()
    return db_manager
