/**
 * Shared WebSocket connection manager.
 * Ensures only one WebSocket connection per connection_id, even when multiple components need it.
 */

type WebSocketMessage = any

interface WebSocketManager {
  connect(connectionId: number): void
  disconnect(connectionId: number): void
  subscribe(connectionId: number, channels: string[]): void
  unsubscribe(connectionId: number, channels: string[]): void
  onMessage(connectionId: number, type: string | 'all', handler: (message: WebSocketMessage) => void): () => void
  isConnected(connectionId: number): boolean
}

class SharedWebSocketManager implements WebSocketManager {
  private connections: Map<number, WebSocket> = new Map()
  private messageHandlers: Map<number, Map<string, Set<(message: WebSocketMessage) => void>>> = new Map()
  private subscribedChannels: Map<number, Set<string>> = new Map()
  private reconnectTimeouts: Map<number, NodeJS.Timeout> = new Map()
  private autoReconnect: boolean = true
  private reconnectInterval: number = 10000 // 10 seconds (increased to reduce connection storms)

  connect(connectionId: number): void {
    // If already connected, don't create another connection
    const existing = this.connections.get(connectionId)
    if (existing?.readyState === WebSocket.OPEN || existing?.readyState === WebSocket.CONNECTING) {
      return
    }

    // Close existing connection if any
    if (existing) {
      try {
        existing.close()
      } catch (e) {
        // Ignore errors when closing
      }
    }

    // Clear any pending reconnect
    const timeout = this.reconnectTimeouts.get(connectionId)
    if (timeout) {
      clearTimeout(timeout)
      this.reconnectTimeouts.delete(connectionId)
    }

    const wsUrl = `ws://localhost:5000/api/v1/ws?connection_id=${connectionId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      this.connections.set(connectionId, ws)
      
      // Subscribe to previously requested channels
      const channels = this.subscribedChannels.get(connectionId)
      if (channels && channels.size > 0) {
        ws.send(JSON.stringify({
          action: 'subscribe',
          channels: Array.from(channels),
        }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        
        // Call all handlers for this connection
        const handlers = this.messageHandlers.get(connectionId)
        if (handlers) {
          // Call type-specific handlers
          const typeHandlers = handlers.get(message.type)
          if (typeHandlers) {
            typeHandlers.forEach(handler => handler(message))
          }
          
          // Call 'all' handlers
          const allHandlers = handlers.get('all')
          if (allHandlers) {
            allHandlers.forEach(handler => handler(message))
          }
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }

    ws.onerror = (err) => {
      console.error(`WebSocket error for connection ${connectionId}:`, err)
    }

    ws.onclose = () => {
      this.connections.delete(connectionId)
      
      // Auto-reconnect if enabled
      if (this.autoReconnect) {
        const timeout = setTimeout(() => {
          this.connect(connectionId)
        }, this.reconnectInterval)
        this.reconnectTimeouts.set(connectionId, timeout)
      }
    }

    this.connections.set(connectionId, ws)
  }

  disconnect(connectionId: number): void {
    // Clear reconnect timeout
    const timeout = this.reconnectTimeouts.get(connectionId)
    if (timeout) {
      clearTimeout(timeout)
      this.reconnectTimeouts.delete(connectionId)
    }

    // Close connection
    const ws = this.connections.get(connectionId)
    if (ws) {
      ws.close()
      this.connections.delete(connectionId)
    }

    // Clean up handlers
    this.messageHandlers.delete(connectionId)
    this.subscribedChannels.delete(connectionId)
  }

  subscribe(connectionId: number, channels: string[]): void {
    // Store requested channels
    if (!this.subscribedChannels.has(connectionId)) {
      this.subscribedChannels.set(connectionId, new Set())
    }
    const channelSet = this.subscribedChannels.get(connectionId)!
    channels.forEach(ch => channelSet.add(ch))

    // If connected, send subscription immediately
    const ws = this.connections.get(connectionId)
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'subscribe',
        channels: channels,
      }))
    } else {
      // If not connected, connect first
      this.connect(connectionId)
    }
  }

  unsubscribe(connectionId: number, channels: string[]): void {
    const channelSet = this.subscribedChannels.get(connectionId)
    if (channelSet) {
      channels.forEach(ch => channelSet.delete(ch))
    }

    const ws = this.connections.get(connectionId)
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'unsubscribe',
        channels: channels,
      }))
    }
  }

  onMessage(connectionId: number, type: string | 'all', handler: (message: WebSocketMessage) => void): () => void {
    if (!this.messageHandlers.has(connectionId)) {
      this.messageHandlers.set(connectionId, new Map())
    }
    const handlers = this.messageHandlers.get(connectionId)!

    if (!handlers.has(type)) {
      handlers.set(type, new Set())
    }
    handlers.get(type)!.add(handler)

    // Return cleanup function
    return () => {
      const typeHandlers = handlers.get(type)
      if (typeHandlers) {
        typeHandlers.delete(handler)
      }
    }
  }

  isConnected(connectionId: number): boolean {
    const ws = this.connections.get(connectionId)
    return ws?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
export const wsManager = new SharedWebSocketManager()

