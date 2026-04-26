import { useEffect, useState } from 'react'
import { BarChart3, Play, FileCode, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function QuantPage() {
  const [templates, setTemplates] = useState<any[]>([])
  const [strategies, setStrategies] = useState<any[]>([])
  const [backtestResult, setBacktestResult] = useState<any>(null)
  const [backtestForm, setBacktestForm] = useState({ strategy_id: '', stock_code: '600519', initial_capital: '1000000' })
  const [running, setRunning] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [tmplRes, stratRes] = await Promise.all([
        api.get('/api/strategy/quant/templates'),
        api.get('/api/strategy/quant'),
      ])
      setTemplates(tmplRes.data.templates || [])
      setStrategies(stratRes.data.strategies || [])
    } catch {}
  }

  const handleBacktest = async () => {
    if (!backtestForm.strategy_id) {
      toast.error('请选择量化策略')
      return
    }
    setRunning(true)
    setBacktestResult(null)
    try {
      const res = await api.post('/api/strategy/quant/backtest', {
        strategy_id: backtestForm.strategy_id,
        stock_code: backtestForm.stock_code,
        initial_capital: parseFloat(backtestForm.initial_capital),
      })
      setBacktestResult(res.data)
      toast.success('回测完成')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '回测失败')
    }
    setRunning(false)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-6 h-6 text-accent-gold" />
        量化交易
      </h1>

      {/* 预置模板 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          预置量化模板
          <span className="text-xs text-gray-500 font-normal">参考幻方量化</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {templates.map((tmpl: any) => (
            <div key={tmpl.template_name} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50">
              <div className="flex items-start justify-between">
                <h3 className="text-white text-sm font-medium">{tmpl.name}</h3>
                <span className="text-[10px] px-1.5 py-0.5 bg-primary-500/20 text-primary-300 rounded">{tmpl.difficulty}</span>
              </div>
              <p className="text-gray-500 text-xs mt-1">{tmpl.description}</p>
              <p className="text-gray-600 text-[10px] mt-2">分类: {tmpl.category}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 回测面板 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Play className="w-5 h-5 text-green-400" />
          策略回测
        </h2>
        <div className="grid grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">选择策略</label>
            <select
              className="input-field"
              value={backtestForm.strategy_id}
              onChange={(e) => setBacktestForm({ ...backtestForm, strategy_id: e.target.value })}
            >
              <option value="">选择量化策略</option>
              {strategies.map((s: any) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">股票代码</label>
            <input
              className="input-field"
              value={backtestForm.stock_code}
              onChange={(e) => setBacktestForm({ ...backtestForm, stock_code: e.target.value })}
              placeholder="600519"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">初始资金</label>
            <input
              className="input-field"
              value={backtestForm.initial_capital}
              onChange={(e) => setBacktestForm({ ...backtestForm, initial_capital: e.target.value })}
            />
          </div>
          <button onClick={handleBacktest} disabled={running} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            <Play className="w-4 h-4" />
            {running ? '回测中...' : '运行回测'}
          </button>
        </div>
      </div>

      {/* 回测结果 */}
      {backtestResult && (
        <div className="space-y-4">
          {/* 绩效指标 */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { label: '总收益', value: `${backtestResult.total_return?.toFixed(2)}%`, color: backtestResult.total_return >= 0 ? 'text-accent-red' : 'text-accent-green' },
              { label: '年化收益', value: `${backtestResult.annual_return?.toFixed(2)}%`, color: backtestResult.annual_return >= 0 ? 'text-accent-red' : 'text-accent-green' },
              { label: '最大回撤', value: `${backtestResult.max_drawdown?.toFixed(2)}%`, color: 'text-yellow-400' },
              { label: '夏普比率', value: backtestResult.sharpe_ratio?.toFixed(2), color: 'text-blue-400' },
              { label: '胜率', value: `${backtestResult.win_rate?.toFixed(1)}%`, color: 'text-purple-400' },
              { label: '总交易', value: backtestResult.total_trades, color: 'text-gray-300' },
              { label: '最终资产', value: `¥${backtestResult.final_value?.toLocaleString()}`, color: 'text-white' },
            ].map(({ label, value, color }) => (
              <div key={label} className="card text-center">
                <p className="text-[10px] text-gray-500">{label}</p>
                <p className={`text-lg font-bold font-mono mt-1 ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* 权益曲线 */}
          {backtestResult.equity_curve_sample?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">权益曲线</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={backtestResult.equity_curve_sample}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3f52" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
                  <Tooltip
                    contentStyle={{ background: '#1a2332', border: '1px solid #2d3f52', borderRadius: '8px', fontSize: '12px' }}
                    labelStyle={{ color: '#9ca3af' }}
                  />
                  <Line type="monotone" dataKey="equity" stroke="#d4a843" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* 交易记录 */}
          {backtestResult.trade_log?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">最近交易记录</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-surface-border">
                      <th className="text-left py-2">日期</th>
                      <th className="text-left py-2">操作</th>
                      <th className="text-right py-2">价格</th>
                      <th className="text-right py-2">数量</th>
                      <th className="text-right py-2">金额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {backtestResult.trade_log.map((t: any, i: number) => (
                      <tr key={i} className="border-b border-surface-border/50">
                        <td className="py-2 text-gray-400 font-mono">{t.date}</td>
                        <td className="py-2">
                          <span className={t.action === 'buy' ? 'badge-buy' : 'badge-sell'}>
                            {t.action === 'buy' ? '买入' : '卖出'}
                          </span>
                        </td>
                        <td className="py-2 text-right text-gray-300 font-mono">{t.price?.toFixed(2)}</td>
                        <td className="py-2 text-right text-gray-300 font-mono">{t.shares}</td>
                        <td className="py-2 text-right text-gray-300 font-mono">¥{t.amount?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 用户策略列表 */}
      {strategies.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FileCode className="w-5 h-5 text-blue-400" />
            我的量化策略
          </h2>
          <div className="space-y-3">
            {strategies.map((s: any) => (
              <div key={s.id} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50 flex items-center justify-between">
                <div>
                  <h3 className="text-white text-sm font-medium">{s.name}</h3>
                  <p className="text-gray-500 text-xs">{s.description}</p>
                  {s.performance_metrics && Object.keys(s.performance_metrics).length > 0 && (
                    <div className="flex gap-3 mt-1 text-[10px]">
                      <span className="text-gray-400">收益: <span className={s.performance_metrics.total_return >= 0 ? 'text-accent-red' : 'text-accent-green'}>{s.performance_metrics.total_return?.toFixed(1)}%</span></span>
                      <span className="text-gray-400">回撤: <span className="text-yellow-400">{s.performance_metrics.max_drawdown?.toFixed(1)}%</span></span>
                      <span className="text-gray-400">夏普: <span className="text-blue-400">{s.performance_metrics.sharpe_ratio?.toFixed(2)}</span></span>
                    </div>
                  )}
                </div>
                <span className={`badge ${s.status === 'active' ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'}`}>
                  {s.status === 'active' ? '运行中' : '草稿'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
