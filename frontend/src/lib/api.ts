import axios from 'axios'

// Use relative URL in production (Vercel rewrites handle proxying)
// Fallback to localhost for local development
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.PROD ? '/api/v1' : 'http://localhost:5000/api/v1')

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout (increased for slow DB queries)
})

// Portfolio API
export const portfolioApi = {
  getValue: async (connectionId: number) => {
    const response = await api.get('/portfolio/value', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getPnl: async (connectionId: number) => {
    const response = await api.get('/portfolio/pnl', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getOverview: async (connectionId: number) => {
    const response = await api.get('/portfolio/overview', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getPerformance: async (connectionId: number) => {
    const response = await api.get('/portfolio/performance', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getAllocation: async (connectionId: number) => {
    const response = await api.get('/portfolio/allocation', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getHistory: async (connectionId: number, days: number = 7) => {
    const response = await api.get('/portfolio/history', { 
      params: { connection_id: connectionId, days } 
    })
    return response.data
  },
}

// Exchange API
export const exchangeApi = {
  getConnections: async () => {
    const response = await api.get('/exchange/connections')
    return response.data
  },
  
  getConnection: async (connectionId: number) => {
    const response = await api.get('/exchange/status', { params: { connection_id: connectionId } })
    return response.data
  },
  
  getBalance: async (connectionId: number) => {
    const response = await api.get('/exchange/balance', { params: { connection_id: connectionId } })
    return response.data
  },
}

// Market API
export const marketApi = {
  getTicker: async (connectionId: number, symbol: string) => {
    const response = await api.get('/market/ticker', { 
      params: { connection_id: connectionId, symbol } 
    })
    return response.data
  },
  getIndicators: async (connectionId: number, symbol: string, timeframe: string = '1h') => {
    const response = await api.get('/market/indicators', {
      params: { connection_id: connectionId, symbol, timeframe },
    })
    return response.data
  },
}

// Strategy API
export const strategyApi = {
  getStrategies: async () => {
    const response = await api.get('/strategy')
    return response.data
  },
  
  getStrategy: async (strategyId: number) => {
    const response = await api.get(`/strategy/${strategyId}`)
    return response.data
  },
}

// Trades API
export const tradesApi = {
  getTrades: async (connectionId?: number, strategyId?: number, limit: number = 50) => {
    const params: any = { limit }
    if (connectionId) {
      params.connection_id = connectionId
    }
    if (strategyId) {
      params.strategy_id = strategyId
    }
    const response = await api.get('/orders/trades/list', { params })
    return response.data
  },
}

// Execution API - Trigger autonomous trading
export const executionApi = {
  executeTrade: async (connectionId: number, strategyId: number, symbol: string) => {
    const response = await api.post('/execution/execute', null, {
      params: {
        connection_id: connectionId,
        strategy_id: strategyId,
        symbol: symbol,
      },
    })
    return response.data
  },
}

// LLM Logs API
export const llmLogsApi = {
  getLogs: async (strategyId?: number, limit: number = 100) => {
    const params: any = { limit }
    if (strategyId) {
      params.strategy_id = strategyId
    }
    const response = await api.get('/llm-logs/logs', { params })
    return response.data
  },
}

// Metrics API
export const metricsApi = {
  getOverview: async (connectionId: number) => {
    const response = await api.get(`/metrics/overview/${connectionId}`)
    return response.data
  },
  
  getPerformance: async (connectionId: number, days: number = 30) => {
    const response = await api.get(`/metrics/performance/${connectionId}`, { params: { days } })
    return response.data
  },
  
  getRisk: async (connectionId: number) => {
    const response = await api.get(`/metrics/risk/${connectionId}`)
    return response.data
  },
  
  getTradeStats: async (connectionId: number) => {
    const response = await api.get(`/metrics/trades/stats/${connectionId}`)
    return response.data
  },
}

// Backtest API
export const backtestApi = {
  quickBacktest: async (params: {
    strategy_id: number
    connection_id: number
    symbol: string
    days: number
    timeframe: string
    initial_balance: number
  }) => {
    const response = await api.get('/backtest/quick', { params })
    return response.data
  },
  runBacktest: async (params: {
    strategy_id: number
    connection_id: number
    symbol: string
    start_date: string
    end_date: string
    timeframe: string
    initial_balance: number
  }) => {
    const response = await api.post('/backtest/run', null, { params })
    return response.data
  },
  getStatus: async (backtestId: number) => {
    const response = await api.get(`/backtest/status/${backtestId}`)
    return response.data
  },
  list: async (params?: {
    strategy_id?: number
    connection_id?: number
    limit?: number
    offset?: number
  }) => {
    const response = await api.get('/backtest/list', { params })
    return response.data
  },
  cancel: async (backtestId: number) => {
    const response = await api.post(`/backtest/cancel/${backtestId}`)
    return response.data
  },
}

