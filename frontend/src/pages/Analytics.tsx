import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { metricsApi, exchangeApi } from '@/lib/api'
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils'
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  BarChart, Bar, CartesianGrid
} from 'recharts'
import { Activity, AlertTriangle, DollarSign, TrendingUp, TrendingDown } from 'lucide-react'

// Custom tooltip for charts
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-bg-card border border-border-default rounded-lg p-3 shadow-card-hover backdrop-blur-sm">
        <p className="text-text-secondary text-xs font-medium mb-2 uppercase tracking-wide">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-text-primary text-sm font-semibold" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' 
              ? (entry.name.includes('P&L') || entry.name.includes('Cumulative') 
                  ? formatCurrency(entry.value) 
                  : formatNumber(entry.value, 2))
              : entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function Analytics() {
  const [_connectionId, setConnectionId] = useState<number | null>(null)
  const [overview, setOverview] = useState<any>(null)
  const [performance, setPerformance] = useState<any>(null)
  const [risk, setRisk] = useState<any>(null)
  const [tradeStats, setTradeStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const connId = 6
    setConnectionId(connId)
    
    const fetchData = async (connId: number) => {
      try {
        const [overviewData, perfData, riskData, statsData] = await Promise.all([
          metricsApi.getOverview(connId),
          metricsApi.getPerformance(connId, 30),
          metricsApi.getRisk(connId),
          metricsApi.getTradeStats(connId),
        ])
        setOverview(overviewData)
        setPerformance(perfData)
        setRisk(riskData)
        setTradeStats(statsData)
      } catch (error) {
        console.error('Failed to fetch analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData(connId)
    
    const fetchConnections = async () => {
      try {
        const response = await exchangeApi.getConnections()
        const conns = response?.connections || []
        if (conns.length > 0 && conns[0].id !== connId) {
          setConnectionId(conns[0].id)
          fetchData(conns[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch connections:', error)
      }
    }

    fetchConnections()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary">
        <Header />
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-text-secondary">Loading analytics...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8 animate-fade-in-up">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">Business Metrics & Analytics</h1>
          <p className="text-text-muted text-sm">Comprehensive trading performance and risk analysis</p>
        </div>

        {/* Overview Metrics - Responsive Grid */}
        {overview && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
            <Card className="bg-gradient-to-br from-bg-card to-bg-elevated hover:from-bg-elevated hover:to-bg-card transition-all duration-300 group">
              <CardContent className="p-4 sm:p-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-accent-primary/5 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-text-secondary text-sm font-medium">Total Trades</span>
                    <div className="p-1.5 bg-accent-primary/10 rounded-lg group-hover:bg-accent-primary/20 transition-colors">
                      <Activity className="h-4 w-4 text-accent-primary" />
                    </div>
                  </div>
                  <div className="text-2xl sm:text-3xl font-bold font-mono text-text-primary mb-1">
                    {formatNumber(overview.total_trades)}
                  </div>
                  <div className="flex items-center gap-2 text-xs sm:text-sm">
                    <span className="text-text-muted">Win Rate:</span>
                    <span className={`font-semibold ${
                      (overview.win_rate || 0) > 50 ? 'text-accent-success' : 'text-accent-danger'
                    }`}>
                      {formatPercent(overview.win_rate)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={`bg-gradient-to-br from-bg-card to-bg-elevated hover:from-bg-elevated hover:to-bg-card transition-all duration-300 group ${
              (overview.total_pnl || 0) >= 0 ? 'hover:shadow-glow-success' : 'hover:shadow-glow-danger'
            }`}>
              <CardContent className="p-4 sm:p-6 relative overflow-hidden">
                <div className={`absolute top-0 right-0 w-20 h-20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                  (overview.total_pnl || 0) >= 0 ? 'bg-accent-success/10' : 'bg-accent-danger/10'
                }`} />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-text-secondary text-sm font-medium">Total P&L</span>
                    <div className={`p-1.5 rounded-lg transition-colors ${
                      (overview.total_pnl || 0) >= 0 
                        ? 'bg-accent-success/10 group-hover:bg-accent-success/20' 
                        : 'bg-accent-danger/10 group-hover:bg-accent-danger/20'
                    }`}>
                      <DollarSign className={`h-4 w-4 ${
                        (overview.total_pnl || 0) >= 0 ? 'text-accent-success' : 'text-accent-danger'
                      }`} />
                    </div>
                  </div>
                  <div className={`text-2xl sm:text-3xl font-bold font-mono mb-1 ${
                    (overview.total_pnl || 0) >= 0 ? 'text-accent-success' : 'text-accent-danger'
                  }`}>
                    {formatCurrency(overview.total_pnl)}
                  </div>
                  <div className="text-xs sm:text-sm text-text-muted">
                    {formatPercent(overview.total_pnl_percent)}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={`bg-gradient-to-br from-bg-card to-bg-elevated hover:from-bg-elevated hover:to-bg-card transition-all duration-300 group ${
              (overview.daily_pnl || 0) >= 0 ? 'hover:shadow-glow-success' : 'hover:shadow-glow-danger'
            }`}>
              <CardContent className="p-4 sm:p-6 relative overflow-hidden">
                <div className={`absolute top-0 right-0 w-20 h-20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                  (overview.daily_pnl || 0) >= 0 ? 'bg-accent-success/10' : 'bg-accent-danger/10'
                }`} />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-text-secondary text-sm font-medium">Daily P&L</span>
                    <div className={`p-1.5 rounded-lg transition-colors ${
                      (overview.daily_pnl || 0) >= 0 
                        ? 'bg-accent-success/10 group-hover:bg-accent-success/20' 
                        : 'bg-accent-danger/10 group-hover:bg-accent-danger/20'
                    }`}>
                      {(overview.daily_pnl || 0) >= 0 ? (
                        <TrendingUp className="h-4 w-4 text-accent-success" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-accent-danger" />
                      )}
                    </div>
                  </div>
                  <div className={`text-2xl sm:text-3xl font-bold font-mono mb-1 ${
                    (overview.daily_pnl || 0) >= 0 ? 'text-accent-success' : 'text-accent-danger'
                  }`}>
                    {formatCurrency(overview.daily_pnl)}
                  </div>
                  <div className="text-xs sm:text-sm text-text-muted">
                    {formatPercent(overview.daily_pnl_percent)}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={`bg-gradient-to-br from-bg-card to-bg-elevated hover:from-bg-elevated hover:to-bg-card transition-all duration-300 group ${
              (overview.portfolio_heat || 0) > 10 ? 'hover:shadow-glow-danger' : 
              (overview.portfolio_heat || 0) > 5 ? 'hover:shadow-glow' : ''
            }`}>
              <CardContent className="p-4 sm:p-6 relative overflow-hidden">
                <div className={`absolute top-0 right-0 w-20 h-20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${
                  (overview.portfolio_heat || 0) > 10 ? 'bg-accent-danger/10' : 
                  (overview.portfolio_heat || 0) > 5 ? 'bg-accent-warning/10' : 'bg-accent-success/10'
                }`} />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-text-secondary text-sm font-medium">Portfolio Heat</span>
                    <div className={`p-1.5 rounded-lg transition-colors ${
                      (overview.portfolio_heat || 0) > 10 
                        ? 'bg-accent-danger/10 group-hover:bg-accent-danger/20' 
                        : (overview.portfolio_heat || 0) > 5
                        ? 'bg-accent-warning/10 group-hover:bg-accent-warning/20'
                        : 'bg-accent-success/10 group-hover:bg-accent-success/20'
                    }`}>
                      <AlertTriangle className={`h-4 w-4 ${
                        (overview.portfolio_heat || 0) > 10 ? 'text-accent-danger' : 
                        (overview.portfolio_heat || 0) > 5 ? 'text-accent-warning' : 'text-accent-success'
                      }`} />
                    </div>
                  </div>
                  <div className={`text-2xl sm:text-3xl font-bold font-mono mb-1 ${
                    (overview.portfolio_heat || 0) > 10 ? 'text-accent-danger' : 
                    (overview.portfolio_heat || 0) > 5 ? 'text-accent-warning' : 'text-accent-success'
                  }`}>
                    {formatPercent(overview.portfolio_heat)}
                  </div>
                  <div className="text-xs sm:text-sm text-text-muted">
                    {overview.active_positions} active positions
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Trade Statistics */}
        {tradeStats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
            <Card>
              <CardContent className="p-4 sm:p-6">
                <div className="text-text-secondary text-sm font-medium mb-2">Profit Factor</div>
                <div className={`text-xl sm:text-2xl font-bold font-mono ${
                  (tradeStats.profit_factor || 0) > 1 ? 'text-accent-success' : 'text-accent-danger'
                }`}>
                  {formatNumber(tradeStats.profit_factor, 2)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 sm:p-6">
                <div className="text-text-secondary text-sm font-medium mb-2">Avg Win</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-accent-success">
                  {formatCurrency(tradeStats.avg_win)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 sm:p-6">
                <div className="text-text-secondary text-sm font-medium mb-2">Avg Loss</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-accent-danger">
                  {formatCurrency(tradeStats.avg_loss)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 sm:p-6">
                <div className="text-text-secondary text-sm font-medium mb-2">Largest Win/Loss</div>
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-accent-success">
                    Win: {formatCurrency(tradeStats.largest_win)}
                  </div>
                  <div className="text-sm font-semibold text-accent-danger">
                    Loss: {formatCurrency(tradeStats.largest_loss)}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Performance Charts */}
        {performance && performance.daily_returns && performance.daily_returns.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6 sm:mb-8">
            <Card>
              <CardHeader>
                <CardTitle>Cumulative P&L (30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={performance.cumulative_pnl} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorCumulative" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.4}/>
                        <stop offset="50%" stopColor="#00d4aa" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#00d4aa" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2a" opacity={0.5} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#94a3b8"
                      tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis 
                      stroke="#94a3b8"
                      tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
                      tickFormatter={(value) => formatCurrency(value)}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area 
                      type="monotone" 
                      dataKey="cumulative" 
                      stroke="#00d4aa" 
                      strokeWidth={2.5}
                      fill="url(#colorCumulative)"
                      dot={false}
                      activeDot={{ r: 4, fill: '#00d4aa', stroke: '#0f1419', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Daily Returns (30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={performance.daily_returns} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1e2a" opacity={0.5} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#94a3b8"
                      tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis 
                      stroke="#94a3b8"
                      tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
                      tickFormatter={(value) => formatCurrency(value)}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar 
                      dataKey="pnl" 
                      radius={[6, 6, 0, 0]}
                      fill="#00d4aa"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Risk Metrics */}
        {risk && (
          <Card className="mb-6 sm:mb-8">
            <CardHeader>
              <CardTitle>Risk Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold mb-3 text-text-primary">Portfolio Heat</h3>
                    <div className={`text-3xl font-bold mb-2 ${
                      (risk.portfolio_heat?.current_heat || 0) > 10 ? 'text-accent-danger' : 
                      (risk.portfolio_heat?.current_heat || 0) > 5 ? 'text-accent-warning' : 'text-accent-success'
                    }`}>
                      {formatPercent(risk.portfolio_heat?.current_heat || 0)}
                    </div>
                    <div className="text-sm text-text-secondary">
                      Total Risk: {formatCurrency(risk.portfolio_heat?.total_risk_usdt || 0)}
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-3 text-text-primary">Strategy Risks</h3>
                  {risk.strategy_risks && risk.strategy_risks.length > 0 ? (
                    <div className="space-y-3">
                      {risk.strategy_risks.map((s: any) => (
                        <div key={s.strategy_id} className="bg-bg-elevated rounded-lg p-3 border border-border-default">
                          <div className="font-medium text-text-primary mb-1">{s.strategy_name}</div>
                          <div className="text-sm text-text-secondary space-y-1">
                            <div>Daily Loss: {formatPercent(s.current_daily_loss)} / {formatPercent(s.max_daily_loss_percent)}</div>
                            {s.circuit_breaker_active && (
                              <div className="text-accent-danger flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Circuit Breaker Active
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-text-secondary">No active strategies</div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
