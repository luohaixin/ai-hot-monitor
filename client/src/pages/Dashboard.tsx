import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp,
  Flame,
  Eye,
  Activity,
  ArrowUpRight,
  Zap,
  X,
  AlertCircle,
  Tag,
  Link2,
  MessageCircle,
  Calendar,
  RefreshCw
} from 'lucide-react'
import axios from 'axios'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useWebSocket } from '../hooks/useWebSocket'

interface DashboardStats {
  total_hotspots: number
  today_hotspots: number
  top_categories: Array<{
    category: string
    count: number
    percentage: number
  }>
  trend_7d: Array<{
    date: string
    count: number
    avg_hot_score: number
  }>
  hot_sources: Array<{
    source: string
    count: number
    last_update: string
  }>
  latest_hotspots: Array<{
    id: number
    title: string
    source: string
    hot_score: number
    category: string
    crawl_time: string
  }>
}

interface HotspotDetail {
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

interface TodayHotspotItem {
  id: number
  title: string
  source: string
  hot_score: number
  category: string
  crawl_time: string
  url: string
  summary: string
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const { onCrawlComplete } = useWebSocket()
  
  // 今日新增热点弹窗状态
  const [showTodayHotspots, setShowTodayHotspots] = useState(false)
  const [todayHotspots, setTodayHotspots] = useState<TodayHotspotItem[]>([])
  const [todayHotspotsLoading, setTodayHotspotsLoading] = useState(false)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  // 订阅抓取完成事件，自动刷新数据
  useEffect(() => {
    const unsubscribe = onCrawlComplete((data) => {
      console.log('抓取完成，自动刷新Dashboard数据:', data)
      fetchDashboardData()
    })
    return unsubscribe
  }, [onCrawlComplete])

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('/api/v1/dashboard')
      if (response.data.code === 200) {
        setStats(response.data.data)
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchHotspotDetail = async (id: number) => {
    try {
      setDetailLoading(true)
      const response = await axios.get(`/api/v1/hot/list?page=1&page_size=100`)
      if (response.data.code === 200) {
        const items = response.data.data.items
        const hotspot = items.find((item: HotspotDetail) => item.id === id)
        if (hotspot) {
          setSelectedHotspot(hotspot)
        }
      }
    } catch (error) {
      console.error('Failed to fetch hotspot detail:', error)
    } finally {
      setDetailLoading(false)
    }
  }

  // 获取今日新增热点列表
  const fetchTodayHotspots = async () => {
    try {
      setTodayHotspotsLoading(true)
      const response = await axios.get('/api/v1/hot/list?today_only=true&page=1&page_size=50')
      if (response.data.code === 200) {
        setTodayHotspots(response.data.data.items)
        setShowTodayHotspots(true)
      }
    } catch (error) {
      console.error('Failed to fetch today hotspots:', error)
    } finally {
      setTodayHotspotsLoading(false)
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

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Zap className="w-16 h-16 text-gray-300 mb-4" />
        <p className="text-gray-500">无法加载数据</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">总热点数</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                {stats.total_hotspots.toLocaleString()}
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Flame className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 cursor-pointer hover:shadow-md hover:border-green-200 dark:hover:border-green-800 transition-all group"
          onClick={fetchTodayHotspots}
          title="点击查看今日新增热点"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400 group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">今日新增</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                {stats.today_hotspots.toLocaleString()}
              </p>
              <div className="flex items-center gap-1 mt-2 text-sm">
                <ArrowUpRight className="w-4 h-4 text-green-500" />
                <span className="text-green-500">+{(stats.today_hotspots / Math.max(stats.total_hotspots, 1) * 100).toFixed(1)}%</span>
              </div>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg group-hover:bg-green-200 dark:group-hover:bg-green-800 transition-colors">
              <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">活跃数据源</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                {stats.hot_sources.length}
              </p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Activity className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">平均热度</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                {stats.trend_7d.length > 0
                  ? (stats.trend_7d.reduce((acc, t) => acc + t.avg_hot_score, 0) / stats.trend_7d.length).toFixed(1)
                  : '0'}
              </p>
            </div>
            <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <Eye className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            7天趋势
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.trend_7d}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => value.slice(5)}
                  stroke="#9ca3af"
                />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Categories Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            分类分布
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.top_categories} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" stroke="#9ca3af" />
                <YAxis
                  dataKey="category"
                  type="category"
                  width={80}
                  stroke="#9ca3af"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Latest Hotspots */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700"
      >
        <div className="p-6 border-b border-gray-100 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            最新热点
          </h3>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-700">
          {stats.latest_hotspots.map((hotspot) => (
            <div
              key={hotspot.id}
              className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
              onClick={() => fetchHotspotDetail(hotspot.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {hotspot.title}
                  </h4>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {hotspot.source}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {hotspot.category}
                    </span>
                    <span className="text-xs text-orange-500">
                      热度: {hotspot.hot_score.toFixed(0)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

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
              {detailLoading ? (
                <div className="p-12 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <>
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
                    </a>
                  </div>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Today Hotspots Modal */}
      <AnimatePresence>
        {showTodayHotspots && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowTodayHotspots(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ type: 'spring', duration: 0.3 }}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      今日新增热点
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      共 {todayHotspots.length} 条新内容
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowTodayHotspots(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {todayHotspotsLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                  </div>
                ) : todayHotspots.length === 0 ? (
                  <div className="text-center py-12">
                    <TrendingUp className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">今日暂无新增热点</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {todayHotspots.map((hotspot, index) => (
                      <motion.div
                        key={hotspot.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer group"
                        onClick={() => {
                          setShowTodayHotspots(false)
                          fetchHotspotDetail(hotspot.id)
                        }}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-xs font-medium text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded">
                                #{index + 1}
                              </span>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded ${getImportanceBadge(hotspot.hot_score).class}`}>
                                {getImportanceBadge(hotspot.hot_score).label}
                              </span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {hotspot.source}
                              </span>
                            </div>
                            <h3 className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors line-clamp-2">
                              {hotspot.title}
                            </h3>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                              {hotspot.summary || '暂无摘要'}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className="text-sm font-semibold text-orange-500">
                              {hotspot.hot_score.toFixed(0)}
                            </span>
                            <span className="text-xs text-gray-400">
                              {format(new Date(hotspot.crawl_time), 'HH:mm', { locale: zhCN })}
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <button
                  onClick={() => setShowTodayHotspots(false)}
                  className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors font-medium"
                >
                  关闭
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
