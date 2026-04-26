import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Activity, PieChart } from 'lucide-react'
import api from '../services/api'

export default function DashboardPage() {
  const [portfolio, setPortfolio] = useState<any>(null)
  const [indices, setIndices] = useState<any[]>([])
  const [watchlistQuotes, setWatchlistQuotes] = useState<any[]>([])

  useEffect(() => { loadDashboard() }, [])

  const loadDashboard = async () => {
    try {
      const [portfolioRes, indicesRes] = await Promise.all([
        api.get('/api/portfolio/'),
        api.get('/api/market/indices'),
      ])
      if (portfolioRes.data.length > 0) setPortfolio(portfolioRes.data[0])
      setIndices(indicesRes.data.indices || [])
    } catch {}

    // Load watchlist quotes (same as market page)
    try {
      const wlRes = await api.get('/api/watchlist/')
      const wl = wlRes.data.watchlists?.find((w: any) => w.is_default) || wlRes.data.watchlists?.[0]
      if (wl?.items?.length) {
        const codes = wl.items.map((it: any) => it.stock_code).join(',')
        const qRes = await api.get(`/api/market/quotes?codes=${codes}`)
        setWatchlistQuotes(qRes.data.stocks || [])
      }
    } catch {}
  }

  const stats = [
    { label: '总资产', value: portfolio ? `¥${(portfolio.total_value || 0).toLocaleString()}` : '¥1,000,000', icon: DollarSign, color: 'text-accent-gold' },
    { label: '总收益', value: portfolio ? `${(portfolio.total_profit_pct || 0).toFixed(2)}%` : '0.00%', icon: (portfolio?.total_profit || 0) >= 0 ? TrendingUp : TrendingDown, color: (portfolio?.total_profit || 0) >= 0 ? 'text-accent-red' : 'text-accent-green' },
    { label: '持仓数', value: portfolio?.positions?.length || 0, icon: PieChart, color: 'text-blue-400' },
    { label: '自选股', value: watchlistQuotes.length, icon: Activity, color: 'text-purple-400' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">总览</h1>
        <p className="text-gray-500 text-sm mt-1">证券交易助手</p>
      </div>

      {/* 市场指数 */}
      {indices.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {indices.map((idx: any, i: number) => (
            <div key={i} className="card">
              <p className="text-xs text-gray-500">{idx.index_name || idx.name}</p>
              <p className={`text-xl font-bold font-mono mt-1 ${(idx.change_pct||0) > 0 ? 'stock-up' : (idx.change_pct||0) < 0 ? 'stock-down' : 'text-white'}`}>
                {idx.current_price?.toFixed(2)}
              </p>
              <p className={`text-xs font-mono ${(idx.change_pct||0) > 0 ? 'stock-up' : (idx.change_pct||0) < 0 ? 'stock-down' : 'text-gray-400'}`}>
                {(idx.change_pct||0) > 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
              </p>
            </div>
          ))}
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">{label}</p>
                <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
              </div>
              <div className="p-2.5 rounded-lg bg-surface-hover"><Icon className={`w-5 h-5 ${color}`} /></div>
            </div>
          </div>
        ))}
      </div>

      {/* 自选股票池行情 (与行情页一致) */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent-gold" /> 自选股票池
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs border-b border-surface-border">
                <th className="text-left py-3 px-2">代码</th>
                <th className="text-left py-3 px-2">名称</th>
                <th className="text-right py-3 px-2">最新价</th>
                <th className="text-right py-3 px-2">涨跌幅</th>
                <th className="text-right py-3 px-2">成交量</th>
                <th className="text-right py-3 px-2">成交额</th>
                <th className="text-right py-3 px-2">市盈率</th>
                <th className="text-center py-3 px-2">详情</th>
              </tr>
            </thead>
            <tbody>
              {watchlistQuotes.map((q: any, i: number) => (
                <tr key={i} className="border-b border-surface-border/50 hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-2 font-mono text-gray-300 text-xs">{q.code?.replace(/^(sh|sz)/, '')}</td>
                  <td className="py-3 px-2 text-white font-medium">{q.name}</td>
                  <td className={`py-3 px-2 text-right font-mono font-medium ${(q.change_pct||0) > 0 ? 'stock-up' : (q.change_pct||0) < 0 ? 'stock-down' : 'text-gray-300'}`}>
                    {q.current_price?.toFixed(2)}
                  </td>
                  <td className={`py-3 px-2 text-right font-mono ${(q.change_pct||0) > 0 ? 'stock-up' : (q.change_pct||0) < 0 ? 'stock-down' : 'text-gray-300'}`}>
                    {(q.change_pct||0) > 0 ? '+' : ''}{q.change_pct?.toFixed(2)}%
                  </td>
                  <td className="py-3 px-2 text-right text-gray-400 font-mono text-xs">{q.volume?.toLocaleString()}</td>
                  <td className="py-3 px-2 text-right text-gray-400 font-mono text-xs">{q.amount?.toLocaleString()}</td>
                  <td className="py-3 px-2 text-right text-gray-400 font-mono text-xs">{q.pe_ratio?.toFixed(1)}</td>
                  <td className="py-3 px-2 text-center">
                    <a href={`https://gu.qq.com/${q.code}/gp`} target="_blank" rel="noopener noreferrer"
                      className="text-primary-400 hover:text-primary-300 text-xs">详情 →</a>
                  </td>
                </tr>
              ))}
              {watchlistQuotes.length === 0 && (
                <tr><td colSpan={8} className="py-8 text-center text-gray-500">自选为空，前往行情页添加</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 持仓概况 */}
      {portfolio?.positions?.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">持仓概况</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {portfolio.positions.map((pos: any, i: number) => (
              <div key={i} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-white font-medium text-sm">{pos.stock_name}</p>
                    <p className="text-gray-500 text-xs font-mono">{pos.stock_code}</p>
                  </div>
                  <span className={`text-sm font-mono font-medium ${(pos.profit||0) >= 0 ? 'stock-up' : 'stock-down'}`}>
                    {(pos.profit_pct||0) >= 0 ? '+' : ''}{pos.profit_pct?.toFixed(2)}%
                  </span>
                </div>
                <div className="mt-2 flex justify-between text-xs text-gray-400">
                  <span>{pos.quantity}股</span>
                  <span>成本 ¥{pos.avg_cost?.toFixed(2)}</span>
                  <span>市值 ¥{pos.market_value?.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
