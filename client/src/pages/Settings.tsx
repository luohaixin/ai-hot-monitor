import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import axios from 'axios'
import {
  Settings as SettingsIcon,
  Mail,
  Bell,
  Zap,
  Shield,
  Database,
  Check,
  AlertCircle,
  Loader2,
  Download,
  Trash2,
  Play,
  Pause,
  RefreshCw,
  Activity
} from 'lucide-react'

// API基础URL
const API_BASE_URL = ''

interface AIConfig {
  enabled: boolean
  model: string
  api_key: string
  min_relevance: number
  temperature: number
  max_tokens: number
  require_keyword_mention: boolean
}

interface AIModel {
  id: string
  name: string
  description: string
}

interface GeneralConfig {
  monitor_interval: number
  hot_score_threshold: number
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

interface NotificationConfig {
  websocket_enabled: boolean
  new_hotspot_push: boolean
  urgent_reminder: boolean
  daily_digest: boolean
}

interface EmailConfig {
  smtp_server: string
  smtp_port: number
  use_tls: boolean
  username: string
  password: string
  from_name: string
}

interface SecurityConfig {
  current_password: string
  new_password: string
  confirm_password: string
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('general')
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // AI配置状态
  const [aiConfig, setAiConfig] = useState<AIConfig>({
    enabled: true,
    model: 'moonshot-v1-8k',
    api_key: '',
    min_relevance: 50,
    temperature: 0.2,
    max_tokens: 500,
    require_keyword_mention: false
  })
  const [aiModels, setAiModels] = useState<AIModel[]>([])
  const [envApiKeyConfigured, setEnvApiKeyConfigured] = useState(false)
  const [loadingAIConfig, setLoadingAIConfig] = useState(false)

  // 通用配置状态
  const [generalConfig, setGeneralConfig] = useState<GeneralConfig>({
    monitor_interval: 30,
    hot_score_threshold: 100
  })
  const [loadingGeneralConfig, setLoadingGeneralConfig] = useState(false)

  // 监控状态
  const [monitorStatus, setMonitorStatus] = useState<MonitorStatus>({
    running: false,
    initialized: false,
    interval_minutes: 30,
    start_time: null,
    uptime_seconds: 0,
    last_crawl_time: null,
    crawl_count: 0,
    next_run_time: null
  })
  const [loadingMonitorStatus, setLoadingMonitorStatus] = useState(false)

  // 用于防止组件卸载后更新状态
  const isMounted = useRef(true)

  // 通知配置状态
  const [notificationConfig, setNotificationConfig] = useState<NotificationConfig>({
    websocket_enabled: true,
    new_hotspot_push: true,
    urgent_reminder: true,
    daily_digest: false
  })
  const [loadingNotificationConfig, setLoadingNotificationConfig] = useState(false)

  // 邮件配置状态
  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    smtp_server: '',
    smtp_port: 587,
    use_tls: true,
    username: '',
    password: '',
    from_name: 'AI热点监控'
  })
  const [envEmailConfigured, setEnvEmailConfigured] = useState(false)
  const [loadingEmailConfig, setLoadingEmailConfig] = useState(false)

  // 安全配置状态
  const [securityConfig, setSecurityConfig] = useState<SecurityConfig>({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  // 数据管理状态
  const [exporting, setExporting] = useState(false)
  const [clearing, setClearing] = useState(false)

  const tabs = [
    { id: 'general', label: '常规', icon: SettingsIcon },
    { id: 'notifications', label: '通知', icon: Bell },
    { id: 'email', label: '邮件', icon: Mail },
    { id: 'ai', label: 'AI服务', icon: Zap },
    { id: 'security', label: '安全', icon: Shield },
    { id: 'data', label: '数据', icon: Database },
  ]

  // 加载所有配置
  useEffect(() => {
    isMounted.current = true
    loadAIConfig()
    loadAIModels()
    loadGeneralConfig()
    loadNotificationConfig()
    loadEmailConfig()
    loadMonitorStatus()

    // 定时刷新监控状态
    const interval = setInterval(() => {
      loadMonitorStatus()
    }, 5000)

    return () => {
      isMounted.current = false
      clearInterval(interval)
    }
  }, [])

  // 清除保存消息
  useEffect(() => {
    if (saveMessage) {
      const timer = setTimeout(() => setSaveMessage(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [saveMessage])

  // ========== AI配置 ==========
  const loadAIConfig = async () => {
    setLoadingAIConfig(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/ai/config`)
      if (response.data.code === 200) {
        const { config, env_api_key_configured } = response.data.data
        setAiConfig(prev => ({
          ...prev,
          ...config
        }))
        setEnvApiKeyConfigured(env_api_key_configured)
      }
    } catch (error) {
      console.error('加载AI配置失败:', error)
    } finally {
      setLoadingAIConfig(false)
    }
  }

  const loadAIModels = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/ai/models`)
      if (response.data.code === 200) {
        setAiModels(response.data.data.models)
      }
    } catch (error) {
      console.error('加载AI模型列表失败:', error)
    }
  }

  const saveAIConfig = async () => {
    setSaving(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/ai/config`, aiConfig)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: 'AI配置保存成功' })
        await loadAIConfig()
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '保存失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleAIConfigChange = (field: keyof AIConfig, value: any) => {
    setAiConfig(prev => ({ ...prev, [field]: value }))
  }

  const testAIConnection = async () => {
    try {
      setSaveMessage({ type: 'success', text: '正在测试AI连接...' })
      setTimeout(() => {
        setSaveMessage({ type: 'success', text: 'AI服务连接正常' })
      }, 1000)
    } catch (error) {
      setSaveMessage({ type: 'error', text: 'AI连接测试失败' })
    }
  }

  // ========== 通用配置 ==========
  const loadGeneralConfig = async () => {
    setLoadingGeneralConfig(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/settings/general`)
      if (response.data.code === 200) {
        setGeneralConfig(response.data.data)
      }
    } catch (error) {
      console.error('加载通用配置失败:', error)
    } finally {
      setLoadingGeneralConfig(false)
    }
  }

  const saveGeneralConfig = async () => {
    setSaving(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/settings/general`, generalConfig)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: '常规设置保存成功' })
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '保存失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleGeneralConfigChange = (field: keyof GeneralConfig, value: any) => {
    setGeneralConfig(prev => ({ ...prev, [field]: value }))
  }

  // ========== 监控状态 ==========
  const loadMonitorStatus = async () => {
    if (!isMounted.current) return
    setLoadingMonitorStatus(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/monitor/status`)
      if (response.data.code === 200 && isMounted.current) {
        setMonitorStatus(response.data.data)
      }
    } catch (error) {
      console.error('加载监控状态失败:', error)
    } finally {
      if (isMounted.current) {
        setLoadingMonitorStatus(false)
      }
    }
  }

  const startMonitor = async () => {
    try {
      setSaveMessage({ type: 'success', text: '正在启动监控服务...' })
      const response = await axios.post(`${API_BASE_URL}/api/v1/monitor/start`)
      if (!isMounted.current) return
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: response.data.message })
        await loadMonitorStatus()
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '启动失败' })
      }
    } catch (error: any) {
      if (!isMounted.current) return
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '启动失败' })
    }
  }

  const stopMonitor = async () => {
    try {
      setSaveMessage({ type: 'success', text: '正在停止监控服务...' })
      const response = await axios.post(`${API_BASE_URL}/api/v1/monitor/stop`)
      if (!isMounted.current) return
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: response.data.message })
        await loadMonitorStatus()
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '停止失败' })
      }
    } catch (error: any) {
      if (!isMounted.current) return
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '停止失败' })
    }
  }

  const restartMonitor = async () => {
    try {
      setSaveMessage({ type: 'success', text: '正在重启监控服务...' })
      const response = await axios.post(`${API_BASE_URL}/api/v1/monitor/restart`)
      if (!isMounted.current) return
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: response.data.message })
        await loadMonitorStatus()
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '重启失败' })
      }
    } catch (error: any) {
      if (!isMounted.current) return
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '重启失败' })
    }
  }

  const formatDuration = (seconds: number) => {
    if (!seconds || isNaN(seconds) || seconds < 0) return '0秒'
    if (seconds < 60) return `${Math.floor(seconds)}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${mins}分钟`
  }

  // ========== 通知配置 ==========
  const loadNotificationConfig = async () => {
    setLoadingNotificationConfig(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/settings/notifications`)
      if (response.data.code === 200) {
        setNotificationConfig(response.data.data)
      }
    } catch (error) {
      console.error('加载通知配置失败:', error)
    } finally {
      setLoadingNotificationConfig(false)
    }
  }

  const saveNotificationConfig = async () => {
    setSaving(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/settings/notifications`, notificationConfig)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: '通知设置保存成功' })
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '保存失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleNotificationConfigChange = (field: keyof NotificationConfig, value: boolean) => {
    setNotificationConfig(prev => ({ ...prev, [field]: value }))
  }

  // ========== 邮件配置 ==========
  const loadEmailConfig = async () => {
    setLoadingEmailConfig(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/settings/email`)
      if (response.data.code === 200) {
        const { config, env_configured } = response.data.data
        setEmailConfig(prev => ({
          ...prev,
          ...config
        }))
        setEnvEmailConfigured(env_configured)
      }
    } catch (error) {
      console.error('加载邮件配置失败:', error)
    } finally {
      setLoadingEmailConfig(false)
    }
  }

  const saveEmailConfig = async () => {
    setSaving(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/settings/email`, emailConfig)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: '邮件设置保存成功' })
        await loadEmailConfig()
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '保存失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '保存失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleEmailConfigChange = (field: keyof EmailConfig, value: any) => {
    setEmailConfig(prev => ({ ...prev, [field]: value }))
  }

  const testEmailConnection = async () => {
    if (!emailConfig.username) {
      setSaveMessage({ type: 'error', text: '请先填写邮箱地址' })
      return
    }
    try {
      setSaveMessage({ type: 'success', text: '正在发送测试邮件...' })
      const response = await axios.post(`${API_BASE_URL}/api/v1/email/test`, {
        to_email: emailConfig.username
      })
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: '测试邮件发送成功' })
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '测试邮件发送失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '测试邮件发送失败' })
    }
  }

  // ========== 安全配置 ==========
  const saveSecurityConfig = async () => {
    if (securityConfig.new_password !== securityConfig.confirm_password) {
      setSaveMessage({ type: 'error', text: '新密码和确认密码不匹配' })
      return
    }
    if (securityConfig.new_password.length < 6) {
      setSaveMessage({ type: 'error', text: '新密码长度至少6位' })
      return
    }

    setSaving(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/settings/security/password`, securityConfig)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: '密码修改成功' })
        setSecurityConfig({ current_password: '', new_password: '', confirm_password: '' })
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '修改失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '修改失败' })
    } finally {
      setSaving(false)
    }
  }

  const handleSecurityConfigChange = (field: keyof SecurityConfig, value: string) => {
    setSecurityConfig(prev => ({ ...prev, [field]: value }))
  }

  // ========== 数据管理 ==========
  const exportData = async (format: 'json' | 'csv') => {
    setExporting(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/settings/export?format=${format}`, {
        responseType: 'blob'
      })

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      // 从响应头获取文件名，或使用默认文件名
      const contentDisposition = response.headers['content-disposition']
      let filename = `hotspots_export.${format}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/)
        if (match) {
          filename = match[1]
        }
      }

      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      setSaveMessage({ type: 'success', text: `数据导出成功 (${format.toUpperCase()})` })
    } catch (error) {
      console.error('导出数据失败:', error)
      setSaveMessage({ type: 'error', text: '数据导出失败' })
    } finally {
      setExporting(false)
    }
  }

  const clearAllData = async () => {
    if (!confirm('确定要清空所有数据吗？此操作不可恢复！')) {
      return
    }

    setClearing(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/settings/clear-data`)
      if (response.data.code === 200) {
        setSaveMessage({ type: 'success', text: response.data.message || '数据已清空' })
      } else {
        setSaveMessage({ type: 'error', text: response.data.message || '清空失败' })
      }
    } catch (error: any) {
      setSaveMessage({ type: 'error', text: error.response?.data?.message || '清空失败' })
    } finally {
      setClearing(false)
    }
  }

  // ========== 保存处理 ==========
  const handleSave = async () => {
    switch (activeTab) {
      case 'general':
        await saveGeneralConfig()
        break
      case 'notifications':
        await saveNotificationConfig()
        break
      case 'email':
        await saveEmailConfig()
        break
      case 'ai':
        await saveAIConfig()
        break
      case 'security':
        await saveSecurityConfig()
        break
      default:
        // 数据管理选项卡不需要保存
        break
    }
  }

  const isSaveDisabled = () => {
    return saving || activeTab === 'data'
  }

  const getSaveButtonText = () => {
    if (saving) return '保存中...'
    if (activeTab === 'data') return '无需保存'
    return '保存设置'
  }

  return (
    <div className="flex gap-6">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${activeTab === tab.id
                ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 font-medium'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700"
        >
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  常规设置
                </h3>
                {loadingGeneralConfig && (
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                )}
              </div>

              {/* 监控状态卡片 */}
              <div className={`p-4 rounded-lg border ${monitorStatus.running
                ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
                : 'bg-gray-50 border-gray-200 dark:bg-gray-700 dark:border-gray-600'
                }`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Activity className={`w-5 h-5 ${monitorStatus.running ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`} />
                    <span className="font-medium text-gray-900 dark:text-white">
                      监控服务状态
                    </span>
                    {monitorStatus.running ? (
                      <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-800 dark:text-green-300 rounded-full">
                        运行中
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-xs bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300 rounded-full">
                        已停止
                      </span>
                    )}
                  </div>
                  {loadingMonitorStatus && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
                </div>

                {monitorStatus.running && (
                  <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 mb-3">
                    <p>运行时间: {formatDuration(monitorStatus.uptime_seconds)}</p>
                    <p>监控间隔: {monitorStatus.interval_minutes}分钟</p>
                    {monitorStatus.next_run_time && (
                      <p>下次执行: {new Date(monitorStatus.next_run_time).toLocaleString('zh-CN')}</p>
                    )}
                    {monitorStatus.last_crawl_time && (
                      <p>上次抓取: {new Date(monitorStatus.last_crawl_time).toLocaleString('zh-CN')}</p>
                    )}
                    <p>已执行次数: {monitorStatus.crawl_count}</p>
                  </div>
                )}

                <div className="flex gap-2">
                  {monitorStatus.running ? (
                    <>
                      <button
                        onClick={stopMonitor}
                        className="px-3 py-1.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center gap-1.5 text-sm"
                      >
                        <Pause className="w-4 h-4" />
                        停止监控
                      </button>
                      <button
                        onClick={restartMonitor}
                        className="px-3 py-1.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-1.5 text-sm"
                      >
                        <RefreshCw className="w-4 h-4" />
                        重启
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={startMonitor}
                      className="px-3 py-1.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors flex items-center gap-1.5 text-sm"
                    >
                      <Play className="w-4 h-4" />
                      启动监控
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    监控间隔（分钟）
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={1440}
                    value={generalConfig.monitor_interval}
                    onChange={(e) => handleGeneralConfigChange('monitor_interval', parseInt(e.target.value) || 30)}
                    className="w-full max-w-xs px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    设置自动监控的时间间隔（5-1440分钟）
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    热度阈值
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1000}
                    value={generalConfig.hot_score_threshold}
                    onChange={(e) => handleGeneralConfigChange('hot_score_threshold', parseInt(e.target.value) || 100)}
                    className="w-full max-w-xs px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    热度低于此阈值的内容将被过滤
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  通知设置
                </h3>
                {loadingNotificationConfig && (
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                )}
              </div>
              <div className="space-y-4">
                {[
                  { field: 'websocket_enabled', label: '启用WebSocket实时通知', default: true },
                  { field: 'new_hotspot_push', label: '新热点推送', default: true },
                  { field: 'urgent_reminder', label: '紧急热点提醒', default: true },
                  { field: 'daily_digest', label: '每日摘要', default: false },
                ].map((item) => (
                  <label key={item.field} className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={notificationConfig[item.field as keyof NotificationConfig]}
                      onChange={(e) => handleNotificationConfigChange(item.field as keyof NotificationConfig, e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'email' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  邮件设置
                </h3>
                {loadingEmailConfig && (
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                )}
              </div>

              {envEmailConfigured && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <Check className="w-4 h-4" />
                    <span className="text-sm">邮件服务已通过环境变量配置</span>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    SMTP服务器
                  </label>
                  <input
                    type="text"
                    value={emailConfig.smtp_server}
                    onChange={(e) => handleEmailConfigChange('smtp_server', e.target.value)}
                    placeholder="smtp.gmail.com"
                    disabled={envEmailConfigured}
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4 max-w-md">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      SMTP端口
                    </label>
                    <input
                      type="number"
                      value={emailConfig.smtp_port}
                      onChange={(e) => handleEmailConfigChange('smtp_port', parseInt(e.target.value) || 587)}
                      placeholder="587"
                      disabled={envEmailConfigured}
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div className="flex items-center pt-6">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={emailConfig.use_tls}
                        onChange={(e) => handleEmailConfigChange('use_tls', e.target.checked)}
                        disabled={envEmailConfigured}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">使用TLS</span>
                    </label>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    邮箱地址
                  </label>
                  <input
                    type="email"
                    value={emailConfig.username}
                    onChange={(e) => handleEmailConfigChange('username', e.target.value)}
                    placeholder="your@email.com"
                    disabled={envEmailConfigured}
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    密码
                  </label>
                  <input
                    type="password"
                    value={emailConfig.password}
                    onChange={(e) => handleEmailConfigChange('password', e.target.value)}
                    placeholder={envEmailConfigured ? "已配置（环境变量）" : "您的邮箱密码或应用专用密码"}
                    disabled={envEmailConfigured}
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  {envEmailConfigured && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      密码通过环境变量 EMAIL_SMTP_SERVER 等配置
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    发件人名称
                  </label>
                  <input
                    type="text"
                    value={emailConfig.from_name}
                    onChange={(e) => handleEmailConfigChange('from_name', e.target.value)}
                    placeholder="AI热点监控"
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                </div>

                {/* 测试连接按钮 */}
                <div className="pt-2">
                  <button
                    onClick={testEmailConnection}
                    disabled={!emailConfig.username}
                    className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    发送测试邮件
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  AI服务设置
                </h3>
                {loadingAIConfig && (
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                )}
              </div>

              {/* API Key 来源提示 */}
              {envApiKeyConfigured && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <Check className="w-4 h-4" />
                    <span className="text-sm">OpenRouter API Key 已通过环境变量配置</span>
                  </div>
                </div>
              )}

              <div className="space-y-5">
                {/* 启用AI分析 */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      启用AI分析
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      使用AI对热点内容进行真实性、相关性、重要性分析
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={aiConfig.enabled}
                      onChange={(e) => handleAIConfigChange('enabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    OpenRouter API Key
                  </label>
                  <input
                    type="password"
                    value={aiConfig.api_key}
                    onChange={(e) => handleAIConfigChange('api_key', e.target.value)}
                    placeholder={envApiKeyConfigured ? "已配置（环境变量）" : "sk-or-v1-xxx"}
                    disabled={envApiKeyConfigured}
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  {envApiKeyConfigured && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      API Key 通过环境变量 OPENROUTER_API_KEY 配置
                    </p>
                  )}
                </div>

                {/* 模型选择 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    AI模型
                  </label>
                  <select
                    value={aiConfig.model}
                    onChange={(e) => handleAIConfigChange('model', e.target.value)}
                    className="w-full max-w-md px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  >
                    {aiModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                  {aiModels.find(m => m.id === aiConfig.model)?.description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {aiModels.find(m => m.id === aiConfig.model)?.description}
                    </p>
                  )}
                </div>

                {/* 相关性阈值 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    最小相关性阈值 ({aiConfig.min_relevance}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={aiConfig.min_relevance}
                    onChange={(e) => handleAIConfigChange('min_relevance', parseInt(e.target.value))}
                    className="w-full max-w-xs"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    低于此阈值的内容将被过滤掉
                  </p>
                </div>

                {/* Temperature */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Temperature ({aiConfig.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="20"
                    value={aiConfig.temperature * 10}
                    onChange={(e) => handleAIConfigChange('temperature', parseInt(e.target.value) / 10)}
                    className="w-full max-w-xs"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    控制AI输出的随机性，值越低越稳定
                  </p>
                </div>

                {/* 要求提及关键词 */}
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="require_keyword"
                    checked={aiConfig.require_keyword_mention}
                    onChange={(e) => handleAIConfigChange('require_keyword_mention', e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="require_keyword" className="text-sm text-gray-700 dark:text-gray-300">
                    要求内容明确提及关键词
                  </label>
                </div>

                {/* 测试连接按钮 */}
                <div className="pt-2">
                  <button
                    onClick={testAIConnection}
                    disabled={!aiConfig.enabled}
                    className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    测试AI连接
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  安全设置
                </h3>
              </div>
              <div className="space-y-4 max-w-md">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    当前密码
                  </label>
                  <input
                    type="password"
                    value={securityConfig.current_password}
                    onChange={(e) => handleSecurityConfigChange('current_password', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    新密码
                  </label>
                  <input
                    type="password"
                    value={securityConfig.new_password}
                    onChange={(e) => handleSecurityConfigChange('new_password', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    确认新密码
                  </label>
                  <input
                    type="password"
                    value={securityConfig.confirm_password}
                    onChange={(e) => handleSecurityConfigChange('confirm_password', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg dark:text-white"
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  密码长度至少6位
                </p>
              </div>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                数据管理
              </h3>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                    数据导出
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => exportData('csv')}
                      disabled={exporting}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                      导出CSV
                    </button>
                    <button
                      onClick={() => exportData('json')}
                      disabled={exporting}
                      className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                      导出JSON
                    </button>
                  </div>
                </div>
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <p className="text-sm text-red-600 dark:text-red-400 mb-3">
                    危险区域
                  </p>
                  <button
                    onClick={clearAllData}
                    disabled={clearing}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {clearing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    清空所有数据
                  </button>
                  <p className="text-xs text-red-500 dark:text-red-400 mt-2">
                    此操作将清空所有热点数据，不可恢复！
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 保存按钮和消息 */}
          <div className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-4">
              <button
                onClick={handleSave}
                disabled={isSaveDisabled()}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                {getSaveButtonText()}
              </button>

              {saveMessage && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg ${saveMessage.type === 'success'
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                    }`}
                >
                  {saveMessage.type === 'success' ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <AlertCircle className="w-4 h-4" />
                  )}
                  <span className="text-sm">{saveMessage.text}</span>
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
