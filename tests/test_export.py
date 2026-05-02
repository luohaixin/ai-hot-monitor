"""
数据导出功能测试
"""

import io
import pytest
from core.export import ExportManager, ExportFormat
from core.models import HotspotORM, init_database


class TestExportManager:
    """测试导出管理器"""

    @pytest.fixture
    def db_session(self):
        """数据库会话fixture"""
        db = init_database(":memory:", force=True)
        session = db.get_session()

        # 创建测试数据
        for i in range(3):
            hotspot = HotspotORM(
                title=f"测试热点{i}",
                source="测试来源",
                url=f"http://example.com/{i}",
                category="技术",
                hot_score=100.0 + i * 10
            )
            session.add(hotspot)

        session.commit()
        yield session
        session.close()

    def test_get_export_fields(self, db_session):
        """测试获取导出字段"""
        manager = ExportManager(db_session)
        fields = manager.get_export_fields()
        assert len(fields) > 0

    def test_export_csv(self, db_session):
        """测试CSV导出"""
        manager = ExportManager(db_session)
        output = io.BytesIO()

        success = manager.export_hotspots(
            format=ExportFormat.CSV,
            output=output,
            fields=["id", "title", "hot_score"]
        )

        assert success is True
