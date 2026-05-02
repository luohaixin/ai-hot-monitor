"""
配置模块单元测试
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path

from core.config_loader import ConfigLoader, get_config


class TestConfigLoader:
    """配置加载器测试"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = ConfigLoader()
        config2 = ConfigLoader()
        assert config1 is config2
    
    def test_get_config_value(self):
        """测试获取配置值"""
        config = get_config()
        
        # 测试存在的配置
        app_name = config.get('app.name')
        assert app_name is not None
        assert isinstance(app_name, str)
        
        # 测试不存在的配置
        not_exist = config.get('not.exist.key', 'default')
        assert not_exist == 'default'
    
    def test_keywords_config(self):
        """测试关键词配置"""
        config = get_config()
        keywords = config.keywords
        
        assert isinstance(keywords, dict)
        assert 'exact' in keywords
        assert 'fuzzy' in keywords
        assert 'exclude' in keywords
        
        assert isinstance(keywords['exact'], list)
        assert isinstance(keywords['fuzzy'], list)
        assert isinstance(keywords['exclude'], list)
    
    def test_data_sources_config(self):
        """测试数据源配置"""
        config = get_config()
        sources = config.data_sources
        
        assert isinstance(sources, dict)
        
        for source_id, source_config in sources.items():
            assert 'name' in source_config
            assert 'url' in source_config
            assert 'enabled' in source_config


def test_config_file_exists():
    """测试配置文件存在"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    assert config_path.exists(), "配置文件不存在"


def test_config_yaml_valid():
    """测试配置文件格式正确"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    assert isinstance(config, dict)
    assert 'app' in config
    assert 'keywords' in config
    assert 'data_sources' in config
