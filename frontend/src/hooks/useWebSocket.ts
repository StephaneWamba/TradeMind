import { useState, useRef, useCallback, useEffect } from 'react'
import { wsManager } from './useWebSocketManager'

export type WebSocketMessage = 
  | { type: 'price_update'; connection_id: number; symbol: string; price: number; change_24h?: number; volume_24h?: number; timestamp: string }
  | { type: 'position_update'; connection_id: number; position_id: number; symbol: string; amount: number; entry_price: number; current_price: number; unrealized_pnl: number; unrealized_pnl_percent: number; timestamp: string }
  | { type: 'portfolio_update'; connection_id: number; total_value_usdt: number; cash_usdt: number; invested_usdt: number; unrealized_pnl: number; unrealized_pnl_percent: number; daily_pnl: number; daily_pnl_percent: number; timestamp: string }
  | { type: 'trade_event'; connection_id: number; trade_id: number; strategy_id: number; symbol: string; side: string; amount: number; price: number; realized_pnl?: number; timestamp: string }
  | { type: 'position_closed'; connection_id: number; position_id: number; symbol: string; final_pnl: number; final_pnl_percent: number; timestamp: string }
  | { type: 'strategy_status'; connection_id: number; strategy_id: number; status: string; performance?: number; timestamp: string }
  | { type: 'connected' | 'subscribed' | 'unsubscribed' | 'pong' | 'error'; [key: string]: any }

export interface UseWebSocketOptions {
  connectionId: number
  channels?: string[]
  autoReconnect?: boolean
  reconnectInterval?: number
}

/**
 * Hook for WebSocket connections.
 * Uses shared connection manager to ensure only one WebSocket per connection_id.
 * Multiple components can use this hook with the same connection_id and they'll share the connection.
 */
export function useWebSocket(options: UseWebSocketOptions) {
  const { connectionId, channels = [], autoReconnect = true, reconnectInterval = 5000 } = options
  
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [error, setError] = useState<Error | null>(null)
  
  const cleanupRef = useRef<(() => void)[]>([])

  // Subscribe to channels and connect when component mounts
  useEffect(() => {
    // Connect if not already connected
    if (!wsManager.isConnected(connectionId)) {
      wsManager.connect(connectionId)
    }

    // Subscribe to requested channels
    if (channels.length > 0) {
      wsManager.subscribe(connectionId, channels)
    }
    
    // Check connection status periodically
    const checkInterval = setInterval(() => {
      setIsConnected(wsManager.isConnected(connectionId))
    }, 1000)

    return () => {
      clearInterval(checkInterval)
      // Unsubscribe from our channels (but don't disconnect - other components might need it)
      if (channels.length > 0) {
        wsManager.unsubscribe(connectionId, channels)
      }
      // Clean up message handlers
      cleanupRef.current.forEach(cleanup => cleanup())
      cleanupRef.current = []
    }
  }, [connectionId, channels.join(',')])

  // Set up message handler
  const onMessage = useCallback((type: string | 'all', handler: (message: WebSocketMessage) => void) => {
    const cleanup = wsManager.onMessage(connectionId, type, (message) => {
      setLastMessage(message)
      handler(message)
    })
    cleanupRef.current.push(cleanup)
    return cleanup
  }, [connectionId])

  const subscribe = useCallback((newChannels: string[]) => {
    wsManager.subscribe(connectionId, newChannels)
  }, [connectionId])

  const unsubscribe = useCallback((channelsToRemove: string[]) => {
    wsManager.unsubscribe(connectionId, channelsToRemove)
  }, [connectionId])

  const disconnect = useCallback(() => {
    wsManager.disconnect(connectionId)
    setIsConnected(false)
  }, [connectionId])

  const reconnect = useCallback(() => {
    wsManager.connect(connectionId)
  }, [connectionId])

  // Update connection status
  useEffect(() => {
    setIsConnected(wsManager.isConnected(connectionId))
  }, [connectionId])

  return {
    isConnected,
    lastMessage,
    error,
    subscribe,
    unsubscribe,
    onMessage,
    reconnect,
    disconnect,
  }
}
