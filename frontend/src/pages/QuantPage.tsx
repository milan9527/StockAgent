import { useEffect, useState } from 'react'
import { BarChart3, Play, FileCode, Zap, Sparkles, Send, Eye, X } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import ReactMarkdown from 'react-markdown'
import StockSearch from '../components/StockSearch'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function QuantPage() {
  const [templates, setTemplates] = useState<any[]>([])
  const [strategies, setStrategies] = useState<any[]>([])
  const [backtestResult, setBacktestResult] = useState<any>(null)
  const [backtestForm, setBacktestForm] = useState({ strategy_id: '', stock_code: '600519', stock_name: '', initial_capital: '1000000', start_date: '', end_date: '' })
  const [running, setRunning] = useState(false)
  const [viewTemplate, setViewTemplate] = useState<any>(null)
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [aiLoading, setAiLoading] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const [tmplRes, stratRes] = await Promise.all([api.get('/api/strategy/quant/templates'), api.get('/api/strategy/quant')])
      setTemplates(tmplRes.data.templates || [])
      setStrategies(stratRes.data.strategies || [])
    } catch {}
  }

  const handleBacktest = async () => {
    if (!backtestForm.strategy_id) { toast.error('请选择策略'); return }
    setRunning(true); setBacktestResult(null)
    try {
      const res = await api.post('/api/strategy/quant/backtest', {
        strategy_id: backtestForm.strategy_id, stock_code: backtestForm.stock_code,
        initial_capital: parseFloat(backtestForm.initial_capital),
        start_date: backtestForm.start_date || undefined, end_date: backtestForm.end_date || undefined,
      })
      setBacktestResult(res.data); toast.success('回测完成')
    } catch (e: any) { toast.error(e.response?.data?.detail || '回测失败') }
    setRunning(false)
  }

  const handleAi = async () => {
    if (!aiPrompt || aiLoading) return
    setAiLoading(true); setAiResult('')
    try {
      const token = (() => { try { return JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token || '' } catch { return '' } })()
      const resp = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/strategy/agent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ prompt: aiPrompt, module: 'quant' }),
      })
      const reader = resp.body?.getReader(); const decoder = new TextDecoder(); let buf = '', result: any = null
      if (reader) { while (true) { const { done, value } = await reader.read(); if (done) break; buf += decoder.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''; for (const l of lines) { if (l.startsWith('data: ')) { try { const p = JSON.parse(l.slice(6)); if (p.type === 'result') result = p } catch {} } } } }
      if (result) setAiResult(result.response); else throw new Error('No response')
    } catch (e: any) { setAiResult(`Error: ${e.message}`) }
    setAiLoading(false)
  }

  // Default dates
  const today = new Date().toISOString().split('T')[0]
  const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().split('T')[0]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2"><BarChart3 className="w-6 h-6 text-accent-gold" /> 量化交易</h1>

      {/* 模板 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" /> 量化策略模板</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {templates.map((t: any) => (
            <div key={t.template_name} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50">
              <div className="flex items-start justify-between">
                <h3 className="text-white text-sm font-medium">{t.name}</h3>
                <span className="text-[10px] px-1.5 py-0.5 bg-primary-500/20 text-primary-300 rounded">{t.difficulty}</span>
              </div>
              <p className="text-gray-500 text-xs mt-1">{t.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] text-gray-600">{t.category}</span>
                <button onClick={() => setViewTemplate(viewTemplate?.template_name === t.template_name ? null : t)}
                  className="text-[10px] text-primary-400 hover:text-primary-300 flex items-center gap-1 ml-auto"><Eye className="w-3 h-3" /> 详情</button>
              </div>
              {viewTemplate?.template_name === t.template_name && (
                <div className="mt-2 pt-2 border-t border-surface-border/30">
                  <p className="text-[10px] text-gray-500 mb-1">默认参数:</p>
                  <pre className="text-[10px] text-gray-400 font-mono bg-surface-dark rounded p-2">{JSON.stringify(t.default_params, null, 2)}</pre>
                  {t.code_template && (
                    <>
                      <p className="text-[10px] text-gray-500 mt-2 mb-1">策略代码:</p>
                      <pre className="text-[10px] text-gray-400 font-mono bg-surface-dark rounded p-2 max-h-40 overflow-auto">{t.code_template}</pre>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 回测 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2"><Play className="w-4 h-4 text-green-400" /> 策略回测</h2>
        <div className="grid grid-cols-6 gap-3 items-end">
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">策略</label>
            <select className="input-field text-xs" value={backtestForm.strategy_id} onChange={e => setBacktestForm({ ...backtestForm, strategy_id: e.target.value })}>
              <option value="">选择策略</option>
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">股票</label>
            <StockSearch onSelect={s => setBacktestForm({ ...backtestForm, stock_code: s.code, stock_name: s.name })} placeholder="股票代码" />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">起始日期</label>
            <input type="date" className="input-field text-xs" value={backtestForm.start_date || oneYearAgo} onChange={e => setBacktestForm({ ...backtestForm, start_date: e.target.value })} />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">结束日期</label>
            <input type="date" className="input-field text-xs" value={backtestForm.end_date || today} onChange={e => setBacktestForm({ ...backtestForm, end_date: e.target.value })} />
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">初始资金</label>
            <input className="input-field text-xs" value={backtestForm.initial_capital} onChange={e => setBacktestForm({ ...backtestForm, initial_capital: e.target.value })} />
          </div>
          <button onClick={handleBacktest} disabled={running} className="btn-primary text-sm flex items-center gap-1 disabled:opacity-50">
            <Play className="w-3 h-3" /> {running ? '回测中...' : '运行'}
          </button>
        </div>
        {backtestForm.stock_name && <p className="text-xs text-gray-500 mt-1">已选: {backtestForm.stock_name}({backtestForm.stock_code})</p>}
      </div>

      {/* 回测结果 */}
      {backtestResult && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { l: '总收益', v: `${backtestResult.total_return?.toFixed(2)}%`, c: backtestResult.total_return >= 0 ? 'text-accent-red' : 'text-accent-green' },
              { l: '年化收益', v: `${backtestResult.annual_return?.toFixed(2)}%`, c: backtestResult.annual_return >= 0 ? 'text-accent-red' : 'text-accent-green' },
              { l: '最大回撤', v: `${backtestResult.max_drawdown?.toFixed(2)}%`, c: 'text-yellow-400' },
              { l: '夏普比率', v: backtestResult.sharpe_ratio?.toFixed(2), c: 'text-blue-400' },
              { l: '胜率', v: `${backtestResult.win_rate?.toFixed(1)}%`, c: 'text-purple-400' },
              { l: '总交易', v: backtestResult.total_trades, c: 'text-gray-300' },
              { l: '最终资产', v: `¥${backtestResult.final_value?.toLocaleString()}`, c: 'text-white' },
            ].map(({ l, v, c }) => (
              <div key={l} className="card text-center"><p className="text-[10px] text-gray-500">{l}</p><p className={`text-lg font-bold font-mono mt-1 ${c}`}>{v}</p></div>
            ))}
          </div>
          {backtestResult.equity_curve_sample?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">权益曲线</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={backtestResult.equity_curve_sample}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3f52" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
                  <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid #2d3f52', borderRadius: '8px', fontSize: '12px' }} />
                  <Line type="monotone" dataKey="equity" stroke="#d4a843" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {backtestResult.trade_log?.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">交易记录</h3>
              <table className="w-full text-xs">
                <thead><tr className="text-gray-500 border-b border-surface-border"><th className="text-left py-2">日期</th><th className="text-left py-2">操作</th><th className="text-right py-2">价格</th><th className="text-right py-2">数量</th><th className="text-right py-2">金额</th></tr></thead>
                <tbody>{backtestResult.trade_log.map((t: any, i: number) => (
                  <tr key={i} className="border-b border-surface-border/50">
                    <td className="py-2 text-gray-400 font-mono">{t.date}</td>
                    <td className="py-2"><span className={t.action === 'buy' ? 'badge-buy' : 'badge-sell'}>{t.action === 'buy' ? '买入' : '卖出'}</span></td>
                    <td className="py-2 text-right text-gray-300 font-mono">{t.price?.toFixed(2)}</td>
                    <td className="py-2 text-right text-gray-300 font-mono">{t.shares}</td>
                    <td className="py-2 text-right text-gray-300 font-mono">¥{t.amount?.toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 我的策略 */}
      {strategies.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2"><FileCode className="w-4 h-4 text-blue-400" /> 我的量化策略</h2>
          <div className="space-y-2">
            {strategies.map(s => (
              <div key={s.id} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50 flex items-center justify-between">
                <div>
                  <h3 className="text-white text-sm font-medium">{s.name}</h3>
                  <p className="text-gray-500 text-xs">{s.description}</p>
                  {s.performance_metrics && Object.keys(s.performance_metrics).length > 0 && (
                    <div className="flex gap-3 mt-1 text-[10px]">
                      <span className="text-gray-400">收益: <span className={s.performance_metrics.total_return >= 0 ? 'text-accent-red' : 'text-accent-green'}>{s.performance_metrics.total_return?.toFixed(1)}%</span></span>
                      <span className="text-gray-400">夏普: <span className="text-blue-400">{s.performance_metrics.sharpe_ratio?.toFixed(2)}</span></span>
                    </div>
                  )}
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.status === 'active' ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'}`}>{s.status === 'active' ? '运行中' : '草稿'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI量化助手 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2"><Sparkles className="w-4 h-4 text-accent-gold" /> AI量化助手</h2>
        <div className="flex gap-3">
          <input className="input-field flex-1" value={aiPrompt} onChange={e => setAiPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !aiLoading && handleAi()} placeholder="用自然语言创建量化模板, 如: 创建一个基于动量因子的多因子选股策略" />
          <button onClick={handleAi} disabled={aiLoading || !aiPrompt} className="btn-primary flex items-center gap-2 disabled:opacity-50"><Send className="w-4 h-4" /></button>
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          {['创建双均线交叉策略模板', '设计一个低回撤的量化策略', '用RSI+MACD组合策略回测贵州茅台'].map(s => (
            <button key={s} onClick={() => setAiPrompt(s)} className="text-[10px] px-2 py-1 bg-surface-hover rounded text-gray-500 hover:text-white">{s}</button>
          ))}
        </div>
        {aiResult && <div className="mt-3 report-container p-4 bg-surface-hover rounded-lg border border-surface-border/50"><ReactMarkdown>{aiResult}</ReactMarkdown></div>}
      </div>
    </div>
  )
}
