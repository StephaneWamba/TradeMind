import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { useWebSocket, type WebSocketMessage } from '@/hooks/useWebSocket'
import { tradesApi } from '@/lib/api'
import { ArrowUp, ArrowDown } from 'lucide-react'
import { format } from 'date-fns'

interface Trade {
  id: number
  symbol: string
  side: 'buy' | 'sell'
  amount: number
  price: number
  realized_pnl?: number
  timestamp: string
}

interface RecentTradesProps {
  connectionId: number
}

export default function RecentTrades({ connectionId }: RecentTradesProps) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)

  const { isConnected, onMessage } = useWebSocket({
    connectionId,
    channels: ['trades'],
  })

  // Fetch historical trades on mount
  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const data = await tradesApi.getTrades(connectionId, undefined, 10)
        if (data && data.trades) {
          setTrades(data.trades)
        }
      } catch (error) {
        console.error('Failed to fetch trades:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchTrades()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchTrades, 30000)
    return () => clearInterval(interval)
  }, [connectionId])

  // Listen for WebSocket trade events
  useEffect(() => {
    const cleanup = onMessage('trade_event', (message: WebSocketMessage) => {
      if (message.type === 'trade_event') {
        const newTrade: Trade = {
          id: message.trade_id,
          symbol: message.symbol,
          side: message.side as 'buy' | 'sell',
          amount: message.amount,
          price: message.price,
          realized_pnl: message.realized_pnl,
          timestamp: message.timestamp || new Date().toISOString(),
        }
        setTrades(prev => [newTrade, ...prev].slice(0, 10)) // Keep last 10
      }
    })
    return cleanup
  }, [onMessage])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">Loading trades...</div>
        </CardContent>
      </Card>
    )
  }

  if (trades.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Trades</CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">
            No recent trades
            <div className="text-xs mt-2">Trades will appear here when executed</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Recent Trades</span>
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-accent-success' : 'bg-text-muted'}`} />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {trades.map((trade) => {
            const isBuy = trade.side === 'buy'
            const isPositive = (trade.realized_pnl || 0) >= 0

            return (
              <div
                key={trade.id}
                className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-3 sm:p-4 border border-border-default hover:border-border-hover hover:shadow-card-hover transition-all duration-300 relative overflow-hidden group"
              >
                <div className={`absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                  isBuy ? 'from-accent-success/5 to-transparent' : 'from-accent-danger/5 to-transparent'
                }`} />
                <div className="relative z-10">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0 mb-3">
                  <div className="flex items-center gap-2">
                    {isBuy ? (
                      <ArrowUp className="h-4 w-4 text-accent-success" />
                    ) : (
                      <ArrowDown className="h-4 w-4 text-accent-danger" />
                    )}
                    <span className="font-semibold text-text-primary text-sm sm:text-base">{trade.symbol}</span>
                    <span className={`text-xs sm:text-sm font-medium px-2 py-0.5 rounded ${
                      isBuy 
                        ? 'text-accent-success bg-accent-success/10' 
                        : 'text-accent-danger bg-accent-danger/10'
                    }`}>
                      {trade.side.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-text-muted font-medium">
                    {format(new Date(trade.timestamp), 'HH:mm:ss')}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4 text-sm">
                  <div>
                    <div className="text-text-secondary text-xs mb-1 font-medium">Amount</div>
                    <div className="text-text-primary font-mono text-sm sm:text-base">{formatNumber(trade.amount, 8)}</div>
                  </div>
                  <div>
                    <div className="text-text-secondary text-xs mb-1 font-medium">Price</div>
                    <div className="text-text-primary font-mono text-sm sm:text-base">{formatCurrency(trade.price)}</div>
                  </div>
                  {trade.realized_pnl !== undefined && (
                    <div className="col-span-2 sm:col-span-1">
                      <div className="text-text-secondary text-xs mb-1 font-medium">P&L</div>
                      <div className={`font-semibold font-mono text-sm sm:text-base ${
                        isPositive ? 'text-accent-success' : 'text-accent-danger'
                      }`}>
                        {isPositive ? '+' : ''}{formatCurrency(trade.realized_pnl)}
                      </div>
                    </div>
                  )}
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


