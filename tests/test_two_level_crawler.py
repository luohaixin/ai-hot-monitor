"""
两级抓取功能测试
测试列表页抓取和详情页抓取的集成
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from core.crawler.detail_crawler import DetailCrawler, DetailTask, DetailResult
from core.crawler.engine import CrawlerEngine, TwoLevelCrawlStats


class TestTwoLevelCrawlStats:
    """测试两级抓取统计"""
    
    def test_init(self):
        stats = TwoLevelCrawlStats()
        assert stats.list_crawl_stats['total'] == 0
        assert stats.list_crawl_stats['success'] == 0
        assert stats.list_crawl_stats['failed'] == 0
        assert stats.detail_crawl_stats['queued'] == 0
        assert stats.detail_crawl_stats['success'] == 0
    
    def test_to_dict(self):
        stats = TwoLevelCrawlStats()
        stats.list_crawl_stats['total'] = 10
        stats.detail_crawl_stats['queued'] = 5
        
        result = stats.to_dict()
        assert result['list_crawl']['total'] == 10
        assert result['detail_crawl']['queued'] == 5


class TestDetailTask:
    """测试详情页任务"""
    
    def test_task_creation(self):
        task = DetailTask(
            hotspot_id=1,
            url="https://example.com/article/1",
            source="测试来源",
            source_id="test_source",
            config={'detail': {'content_selector': '.content'}},
            retry_count=0,
            max_retries=3
        )
        
        assert task.hotspot_id == 1
        assert task.url == "https://example.com/article/1"
        assert task.source == "测试来源"
        assert task.retry_count == 0
        assert task.max_retries == 3


class TestDetailResult:
    """测试详情页结果"""
    
    def test_result_creation(self):
        result = DetailResult(
            hotspot_id=1,
            url="https://example.com/article/1",
            source="测试来源",
            success=True,
            content="这是一篇测试文章",
            message="成功提取 10 字符"
        )
        
        assert result.hotspot_id == 1
        assert result.success is True
        assert result.content == "这是一篇测试文章"
        assert result.message == "成功提取 10 字符"


class TestDetailCrawler:
    """测试详情页抓取器"""
    
    def test_init(self):
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler(max_workers=5, delay_range=(1, 3))
            assert crawler.max_workers == 5
            assert crawler.delay_range == (1, 3)
            assert crawler.stats['queued'] == 0
    
    def test_extract_content_with_selector(self):
        """测试使用选择器提取内容"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            
            html = """
            <html>
                <body>
                    <div class="article-content">
                        <p>这是文章第一段</p>
                        <p>这是文章第二段</p>
                    </div>
                </body>
            </html>
            """
            
            content = crawler.extract_content(html, '.article-content')
            assert "这是文章第一段" in content
            assert "这是文章第二段" in content
    
    def test_extract_content_fallback(self):
        """测试使用备用选择器提取内容"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            
            html = """
            <html>
                <body>
                    <article>
                        <p>文章内容</p>
                    </article>
                </body>
            </html>
            """
            
            # 配置的选择器不存在，应该使用备用选择器
            content = crawler.extract_content(html, '.non-existent')
            assert "文章内容" in content
    
    def test_extract_content_no_match(self):
        """测试无法提取内容的情况"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            
            html = "<html><body><div>无内容</div></body></html>"
            content = crawler.extract_content(html, '.article-content')
            assert content is None
    
    def test_clean_content(self):
        """测试内容清理"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            
            raw_text = "  第一行  \n\n\n  第二行  \n\t  第三行  "
            cleaned = crawler._clean_content(raw_text)
            
            # 清理后应该是空格分隔的行
            assert "第一行" in cleaned
            assert "第二行" in cleaned
            assert "第三行" in cleaned
    
    def test_add_task_disabled_source(self):
        """测试添加任务到禁用的数据源"""
        mock_config = MagicMock()
        mock_config.data_sources = {
            'test_source': {
                'detail': {'enabled': False}
            }
        }
        
        with patch('core.crawler.detail_crawler.get_config', return_value=mock_config):
            crawler = DetailCrawler()
            result = crawler.add_task(1, "https://example.com", "测试", "test_source")
            
            assert result is False
            assert crawler.stats['skipped'] == 1
    
    def test_add_task_enabled_source(self):
        """测试添加任务到启用的数据源"""
        mock_config = MagicMock()
        mock_config.data_sources = {
            'test_source': {
                'detail': {'enabled': True, 'content_selector': '.content'}
            }
        }
        
        with patch('core.crawler.detail_crawler.get_config', return_value=mock_config):
            crawler = DetailCrawler()
            result = crawler.add_task(1, "https://example.com", "测试", "test_source")
            
            assert result is True
            assert crawler.stats['queued'] == 1
    
    def test_add_tasks_from_hotspots(self):
        """测试从热点列表批量添加任务"""
        mock_config = MagicMock()
        mock_config.data_sources = {
            'source1': {'detail': {'enabled': True}}
        }
        
        with patch('core.crawler.detail_crawler.get_config', return_value=mock_config):
            crawler = DetailCrawler()
            
            hotspots = [
                {'id': 1, 'url': 'https://example.com/1', 'source': '测试', 'source_id': 'source1', 'content': ''},
                {'id': 2, 'url': 'https://example.com/2', 'source': '测试', 'source_id': 'source1', 'content': '短'},
            ]
            
            added = crawler.add_tasks_from_hotspots(hotspots)
            assert added == 2  # 两个都需要抓取（没有content或content太短<100字符）
    
    def test_get_stats(self):
        """测试获取统计信息"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            crawler.stats = {'queued': 5, 'success': 3}
            
            stats = crawler.get_stats()
            assert stats['queued'] == 5
            assert stats['success'] == 3
    
    def test_reset_stats(self):
        """测试重置统计"""
        with patch('core.crawler.detail_crawler.get_config'):
            crawler = DetailCrawler()
            crawler.stats['queued'] = 10
            
            crawler.reset_stats()
            assert crawler.stats['queued'] == 0


class TestCrawlerEngineTwoLevel:
    """测试爬虫引擎的两级抓取功能"""
    
    def test_init_with_two_level(self):
        """测试启用两级抓取的初始化"""
        with patch('core.crawler.engine.get_config') as mock_config, \
             patch('core.crawler.engine.DetailCrawler') as mock_detail:
            
            mock_config.return_value.system_config = {'concurrency': {'max_workers': 5}}
            
            engine = CrawlerEngine(enable_two_level=True)
            assert engine.enable_two_level is True
            assert engine.detail_crawler is not None
    
    def test_init_without_two_level(self):
        """测试禁用两级抓取的初始化"""
        with patch('core.crawler.engine.get_config') as mock_config:
            mock_config.return_value.system_config = {'concurrency': {'max_workers': 5}}
            
            engine = CrawlerEngine(enable_two_level=False)
            assert engine.enable_two_level is False
            assert engine.detail_crawler is None
    
    def test_crawl_source_adds_source_id(self):
        """测试抓取时添加source_id"""
        with patch('core.crawler.engine.get_config') as mock_config, \
             patch('core.crawler.engine.DetailCrawler'), \
             patch.object(CrawlerEngine, '_generate_demo_data', return_value=[]):
            
            mock_config.return_value.system_config = {'concurrency': {'max_workers': 5}}
            
            engine = CrawlerEngine()
            engine.fetcher = Mock()
            engine.fetcher.fetch_html = Mock(return_value='<html></html>')
            engine.parser = Mock()
            engine.parser.parse_html = Mock(return_value=[{'title': '测试', 'url': 'https://example.com'}])
            
            source_config = {
                'name': '测试来源',
                'url': 'https://example.com',
                'selectors': {'container': '.item'}
            }
            
            result = engine.crawl_source('test_source', source_config)
            
            assert result.source_id == 'test_source'
            assert result.items[0]['source_id'] == 'test_source'


class TestIntegration:
    """集成测试"""
    
    def test_two_level_crawl_flow(self):
        """测试完整的两级抓取流程"""
        # 这是一个概念性的集成测试，实际执行需要完整的系统环境
        
        # 第一阶段：列表页抓取
        # 1. 从列表页获取文章URL和摘要
        # 2. 保存到数据库，获取热点ID
        
        # 第二阶段：详情页抓取
        # 1. 为每个热点创建详情页抓取任务
        # 2. 抓取详情页并提取完整内容
        # 3. 更新数据库中的content字段
        
        # 验证：
        # - 热点记录包含完整的content字段
        # - content长度大于summary
        # - 统计信息正确
        
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
