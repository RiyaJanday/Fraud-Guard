import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import { fraudApi, getNotificationsWebSocketUrl } from '../lib/api'
import { useAuth } from './AuthContext'

const NotificationsContext = createContext(null)

const TYPE_META = {
  blocked_transaction: { dotClass: 'bg-danger', toastIcon: '🚫' },
  high_risk_alert: { dotClass: 'bg-warning', toastIcon: '⚠️' },
  review_required: { dotClass: 'bg-accent', toastIcon: '🔍' },
  model_update: { dotClass: 'bg-accent', toastIcon: '🤖' },
  system: { dotClass: 'bg-accent', toastIcon: 'ℹ️' },
}

export function typeMeta(type) {
  return TYPE_META[type] || TYPE_META.system
}

export function NotificationsProvider({ children }) {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptRef = useRef(0)

  const refresh = useCallback(async () => {
    try {
      const { data } = await fraudApi.listNotifications({ page: 1, page_size: 20 })
      setNotifications(data.items)
      setUnreadCount(data.unread_count)
    } catch {
      // Silent — the panel just stays empty/stale rather than surfacing a
      // toast for a background poll the person didn't explicitly trigger.
    }
  }, [])

  const markRead = useCallback(async (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    setUnreadCount((c) => Math.max(0, c - 1))
    try {
      await fraudApi.markNotificationRead(id)
    } catch {
      refresh() // resync with the server if the optimistic update didn't actually stick
    }
  }, [refresh])

  const markAllRead = useCallback(async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    setUnreadCount(0)
    try {
      await fraudApi.markAllNotificationsRead()
    } catch {
      refresh()
    }
  }, [refresh])

  // Live WebSocket connection — reconnects with backoff on drop (Render's
  // free tier, proxies, laptop sleep/wake all close idle sockets sometimes;
  // a notification feed that silently stays dead until next page load isn't
  // "real-time" in any way that matters for a demo).
  useEffect(() => {
    if (!user) {
      wsRef.current?.close()
      setConnected(false)
      return
    }

    let cancelled = false

    function connect() {
      if (cancelled) return

      // No token argument — the access_token httpOnly cookie authenticates
      // the WS handshake automatically. See lib/api.js.
      const ws = new WebSocket(getNotificationsWebSocketUrl())
      wsRef.current = ws

      ws.onopen = () => {
        reconnectAttemptRef.current = 0
        setConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === 'notification' && payload.notification) {
            const n = payload.notification
            setNotifications((prev) => [n, ...prev].slice(0, 20))
            setUnreadCount((c) => c + 1)
            toast(n.title, { icon: typeMeta(n.type).toastIcon })
          }
        } catch {
          // Ignore malformed frames rather than crash the socket handler.
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (cancelled) return
        const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 30000)
        reconnectAttemptRef.current += 1
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    refresh()
    connect()

    return () => {
      cancelled = true
      clearTimeout(reconnectTimeoutRef.current)
      wsRef.current?.close()
    }
  }, [user, refresh])

  return (
    <NotificationsContext.Provider value={{ notifications, unreadCount, connected, markRead, markAllRead, refresh }}>
      {children}
    </NotificationsContext.Provider>
  )
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext)
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider')
  return ctx
}
