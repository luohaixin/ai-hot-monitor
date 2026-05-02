"""
爬虫任务管理器 - 跟踪抓取任务进度和结果
"""

import time
import threading
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class CrawlTaskInfo:
    """抓取任务信息"""
    task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    source_filter: Optional[str] = None


class CrawlTaskManager:
    """
    爬虫任务管理器
    
    用于跟踪和管理爬虫任务的进度和结果
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._tasks: Dict[str, CrawlTaskInfo] = {}
        self._lock = threading.Lock()
        self._max_tasks = 10  # 最多保留10个任务历史
    
    def create_task(self, source_filter: Optional[str] = None) -> str:
        """
        创建新任务
        
        Args:
            source_filter: 指定抓取的来源，None表示全部
            
        Returns:
            任务ID
        """
        task_id = f"crawl_{int(time.time() * 1000)}"
        
        with self._lock:
            # 清理旧任务
            if len(self._tasks) >= self._max_tasks:
                oldest_key = min(self._tasks.keys(), 
                               key=lambda k: self._tasks[k].created_at.timestamp())
                del self._tasks[oldest_key]
            
            self._tasks[task_id] = CrawlTaskInfo(
                task_id=task_id,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
                source_filter=source_filter,
                progress={
                    'total_sources': 0,
                    'completed_sources': 0,
                    'current_source': None,
                    'total_crawled': 0,
                    'total_filtered': 0,
                    'total_saved': 0,
                    'total_new': 0
                }
            )
        
        logger.info(f"创建抓取任务: {task_id}")
        return task_id
    
    def start_task(self, task_id: str, total_sources: int):
        """开始任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                task.progress['total_sources'] = total_sources
                logger.info(f"任务开始: {task_id}, 共 {total_sources} 个数据源")
    
    def update_progress(self, task_id: str, source_name: str,
                       crawled: int, filtered: int, saved: int, new: int = 0):
        """更新进度"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress['current_source'] = source_name
                task.progress['completed_sources'] += 1
                task.progress['total_crawled'] += crawled
                task.progress['total_filtered'] += filtered
                task.progress['total_saved'] += saved
                task.progress['total_new'] += new
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = result
                logger.info(f"任务完成: {task_id}")
    
    def fail_task(self, task_id: str, error_message: str):
        """标记任务失败"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = error_message
                logger.error(f"任务失败: {task_id}, 错误: {error_message}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        with self._lock:
            if task_id not in self._tasks:
                return None
            
            task = self._tasks[task_id]
            return {
                'task_id': task.task_id,
                'status': task.status.value,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'elapsed_seconds': self._calculate_elapsed(task),
                'progress': task.progress,
                'result': task.result,
                'error_message': task.error_message,
                'source_filter': task.source_filter
            }
    
    def get_latest_task(self) -> Optional[Dict[str, Any]]:
        """获取最新的任务"""
        with self._lock:
            if not self._tasks:
                return None
            
            latest_task_id = max(self._tasks.keys(),
                               key=lambda k: self._tasks[k].created_at.timestamp())
            return self.get_task(latest_task_id)
    
    def list_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出任务历史"""
        with self._lock:
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at.timestamp(),
                reverse=True
            )[:limit]
            
            return [self.get_task(t.task_id) for t in sorted_tasks]
    
    def _calculate_elapsed(self, task: CrawlTaskInfo) -> Optional[float]:
        """计算已运行时间（秒）"""
        if not task.started_at:
            return None
        
        end_time = task.completed_at or datetime.utcnow()
        return (end_time - task.started_at).total_seconds()
    
    def clear_completed(self, keep_count: int = 5):
        """清理已完成的任务，只保留最近几个"""
        with self._lock:
            completed_tasks = [
                (k, v) for k, v in self._tasks.items()
                if v.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]
            
            if len(completed_tasks) > keep_count:
                # 按完成时间排序
                sorted_tasks = sorted(
                    completed_tasks,
                    key=lambda x: x[1].completed_at.timestamp() if x[1].completed_at else 0,
                    reverse=True
                )
                
                # 删除旧的任务
                for task_id, _ in sorted_tasks[keep_count:]:
                    del self._tasks[task_id]


# 全局任务管理器实例
task_manager = CrawlTaskManager()
