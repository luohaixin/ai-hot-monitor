"""
内容解析模块 - 解析HTML提取数据
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger


class ContentParser:
    """内容解析器"""
    
    def __init__(self):
        self.date_patterns = [
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{4}年\d{2}月\d{2}日)',
            r'(\d{2}:\d{2})',
        ]
    
    def parse_html(self, html: str, selectors: Dict[str, str], base_url: str = "") -> List[Dict[str, Any]]:
        """
        解析HTML内容
        
        Args:
            html: HTML字符串
            selectors: CSS选择器配置
            base_url: 基础URL（用于拼接相对链接）
        
        Returns:
            解析出的数据列表
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        container_selector = selectors.get('container', '')
        containers = soup.select(container_selector) if container_selector else [soup]
        
        for container in containers:
            try:
                item = self._parse_item(container, selectors, base_url)
                if item and item.get('title'):
                    results.append(item)
            except Exception as e:
                logger.debug(f"Parse item error: {e}")
                continue
        
        return results
    
    def _parse_item(self, container: BeautifulSoup, selectors: Dict[str, str], base_url: str) -> Dict[str, Any]:
        """解析单个条目"""
        item = {}
        
        # 标题
        title_sel = selectors.get('title', '')
        if title_sel:
            title_elem = container.select_one(title_sel)
            item['title'] = self._get_text(title_elem) if title_elem else ''
        
        # 链接
        link_sel = selectors.get('link', '')
        if link_sel:
            link_elem = container.select_one(link_sel)
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                item['url'] = urljoin(base_url, href)
            else:
                item['url'] = ''
        
        # 摘要
        summary_sel = selectors.get('summary', '')
        if summary_sel:
            summary_elem = container.select_one(summary_sel)
            item['summary'] = self._get_text(summary_elem) if summary_elem else ''
        else:
            item['summary'] = ''
        
        # 完整内容（可选）
        content_sel = selectors.get('content', '')
        if content_sel:
            content_elem = container.select_one(content_sel)
            item['content'] = self._get_text(content_elem) if content_elem else item.get('summary', '')
        else:
            # 如果没有单独配置content选择器，默认使用summary作为content
            item['content'] = item.get('summary', '')
        
        # 时间
        time_sel = selectors.get('time', '')
        if time_sel:
            time_elem = container.select_one(time_sel)
            time_str = self._get_text(time_elem) if time_elem else ''
            item['publish_time'] = self._parse_time(time_str)
        else:
            item['publish_time'] = None
        
        # 浏览量/热度（GitHub星标等）
        views_sel = selectors.get('views') or selectors.get('stars')
        if views_sel:
            views_elem = container.select_one(views_sel)
            views_text = self._get_text(views_elem) if views_elem else '0'
            item['views'] = self._parse_number(views_text)
        else:
            item['views'] = 0
        
        # 互动量
        interactions_sel = selectors.get('interactions')
        if interactions_sel:
            inter_elem = container.select_one(interactions_sel)
            inter_text = self._get_text(inter_elem) if inter_elem else '0'
            item['interactions'] = self._parse_number(inter_text)
        else:
            item['interactions'] = 0
        
        return item
    
    def _get_text(self, elem) -> str:
        """获取元素文本并清理"""
        if not elem:
            return ''
        text = elem.get_text(strip=True)
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        # 尝试匹配各种格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
            '%m月%d日 %H:%M',
            '%H:%M',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        # 正则匹配
        for pattern in self.date_patterns:
            match = re.search(pattern, time_str)
            if match:
                date_str = match.group(1)
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
        
        # 相对时间处理
        now = datetime.now()
        if '分钟前' in time_str:
            mins = re.search(r'(\d+)', time_str)
            if mins:
                return now - timedelta(minutes=int(mins.group(1)))
        elif '小时前' in time_str:
            hours = re.search(r'(\d+)', time_str)
            if hours:
                return now - timedelta(hours=int(hours.group(1)))
        
        return None
    
    def _parse_number(self, num_str: str) -> int:
        """解析数字（支持k/m后缀）"""
        if not num_str:
            return 0
        
        num_str = str(num_str).strip().replace(',', '').replace(' ', '')
        
        # 提取数字
        match = re.search(r'[\d.]+', num_str)
        if not match:
            return 0
        
        try:
            num = float(match.group())
        except ValueError:
            return 0
        
        # 处理单位
        lower_str = num_str.lower()
        if 'k' in lower_str:
            num *= 1000
        elif 'm' in lower_str:
            num *= 1000000
        elif '万' in num_str:
            num *= 10000
        elif '亿' in num_str:
            num *= 100000000
        
        return int(num)
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ''
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除特殊字符
        text = re.sub(r'[\n\r\t]', ' ', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()


class JSONParser:
    """JSON数据解析器"""
    
    def parse(self, data: Dict, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        解析JSON数据
        
        Args:
            data: JSON数据
            mapping: 字段映射配置
        
        Returns:
            解析后的数据列表
        """
        results = []
        
        # 获取列表路径
        list_path = mapping.get('_list_path', '')
        items = self._get_nested_value(data, list_path) if list_path else [data]
        
        if not isinstance(items, list):
            items = [items]
        
        for item in items:
            parsed = {}
            for key, path in mapping.items():
                if key.startswith('_'):
                    continue
                parsed[key] = self._get_nested_value(item, path)
            results.append(parsed)
        
        return results
    
    def _get_nested_value(self, data: Any, path: str) -> Any:
        """获取嵌套值"""
        if not path:
            return data
        
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if 0 <= idx < len(value) else None
            else:
                return None
            
            if value is None:
                return None
        
        return value
