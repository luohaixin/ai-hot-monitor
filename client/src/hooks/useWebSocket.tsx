import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { io, type Socket } from 'socket.io-client'

interface NotificationMessage {
  type: string
  title: string
  content: string
  importance: string
  data?: any
  timestamp: string
}

interface CrawlCompleteData {
  saved: number
  filtered: number
  crawled: number
}

interface WebSocketContextType {
  socket: Socket | null
  isConnected: boolean
  notifications: NotificationMessage[]
  subscribeToKeywords: (keywords: string[]) => void
  unsubscribeFromKeywords: (keywords: string[]) => void
  clearNotifications: () => void
  onCrawlComplete: (callback: (data: CrawlCompleteData) => void) => () => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [notifications, setNotifications] = useState<NotificationMessage[]>([])
  const [crawlCompleteCallbacks, setCrawlCompleteCallbacks] = useState<((data: CrawlCompleteData) => void)[]>([])

  useEffect(() => {
    const newSocket = io(window.location.origin, {
      transports: ['websocket'],
      autoConnect: true,
    })

    newSocket.on('connect', () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    })

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    })

    newSocket.on('hotspot:new', (data: NotificationMessage) => {
      setNotifications(prev => [data, ...prev].slice(0, 50))
    })

    newSocket.on('hotspot:urgent', (data: NotificationMessage) => {
      setNotifications(prev => [data, ...prev].slice(0, 50))
    })

    newSocket.on('notification', (data: NotificationMessage) => {
      setNotifications(prev => [data, ...prev].slice(0, 50))
      // 检查是否是抓取完成通知
      if (data.type === 'system' && data.title === '抓取完成') {
        const crawlData = data.data as CrawlCompleteData
        if (crawlData && crawlData.saved > 0) {
          // 触发所有注册的回调
          crawlCompleteCallbacks.forEach(callback => callback(crawlData))
        }
      }
    })

    setSocket(newSocket)

    return () => {
      newSocket.close()
    }
  }, [crawlCompleteCallbacks])

  const subscribeToKeywords = useCallback((keywords: string[]) => {
    if (socket) {
      socket.emit('subscribe', { keywords })
    }
  }, [socket])

  const unsubscribeFromKeywords = useCallback((keywords: string[]) => {
    if (socket) {
      socket.emit('unsubscribe', { keywords })
    }
  }, [socket])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // 注册抓取完成回调
  const onCrawlComplete = useCallback((callback: (data: CrawlCompleteData) => void) => {
    setCrawlCompleteCallbacks(prev => [...prev, callback])
    // 返回取消订阅函数
    return () => {
      setCrawlCompleteCallbacks(prev => prev.filter(cb => cb !== callback))
    }
  }, [])

  return (
    <WebSocketContext.Provider
      value={{
        socket,
        isConnected,
        notifications,
        subscribeToKeywords,
        unsubscribeFromKeywords,
        clearNotifications,
        onCrawlComplete,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

// 导出类型
export type { CrawlCompleteData }
