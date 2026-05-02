"""
用户认证与权限管理测试
"""

import pytest
from fastapi.testclient import TestClient

from core.auth import (
    AuthManager, UserManager, UserCreate, init_default_users,
    ROLE_PERMISSIONS, Permissions
)
from core.models import get_db, init_database, UserORM


class TestAuthManager:
    """测试认证管理器"""

    def test_hash_password(self):
        """测试密码哈希"""
        auth = AuthManager()
        password = "test123"
        hashed = auth.hash_password(password)

        assert hashed != password
        assert auth.verify_password(password, hashed)
        assert not auth.verify_password("wrong", hashed)


class TestUserManager:
    """测试用户管理器"""

    @pytest.fixture
    def db_session(self):
        """数据库会话fixture"""
        db = init_database(":memory:", force=True)
        session = db.get_session()
        yield session
        session.close()

    def test_create_user(self, db_session):
        """测试创建用户"""
        manager = UserManager(db_session)

        user = manager.create_user(UserCreate(
            username="testuser",
            password="test123",
            is_active=True
        ))

        assert user is not None
        assert user.username == "testuser"
        assert user.is_active is True


class TestPermissions:
    """测试权限系统"""

    def test_role_permissions(self):
        """测试角色权限定义"""
        viewer_perms = ROLE_PERMISSIONS["viewer"]
        assert Permissions.HOTSPOT_VIEW in viewer_perms
