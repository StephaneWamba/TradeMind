import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { strategyApi, exchangeApi } from '@/lib/api'
import { formatPercent } from '@/lib/utils'
import { useWebSocket, type WebSocketMessage } from '@/hooks/useWebSocket'
import { Play, Pause, Settings, TrendingUp, Search, Zap } from 'lucide-react'
import { executionApi } from '@/lib/api'

interface Strategy {
  id: number
  name: string
  status: string
  is_active: boolean
  performance?: number
  trade_count?: number
}

export default function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showActiveOnly, setShowActiveOnly] = useState(false)
  const [executing, setExecuting] = useState<number | null>(null)

  const [connectionId, setConnectionId] = useState<number>(6)

  useEffect(() => {
    // Try to get connection ID from strategies or default to 6
    const fetchConnections = async () => {
      try {
        const response = await exchangeApi.getConnections()
        const conns = response?.connections || []
        if (conns.length > 0) {
          setConnectionId(conns[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch connections:', error)
      }
    }
    fetchConnections()
  }, [])

  const { isConnected, onMessage } = useWebSocket({
    connectionId,
    channels: ['strategies'],
  })

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const data = await strategyApi.getStrategies()
        // Handle both dict with 'strategies' key and list
        if (data && typeof data === 'object') {
          if (Array.isArray(data)) {
            setStrategies(data)
          } else if (data.strategies && Array.isArray(data.strategies)) {
            setStrategies(data.strategies)
          } else {
            setStrategies([])
          }
        } else {
          setStrategies([])
        }
      } catch (error) {
        console.error('Failed to fetch strategies:', error)
        setStrategies([])
      } finally {
        setLoading(false)
      }
    }

    fetchStrategies()
    const interval = setInterval(fetchStrategies, 30000)
    return () => clearInterval(interval)
  }, [])

  // Listen for WebSocket updates
  useEffect(() => {
    const cleanup = onMessage('strategy_status', (message: WebSocketMessage) => {
      if (message.type === 'strategy_status') {
        setStrategies(prev =>
          prev.map(s =>
            s.id === message.strategy_id
              ? { ...s, status: message.status, performance: message.performance }
              : s
          )
        )
      }
    })
    return cleanup
  }, [onMessage])

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">Loading strategies...</div>
        </CardContent>
      </Card>
    )
  }

  if (strategies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Active Strategies</CardTitle>
        </CardHeader>
        <CardContent className="p-8">
          <div className="text-center text-text-secondary">No strategies found</div>
        </CardContent>
      </Card>
    )
  }

  // Filter strategies
  const filteredStrategies = strategies.filter(strategy => {
    const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesActive = !showActiveOnly || strategy.is_active
    return matchesSearch && matchesActive
  })

  const handleExecuteTrade = async (strategyId: number) => {
    if (executing) return
    setExecuting(strategyId)
    try {
      // Default to BTC/USDT for now - could be made configurable
      await executionApi.executeTrade(connectionId, strategyId, 'BTC/USDT')
      alert('Trade execution initiated! Check LLM Logs for details.')
    } catch (error: any) {
      alert(`Failed to execute trade: ${error.response?.data?.detail || error.message}`)
    } finally {
      setExecuting(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between mb-4">
          <span>Trading Strategies ({strategies.filter(s => s.is_active).length} active)</span>
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-accent-success' : 'bg-text-muted'}`} />
        </CardTitle>
        {/* Search and Filter */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search strategies..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-bg-elevated border border-border-default rounded-lg text-text-primary text-sm focus:outline-none focus:border-accent-primary"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={showActiveOnly}
              onChange={(e) => setShowActiveOnly(e.target.checked)}
              className="w-4 h-4 rounded border-border-default bg-bg-elevated text-accent-primary focus:ring-accent-primary"
            />
            Active only
          </label>
        </div>
      </CardHeader>
      <CardContent>
        {filteredStrategies.length === 0 ? (
          <div className="text-center text-text-secondary py-8">
            {searchTerm || showActiveOnly ? 'No strategies match your filters' : 'No strategies found'}
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {filteredStrategies.map((strategy) => {
              const isActive = strategy.is_active && strategy.status === 'active'
              const isPositive = (strategy.performance || 0) >= 0

              return (
              <div
                key={strategy.id}
                className="bg-gradient-to-br from-bg-elevated to-bg-card rounded-lg p-4 border border-border-default hover:border-border-hover hover:shadow-card-hover transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-accent-primary/0 to-accent-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <div className="relative z-10">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`h-3 w-3 rounded-full ${isActive ? 'bg-accent-success' : 'bg-text-muted'}`} />
                    <div>
                      <div className="font-semibold text-text-primary">{strategy.name}</div>
                      <div className="text-xs text-text-secondary capitalize">{strategy.status}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExecuteTrade(strategy.id)}
                      disabled={executing === strategy.id}
                      className="p-1.5 bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Execute autonomous trade"
                    >
                      <Zap className={`h-4 w-4 ${executing === strategy.id ? 'animate-pulse' : ''}`} />
                    </button>
                    {isActive ? (
                      <Pause className="h-4 w-4 text-text-secondary hover:text-text-primary cursor-pointer" />
                    ) : (
                      <Play className="h-4 w-4 text-text-secondary hover:text-text-primary cursor-pointer" />
                    )}
                    <Settings className="h-4 w-4 text-text-secondary hover:text-text-primary cursor-pointer" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-text-secondary mb-1">ROI</div>
                    <div className={`flex items-center gap-1 font-semibold ${
                      isPositive ? 'text-accent-success' : 'text-accent-danger'
                    }`}>
                      {strategy.performance !== undefined && (
                        <>
                          <TrendingUp className="h-4 w-4" />
                          {formatPercent(strategy.performance)}
                        </>
                      )}
                      {strategy.performance === undefined && (
                        <span className="text-text-muted">N/A</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-text-secondary mb-1">Trade Count</div>
                    <div className="text-text-primary font-semibold">
                      {strategy.trade_count || 0}
                    </div>
                  </div>
                </div>
                </div>
              </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

