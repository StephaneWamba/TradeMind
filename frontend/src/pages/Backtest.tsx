import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { backtestApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils'
import { TrendingUp, TrendingDown, Clock } from 'lucide-react'

export default function Backtest() {
  const [strategyId, setStrategyId] = useState(1)
  const [connectionId, setConnectionId] = useState(6)
  const [symbol, setSymbol] = useState('BTC/USDT')
  const [days, setDays] = useState(30)
  const [timeframe, setTimeframe] = useState('1h')
  const [initialBalance, setInitialBalance] = useState(10000)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [backtestId, setBacktestId] = useState<number | null>(null)
  const [status, setStatus] = useState<string>('idle') // idle, pending, running, completed, failed
  const [backtestHistory, setBacktestHistory] = useState<any[]>([])
  const [selectedBacktest, setSelectedBacktest] = useState<number | null>(null)

  // Load backtest history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const historyData = await backtestApi.list({ limit: 20 })
        setBacktestHistory(historyData.backtests || [])
      } catch (err: any) {
        console.error('Error loading backtest history:', err)
      }
    }
    loadHistory()
  }, [])

  // Poll for backtest results
  useEffect(() => {
    if (!backtestId) {
      return
    }

    const pollInterval = setInterval(async () => {
      try {
        const statusData = await backtestApi.getStatus(backtestId)
        console.log('Polling backtest status:', statusData)
        setStatus(statusData.status)

        if (statusData.status === 'completed') {
          setResults(statusData)
          setLoading(false)
          clearInterval(pollInterval)
          // Reload history to show the completed backtest
          const historyData = await backtestApi.list({ limit: 20 })
          setBacktestHistory(historyData.backtests || [])
        } else if (statusData.status === 'failed') {
          setError(statusData.error_message || 'Backtest failed')
          setLoading(false)
          clearInterval(pollInterval)
          // Reload history
          const historyData = await backtestApi.list({ limit: 20 })
          setBacktestHistory(historyData.backtests || [])
        }
      } catch (err: any) {
        console.error('Error polling backtest status:', err)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(pollInterval)
  }, [backtestId]) // Only depend on backtestId, not status

  const handleQuickBacktest = async () => {
    setLoading(true)
    setError(null)
    setResults(null)
    setStatus('idle')
    setBacktestId(null)

    try {
      const result = await backtestApi.quickBacktest({
        strategy_id: strategyId,
        connection_id: connectionId,
        symbol,
        days,
        timeframe,
        initial_balance: initialBalance,
      })
      
      // Backend now returns { backtest_id, status, message }
      if (result.backtest_id) {
        console.log('Backtest started:', result)
        setBacktestId(result.backtest_id)
        setStatus(result.status || 'pending')
        // Reload history to show the new backtest
        const historyData = await backtestApi.list({ limit: 20 })
        setBacktestHistory(historyData.backtests || [])
      } else {
        // Fallback for old API format (direct results)
        setResults(result)
        setLoading(false)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Backtest failed')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Backtesting</h1>
        <p className="text-text-secondary">Test your strategies on historical data</p>
      </div>

      {backtestHistory.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Backtest History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-divider">
                    <th className="text-left py-2 px-4 text-text-secondary">ID</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Symbol</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Date Range</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Status</th>
                    <th className="text-left py-2 px-4 text-text-secondary">P&L</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Trades</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Created</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {backtestHistory.map((bt: any) => (
                    <tr 
                      key={bt.backtest_id} 
                      className={`border-b border-border-divider cursor-pointer hover:bg-bg-elevated ${selectedBacktest === bt.backtest_id ? 'bg-bg-elevated' : ''}`}
                      onClick={async () => {
                        if (bt.status === 'completed' || bt.status === 'failed' || bt.status === 'cancelled') {
                          setSelectedBacktest(bt.backtest_id)
                          try {
                            const data = await backtestApi.getStatus(bt.backtest_id)
                            setResults(data)
                            setBacktestId(bt.backtest_id)
                            setStatus(bt.status)
                          } catch (err: any) {
                            console.error('Error loading backtest:', err)
                          }
                        }
                      }}
                    >
                      <td className="py-2 px-4 text-text-primary">{bt.backtest_id}</td>
                      <td className="py-2 px-4 text-text-primary">{bt.symbol}</td>
                      <td className="py-2 px-4 text-text-primary text-sm">
                        {new Date(bt.start_date).toLocaleDateString()} - {new Date(bt.end_date).toLocaleDateString()}
                      </td>
                      <td className="py-2 px-4">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            bt.status === 'completed'
                              ? 'bg-accent-success/20 text-accent-success'
                              : bt.status === 'failed' || bt.status === 'cancelled'
                              ? 'bg-accent-danger/20 text-accent-danger'
                              : bt.status === 'running'
                              ? 'bg-accent-warning/20 text-accent-warning'
                              : 'bg-accent-info/20 text-accent-info'
                          }`}
                        >
                          {bt.status}
                        </span>
                      </td>
                      <td className={`py-2 px-4 font-semibold ${bt.total_pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                        {bt.total_pnl !== null ? `${formatCurrency(bt.total_pnl)} (${formatPercent(bt.total_pnl_percent / 100)})` : '-'}
                      </td>
                      <td className="py-2 px-4 text-text-primary">{bt.total_trades || '-'}</td>
                      <td className="py-2 px-4 text-text-primary text-sm">
                        {new Date(bt.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 px-4">
                        <div className="flex gap-2">
                          {(bt.status === 'pending' || bt.status === 'running') && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation()
                                try {
                                  await backtestApi.cancel(bt.backtest_id)
                                  // Reload history
                                  const historyData = await backtestApi.list({ limit: 20 })
                                  setBacktestHistory(historyData.backtests || [])
                                } catch (err: any) {
                                  console.error('Error cancelling backtest:', err)
                                  alert(err.response?.data?.detail || 'Failed to cancel backtest')
                                }
                              }}
                              className="px-3 py-1 bg-accent-danger text-white rounded text-sm hover:bg-accent-danger/90"
                            >
                              Cancel
                            </button>
                          )}
                          {bt.status === 'completed' && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation()
                                setSelectedBacktest(bt.backtest_id)
                                try {
                                  const data = await backtestApi.getStatus(bt.backtest_id)
                                  console.log('Backtest data loaded:', data)
                                  setResults(data)
                                  setBacktestId(bt.backtest_id)
                                  setStatus(bt.status)
                                  // Scroll to results section
                                  setTimeout(() => {
                                    const resultsSection = document.querySelector('[data-backtest-results]')
                                    if (resultsSection) {
                                      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                    }
                                  }, 100)
                                } catch (err: any) {
                                  console.error('Error loading backtest:', err)
                                  alert(err.response?.data?.detail || 'Failed to load backtest details')
                                }
                              }}
                              className="px-3 py-1 bg-accent-primary text-white rounded text-sm hover:bg-accent-primary/90"
                            >
                              View
                            </button>
                          )}
                          {(bt.status === 'failed' || bt.status === 'cancelled') && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation()
                                setSelectedBacktest(bt.backtest_id)
                                try {
                                  const data = await backtestApi.getStatus(bt.backtest_id)
                                  console.log('Backtest data loaded:', data)
                                  setResults(data)
                                  setBacktestId(bt.backtest_id)
                                  setStatus(bt.status)
                                  // Scroll to results section
                                  setTimeout(() => {
                                    const resultsSection = document.querySelector('[data-backtest-results]')
                                    if (resultsSection) {
                                      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                    }
                                  }, 100)
                                } catch (err: any) {
                                  console.error('Error loading backtest:', err)
                                  alert(err.response?.data?.detail || 'Failed to load backtest details')
                                }
                              }}
                              className="px-3 py-1 bg-accent-info text-white rounded text-sm hover:bg-accent-info/90"
                            >
                              View
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Backtest Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Strategy ID
              </label>
              <input
                type="number"
                value={strategyId}
                onChange={(e) => setStrategyId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Connection ID
              </label>
              <input
                type="number"
                value={connectionId}
                onChange={(e) => setConnectionId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Symbol
              </label>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="BTC/USDT"
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Days
              </label>
              <input
                type="number"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Timeframe
              </label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              >
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hours</option>
                <option value="1d">1 Day</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Initial Balance (USDT)
              </label>
              <input
                type="number"
                value={initialBalance}
                onChange={(e) => setInitialBalance(Number(e.target.value))}
                className="w-full px-3 py-2 bg-bg-card border border-border-default rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <button
              onClick={handleQuickBacktest}
              disabled={loading || status === 'running' || status === 'pending'}
              className="w-full px-4 py-2 bg-accent-primary text-white rounded-lg font-medium hover:bg-accent-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {status === 'pending' || status === 'running' 
                ? `Running Backtest... (${status})` 
                : loading 
                ? 'Starting Backtest...' 
                : 'Run Quick Backtest'}
            </button>
          </CardContent>
        </Card>

        {results && (
          <div data-backtest-results>
            <Card>
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Initial Balance</span>
                  <span className="text-text-primary font-semibold">
                    {formatCurrency(results.initial_balance)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Final Balance</span>
                  <span className="text-text-primary font-semibold">
                    {formatCurrency(results.final_balance)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Total P&L</span>
                  <span
                    className={`font-semibold ${
                      results.total_pnl >= 0
                        ? 'text-accent-success'
                        : 'text-accent-danger'
                    }`}
                  >
                    {formatCurrency(results.total_pnl)} (
                    {formatPercent(results.total_pnl_percent / 100)})
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Total Trades</span>
                  <span className="text-text-primary font-semibold">
                    {results.total_trades}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Win Rate</span>
                  <span className="text-text-primary font-semibold">
                    {formatPercent(results.win_rate / 100)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Profit Factor</span>
                  <span className="text-text-primary font-semibold">
                    {formatNumber(results.profit_factor)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Max Drawdown</span>
                  <span className="text-accent-danger font-semibold">
                    {formatPercent(results.max_drawdown_percent / 100)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Sharpe Ratio</span>
                  <span className="text-text-primary font-semibold">
                    {formatNumber(results.sharpe_ratio)}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trade Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Winning Trades</span>
                  <span className="text-accent-success font-semibold flex items-center gap-1">
                    <TrendingUp className="w-4 h-4" />
                    {results.winning_trades}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Losing Trades</span>
                  <span className="text-accent-danger font-semibold flex items-center gap-1">
                    <TrendingDown className="w-4 h-4" />
                    {results.losing_trades}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Avg Win</span>
                  <span className="text-accent-success font-semibold">
                    {formatCurrency(results.avg_win)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Avg Loss</span>
                  <span className="text-accent-danger font-semibold">
                    {formatCurrency(results.avg_loss)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Largest Win</span>
                  <span className="text-accent-success font-semibold">
                    {formatCurrency(results.largest_win)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Largest Loss</span>
                  <span className="text-accent-danger font-semibold">
                    {formatCurrency(results.largest_loss)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Avg Duration</span>
                  <span className="text-text-primary font-semibold flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {formatNumber(results.avg_trade_duration_hours)}h
                  </span>
                </div>
              </CardContent>
            </Card>
            </div>
        )}
      </div>

      {error && (
        <Card className="mb-8 border-accent-danger">
          <CardContent className="pt-6">
            <p className="text-accent-danger">{error}</p>
          </CardContent>
        </Card>
      )}

      {results && results.trades && results.trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Trade History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-divider">
                    <th className="text-left py-2 px-4 text-text-secondary">Entry Time</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Exit Time</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Entry Price</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Exit Price</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Quantity</th>
                    <th className="text-left py-2 px-4 text-text-secondary">P&L</th>
                    <th className="text-left py-2 px-4 text-text-secondary">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.trades.map((trade: any, idx: number) => (
                    <tr key={idx} className="border-b border-border-divider">
                      <td className="py-2 px-4 text-text-primary">
                        {new Date(trade.entry_time).toLocaleString()}
                      </td>
                      <td className="py-2 px-4 text-text-primary">
                        {trade.exit_time
                          ? new Date(trade.exit_time).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-2 px-4 text-text-primary">
                        {formatCurrency(trade.entry_price)}
                      </td>
                      <td className="py-2 px-4 text-text-primary">
                        {trade.exit_price
                          ? formatCurrency(trade.exit_price)
                          : '-'}
                      </td>
                      <td className="py-2 px-4 text-text-primary">
                        {formatNumber(trade.quantity)}
                      </td>
                      <td
                        className={`py-2 px-4 font-semibold ${
                          trade.pnl >= 0
                            ? 'text-accent-success'
                            : 'text-accent-danger'
                        }`}
                      >
                        {formatCurrency(trade.pnl)} (
                        {formatPercent(trade.pnl_percent / 100)})
                      </td>
                      <td className="py-2 px-4">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            trade.status === 'closed'
                              ? 'bg-accent-success/20 text-accent-success'
                              : trade.status === 'stopped_out'
                              ? 'bg-accent-danger/20 text-accent-danger'
                              : 'bg-accent-warning/20 text-accent-warning'
                          }`}
                        >
                          {trade.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
      </main>
    </div>
  )
}

