"""
API接口集成测试
"""

import pytest
import os
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 删除旧的数据库文件，确保使用最新的schema
data_dir = project_root / "data"
db_file = data_dir / "hotspots.db"
if db_file.exists():
    try:
        db_file.unlink()
        print(f"已删除旧数据库: {db_file}")
    except Exception as e:
        print(f"删除数据库失败: {e}")

from main import app, create_app

# 创建应用实例（会自动初始化数据库）
app = create_app()

client = TestClient(app)


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data['code'] == 200
        assert data['data']['status'] == 'healthy'
    
    def test_root(self):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200


class TestConfigEndpoints:
    """配置端点测试"""

    def test_get_config(self):
        """测试获取配置"""
        response = client.get("/api/v1/config")
        assert response.status_code == 200

        data = response.json()
        assert data['code'] == 200
        assert 'data' in data
        assert 'keywords' in data['data']

    def test_reload_config(self):
        """测试重新加载配置"""
        response = client.post("/api/v1/config/reload")
        assert response.status_code == 200

        data = response.json()
        assert data['code'] == 200


class TestHotspotEndpoints:
    """热点端点测试"""
    
    def test_get_hot_list(self):
        """测试获取热点列表"""
        response = client.get("/api/v1/hot/list?page=1&page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'data' in data
        assert 'items' in data['data']
        assert 'pagination' in data['data']
    
    def test_get_hot_top(self):
        """测试获取热点TOP"""
        response = client.get("/api/v1/hot/top?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'items' in data['data']
    
    def test_get_hot_trend(self):
        """测试获取趋势"""
        response = client.get("/api/v1/hot/trend?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'trend' in data['data']
    
    def test_get_hot_stats(self):
        """测试获取统计"""
        response = client.get("/api/v1/hot/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'total_hotspots' in data['data']
    
    def test_get_hot_history(self):
        """测试获取历史"""
        from datetime import datetime, timedelta
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        response = client.get(f"/api/v1/hot/history?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'items' in data['data']


class TestCrawlerEndpoints:
    """爬虫端点测试"""
    
    def test_get_crawler_status(self):
        """测试获取爬虫状态"""
        response = client.get("/api/v1/crawler/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'sources' in data['data']
    
    def test_run_crawler(self):
        """测试手动触发抓取"""
        response = client.post("/api/v1/crawler/run", json={})
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'message' in data


class TestPushEndpoints:
    """推送端点测试"""
    
    def test_get_push_channels(self):
        """测试获取推送渠道"""
        response = client.get("/api/v1/push/channels")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'channels' in data['data']
    
    def test_test_push(self):
        """测试推送测试"""
        response = client.post("/api/v1/push/test", json={})
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'results' in data['data']
    
    def test_push_now(self):
        """测试立即推送"""
        response = client.post("/api/v1/push/now")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'message' in data


class TestDashboardEndpoints:
    """仪表盘端点测试"""
    
    def test_get_dashboard(self):
        """测试获取仪表盘数据"""
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert data['code'] == 200
        assert 'total_hotspots' in data['data']
        assert 'today_hotspots' in data['data']
        assert 'top_categories' in data['data']
        assert 'trend_7d' in data['data']


class TestErrorHandling:
    """错误处理测试"""
    
    def test_404_endpoint(self):
        """测试404端点"""
        response = client.get("/api/v1/not-exist")
        assert response.status_code == 404
    
    def test_invalid_params(self):
        """测试无效参数"""
        response = client.get("/api/v1/hot/list?page=-1")
        # FastAPI会自动验证参数
        assert response.status_code in [200, 422]
