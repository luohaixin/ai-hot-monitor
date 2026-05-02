"""
用户认证与权限管理系统 - JWT + RBAC
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from core.models import get_db, UserORM

# JWT配置
SECRET_KEY = secrets.token_urlsafe(32)  # 生成随机密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer安全方案
security = HTTPBearer(auto_error=False)


# ========== Pydantic模型 ==========

class TokenData(BaseModel):
    """Token数据"""
    username: Optional[str] = None
    scopes: List[str] = []


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    is_active: bool = True


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


class Permission(BaseModel):
    """权限定义"""
    name: str
    description: str
    scope: str


# ========== 权限定义 ==========

class Permissions:
    """系统权限定义"""
    
    # 热点相关权限
    HOTSPOT_VIEW = Permission(
        name="hotspot:view",
        description="查看热点",
        scope="read"
    )
    HOTSPOT_MANAGE = Permission(
        name="hotspot:manage",
        description="管理热点",
        scope="write"
    )
    
    # 爬虫相关权限
    CRAWLER_VIEW = Permission(
        name="crawler:view",
        description="查看爬虫状态",
        scope="read"
    )
    CRAWLER_CONTROL = Permission(
        name="crawler:control",
        description="控制爬虫",
        scope="write"
    )
    
    # 配置相关权限
    CONFIG_VIEW = Permission(
        name="config:view",
        description="查看配置",
        scope="read"
    )
    CONFIG_EDIT = Permission(
        name="config:edit",
        description="编辑配置",
        scope="write"
    )
    
    # 推送相关权限
    PUSH_VIEW = Permission(
        name="push:view",
        description="查看推送状态",
        scope="read"
    )
    PUSH_CONTROL = Permission(
        name="push:control",
        description="控制推送",
        scope="write"
    )
    
    # 用户管理权限
    USER_VIEW = Permission(
        name="user:view",
        description="查看用户",
        scope="read"
    )
    USER_MANAGE = Permission(
        name="user:manage",
        description="管理用户",
        scope="write"
    )
    
    # 系统管理权限
    SYSTEM_ADMIN = Permission(
        name="system:admin",
        description="系统管理",
        scope="admin"
    )


# 角色权限映射
ROLE_PERMISSIONS = {
    "viewer": [
        Permissions.HOTSPOT_VIEW,
        Permissions.CRAWLER_VIEW,
        Permissions.PUSH_VIEW,
        Permissions.CONFIG_VIEW,
    ],
    "operator": [
        Permissions.HOTSPOT_VIEW,
        Permissions.HOTSPOT_MANAGE,
        Permissions.CRAWLER_VIEW,
        Permissions.CRAWLER_CONTROL,
        Permissions.PUSH_VIEW,
        Permissions.PUSH_CONTROL,
        Permissions.CONFIG_VIEW,
    ],
    "admin": [
        Permissions.HOTSPOT_VIEW,
        Permissions.HOTSPOT_MANAGE,
        Permissions.CRAWLER_VIEW,
        Permissions.CRAWLER_CONTROL,
        Permissions.PUSH_VIEW,
        Permissions.PUSH_CONTROL,
        Permissions.CONFIG_VIEW,
        Permissions.CONFIG_EDIT,
        Permissions.USER_VIEW,
        Permissions.USER_MANAGE,
        Permissions.SYSTEM_ADMIN,
    ],
}


# ========== 核心认证类 ==========

class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self._secret_key = SECRET_KEY
        self._algorithm = ALGORITHM
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        # bcrypt有72字节限制，需要截断
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return pwd_context.hash(password_bytes)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        # bcrypt有72字节限制，需要截断
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return pwd_context.verify(password_bytes, hashed_password)
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌"""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except JWTError:
            return None
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """验证令牌"""
        payload = self.decode_token(token)
        if payload is None:
            return None
        
        # 检查令牌类型
        if payload.get("type") != token_type:
            return None
        
        username: str = payload.get("sub")
        scopes: List[str] = payload.get("scopes", [])
        
        if username is None:
            return None
        
        return TokenData(username=username, scopes=scopes)


class UserManager:
    """用户管理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.auth = AuthManager()
    
    def get_user_by_username(self, username: str) -> Optional[UserORM]:
        """通过用户名获取用户"""
        return self.db.query(UserORM).filter(
            UserORM.username == username
        ).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[UserORM]:
        """通过ID获取用户"""
        return self.db.query(UserORM).filter(
            UserORM.id == user_id
        ).first()
    
    def create_user(self, user_data: UserCreate) -> Optional[UserORM]:
        """创建用户"""
        # 检查用户名是否已存在
        existing = self.get_user_by_username(user_data.username)
        if existing:
            return None
        
        # 创建用户
        hashed_password = self.auth.hash_password(user_data.password)
        user = UserORM(
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=user_data.is_active
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"用户创建成功: {user_data.username}")
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserORM]:
        """认证用户"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not self.auth.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.hashed_password = self.auth.hash_password(new_password)
        self.db.commit()
        
        logger.info(f"用户密码修改成功: {user.username}")
        return True
    
    def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        
        logger.info(f"用户已停用: {user.username}")
        return True
    
    def list_users(self, skip: int = 0, limit: int = 100) -> List[UserORM]:
        """列出所有用户"""
        return self.db.query(UserORM).offset(skip).limit(limit).all()


# ========== FastAPI依赖 ==========

# 全局认证管理器实例
auth_manager = AuthManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserORM:
    """获取当前登录用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = auth_manager.verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建数据库会话
    db = get_db().get_session()
    try:
        user_manager = UserManager(db)
        user = user_manager.get_user_by_username(token_data.username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已停用"
            )
        
        return user
    finally:
        db.close()


async def get_current_active_user(
    current_user: UserORM = Depends(get_current_user)
) -> UserORM:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已停用")
    return current_user


def require_permissions(required_permissions: List[str]):
    """权限检查装饰器"""
    async def permission_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未提供认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = auth_manager.verify_token(credentials.credentials)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查权限
        user_permissions = set(token_data.scopes)
        required = set(required_permissions)

        if not required.issubset(user_permissions):
            missing = required - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}"
            )

        return token_data

    return permission_checker


def require_admin(
    current_user: UserORM = Depends(get_current_user)
) -> UserORM:
    """要求管理员权限"""
    # 这里简化处理，第一个用户或特定用户为管理员
    # 实际项目中应该有角色字段
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ========== 初始化默认用户 ==========

def init_default_users():
    """初始化默认用户"""
    from core.models import get_db
    
    db = get_db()
    session = db.get_session()
    
    try:
        user_manager = UserManager(session)
        
        # 检查是否已有admin用户
        admin = user_manager.get_user_by_username("admin")
        if not admin:
            # 创建默认管理员
            user_manager.create_user(UserCreate(
                username="admin",
                password="admin123",
                is_active=True
            ))
            logger.info("默认管理员用户已创建: admin/admin123")
        
        # 创建默认只读用户
        viewer = user_manager.get_user_by_username("viewer")
        if not viewer:
            user_manager.create_user(UserCreate(
                username="viewer",
                password="viewer123",
                is_active=True
            ))
            logger.info("默认只读用户已创建: viewer/viewer123")
            
    finally:
        session.close()
