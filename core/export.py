"""
数据导出模块 - 支持 CSV, Excel, JSON 格式
"""

import csv
import json
import io
from datetime import datetime
from typing import List, Optional, Dict, Any, BinaryIO
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from loguru import logger

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from core.models import HotspotORM, get_db


class ExportFormat(str, Enum):
    """导出格式枚举"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


@dataclass
class ExportField:
    """导出字段定义"""
    key: str
    label: str
    getter: Optional[callable] = None


class ExportManager:
    """数据导出管理器"""
    
    # 预定义的热点导出字段
    HOTSPOT_FIELDS = [
        ExportField("id", "ID"),
        ExportField("title", "标题"),
        ExportField("source", "来源"),
        ExportField("url", "链接"),
        ExportField("summary", "摘要"),
        ExportField("category", "分类"),
        ExportField("sentiment", "情感"),
        ExportField("hot_score", "热度分数"),
        ExportField("views", "浏览量"),
        ExportField("interactions", "互动量"),
        ExportField("keywords", "关键词"),
        ExportField("publish_time", "发布时间"),
        ExportField("crawl_time", "抓取时间"),
        ExportField("is_urgent", "是否紧急"),
        ExportField("urgent_score", "紧急分数"),
        ExportField("urgent_reason", "紧急原因"),
        ExportField("is_pushed", "是否已推送"),
    ]
    
    def __init__(self, db: Session = None):
        self.db = db or get_db().get_session()
    
    def _get_field_value(self, hotspot: HotspotORM, field: ExportField) -> Any:
        """获取字段值"""
        if field.getter:
            return field.getter(hotspot)
        
        value = getattr(hotspot, field.key, None)
        
        # 处理特殊类型
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        
        if value is None:
            return ""
        
        return value
    
    def _serialize_hotspot(self, hotspot: HotspotORM, fields: List[ExportField]) -> Dict[str, Any]:
        """序列化热点数据为字典"""
        return {
            field.label: self._get_field_value(hotspot, field)
            for field in fields
        }
    
    def export_hotspots(
        self,
        format: ExportFormat,
        output: BinaryIO,
        hotspots: Optional[List[HotspotORM]] = None,
        fields: Optional[List[str]] = None,
        include_header: bool = True
    ) -> bool:
        """
        导出热点数据
        
        Args:
            format: 导出格式
            output: 输出文件对象
            hotspots: 要导出的热点列表，None则导出所有
            fields: 要导出的字段列表，None则导出所有字段
            include_header: 是否包含表头
        
        Returns:
            导出是否成功
        """
        try:
            # 获取要导出的热点
            if hotspots is None:
                hotspots = self.db.query(HotspotORM).filter_by(is_deleted=False).all()
            
            # 获取要导出的字段
            if fields:
                export_fields = [f for f in self.HOTSPOT_FIELDS if f.key in fields]
            else:
                export_fields = self.HOTSPOT_FIELDS
            
            # 根据格式导出
            if format == ExportFormat.CSV:
                return self._export_csv(hotspots, export_fields, output, include_header)
            elif format == ExportFormat.EXCEL:
                return self._export_excel(hotspots, export_fields, output, include_header)
            elif format == ExportFormat.JSON:
                return self._export_json(hotspots, export_fields, output)
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
                
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            return False
    
    def _export_csv(
        self,
        hotspots: List[HotspotORM],
        fields: List[ExportField],
        output: BinaryIO,
        include_header: bool
    ) -> bool:
        """导出为CSV格式"""
        try:
            # 使用文本模式写入
            text_output = io.StringIO()
            writer = csv.writer(text_output)
            
            # 写入表头
            if include_header:
                writer.writerow([f.label for f in fields])
            
            # 写入数据
            for hotspot in hotspots:
                row = [self._get_field_value(hotspot, f) for f in fields]
                writer.writerow(row)
            
            # 写入二进制输出
            output.write(text_output.getvalue().encode('utf-8-sig'))  # BOM头，Excel兼容
            return True
            
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
    
    def _export_excel(
        self,
        hotspots: List[HotspotORM],
        fields: List[ExportField],
        output: BinaryIO,
        include_header: bool
    ) -> bool:
        """导出为Excel格式"""
        if not PANDAS_AVAILABLE:
            logger.error("导出Excel需要pandas库，请安装: pip install pandas openpyxl")
            return False
        
        try:
            # 准备数据
            data = []
            for hotspot in hotspots:
                row = self._serialize_hotspot(hotspot, fields)
                data.append(row)
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 写入Excel
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='热点数据', index=not include_header)
            
            return True
            
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return False
    
    def _export_json(
        self,
        hotspots: List[HotspotORM],
        fields: List[ExportField],
        output: BinaryIO
    ) -> bool:
        """导出为JSON格式"""
        try:
            data = []
            for hotspot in hotspots:
                row = self._serialize_hotspot(hotspot, fields)
                data.append(row)
            
            # 添加元数据
            result = {
                "export_time": datetime.now().isoformat(),
                "total_count": len(data),
                "data": data
            }
            
            output.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            return False
    
    def export_by_filter(
        self,
        format: ExportFormat,
        output: BinaryIO,
        source: Optional[str] = None,
        category: Optional[str] = None,
        sentiment: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_hot_score: Optional[float] = None,
        is_urgent: Optional[bool] = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        根据筛选条件导出热点
        
        Returns:
            包含导出结果信息的字典
        """
        try:
            query = self.db.query(HotspotORM).filter_by(is_deleted=False)
            
            # 应用筛选条件
            if source:
                query = query.filter_by(source=source)
            if category:
                query = query.filter_by(category=category)
            if sentiment:
                query = query.filter_by(sentiment=sentiment)
            if min_hot_score:
                query = query.filter(HotspotORM.hot_score >= min_hot_score)
            if is_urgent is not None:
                query = query.filter_by(is_urgent=is_urgent)
            if start_date:
                query = query.filter(HotspotORM.crawl_time >= start_date)
            if end_date:
                query = query.filter(HotspotORM.crawl_time <= end_date)
            
            hotspots = query.all()
            
            # 执行导出
            success = self.export_hotspots(format, output, hotspots, fields)
            
            return {
                "success": success,
                "count": len(hotspots),
                "format": format.value,
                "filters_applied": {
                    "source": source,
                    "category": category,
                    "sentiment": sentiment,
                    "start_date": start_date,
                    "end_date": end_date,
                    "min_hot_score": min_hot_score,
                    "is_urgent": is_urgent
                }
            }
            
        except Exception as e:
            logger.error(f"按筛选条件导出失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0
            }
    
    def get_export_fields(self) -> List[Dict[str, str]]:
        """获取可用的导出字段列表"""
        return [
            {"key": f.key, "label": f.label}
            for f in self.HOTSPOT_FIELDS
        ]
    
    def get_content_type(self, format: ExportFormat) -> str:
        """获取导出格式的Content-Type"""
        content_types = {
            ExportFormat.CSV: "text/csv; charset=utf-8",
            ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ExportFormat.JSON: "application/json; charset=utf-8"
        }
        return content_types.get(format, "application/octet-stream")
    
    def get_file_extension(self, format: ExportFormat) -> str:
        """获取导出格式的文件扩展名"""
        extensions = {
            ExportFormat.CSV: "csv",
            ExportFormat.EXCEL: "xlsx",
            ExportFormat.JSON: "json"
        }
        return extensions.get(format, "bin")


class ExportService:
    """导出服务 - 提供高级导出功能"""
    
    def __init__(self, db: Session = None):
        self.db = db or get_db().get_session()
        self.manager = ExportManager(self.db)
    
    def export_to_file(
        self,
        format: ExportFormat,
        filepath: str,
        **kwargs
    ) -> bool:
        """
        导出数据到文件
        
        Args:
            format: 导出格式
            filepath: 文件路径
            **kwargs: 其他导出参数
        
        Returns:
            导出是否成功
        """
        try:
            with open(filepath, 'wb') as f:
                return self.manager.export_hotspots(format, f, **kwargs)
        except Exception as e:
            logger.error(f"导出到文件失败: {e}")
            return False
    
    def export_to_bytes(
        self,
        format: ExportFormat,
        **kwargs
    ) -> Optional[bytes]:
        """
        导出数据到字节
        
        Args:
            format: 导出格式
            **kwargs: 其他导出参数
        
        Returns:
            导出的字节数据，失败返回None
        """
        try:
            output = io.BytesIO()
            success = self.manager.export_hotspots(format, output, **kwargs)
            if success:
                output.seek(0)
                return output.getvalue()
            return None
        except Exception as e:
            logger.error(f"导出到字节失败: {e}")
            return None
    
    def generate_filename(self, format: ExportFormat, prefix: str = "hotspots") -> str:
        """生成导出文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = self.manager.get_file_extension(format)
        return f"{prefix}_{timestamp}.{extension}"


# 便捷函数
def export_hotspots(
    format: str,
    output_path: str,
    **kwargs
) -> bool:
    """
    导出热点数据的便捷函数
    
    Args:
        format: 导出格式 (csv/excel/json)
        output_path: 输出文件路径
        **kwargs: 其他参数
    
    Returns:
        导出是否成功
    """
    export_format = ExportFormat(format.lower())
    service = ExportService()
    return service.export_to_file(export_format, output_path, **kwargs)
