import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { portfolioApi } from '@/lib/api'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { useWebSocket, type WebSocketMessage } from '@/hooks/useWebSocket'
import { TrendingUp, TrendingDown, DollarSign, Wallet } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'

interface PortfolioOverviewProps {
  connectionId: number
}

export default function PortfolioOverview({ connectionId }: PortfolioOverviewProps) {
  const [portfolioData, setPortfolioData] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const { isConnected, onMessage } = useWebSocket({
    connectionId,
    channels: ['portfolio'],
  })

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [overview, historyData] = await Promise.all([
          portfolioApi.getOverview(connectionId).catch(err => {
            console.error('Failed to fetch overview:', err)
            // Return default structure
            return {
              current_value: {
                total_value_usdt: 0,
                cash_usdt: 0,
                invested_usdt: 0,
                unrealized_pnl: 0,
                unrealized_pnl_percent: 0,
                daily_pnl: 0,
                daily_pnl_percent: 0,
              }
            }
          }),
          portfolioApi.getHistory(connectionId, 7).catch(err => {
            console.error('Failed to fetch history:', err)
            return { history: [] }
          }),
        ])
        
        // Extract current_value if it's nested
        const data = overview.current_value || overview
        setPortfolioData(data)
        setHistory(historyData.history || [])
      } catch (error) {
        console.error('Failed to fetch portfolio data:', error)
        // Set default empty data
        setPortfolioData({
          total_value_usdt: 0,
          cash_usdt: 0,
          invested_usdt: 0,
          unrealized_pnl: 0,
          unrealized_pnl_percent: 0,
          daily_pnl: 0,
          daily_pnl_percent: 0,
        })
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    
    // Refresh every 10 seconds
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [connectionId])

  // Listen for WebSocket updates
  useEffect(() => {
    const cleanup = onMessage('portfolio_update', (message: WebSocketMessage) => {
      if (message.type === 'portfolio_update') {
        setPortfolioData({
          total_value_usdt: message.total_value_usdt,
          cash_usdt: message.cash_usdt,
          invested_usdt: message.invested_usdt,
          unrealized_pnl: message.unrealized_pnl,
          unrealized_pnl_percent: message.unrealized_pnl_percent,
          daily_pnl: message.daily_pnl,
          daily_pnl_percent: message.daily_pnl_percent,
        })
      }
    })
    return cleanup
  }, [onMessage])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">Loading portfolio data...</div>
        </CardContent>
      </Card>
    )
  }

  if (!portfolioData) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">No portfolio data available</div>
        </CardContent>
      </Card>
    )
  }

  const isPositive = (portfolioData.daily_pnl ?? 0) >= 0
  const isUnrealizedPositive = (portfolioData.unrealized_pnl ?? 0) >= 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Portfolio Overview</span>
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-accent-success' : 'bg-text-muted'}`} />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 mb-6">
          {/* Total Value */}
          <div className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-3 sm:p-4 border border-border-default hover:border-border-hover hover:shadow-inner transition-all duration-300 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-accent-primary/0 to-accent-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-text-muted" />
              <span className="text-xs sm:text-sm text-text-secondary font-medium">Total Equity</span>
            </div>
            <div className="text-xl sm:text-2xl font-bold text-text-primary font-mono">
              {formatCurrency(portfolioData.total_value_usdt)}
            </div>
            </div>
          </div>

          {/* Daily P&L */}
          <div className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-3 sm:p-4 border border-border-default hover:border-border-hover hover:shadow-inner transition-all duration-300 relative overflow-hidden group">
            <div className={`absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
              isPositive ? 'from-accent-success/0 to-accent-success/5' : 'from-accent-danger/0 to-accent-danger/5'
            }`} />
            <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              {isPositive ? (
                <TrendingUp className="h-4 w-4 text-accent-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-accent-danger" />
              )}
              <span className="text-xs sm:text-sm text-text-secondary font-medium">Daily P&L</span>
            </div>
            <div className={`text-xl sm:text-2xl font-bold font-mono ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
              {isPositive ? '+' : ''}{formatCurrency(portfolioData.daily_pnl)}
            </div>
            <div className={`text-xs sm:text-sm font-medium ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
              {formatPercent(portfolioData.daily_pnl_percent)}
            </div>
            </div>
          </div>

          {/* Cash */}
          <div className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-3 sm:p-4 border border-border-default hover:border-border-hover hover:shadow-inner transition-all duration-300 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-accent-info/0 to-accent-info/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Wallet className="h-4 w-4 text-text-muted" />
              <span className="text-xs sm:text-sm text-text-secondary font-medium">Available Balance</span>
            </div>
            <div className="text-lg sm:text-xl font-semibold text-text-primary font-mono">
              {formatCurrency(portfolioData.cash_usdt)}
            </div>
            </div>
          </div>

          {/* Invested */}
          <div className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-3 sm:p-4 border border-border-default hover:border-border-hover hover:shadow-inner transition-all duration-300 relative overflow-hidden group">
            <div className={`absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
              isUnrealizedPositive ? 'from-accent-success/0 to-accent-success/5' : 'from-accent-danger/0 to-accent-danger/5'
            }`} />
            <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-text-muted" />
              <span className="text-xs sm:text-sm text-text-secondary font-medium">Margin Used</span>
            </div>
            <div className="text-lg sm:text-xl font-semibold text-text-primary font-mono">
              {formatCurrency(portfolioData.invested_usdt)}
            </div>
            <div className={`text-xs sm:text-sm font-medium ${isUnrealizedPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
              {formatPercent(portfolioData.unrealized_pnl_percent)} unrealized
            </div>
            </div>
          </div>
        </div>

        {/* Mini Performance Chart */}
        {history.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border-divider">
            <div className="text-sm text-text-secondary mb-3 font-medium">7-Day Equity Curve</div>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={history} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isPositive ? '#00d4aa' : '#ff4757'} stopOpacity={0.3}/>
                    <stop offset="50%" stopColor={isPositive ? '#00d4aa' : '#ff4757'} stopOpacity={0.15}/>
                    <stop offset="95%" stopColor={isPositive ? '#00d4aa' : '#ff4757'} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Line 
                  type="monotone" 
                  dataKey="total_value_usdt" 
                  stroke={isPositive ? '#00d4aa' : '#ff4757'} 
                  strokeWidth={3}
                  dot={false}
                  fill="url(#colorValue)"
                  activeDot={{ r: 4, fill: isPositive ? '#00d4aa' : '#ff4757', stroke: '#0f1419', strokeWidth: 2 }}
                />
                <XAxis 
                  dataKey="date" 
                  hide 
                  stroke="#94a3b8"
                />
                <YAxis 
                  hide 
                  stroke="#94a3b8"
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e222d', 
                    border: '1px solid #363a45',
                    borderRadius: '8px',
                    padding: '10px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
                  }}
                  labelStyle={{ color: '#cbd5e1', fontSize: '12px', fontWeight: 600 }}
                  formatter={(value: number) => formatCurrency(value)}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

