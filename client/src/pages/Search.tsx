import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search as SearchIcon, ExternalLink, Loader2, X, Calendar, Link2, Eye, Heart, Filter } from 'lucide-react'
import axios from 'axios'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface SearchResult {
  title: string
  content: string
  url: string
  source: string
  author?: string
  published_at?: string
  views?: number
  likes?: number
}

interface DataSource {
  id: string
  name: string
  icon: string
  category: string
}

const DATA_SOURCES: DataSource[] = [
  // 社交媒体
  { id: 'twitter', name: 'Twitter/X', icon: '🐦', category: '社交媒体' },
  { id: 'weibo', name: '微博', icon: '📱', category: '社交媒体' },
  { id: 'bilibili', name: 'Bilibili', icon: '📺', category: '社交媒体' },
  // 搜索引擎
  { id: 'bing', name: 'Bing', icon: '🔍', category: '搜索引擎' },
  { id: 'sogou', name: '搜狗', icon: '🐕', category: '搜索引擎' },
  // 技术社区
  { id: 'hackernews', name: 'HackerNews', icon: '📰', category: '技术社区' },
]

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [showFilter, setShowFilter] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)

    try {
      const response = await axios.post('/api/v1/hotspots/search', {
        query: query.trim(),
        sources: selectedSources.length > 0 ? selectedSources : undefined
      })
      if (response.data.code === 200) {
        setResults(response.data.data.results || [])
      }
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSource = (sourceId: string) => {
    setSelectedSources(prev =>
      prev.includes(sourceId)
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    )
  }

  const clearFilters = () => {
    setSelectedSources([])
  }

  return (
    <div className="space-y-6">
      {/* Search Input */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          全网搜索
        </h3>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="输入关键词搜索多个数据源..."
              className="w-full pl-12 pr-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                搜索中...
              </>
            ) : (
              <>
                <SearchIcon className="w-4 h-4" />
                搜索
              </>
            )}
          </button>
        </div>

        {/* Data Source Filter */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-600 dark:text-gray-400">数据源筛选</span>
              {selectedSources.length > 0 && (
                <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded-full">
                  已选 {selectedSources.length} 个
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {selectedSources.length > 0 && (
                <button
                  onClick={clearFilters}
                  className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                >
                  清除筛选
                </button>
              )}
              <button
                onClick={() => setShowFilter(!showFilter)}
                className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {showFilter ? '收起' : '展开'}
              </button>
            </div>
          </div>

          {showFilter && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              {/* 社交媒体 */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">社交媒体</h4>
                <div className="flex flex-wrap gap-2">
                  {DATA_SOURCES.filter(s => s.category === '社交媒体').map(source => (
                    <button
                      key={source.id}
                      onClick={() => toggleSource(source.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-all ${selectedSources.includes(source.id)
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-2 border-blue-300 dark:border-blue-700'
                        : 'bg-gray-50 text-gray-600 dark:bg-gray-700 dark:text-gray-400 border-2 border-transparent hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                    >
                      <span>{source.icon}</span>
                      <span>{source.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 搜索引擎 */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">搜索引擎</h4>
                <div className="flex flex-wrap gap-2">
                  {DATA_SOURCES.filter(s => s.category === '搜索引擎').map(source => (
                    <button
                      key={source.id}
                      onClick={() => toggleSource(source.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-all ${selectedSources.includes(source.id)
                        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 border-2 border-green-300 dark:border-green-700'
                        : 'bg-gray-50 text-gray-600 dark:bg-gray-700 dark:text-gray-400 border-2 border-transparent hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                    >
                      <span>{source.icon}</span>
                      <span>{source.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 技术社区 */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">技术社区</h4>
                <div className="flex flex-wrap gap-2">
                  {DATA_SOURCES.filter(s => s.category === '技术社区').map(source => (
                    <button
                      key={source.id}
                      onClick={() => toggleSource(source.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-all ${selectedSources.includes(source.id)
                        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300 border-2 border-orange-300 dark:border-orange-700'
                        : 'bg-gray-50 text-gray-600 dark:bg-gray-700 dark:text-gray-400 border-2 border-transparent hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                    >
                      <span>{source.icon}</span>
                      <span>{source.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {!showFilter && selectedSources.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedSources.map(sourceId => {
                const source = DATA_SOURCES.find(s => s.id === sourceId)
                return source ? (
                  <span
                    key={source.id}
                    className="flex items-center gap-1 px-2 py-1 text-sm bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded-lg"
                  >
                    <span>{source.icon}</span>
                    <span>{source.name}</span>
                  </span>
                ) : null
              })}
            </div>
          )}

          {!showFilter && selectedSources.length === 0 && (
            <div className="flex flex-wrap gap-2 text-sm text-gray-500">
              <span>默认搜索全部数据源:</span>
              {DATA_SOURCES.map(source => (
                <span key={source.id} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
                  {source.icon} {source.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* Results */}
      {searched && !loading && (
        <div className="space-y-4">
          {results.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <SearchIcon className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>未找到相关结果</p>
            </div>
          ) : (
            results.map((result, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedResult(result)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {result.source}
                      </span>
                      {result.author && (
                        <span className="text-xs text-gray-500">
                          @{result.author}
                        </span>
                      )}
                    </div>

                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                      {result.title}
                    </h3>

                    <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 mb-3">
                      {result.content}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {result.views !== undefined && (
                        <span className="flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          浏览 {result.views}
                        </span>
                      )}
                      {result.likes !== undefined && (
                        <span className="flex items-center gap-1">
                          <Heart className="w-3 h-3" />
                          点赞 {result.likes}
                        </span>
                      )}
                      {result.published_at && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {format(new Date(result.published_at), 'yyyy-MM-dd HH:mm', { locale: zhCN })}
                        </span>
                      )}
                    </div>
                  </div>

                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                </div>
              </motion.div>
            ))
          )}
        </div>
      )}

      {/* Search Result Detail Modal */}
      <AnimatePresence>
        {selectedResult && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedResult(null)}
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
                  <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {selectedResult.source}
                  </span>
                  {selectedResult.author && (
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      @{selectedResult.author}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedResult(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[60vh]">
                {/* Title */}
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 leading-relaxed">
                  {selectedResult.title}
                </h2>

                {/* Content */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    内容摘要
                  </h3>
                  <p className="text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {selectedResult.content || '暂无内容'}
                  </p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {selectedResult.views !== undefined && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-center">
                      <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400 text-xs mb-1">
                        <Eye className="w-3 h-3" />
                        浏览量
                      </div>
                      <div className="text-xl font-bold text-gray-900 dark:text-white">
                        {selectedResult.views.toLocaleString()}
                      </div>
                    </div>
                  )}
                  {selectedResult.likes !== undefined && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 text-center">
                      <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400 text-xs mb-1">
                        <Heart className="w-3 h-3" />
                        点赞数
                      </div>
                      <div className="text-xl font-bold text-gray-900 dark:text-white">
                        {selectedResult.likes.toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>

                {/* Time Info */}
                {selectedResult.published_at && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      <span>
                        发布时间: {format(new Date(selectedResult.published_at), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-6 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <a
                  href={selectedResult.url}
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
