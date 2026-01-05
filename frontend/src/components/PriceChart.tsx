import { useEffect, useRef, useState } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { marketApi } from '@/lib/api'
import { useWebSocket, type WebSocketMessage } from '@/hooks/useWebSocket'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface PriceChartProps {
  connectionId: number
  symbol?: string
}

type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w'

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '4h', value: '4h' },
  { label: '1d', value: '1d' },
  { label: '1w', value: '1w' },
]

export default function PriceChart({ connectionId, symbol = 'BTC/USDT' }: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [timeframe, setTimeframe] = useState<Timeframe>('1h')
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [priceChange, setPriceChange] = useState<number>(0)
  const [indicators, setIndicators] = useState<{
    rsi?: number
    macd?: { macd: number; signal: number; histogram: number }
    signal?: 'BUY' | 'SELL' | 'NEUTRAL'
  } | null>(null)

  const { isConnected, onMessage } = useWebSocket({
    connectionId,
    channels: ['prices'],
  })

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#0f1419' },
        textColor: '#cbd5e1',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1a1e2a', style: 1, visible: true },
        horzLines: { color: '#1a1e2a', style: 1, visible: true },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#3b82f6',
          width: 1,
          style: 2,
          labelBackgroundColor: '#1e222d',
        },
        horzLine: {
          color: '#3b82f6',
          width: 1,
          style: 2,
          labelBackgroundColor: '#1e222d',
        },
      },
      rightPriceScale: {
        borderColor: '#1a1e2a',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
        textColor: '#94a3b8',
      },
      timeScale: {
        borderColor: '#1a1e2a',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#00d4aa',
      downColor: '#ff4757',
      borderVisible: false,
      wickUpColor: '#00d4aa',
      wickDownColor: '#ff4757',
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Fetch initial data and indicators
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch ticker for price
        const ticker = await marketApi.getTicker(connectionId, symbol)
        if (ticker) {
          const price = parseFloat(ticker.last || ticker.price || '0')
          setCurrentPrice(price)
          setPriceChange(ticker.percentage || 0)
        }
        
        // Fetch real indicators from backend
        try {
          const indicatorData = await marketApi.getIndicators(connectionId, symbol, timeframe)
          if (indicatorData) {
            const rsi = indicatorData.rsi
            const macd = indicatorData.macd
            const signal = indicatorData.signal || 'NEUTRAL'
            
            setIndicators({
              rsi: rsi,
              macd: macd ? {
                macd: macd.macd || 0,
                signal: macd.signal || 0,
                histogram: macd.histogram || 0,
              } : undefined,
              signal: signal as 'BUY' | 'SELL' | 'NEUTRAL',
            })
          }
        } catch (indicatorError) {
          console.error('Failed to fetch indicators:', indicatorError)
          // Keep previous indicators or set to null
        }
      } catch (error) {
        console.error('Failed to fetch ticker:', error)
      }
    }

    fetchData()
    // Update indicators every 30 seconds (less frequent than price updates)
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [connectionId, symbol, timeframe])

  // Listen for WebSocket price updates
  useEffect(() => {
    const cleanup = onMessage('price_update', (message: WebSocketMessage) => {
      if (message.type === 'price_update' && message.symbol === symbol.replace('/', '')) {
        setCurrentPrice(message.price)
        if (message.change_24h !== undefined) {
          setPriceChange(message.change_24h)
        }
      }
    })
    return cleanup
  }, [onMessage, symbol])

  // Mock candlestick data (in production, fetch from backend)
  useEffect(() => {
    if (!seriesRef.current) return

    // Generate mock data for demonstration
    const generateMockData = (): CandlestickData[] => {
      const data: CandlestickData[] = []
      const basePrice = currentPrice || 90000
      const now = Math.floor(Date.now() / 1000)
      
      for (let i = 100; i >= 0; i--) {
        const time = (now - i * 3600) as Time
        const open = basePrice + (Math.random() - 0.5) * 1000
        const close = open + (Math.random() - 0.5) * 500
        const high = Math.max(open, close) + Math.random() * 200
        const low = Math.min(open, close) - Math.random() * 200
        
        data.push({
          time,
          open,
          high,
          low,
          close,
        })
      }
      
      return data
    }

    const data = generateMockData()
    seriesRef.current.setData(data)
  }, [currentPrice])

  const isPositive = priceChange >= 0

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <div>
            <CardTitle className="mb-2 text-lg sm:text-xl">{symbol}</CardTitle>
            <div className="flex flex-wrap items-center gap-3">
              {currentPrice && (
                <span className="text-xl sm:text-2xl font-bold font-mono text-text-primary">
                  ${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              )}
              <span className={`text-sm sm:text-base font-semibold px-2 py-1 rounded ${
                isPositive 
                  ? 'text-accent-success bg-accent-success/10' 
                  : 'text-accent-danger bg-accent-danger/10'
              }`}>
                {isPositive ? '+' : ''}{priceChange.toFixed(2)}%
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full animate-pulse ${isConnected ? 'bg-accent-success' : 'bg-text-muted'}`} />
            <span className="text-xs text-text-secondary font-medium">Live</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Timeframe selector */}
        <div className="flex flex-wrap gap-2 mb-4">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all ${
                timeframe === tf.value
                  ? 'bg-accent-primary text-white shadow-card'
                  : 'bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-bg-hover border border-border-default'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>

        {/* Chart container */}
        <div ref={chartContainerRef} className="w-full rounded-lg overflow-hidden mb-4" style={{ height: '400px', minHeight: '300px' }} />
        
        {/* Technical Indicators Panel */}
        {indicators && indicators.rsi !== undefined && indicators.macd ? (
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-default">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-text-secondary mb-1">RSI (14)</div>
                <div className={`text-lg font-bold font-mono ${
                  indicators.rsi < 30 ? 'text-accent-success' :
                  indicators.rsi > 70 ? 'text-accent-danger' :
                  'text-text-primary'
                }`}>
                  {indicators.rsi.toFixed(1)}
                </div>
                <div className="text-xs text-text-muted mt-1">
                  {indicators.rsi < 30 ? 'Oversold' :
                   indicators.rsi > 70 ? 'Overbought' :
                   'Neutral'}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-text-secondary mb-1">MACD</div>
                <div className={`text-lg font-bold font-mono ${
                  indicators.macd.histogram > 0 ? 'text-accent-success' : 'text-accent-danger'
                }`}>
                  {indicators.macd.macd.toFixed(2)}
                </div>
                <div className="text-xs text-text-muted mt-1">
                  Signal: {indicators.macd.signal.toFixed(2)}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-text-secondary mb-1">Histogram</div>
                <div className={`text-lg font-bold font-mono ${
                  indicators.macd.histogram > 0 ? 'text-accent-success' : 'text-accent-danger'
                }`}>
                  {indicators.macd.histogram > 0 ? '+' : ''}{indicators.macd.histogram.toFixed(2)}
                </div>
                <div className="text-xs text-text-muted mt-1">
                  {indicators.macd.histogram > 0 ? 'Bullish' : 'Bearish'}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-text-secondary mb-1">Signal</div>
                <div className={`flex items-center gap-2 text-lg font-bold ${
                  indicators.signal === 'BUY' ? 'text-accent-success' :
                  indicators.signal === 'SELL' ? 'text-accent-danger' :
                  'text-text-primary'
                }`}>
                  {indicators.signal === 'BUY' && <TrendingUp className="h-5 w-5" />}
                  {indicators.signal === 'SELL' && <TrendingDown className="h-5 w-5" />}
                  <span>{indicators.signal}</span>
                </div>
                <div className="text-xs text-text-muted mt-1">
                  {indicators.signal === 'BUY' && 'RSI oversold + MACD bullish'}
                  {indicators.signal === 'SELL' && 'RSI overbought + MACD bearish'}
                  {indicators.signal === 'NEUTRAL' && 'No clear signal'}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-default">
            <div className="text-center text-text-secondary text-sm">Loading indicators...</div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}


