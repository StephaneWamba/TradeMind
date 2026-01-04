import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils'
import { llmLogsApi } from '@/lib/api'
import { format } from 'date-fns'
import { Brain, TrendingUp, TrendingDown, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

interface LLMLog {
  id: number
  type: 'trade' | 'execution'
  strategy_id: number
  symbol?: string
  action?: string
  reasoning: string
  confidence?: number
  entry_price?: number
  exit_price?: number
  amount?: number
  pnl?: number
  pnl_percent?: number
  status?: string
  execution_type?: string
  result?: any
  execution_time_ms?: number
  timestamp: string
}

export default function LLMLogs() {
  const [logs, setLogs] = useState<LLMLog[]>([])
  const [loading, setLoading] = useState(true)
  const [strategyFilter, setStrategyFilter] = useState<number | null>(null)

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await llmLogsApi.getLogs(strategyFilter || undefined, 100)
        setLogs(data.logs || [])
      } catch (error) {
        console.error('Failed to fetch LLM logs:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchLogs()
    // Refresh every 10 seconds
    const interval = setInterval(fetchLogs, 10000)
    return () => clearInterval(interval)
  }, [strategyFilter])

  const getActionColor = (action?: string) => {
    if (!action) return 'text-text-secondary'
    if (action === 'BUY') return 'text-accent-success'
    if (action === 'SELL') return 'text-accent-danger'
    return 'text-text-primary'
  }

  const getStatusIcon = (status?: string) => {
    if (status === 'closed') return <CheckCircle className="h-4 w-4 text-accent-success" />
    if (status === 'open') return <AlertCircle className="h-4 w-4 text-accent-warning" />
    if (status === 'stopped') return <XCircle className="h-4 w-4 text-accent-danger" />
    return null
  }

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-text-secondary'
    if (confidence >= 0.8) return 'text-accent-success'
    if (confidence >= 0.6) return 'text-accent-warning'
    return 'text-accent-danger'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary">
        <Header />
        <div className="container mx-auto px-6 py-8">
          <div className="text-center text-text-secondary">Loading LLM logs...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8 animate-fade-in-up">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-0 mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary flex items-center gap-3">
            <Brain className="h-6 w-6 sm:h-8 sm:w-8 text-accent-primary" />
            LLM Decision Logs
          </h1>
          
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <label className="text-text-secondary text-sm font-medium whitespace-nowrap">Strategy:</label>
            <select
              value={strategyFilter || ''}
              onChange={(e) => setStrategyFilter(e.target.value ? parseInt(e.target.value) : null)}
              className="flex-1 sm:flex-none bg-bg-elevated border border-border-default rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-accent-primary hover:border-border-hover transition-colors"
            >
              <option value="">All Strategies</option>
              <option value="1">Strategy 1</option>
            </select>
          </div>
        </div>

        {logs.length === 0 ? (
          <Card>
            <CardContent className="p-8">
              <div className="text-center text-text-secondary">
                <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No LLM logs found</p>
                <p className="text-sm mt-2">LLM reasoning will appear here when trades are executed</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {logs.map((log) => (
              <Card key={`${log.type}-${log.id}`} className="border-l-4 border-l-accent-primary hover:shadow-card-hover transition-shadow">
                <CardHeader>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
                    <div className="flex items-center gap-3">
                      <div className="bg-accent-primary/20 p-2 rounded-lg">
                        <Brain className="h-5 w-5 text-accent-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-base sm:text-lg">
                          {log.type === 'trade' ? (
                            <>
                              <span className={getActionColor(log.action)}>{log.action}</span>
                              {' '}
                              <span className="text-text-primary">{log.symbol}</span>
                              {log.status && (
                                <span className="ml-2">{getStatusIcon(log.status)}</span>
                              )}
                            </>
                          ) : (
                            <span className="text-text-primary">
                              {log.execution_type?.toUpperCase()} Execution
                            </span>
                          )}
                        </CardTitle>
                        <div className="text-xs sm:text-sm text-text-secondary mt-1">
                          Strategy {log.strategy_id} • {format(new Date(log.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                        </div>
                      </div>
                    </div>
                    
                    {log.confidence !== undefined && (
                      <div className={`text-base sm:text-lg font-bold font-mono ${getConfidenceColor(log.confidence)}`}>
                        {(log.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                  </div>
                </CardHeader>
                
                <CardContent>
                  {/* LLM Reasoning */}
                  <div className="mb-4">
                    <div className="text-sm font-semibold text-text-secondary mb-2">LLM Reasoning:</div>
                    <div className="bg-bg-elevated rounded-lg p-4 border border-border-default">
                      <p className="text-text-primary whitespace-pre-wrap leading-relaxed">
                        {log.reasoning}
                      </p>
                    </div>
                  </div>

                  {/* Trade Details */}
                  {log.type === 'trade' && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4">
                      {log.entry_price && (
                        <div>
                          <div className="text-xs text-text-secondary mb-1">Entry Price</div>
                          <div className="text-text-primary font-mono font-semibold">
                            {formatCurrency(log.entry_price)}
                          </div>
                        </div>
                      )}
                      {log.exit_price && (
                        <div>
                          <div className="text-xs text-text-secondary mb-1">Exit Price</div>
                          <div className="text-text-primary font-mono font-semibold">
                            {formatCurrency(log.exit_price)}
                          </div>
                        </div>
                      )}
                      {log.amount && (
                        <div>
                          <div className="text-xs text-text-secondary mb-1">Amount</div>
                          <div className="text-text-primary font-mono font-semibold">
                            {formatNumber(log.amount, 8)}
                          </div>
                        </div>
                      )}
                      {log.pnl !== undefined && (
                        <div>
                          <div className="text-xs text-text-secondary mb-1">P&L</div>
                          <div className={`font-mono font-semibold ${
                            log.pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'
                          }`}>
                            {log.pnl >= 0 ? '+' : ''}{formatCurrency(log.pnl)}
                            {log.pnl_percent !== undefined && (
                              <span className="text-sm ml-1">
                                ({formatPercent(log.pnl_percent)})
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Execution Details */}
                  {log.type === 'execution' && log.result && (
                    <div className="mb-4">
                      <div className="text-sm font-semibold text-text-secondary mb-2">Execution Result:</div>
                      <div className="bg-bg-elevated rounded-lg p-4 border border-border-default">
                        <pre className="text-xs text-text-primary overflow-x-auto">
                          {JSON.stringify(log.result, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Performance Metrics */}
                  <div className="flex items-center gap-4 text-sm text-text-secondary">
                    {log.execution_time_ms && (
                      <div>
                        Latency: <span className="text-text-primary font-mono">{log.execution_time_ms.toFixed(0)}ms</span>
                      </div>
                    )}
                    {log.status && (
                      <div>
                        Status: <span className="text-text-primary capitalize">{log.status}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

