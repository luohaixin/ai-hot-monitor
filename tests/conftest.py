"""
测试配置和Fixture
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import init_database, get_db


@pytest.fixture(scope="function")
def test_db():
    """
    提供测试用的内存数据库
    每个测试函数使用独立的数据库实例
    """
    # 使用内存数据库进行测试
    db = init_database(":memory:")
    yield db
    # 清理
    db.close()


@pytest.fixture(scope="function")
def db_session(test_db):
    """
    提供数据库会话
    """
    session = test_db.get_session()
    try:
        yield session
    finally:
        session.close()
