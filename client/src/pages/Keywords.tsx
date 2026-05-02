import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, X, Tag, AlertCircle } from 'lucide-react'
import axios from 'axios'

interface KeywordsData {
  exact: string[]
  fuzzy: string[]
  exclude: string[]
}

export default function Keywords() {
  const [keywords, setKeywords] = useState<KeywordsData>({
    exact: [],
    fuzzy: [],
    exclude: []
  })
  const [loading, setLoading] = useState(true)
  const [newKeyword, setNewKeyword] = useState('')
  const [selectedType, setSelectedType] = useState<'exact' | 'fuzzy' | 'exclude'>('exact')

  useEffect(() => {
    fetchKeywords()
  }, [])

  const fetchKeywords = async () => {
    try {
      const response = await axios.get('/api/v1/keywords')
      if (response.data.code === 200) {
        setKeywords(response.data.data.keywords)
      }
    } catch (error) {
      console.error('Failed to fetch keywords:', error)
    } finally {
      setLoading(false)
    }
  }

  const addKeyword = async () => {
    if (!newKeyword.trim()) return

    try {
      await axios.post('/api/v1/keywords/add', {
        type: selectedType,
        keyword: newKeyword.trim()
      })
      setNewKeyword('')
      fetchKeywords()
    } catch (error) {
      console.error('Failed to add keyword:', error)
    }
  }

  const removeKeyword = async (type: string, keyword: string) => {
    try {
      await axios.post('/api/v1/keywords/remove', {
        type,
        keyword
      })
      fetchKeywords()
    } catch (error) {
      console.error('Failed to remove keyword:', error)
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'exact': return '精确匹配'
      case 'fuzzy': return '模糊匹配'
      case 'exclude': return '排除词'
      default: return type
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'exact': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'fuzzy': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'exclude': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Add Keyword */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          添加监控词
        </h3>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as 'exact' | 'fuzzy' | 'exclude')}
            className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
          >
            <option value="exact">精确匹配</option>
            <option value="fuzzy">模糊匹配</option>
            <option value="exclude">排除词</option>
          </select>
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
            placeholder="输入关键词..."
            className="flex-1 min-w-[200px] px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-white"
          />
          <button
            onClick={addKeyword}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加
          </button>
        </div>
      </motion.div>

      {/* Keywords Lists */}
      {(['exact', 'fuzzy', 'exclude'] as const).map((type, index) => (
        <motion.div
          key={type}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: (index + 1) * 0.1 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          <div className="flex items-center gap-2 mb-4">
            <Tag className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {getTypeLabel(type)}
            </h3>
            <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
              {keywords[type].length}
            </span>
          </div>

          {keywords[type].length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-400">
              <AlertCircle className="w-8 h-8 mb-2" />
              <p className="text-sm">暂无{getTypeLabel(type)}词</p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {keywords[type].map((keyword) => (
                <span
                  key={keyword}
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm ${getTypeColor(type)}`}
                >
                  {keyword}
                  <button
                    onClick={() => removeKeyword(type, keyword)}
                    className="ml-1 p-0.5 hover:bg-black/10 dark:hover:bg-white/10 rounded-full transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  )
}
