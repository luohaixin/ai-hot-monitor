import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Flame,
  Tags,
  Search,
  Settings,
  Bell,
  Zap,
  Menu,
  X,
  Loader2,
  Trash2,
  AlertCircle,
  Info,
  CheckCircle,
  XCircle,
  BarChart3,
  Globe,
  Database,
  Filter,
  Clock,
  Activity,
  Play,
  Pause,
  RefreshCw,
  Sparkles
} from 'lucide-react'
import { useState, useRef, useEffect, useCallback } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useLanguage } from '../hooks/useLanguage'
import LanguageSwitcher from './LanguageSwitcher'
import axios from 'axios'
import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'

interface LayoutProps {
  children: React.ReactNode
}

interface CrawlProgress {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: {
    total_sources: number
    completed_sources: number
    current_source: string | null
    total_crawled: number
    total_filtered: number
    total_saved: number
    total_new: number
  }
  result?: {
    total_crawled: number
    total_filtered: number
    total_saved: number
    total_new: number
    sources: Record<string, {
      crawled: number
      filtered: number
      saved: number
      new: number
      success: boolean
      message: string
    }>
  }
  error_message?: string
  elapsed_seconds?: number
}

interface MonitorStatus {
  running: boolean
  initialized: boolean
  interval_minutes: number
  start_time: string | null
  uptime_seconds: number
  last_crawl_time: string | null
  crawl_count: number
  next_run_time: string | null
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState('')
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProgress, setShowProgress] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [crawlProgress, setCrawlProgress] = useState<CrawlProgress | null>(null)
  const [monitorStatus, setMonitorStatus] = useState<MonitorStatus | null>(null)
  const [showMonitorDropdown, setShowMonitorDropdown] = useState(false)
  const notificationRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)
  const monitorRef = useRef<HTMLDivElement>(null)
  const { isConnected, notifications, clearNotifications } = useWebSocket()
  const { t, currentLanguage } = useLanguage()

  // 点击外部关闭通知弹窗和进度弹窗
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotifications(false)
      }
      if (progressRef.current && !progressRef.current.contains(event.target as Node)) {
        setShowProgress(false)
      }
      if (monitorRef.current && !monitorRef.current.contains(event.target as Node)) {
        setShowMonitorDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 加载监控状态
  const fetchMonitorStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/monitor/status')
      if (response.data.code === 200) {
        setMonitorStatus(response.data.data)
      }
    } catch (error) {
      console.error('获取监控状态失败:', error)
    }
  }, [])

  // 定时刷新监控状态
  useEffect(() => {
    fetchMonitorStatus()
    const interval = setInterval(fetchMonitorStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchMonitorStatus])

  // 控制监控服务
  const controlMonitor = async (action: 'start' | 'stop' | 'restart') => {
    try {
      const response = await axios.post(`/api/v1/monitor/${action}`)
      if (response.data.code === 200) {
        await fetchMonitorStatus()
      }
    } catch (error) {
      console.error(`监控${action}失败:`, error)
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${mins}分钟`
  }

  // 查询任务进度
  const fetchTaskProgress = useCallback(async (taskId: string) => {
    try {
      const response = await axios.get(`/api/v1/crawler/task/${taskId}`)
      if (response.data.code === 200) {
        setCrawlProgress(response.data.data.task)
        return response.data.data.task
      }
    } catch (error) {
      console.error('获取任务进度失败:', error)
    }
    return null
  }, [])

  // 轮询任务进度
  useEffect(() => {
    if (!currentTaskId || !isScanning) return

    const interval = setInterval(async () => {
      const task = await fetchTaskProgress(currentTaskId)
      if (task && (task.status === 'completed' || task.status === 'failed')) {
        setIsScanning(false)
        clearInterval(interval)
        
        // 任务完成时显示反馈消息
        if (task.status === 'completed') {
          const newCount = task.progress?.total_new || 0
          const savedCount = task.progress?.total_saved || 0
          if (newCount > 0) {
            setScanMessage(`✨ 扫描完成！新增 ${newCount} 条热点数据`)
          } else if (savedCount > 0) {
            setScanMessage(`✓ 扫描完成！更新 ${savedCount} 条已有数据`)
          } else {
            setScanMessage('✓ 扫描完成，暂无新数据')
          }
          // 5秒后清除消息
          setTimeout(() => setScanMessage(''), 5000)
        }
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [currentTaskId, isScanning, fetchTaskProgress])

  const handleScan = async () => {
    if (isScanning) return

    setIsScanning(true)
    setScanMessage('正在启动扫描任务...')
    setShowProgress(true)

    try {
      const response = await axios.post('/api/v1/crawler/run', {})
      if (response.data.code === 200) {
        const { task_id } = response.data.data
        setCurrentTaskId(task_id)
        setScanMessage('扫描任务进行中...')
        // 立即获取一次进度
        await fetchTaskProgress(task_id)
      } else {
        setScanMessage(`启动失败: ${response.data.message}`)
        setIsScanning(false)
        setTimeout(() => setScanMessage(''), 5000)
      }
    } catch (error: any) {
      console.error('扫描失败:', error)
      setScanMessage(`扫描失败: ${error.response?.data?.message || error.message}`)
      setIsScanning(false)
      setTimeout(() => setScanMessage(''), 5000)
    }
  }

  const navItems = [
    { path: '/', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
    { path: '/hotspots', icon: Flame, labelKey: 'nav.hotspots' },
    { path: '/keywords', icon: Tags, labelKey: 'nav.keywords' },
    { path: '/search', icon: Search, labelKey: 'nav.search' },
    { path: '/settings', icon: Settings, labelKey: 'nav.settings' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 240 : 72 }}
        className="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex-shrink-0"
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-blue-600" />
            {sidebarOpen && (
              <span className="font-bold text-gray-900 dark:text-white whitespace-nowrap">
                {t('app.name')}
              </span>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            ) : (
              <Menu className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            )}
          </button>
        </div>

        <nav className="p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${isActive
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 font-medium'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`
              }
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span className="whitespace-nowrap">{t(item.labelKey)}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Connection Status */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
            />
            {sidebarOpen && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {isConnected ? t('common.connected') : t('common.disconnected')}
              </span>
            )}
          </div>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            {t('app.name')}
          </h1>

          <div className="flex items-center gap-4">
            {/* Language Switcher */}
            <LanguageSwitcher />
            {/* Monitor Status */}
            {monitorStatus && (
              <div className="relative" ref={monitorRef}>
                <button
                  onClick={() => setShowMonitorDropdown(!showMonitorDropdown)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${monitorStatus.running
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                >
                  <Activity className={`w-4 h-4 ${monitorStatus.running ? 'animate-pulse' : ''}`} />
                  <span className="text-sm font-medium">
                    {monitorStatus.running ? '监控中' : '监控停止'}
                  </span>
                  {monitorStatus.running && (
                    <span className="w-2 h-2 bg-green-500 rounded-full" />
                  )}
                </button>

                {/* Monitor Dropdown */}
                <AnimatePresence>
                  {showMonitorDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: -10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -10, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden"
                    >
                      <div className={`p-4 ${monitorStatus.running
                        ? 'bg-green-50 dark:bg-green-900/20'
                        : 'bg-gray-50 dark:bg-gray-700'
                        }`}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Activity className={`w-5 h-5 ${monitorStatus.running ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`} />
                            <span className="font-medium text-gray-900 dark:text-white">监控服务</span>
                          </div>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${monitorStatus.running
                            ? 'bg-green-100 text-green-700 dark:bg-green-800 dark:text-green-300'
                            : 'bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300'
                            }`}>
                            {monitorStatus.running ? '运行中' : '已停止'}
                          </span>
                        </div>

                        {monitorStatus.running && (
                          <div className="text-xs text-gray-600 dark:text-gray-300 space-y-1 mb-3">
                            <p>运行时间: {formatDuration(monitorStatus.uptime_seconds)}</p>
                            <p>监控间隔: {monitorStatus.interval_minutes}分钟</p>
                            <p>已执行次数: {monitorStatus.crawl_count}</p>
                            {monitorStatus.next_run_time && (
                              <p>下次执行: {new Date(monitorStatus.next_run_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</p>
                            )}
                            {monitorStatus.last_crawl_time && (
                              <p>上次抓取: {new Date(monitorStatus.last_crawl_time).toLocaleString('zh-CN')}</p>
                            )}
                          </div>
                        )}

                        <div className="flex gap-2">
                          {monitorStatus.running ? (
                            <>
                              <button
                                onClick={() => controlMonitor('stop')}
                                className="flex-1 px-3 py-1.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center justify-center gap-1 text-xs"
                              >
                                <Pause className="w-3 h-3" />
                                停止
                              </button>
                              <button
                                onClick={() => controlMonitor('restart')}
                                className="flex-1 px-3 py-1.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center justify-center gap-1 text-xs"
                              >
                                <RefreshCw className="w-3 h-3" />
                                重启
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => controlMonitor('start')}
                              className="flex-1 px-3 py-1.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors flex items-center justify-center gap-1 text-xs"
                            >
                              <Play className="w-3 h-3" />
                              启动监控
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Notification Bell */}
            <div className="relative" ref={notificationRef}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <Bell className="w-5 h-5" />
                {notifications.length > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                    {notifications.length > 9 ? '9+' : notifications.length}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              <AnimatePresence>
                {showNotifications && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 top-full mt-2 w-96 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden"
                  >
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                      <h3 className="font-semibold text-gray-900 dark:text-white">通知中心</h3>
                      {notifications.length > 0 && (
                        <button
                          onClick={clearNotifications}
                          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-600 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          清空
                        </button>
                      )}
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
                          <Info className="w-10 h-10 mb-2 opacity-50" />
                          <p className="text-sm">暂无通知</p>
                        </div>
                      ) : (
                        notifications.map((notification, index) => (
                          <motion.div
                            key={index}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className={`px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer ${notification.importance === 'urgent'
                              ? 'bg-red-50 dark:bg-red-900/10'
                              : notification.importance === 'high'
                                ? 'bg-orange-50 dark:bg-orange-900/10'
                                : ''
                              }`}
                            onClick={() => {
                              if (notification.data?.id) {
                                window.location.href = `/hotspots?id=${notification.data.id}`
                                setShowNotifications(false)
                              }
                            }}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`flex-shrink-0 w-2 h-2 mt-2 rounded-full ${notification.importance === 'urgent'
                                ? 'bg-red-500'
                                : notification.importance === 'high'
                                  ? 'bg-orange-500'
                                  : notification.importance === 'medium'
                                    ? 'bg-yellow-500'
                                    : 'bg-blue-500'
                                }`} />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {notification.title}
                                  </p>
                                  {notification.importance === 'urgent' && (
                                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                                  )}
                                </div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mb-1">
                                  {notification.content}
                                </p>
                                <p className="text-xs text-gray-400 dark:text-gray-500">
                                  {format(new Date(notification.timestamp), 'MM-dd HH:mm', { locale: zhCN })}
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        ))
                      )}
                    </div>

                    {notifications.length > 0 && (
                      <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 text-center">
                        <NavLink
                          to="/hotspots"
                          onClick={() => setShowNotifications(false)}
                          className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                        >
                          查看全部热点 →
                        </NavLink>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Scan Button & Progress */}
            <div className="flex items-center gap-2">
              {scanMessage && !showProgress && (
                <span className="text-sm text-gray-600 dark:text-gray-400 animate-pulse">
                  {scanMessage}
                </span>
              )}
              <div className="relative" ref={progressRef}>
                <button
                  onClick={() => {
                    if (isScanning || crawlProgress) {
                      setShowProgress(!showProgress)
                    } else {
                      handleScan()
                    }
                  }}
                  disabled={isScanning && false}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isScanning ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                  <span>{isScanning ? '扫描中...' : crawlProgress ? '查看进度' : '立即扫描'}</span>
                  {crawlProgress && !isScanning && (
                    <span className={`ml-1 w-2 h-2 rounded-full ${crawlProgress.status === 'completed' ? 'bg-green-400' : crawlProgress.status === 'failed' ? 'bg-red-400' : 'bg-yellow-400'}`} />
                  )}
                </button>

                {/* Progress Dropdown */}
                <AnimatePresence>
                  {showProgress && crawlProgress && (
                    <motion.div
                      initial={{ opacity: 0, y: -10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -10, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="absolute right-0 top-full mt-2 w-[420px] bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden"
                    >
                      {/* Header */}
                      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
                        <div className="flex items-center justify-between">
                          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-blue-600" />
                            抓取进度
                          </h3>
                          <div className="flex items-center gap-2">
                            {isScanning ? (
                              <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center gap-1">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                进行中
                              </span>
                            ) : crawlProgress.status === 'completed' ? (
                              <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-full flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                完成
                              </span>
                            ) : crawlProgress.status === 'failed' ? (
                              <span className="text-xs px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full flex items-center gap-1">
                                <XCircle className="w-3 h-3" />
                                失败
                              </span>
                            ) : null}
                            <button
                              onClick={() => setShowProgress(false)}
                              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                            >
                              <X className="w-4 h-4 text-gray-500" />
                            </button>
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          任务ID: {crawlProgress.task_id.slice(0, 16)}...
                        </p>
                      </div>

                      {/* Progress Stats */}
                      <div className="p-4 space-y-4">
                        {/* Overall Progress Bar */}
                        <div>
                          <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                            <span>总体进度</span>
                            <span>{crawlProgress.progress.completed_sources}/{crawlProgress.progress.total_sources} 数据源</span>
                          </div>
                          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500"
                              initial={{ width: 0 }}
                              animate={{ width: `${crawlProgress.progress.total_sources > 0 ? (crawlProgress.progress.completed_sources / crawlProgress.progress.total_sources) * 100 : 0}%` }}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        </div>

                        {/* Stats Cards */}
                        <div className="grid grid-cols-4 gap-3">
                          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
                            <Globe className="w-5 h-5 text-blue-600 mx-auto mb-1" />
                            <p className="text-lg font-semibold text-gray-900 dark:text-white">{crawlProgress.progress.total_crawled}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">已抓取</p>
                          </div>
                          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
                            <Filter className="w-5 h-5 text-amber-600 mx-auto mb-1" />
                            <p className="text-lg font-semibold text-gray-900 dark:text-white">{crawlProgress.progress.total_filtered}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">已过滤</p>
                          </div>
                          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                            <Database className="w-5 h-5 text-green-600 mx-auto mb-1" />
                            <p className="text-lg font-semibold text-gray-900 dark:text-white">{crawlProgress.progress.total_saved}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">已保存</p>
                          </div>
                          <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 text-center">
                            <Sparkles className="w-5 h-5 text-purple-600 mx-auto mb-1" />
                            <p className="text-lg font-semibold text-gray-900 dark:text-white">{crawlProgress.progress.total_new || 0}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">新增</p>
                          </div>
                        </div>

                        {/* Current Source */}
                        {isScanning && crawlProgress.progress.current_source && (
                          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                            <span>正在处理: <span className="font-medium text-gray-900 dark:text-white">{crawlProgress.progress.current_source}</span></span>
                          </div>
                        )}

                        {/* Elapsed Time */}
                        {crawlProgress.elapsed_seconds !== undefined && (
                          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                            <Clock className="w-4 h-4" />
                            <span>
                              耗时: {Math.floor(crawlProgress.elapsed_seconds / 60)}分{Math.floor(crawlProgress.elapsed_seconds % 60)}秒
                            </span>
                          </div>
                        )}

                        {/* Error Message */}
                        {crawlProgress.error_message && (
                          <div className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            <span>{crawlProgress.error_message}</span>
                          </div>
                        )}

                        {/* Source Details */}
                        {crawlProgress.result?.sources && Object.keys(crawlProgress.result.sources).length > 0 && (
                          <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">数据源详情</p>
                            <div className="max-h-32 overflow-y-auto space-y-1">
                              {Object.entries(crawlProgress.result.sources).map(([source, stats]) => (
                                <div key={source} className="flex items-center justify-between text-xs py-1 px-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded">
                                  <div className="flex items-center gap-2">
                                    {stats.success ? (
                                      <CheckCircle className="w-3 h-3 text-green-500" />
                                    ) : (
                                      <XCircle className="w-3 h-3 text-red-500" />
                                    )}
                                    <span className="text-gray-700 dark:text-gray-300 truncate max-w-[120px]">{source}</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-gray-500">
                                    <span>抓:{stats.crawled}</span>
                                    <span>存:{stats.saved}</span>
                                    {stats.new > 0 && (
                                      <span className="text-purple-600 dark:text-purple-400">新:{stats.new}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-2">
                          {isScanning ? (
                            <button
                              onClick={() => setShowProgress(false)}
                              className="flex-1 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                              后台运行
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setCrawlProgress(null)
                                  setCurrentTaskId(null)
                                  setShowProgress(false)
                                }}
                                className="flex-1 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                              >
                                清除记录
                              </button>
                              <button
                                onClick={handleScan}
                                className="flex-1 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                              >
                                再次扫描
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}
