import { useEffect, useState } from 'react'
import { Target, Plus, Sparkles, Send, Eye, Edit3, Trash2, Play, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import StockSearch from '../components/StockSearch'
import api from '../services/api'
import toast from 'react-hot-toast'

const STRATEGY_TEMPLATES = [
  { name: '均线交叉策略', desc: 'MA5上穿MA20买入, 下穿卖出', type: 'technical', indicators: 'MA5,MA10,MA20', buy: 'MA5上穿MA20\nMACD金叉', sell: 'MA5下穿MA20\n止损-5%' },
  { name: 'RSI超卖反弹', desc: 'RSI<30买入, RSI>70卖出', type: 'technical', indicators: 'RSI,MACD', buy: 'RSI(14)<30\nMACD金叉确认', sell: 'RSI(14)>70\n止损-5%' },
  { name: '布林带突破', desc: '价格突破下轨买入, 突破上轨卖出', type: 'technical', indicators: 'BOLL,RSI', buy: '价格触及布林下轨\n成交量放大', sell: '价格触及布林上轨\n止损-5%' },
  { name: 'MACD趋势跟踪', desc: 'MACD金叉+均线多头买入', type: 'technical', indicators: 'MACD,MA,KDJ', buy: 'MACD金叉\nMA5>MA10>MA20', sell: 'MACD死叉\n止损-5%' },
]

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState('')
  const [form, setForm] = useState({ name: '', description: '', strategy_type: 'technical', indicators: '', buy_conditions: '', sell_conditions: '', risk_rules: '{"max_position_pct": 0.3, "stop_loss_pct": 0.05}' })
  const [viewStrategy, setViewStrategy] = useState<any>(null)
  // AI
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  // Apply to stock
  const [applyStrategy, setApplyStrategy] = useState<any>(null)
  const [applyStock, setApplyStock] = useState({ code: '', name: '' })
  const [applyResult, setApplyResult] = useState('')
  const [applyLoading, setApplyLoading] = useState(false)

  useEffect(() => { loadStrategies() }, [])
  const loadStrategies = async () => { try { const r = await api.get('/api/strategy/trading'); setStrategies(r.data) } catch {} }

  const handleSelectTemplate = (tpl: any) => {
    setForm({ name: tpl.name, description: tpl.desc, strategy_type: tpl.type, indicators: tpl.indicators, buy_conditions: tpl.buy, sell_conditions: tpl.sell, risk_rules: '{"max_position_pct": 0.3, "stop_loss_pct": 0.05}' })
    setShowForm(true); setEditId('')
  }

  const handleEdit = (s: any) => {
    setForm({ name: s.name, description: s.description, strategy_type: s.strategy_type, indicators: (s.indicators || []).join(','), buy_conditions: (s.buy_conditions || []).join('\n'), sell_conditions: (s.sell_conditions || []).join('\n'), risk_rules: JSON.stringify(s.risk_rules || {}) })
    setEditId(s.id); setShowForm(true)
  }

  const handleSave = async () => {
    const data = { name: form.name, description: form.description, strategy_type: form.strategy_type, parameters: {}, indicators: form.indicators.split(',').map(s => s.trim()).filter(Boolean), buy_conditions: form.buy_conditions.split('\n').filter(Boolean), sell_conditions: form.sell_conditions.split('\n').filter(Boolean), risk_rules: JSON.parse(form.risk_rules || '{}') }
    try {
      if (editId) { await api.put(`/api/strategy/trading/${editId}`, data); toast.success('策略已更新') }
      else { await api.post('/api/strategy/trading', data); toast.success('策略已创建') }
      setShowForm(false); setEditId('')
      setForm({ name: '', description: '', strategy_type: 'technical', indicators: '', buy_conditions: '', sell_conditions: '', risk_rules: '{"max_position_pct": 0.3, "stop_loss_pct": 0.05}' })
      await loadStrategies()
    } catch (e: any) { toast.error(e.response?.data?.detail || '保存失败') }
  }

  const handleDelete = async (id: string) => {
    try { await api.delete(`/api/strategy/trading/${id}`); toast.success('已删除'); loadStrategies() } catch {}
  }

  const handleAi = async () => {
    if (!aiPrompt || aiLoading) return
    setAiLoading(true); setAiResult('')
    try {
      const token = (() => { try { return JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token || '' } catch { return '' } })()
      const resp = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/strategy/agent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ prompt: aiPrompt, module: 'trading' }),
      })
      if (!resp.ok) throw new Error(`Request failed: ${resp.status}`)
      const reader = resp.body?.getReader(); const decoder = new TextDecoder(); let buf = '', result: any = null, streamText = ''
      if (reader) {
        while (true) {
          const { done, value } = await reader.read(); if (done) break
          buf += decoder.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''
          for (const l of lines) {
            if (l.startsWith('data: ')) {
              try {
                const p = JSON.parse(l.slice(6))
                if (p.type === 'result') result = p
                else if (p.type === 'text') { streamText += p.content; setAiResult(streamText) }
                else if (p.type === 'status') { setAiResult(streamText ? streamText + `\n\n_${p.content}_` : `_${p.content}_`) }
              } catch {}
            }
          }
        }
      }
      if (result?.response) setAiResult(result.response)
      else if (!streamText) throw new Error('No response received')
    } catch (e: any) { if (!aiResult) setAiResult(`Error: ${e.message}`) }
    setAiLoading(false)
    // Auto-reload strategies in case AI created one
    loadStrategies()
  }

  const handleApply = async () => {
    if (!applyStrategy || !applyStock.code) return
    setApplyLoading(true); setApplyResult('')
    try {
      const token = (() => { try { return JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token || '' } catch { return '' } })()
      const prompt = `应用交易策略"${applyStrategy.name}"到股票${applyStock.name}(${applyStock.code})。策略条件: 买入[${(applyStrategy.buy_conditions||[]).join(',')}] 卖出[${(applyStrategy.sell_conditions||[]).join(',')}]。请分析当前是否满足买卖条件, 给出具体建议。`
      const resp = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/strategy/agent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ prompt, module: 'trading' }),
      })
      if (!resp.ok) throw new Error(`Request failed: ${resp.status}`)
      const reader = resp.body?.getReader(); const decoder = new TextDecoder(); let buf = '', result: any = null, streamText = ''
      if (reader) {
        while (true) {
          const { done, value } = await reader.read(); if (done) break
          buf += decoder.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''
          for (const l of lines) {
            if (l.startsWith('data: ')) {
              try {
                const p = JSON.parse(l.slice(6))
                if (p.type === 'result') result = p
                else if (p.type === 'text') { streamText += p.content; setApplyResult(streamText) }
                else if (p.type === 'status') { setApplyResult(streamText ? streamText + `\n\n_${p.content}_` : `_${p.content}_`) }
              } catch {}
            }
          }
        }
      }
      if (result?.response) setApplyResult(result.response)
    } catch (e: any) { setApplyResult(`Error: ${e.message}`) }
    setApplyLoading(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Target className="w-6 h-6 text-accent-gold" /> 交易策略</h1>
        <button onClick={() => { setShowForm(true); setEditId(''); setForm({ name: '', description: '', strategy_type: 'technical', indicators: '', buy_conditions: '', sell_conditions: '', risk_rules: '{"max_position_pct": 0.3, "stop_loss_pct": 0.05}' }) }} className="btn-primary flex items-center gap-2"><Plus className="w-4 h-4" /> 新建策略</button>
      </div>

      {/* 策略模板 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">策略模板 (点击使用)</h2>
        <div className="grid grid-cols-4 gap-3">
          {STRATEGY_TEMPLATES.map(tpl => (
            <button key={tpl.name} onClick={() => handleSelectTemplate(tpl)} className="text-left p-3 rounded-lg bg-surface-hover border border-surface-border hover:border-primary-500/30">
              <p className="text-xs text-white font-medium">{tpl.name}</p>
              <p className="text-[10px] text-gray-500 mt-1">{tpl.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* 创建/编辑表单 */}
      {showForm && (
        <div className="card space-y-3">
          <h2 className="text-sm font-semibold text-white">{editId ? '编辑策略' : '新建策略'}</h2>
          <div className="grid grid-cols-3 gap-3">
            <input className="input-field" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="策略名称" />
            <select className="input-field" value={form.strategy_type} onChange={e => setForm({ ...form, strategy_type: e.target.value })}>
              <option value="technical">技术面</option><option value="fundamental">基本面</option><option value="mixed">综合</option>
            </select>
            <input className="input-field" value={form.indicators} onChange={e => setForm({ ...form, indicators: e.target.value })} placeholder="指标: MA,MACD,RSI" />
          </div>
          <textarea className="input-field h-16" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="策略描述" />
          <div className="grid grid-cols-2 gap-3">
            <textarea className="input-field h-20 text-xs" value={form.buy_conditions} onChange={e => setForm({ ...form, buy_conditions: e.target.value })} placeholder="买入条件 (每行一条)" />
            <textarea className="input-field h-20 text-xs" value={form.sell_conditions} onChange={e => setForm({ ...form, sell_conditions: e.target.value })} placeholder="卖出条件 (每行一条)" />
          </div>
          <div className="flex gap-3">
            <button onClick={handleSave} className="btn-primary text-sm">{editId ? '保存修改' : '创建策略'}</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">取消</button>
          </div>
        </div>
      )}

      {/* 策略列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {strategies.map((s: any) => (
          <div key={s.id} className="card">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-white font-semibold text-sm">{s.name}</h3>
                <p className="text-gray-500 text-xs">{s.description}</p>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.status === 'active' ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'}`}>{s.status === 'active' ? '已启用' : '未启用'}</span>
            </div>
            <div className="flex gap-1 flex-wrap mb-2">
              {(s.indicators || []).map((ind: string) => <span key={ind} className="text-[9px] px-1.5 py-0.5 bg-surface-hover rounded text-accent-gold">{ind}</span>)}
            </div>
            <div className="flex gap-2 pt-2 border-t border-surface-border/30">
              <button onClick={() => setViewStrategy(viewStrategy?.id === s.id ? null : s)} className="text-[10px] text-primary-400 hover:text-primary-300 flex items-center gap-1"><Eye className="w-3 h-3" /> 查看</button>
              <button onClick={() => handleEdit(s)} className="text-[10px] text-accent-gold hover:text-yellow-300 flex items-center gap-1"><Edit3 className="w-3 h-3" /> 编辑</button>
              <button onClick={() => { setApplyStrategy(s); setApplyStock({ code: '', name: '' }); setApplyResult('') }} className="text-[10px] text-green-400 hover:text-green-300 flex items-center gap-1"><Play className="w-3 h-3" /> 应用</button>
              <button onClick={() => handleDelete(s.id)} className="text-[10px] text-gray-500 hover:text-red-400 flex items-center gap-1 ml-auto"><Trash2 className="w-3 h-3" /> 删除</button>
            </div>
            {viewStrategy?.id === s.id && (
              <div className="mt-2 pt-2 border-t border-surface-border/30 text-xs space-y-1">
                <p className="text-gray-500">买入: <span className="text-accent-red">{(s.buy_conditions || []).join(' | ')}</span></p>
                <p className="text-gray-500">卖出: <span className="text-accent-green">{(s.sell_conditions || []).join(' | ')}</span></p>
                <p className="text-gray-500">风控: <span className="text-gray-400 font-mono">{JSON.stringify(s.risk_rules)}</span></p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 应用策略到股票 */}
      {applyStrategy && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">应用策略: {applyStrategy.name}</h2>
            <button onClick={() => setApplyStrategy(null)} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
          </div>
          <p className="text-xs text-gray-500">
            买入: <span className="text-accent-red">{(applyStrategy.buy_conditions||[]).join(' | ')}</span>
            <br/>卖出: <span className="text-accent-green">{(applyStrategy.sell_conditions||[]).join(' | ')}</span>
          </p>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">选择股票</label>
              <StockSearch onSelect={(s) => setApplyStock({ code: s.code, name: s.name })} placeholder="输入股票代码或名称..." />
            </div>
            {applyStock.code && <span className="text-xs text-gray-400 pb-2">{applyStock.name}({applyStock.code})</span>}
            <button onClick={handleApply} disabled={!applyStock.code || applyLoading} className="btn-primary text-sm disabled:opacity-50">
              {applyLoading ? '分析中...' : '分析买卖点'}
            </button>
            <button onClick={async () => {
              setApplyLoading(true); setApplyResult('')
              try {
                const token = (() => { try { return JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token || '' } catch { return '' } })()
                const prompt = `应用交易策略"${applyStrategy.name}"到我的自选股池中所有股票。策略条件: 买入[${(applyStrategy.buy_conditions||[]).join(',')}] 卖出[${(applyStrategy.sell_conditions||[]).join(',')}]。请逐一分析每只自选股当前是否满足买卖条件, 用表格列出每只股票的信号(买入/卖出/持有)和理由。`
                const resp = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/strategy/agent`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                  body: JSON.stringify({ prompt, module: 'trading' }),
                })
                if (!resp.ok) throw new Error(`Request failed: ${resp.status}`)
                const reader = resp.body?.getReader(); const decoder = new TextDecoder(); let buf = '', result: any = null, streamText = ''
                setApplyResult('⏳ 正在分析自选股...')
                if (reader) { while (true) { const { done, value } = await reader.read(); if (done) break; buf += decoder.decode(value, { stream: true }); const lines = buf.split('\n'); buf = lines.pop() || ''; for (const l of lines) { if (l.startsWith('data: ')) { try { const p = JSON.parse(l.slice(6)); if (p.type === 'result') result = p; else if (p.type === 'text') { streamText += p.content; setApplyResult(streamText) } else if (p.type === 'status') { setApplyResult(streamText ? streamText + `\n\n_${p.content}_` : `_${p.content}_`) } } catch {} } } } }
                if (result) setApplyResult(result.response)
              } catch (e: any) { setApplyResult(`Error: ${e.message}`) }
              setApplyLoading(false)
            }} disabled={applyLoading} className="btn-secondary text-sm disabled:opacity-50 whitespace-nowrap">
              {applyLoading ? '分析中...' : '应用到自选股'}
            </button>
          </div>
          {applyResult && <div className="report-container p-4 bg-surface-hover rounded-lg"><ReactMarkdown>{applyResult}</ReactMarkdown></div>}
        </div>
      )}

      {/* AI策略助手 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2"><Sparkles className="w-4 h-4 text-accent-gold" /> AI策略助手</h2>
        <div className="flex gap-3">
          <input className="input-field flex-1" value={aiPrompt} onChange={e => setAiPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !aiLoading && handleAi()} placeholder="用自然语言创建/修改策略, 或搜索满足条件的股票" />
          <button onClick={handleAi} disabled={aiLoading || !aiPrompt} className="btn-primary flex items-center gap-2 disabled:opacity-50"><Send className="w-4 h-4" /></button>
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          {['创建基于MACD和KDJ金叉的中线策略', '用我的策略分析自选股的买卖信号', '搜索A股中满足均线多头排列的股票', '模拟买入贵州茅台1000股'].map(s => (
            <button key={s} onClick={() => setAiPrompt(s)} className="text-[10px] px-2 py-1 bg-surface-hover rounded text-gray-500 hover:text-white">{s}</button>
          ))}
        </div>
        {aiResult && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-gray-500">AI策略助手结果</span>
              <div className="flex gap-2">
                <button onClick={() => {
                  // Pre-fill the strategy form with AI suggestion
                  setForm({ ...form, name: aiPrompt.slice(0, 30), description: aiPrompt })
                  setShowForm(true); setEditId('')
                  toast.success('请在上方表单中完善策略详情并保存')
                }} className="text-[10px] px-2 py-1 bg-accent-gold/20 text-accent-gold rounded hover:bg-accent-gold/30">
                  保存为策略
                </button>
                <button onClick={async () => {
                  try {
                    await api.post('/api/documents/', {
                      title: `AI策略: ${aiPrompt.slice(0, 40)}`,
                      category: 'strategy', content: aiResult,
                      tags: ['strategy', 'ai'], source: 'agent', add_to_kb: true,
                    })
                    toast.success('已保存到文档知识库')
                  } catch { toast.error('保存失败') }
                }} className="text-[10px] px-2 py-1 bg-primary-500/20 text-primary-300 rounded hover:bg-primary-500/30">
                  保存到知识库
                </button>
              </div>
            </div>
            <div className="report-container p-4 bg-surface-hover rounded-lg border border-surface-border/50"><ReactMarkdown>{aiResult}</ReactMarkdown></div>
          </div>
        )}
      </div>
    </div>
  )
}
