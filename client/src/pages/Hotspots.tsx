import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Filter,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  X,
  Calendar,
  TrendingUp,
  Eye,
  MessageCircle,
  Tag,
  Link2
} from 'lucide-react'
import axios from 'axios'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useWebSocket } from '../hooks/useWebSocket'

interface Hotspot {
  id: number
  title: string
  source: string
  url: string
  summary: string
  hot_score: number
  views: number
  interactions: number
  sentiment: string
  category: string
  keywords: string
  publish_time: string
  crawl_time: string
}

export default function Hotspots() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null)
  const [filter, setFilter] = useState({
    source: '',
    category: '',
    sentiment: '',
    min_hot_score: '',
  })
  const { onCrawlComplete } = useWebSocket()

  useEffect(() => {
    fetchHotspots()
  }, [page, filter])

  // 订阅抓取完成事件，自动刷新数据
  useEffect(() => {
    const unsubscribe = onCrawlComplete((data) => {
      console.log('抓取完成，自动刷新Hotspots数据:', data)
      fetchHotspots()
    })
    return unsubscribe
  }, [onCrawlComplete])

  const fetchHotspots = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...Object.fromEntries(
          Object.entries(filter).filter(([_, v]) => v !== '')
        ),
      })

      const response = await axios.get(`/api/v1/hot/list?${params}`)
      if (response.data.code === 200) {
        setHotspots(response.data.data.items)
        setTotal(response.data.data.pagination.total)
      }
    } catch (error) {
      console.error('Failed to fetch hotspots:', error)
    } finally {
      setLoading(false)
    }
  }

  const getImportanceBadge = (score: number) => {
    if (score >= 80) return { label: '爆', class: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' }
    if (score >= 60) return { label: '热', class: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' }
    if (score >= 40) return { label: '温', class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' }
    if (score >= 20) return { label: '凉', class: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' }
    return { label: '冷', class: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200' }
  }

  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return { label: '正面', class: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' }
      case 'negative':
        return { label: '负面', class: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' }
      default:
        return { label: '中性', class: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' }
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      {/* Filter Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
        <div className="flex flex-wrap items-center gap-3">
          <Filter className="w-5 h-5 text-gray-400" />
          
          <select
            value={filter.source}
            onChange={(e) => setFilter({ ...filter, source: e.target.value })}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
          >
            <option value="">全部来源</option>
            <optgroup label="社交媒体">
              <option value="Twitter">Twitter</option>
              <option value="Bing">Bing</option>
              <option value="HackerNews">HackerNews</option>
              <option value="搜狗">搜狗</option>
              <option value="Bilibili">Bilibili</option>
              <option value="微博">微博</option>
            </optgroup>
            <optgroup label="AI资讯">
              <option value="机器之心">机器之心</option>
              <option value="机器之心英文版">机器之心英文版</option>
              <option value="新智元">新智元</option>
              <option value="量子位">量子位</option>
              <option value="InfoQ AI">InfoQ AI</option>
            </optgroup>
            <optgroup label="开源社区">
              <option value="GitHub Trending">GitHub Trending</option>
              <option value="GitHub AI Agents">GitHub AI Agents</option>
            </optgroup>
          </select>

          <select
            value={filter.category}
            onChange={(e) => setFilter({ ...filter, category: e.target.value })}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
          >
            <option value="">全部分类</option>
            <option value="技术">技术</option>
            <option value="产品">产品</option>
            <option value="论文">论文</option>
            <option value="政策">政策</option>
            <option value="行业应用">行业应用</option>
          </select>

          <select
            value={filter.sentiment}
            onChange={(e) => setFilter({ ...filter, sentiment: e.target.value })}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
          >
            <option value="">全部情感</option>
            <option value="positive">正面</option>
            <option value="neutral">中性</option>
            <option value="negative">负面</option>
          </select>

          <input
            type="number"
            placeholder="最小热度"
            value={filter.min_hot_score}
            onChange={(e) => setFilter({ ...filter, min_hot_score: e.target.value })}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white w-24"
          />

          <button
            onClick={fetchHotspots}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
      </div>

      {/* Hotspots List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : hotspots.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <AlertCircle className="w-16 h-16 text-gray-300 mb-4" />
          <p className="text-gray-500">暂无热点数据</p>
        </div>
      ) : (
        <div className="space-y-4">
          {hotspots.map((hotspot, index) => {
            const importance = getImportanceBadge(hotspot.hot_score)
            const sentimentBadge = getSentimentBadge(hotspot.sentiment)
            return (
              <motion.div
                key={hotspot.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedHotspot(hotspot)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${importance.class}`}>
                        {importance.label}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {hotspot.source}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {hotspot.category}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${sentimentBadge.class}`}>
                        {sentimentBadge.label}
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                      {hotspot.title}
                    </h3>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 mb-3">
                      {hotspot.summary}
                    </p>
                    
                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                      <span className="flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        热度 {hotspot.hot_score.toFixed(0)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        浏览 {hotspot.views}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageCircle className="w-3 h-3" />
                        互动 {hotspot.interactions}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {hotspot.publish_time
                          ? format(new Date(hotspot.publish_time), 'MM-dd HH:mm', { locale: zhCN })
                          : format(new Date(hotspot.crawl_time), 'MM-dd HH:mm', { locale: zhCN })}
                      </span>
                    </div>
                  </div>
                  
                  <a
                    href={hotspot.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          
          <span className="text-sm text-gray-600 dark:text-gray-400">
            第 {page} 页，共 {totalPages} 页
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Hotspot Detail Modal */}
      <AnimatePresence>
        {selectedHotspot && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedHotspot(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ type: 'spring', duration: 0.3 }}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${getImportanceBadge(selectedHotspot.hot_score).class}`}>
                    {getImportanceBadge(selectedHotspot.hot_score).label}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedHotspot.source}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedHotspot(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {/* Title */}
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 leading-relaxed">
                  {selectedHotspot.title}
                </h2>

                {/* Tags */}
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  <span className="px-3 py-1 text-sm bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded-full">
                    {selectedHotspot.category}
                  </span>
                  <span className={`px-3 py-1 text-sm rounded-full ${getSentimentBadge(selectedHotspot.sentiment).class}`}>
                    {getSentimentBadge(selectedHotspot.sentiment).label}
                  </span>
                </div>

                {/* Summary */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    内容摘要
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {selectedHotspot.summary || '暂无摘要'}
                  </p>
                </div>

                {/* Keywords */}
                {selectedHotspot.keywords && (
                  <div className="mb-6">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                      <Tag className="w-4 h-4" />
                      关键词
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedHotspot.keywords.split(',').map((keyword, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg"
                        >
                          {keyword.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400 text-xs mb-1">
                      <TrendingUp className="w-3 h-3" />
                      热度
                    </div>
                    <div className="text-xl font-bold text-gray-900 dark:text-white">
                      {selectedHotspot.hot_score.toFixed(0)}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400 text-xs mb-1">
                      <Eye className="w-3 h-3" />
                      浏览
                    </div>
                    <div className="text-xl font-bold text-gray-900 dark:text-white">
                      {selectedHotspot.views}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400 text-xs mb-1">
                      <MessageCircle className="w-3 h-3" />
                      互动
                    </div>
                    <div className="text-xl font-bold text-gray-900 dark:text-white">
                      {selectedHotspot.interactions}
                    </div>
                  </div>
                </div>

                {/* Time Info */}
                <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    <span>
                      发布时间: {selectedHotspot.publish_time
                        ? format(new Date(selectedHotspot.publish_time), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })
                        : '未知'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    <span>
                      抓取时间: {format(new Date(selectedHotspot.crawl_time), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="p-6 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <a
                  href={selectedHotspot.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium"
                >
                  <Link2 className="w-4 h-4" />
                  查看原文
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
