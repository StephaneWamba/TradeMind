import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { portfolioApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils'
import { useWebSocket } from '@/hooks/useWebSocket'
import { TrendingUp, TrendingDown } from 'lucide-react'
import type { WebSocketMessage } from '@/hooks/useWebSocket'

interface ActivePositionsProps {
  connectionId: number
}

interface Position {
  id: number
  symbol: string
  amount: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
}

export default function ActivePositions({ connectionId }: ActivePositionsProps) {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)

  const { isConnected, onMessage } = useWebSocket({
    connectionId,
    channels: ['positions'],
  })

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await portfolioApi.getValue(connectionId).catch(err => {
          console.error('Failed to fetch positions:', err)
          return { positions: [] }
        })
        setPositions(data.positions || [])
      } catch (error) {
        console.error('Failed to fetch positions:', error)
        setPositions([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    
    // Refresh every 5 seconds
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [connectionId])

  // Listen for WebSocket updates
  useEffect(() => {
    const cleanup = onMessage('position_update', (message: WebSocketMessage) => {
      if (message.type === 'position_update') {
        setPositions(prev => {
          const index = prev.findIndex(p => p.id === message.position_id)
          if (index >= 0) {
            const updated = [...prev]
            updated[index] = {
              ...updated[index],
              current_price: message.current_price,
              unrealized_pnl: message.unrealized_pnl,
              unrealized_pnl_percent: message.unrealized_pnl_percent,
            }
            return updated
          }
          return prev
        })
      }
    })

    const cleanupClosed = onMessage('position_closed', (message: WebSocketMessage) => {
      if (message.type === 'position_closed') {
        setPositions(prev => prev.filter(p => p.id !== message.position_id))
      }
    })

    return () => {
      cleanup()
      cleanupClosed()
    }
  }, [onMessage])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">Loading positions...</div>
        </CardContent>
      </Card>
    )
  }

  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Active Positions</CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">No open positions</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Open Positions ({positions.length})</span>
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-accent-success' : 'bg-text-muted'}`} />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {positions.map((position) => {
            const isPositive = position.unrealized_pnl >= 0
            return (
              <div
                key={position.id}
                className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-4 border border-border-default hover:border-border-hover hover:shadow-card-hover transition-all duration-300 relative overflow-hidden group"
              >
                <div className={`absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                  isPositive ? 'from-accent-success/5 to-transparent' : 'from-accent-danger/5 to-transparent'
                }`} />
                <div className="relative z-10">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-base sm:text-lg font-bold text-text-primary">{position.symbol}</div>
                  <div className={`flex items-center gap-1 font-mono font-semibold ${
                    isPositive ? 'text-accent-success' : 'text-accent-danger'
                  }`}>
                    {isPositive ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    {formatPercent(position.unrealized_pnl_percent)}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-base">
                  <div>
                    <div className="text-text-secondary mb-2 font-medium">
                      Position Size
                    </div>
                    <div className="text-text-primary font-mono font-semibold text-lg">{formatNumber(position.amount, 8)}</div>
                  </div>
                  <div>
                    <div className="text-text-secondary mb-2 font-medium">Entry Price</div>
                    <div className="text-text-primary font-mono font-semibold text-lg">{formatCurrency(position.entry_price)}</div>
                  </div>
                  <div>
                    <div className="text-text-secondary mb-2 font-medium">Mark Price</div>
                    <div className="text-text-primary font-mono font-semibold text-lg">{formatCurrency(position.current_price)}</div>
                  </div>
                  <div>
                    <div className="text-text-secondary mb-2 font-medium">Unrealized P&L</div>
                    <div className={`font-mono font-bold text-lg ${
                      isPositive ? 'text-accent-success' : 'text-accent-danger'
                    }`}>
                      {isPositive ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
                    </div>
                  </div>
                </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

