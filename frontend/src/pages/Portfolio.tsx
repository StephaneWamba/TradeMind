import { useState, useEffect } from 'react'
import Header from '@/components/Header'
import PortfolioOverview from '@/components/PortfolioOverview'
import ActivePositions from '@/components/ActivePositions'
import PriceChart from '@/components/PriceChart'
import { exchangeApi } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'

export default function Portfolio() {
  const [connectionId, setConnectionId] = useState<number | null>(null)
  const [manualConnectionId, setManualConnectionId] = useState<string>('6')
  const [loading, setLoading] = useState(true)
  const [connections, setConnections] = useState<any[]>([])
  const [_showManualInput, setShowManualInput] = useState(false)

  useEffect(() => {
    // Set default connection immediately to prevent infinite loading
    setConnectionId(6)
    setLoading(false)
    
    // Try to fetch connections in background (non-blocking)
    const fetchConnections = async () => {
      try {
        const response = await exchangeApi.getConnections()
        const conns = response?.connections || []
        setConnections(conns)
        
        if (conns.length > 0) {
          setConnectionId(conns[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch connections:', error)
        // Keep default connection ID 6
      }
    }

    // Fetch in background, don't block UI
    fetchConnections()
  }, [])

  const handleManualConnection = () => {
    const id = parseInt(manualConnectionId)
    if (!isNaN(id) && id > 0) {
      setConnectionId(id)
      setShowManualInput(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-primary">
        <Header />
        <div className="container mx-auto px-6 py-8">
          <div className="text-center text-text-secondary">Loading...</div>
        </div>
      </div>
    )
  }

  if (!connectionId) {
    return (
      <div className="min-h-screen bg-bg-primary">
        <Header />
        <div className="container mx-auto px-6 py-8">
          <Card className="max-w-md mx-auto">
            <CardContent className="p-6">
              <h2 className="text-2xl font-bold text-text-primary mb-4 text-center">No Exchange Connection</h2>
              <p className="text-text-secondary mb-6 text-center">
                Enter a connection ID to continue
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-2">Connection ID</label>
                  <input
                    type="number"
                    value={manualConnectionId}
                    onChange={(e) => setManualConnectionId(e.target.value)}
                    className="w-full bg-bg-elevated border border-border-default rounded-lg px-4 py-2 text-text-primary focus:outline-none focus:border-accent-primary"
                    placeholder="Enter connection ID (e.g., 6)"
                  />
                </div>
                
                <button
                  onClick={handleManualConnection}
                  className="w-full bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                >
                  Connect
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Header />
      <main className="max-w-page mx-auto px-6 sm:px-8 lg:px-16 xl:px-20 py-6 sm:py-8 animate-fade-in-up">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2">Portfolio</h1>
          <p className="text-text-muted text-sm">Monitor your trading positions and performance</p>
        </div>

        {connections.length > 0 && (
          <div className="mb-4 sm:mb-6 flex items-center gap-3">
            <span className="text-text-secondary text-sm font-medium whitespace-nowrap">Connection:</span>
            <select
              value={connectionId || ''}
              onChange={(e) => setConnectionId(parseInt(e.target.value))}
              className="flex-1 sm:flex-none bg-bg-elevated border border-border-default rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-accent-primary hover:border-border-hover transition-colors"
            >
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.exchange} {conn.is_testnet ? '(Testnet)' : ''} - ID: {conn.id}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
          <PortfolioOverview connectionId={connectionId} />
          <ActivePositions connectionId={connectionId} />
        </div>
        
        <div className="mb-6">
          <PriceChart connectionId={connectionId} symbol="BTC/USDT" />
        </div>
      </main>
    </div>
  )
}

