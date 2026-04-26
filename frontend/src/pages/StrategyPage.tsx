import { useEffect, useState } from 'react'
import { Target, Plus, Edit, Play } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '', description: '', strategy_type: 'technical',
    parameters: '{}', indicators: '', buy_conditions: '', sell_conditions: '',
    risk_rules: '{"max_position_pct": 0.3, "stop_loss_pct": 0.05}',
  })

  useEffect(() => { loadStrategies() }, [])

  const loadStrategies = async () => {
    try {
      const res = await api.get('/api/strategy/trading')
      setStrategies(res.data)
    } catch {}
  }

  const handleCreate = async () => {
    try {
      await api.post('/api/strategy/trading', {
        name: form.name,
        description: form.description,
        strategy_type: form.strategy_type,
        parameters: JSON.parse(form.parameters || '{}'),
        indicators: form.indicators.split(',').map(s => s.trim()).filter(Boolean),
        buy_conditions: form.buy_conditions.split('\n').filter(Boolean),
        sell_conditions: form.sell_conditions.split('\n').filter(Boolean),
        risk_rules: JSON.parse(form.risk_rules || '{}'),
      })
      toast.success('策略创建成功')
      setShowForm(false)
      loadStrategies()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Target className="w-6 h-6 text-accent-gold" />
          交易策略
        </h1>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          新建策略
        </button>
      </div>

      {/* 创建表单 */}
      {showForm && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold text-white">创建交易策略</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">策略名称</label>
              <input className="input-field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：均线+MACD综合策略" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">策略类型</label>
              <select className="input-field" value={form.strategy_type} onChange={(e) => setForm({ ...form, strategy_type: e.target.value })}>
                <option value="technical">技术面</option>
                <option value="fundamental">基本面</option>
                <option value="mixed">综合</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">策略描述</label>
            <textarea className="input-field h-20" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="描述策略逻辑..." />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">技术指标(逗号分隔)</label>
            <input className="input-field" value={form.indicators} onChange={(e) => setForm({ ...form, indicators: e.target.value })} placeholder="MA, MACD, RSI, BOLL" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">买入条件(每行一条)</label>
              <textarea className="input-field h-24" value={form.buy_conditions} onChange={(e) => setForm({ ...form, buy_conditions: e.target.value })} placeholder="短期均线上穿长期均线&#10;MACD金叉" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">卖出条件(每行一条)</label>
              <textarea className="input-field h-24" value={form.sell_conditions} onChange={(e) => setForm({ ...form, sell_conditions: e.target.value })} placeholder="短期均线下穿长期均线&#10;止损线触发(-5%)" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">风控规则(JSON)</label>
            <input className="input-field font-mono text-xs" value={form.risk_rules} onChange={(e) => setForm({ ...form, risk_rules: e.target.value })} />
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate} className="btn-primary">创建策略</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">取消</button>
          </div>
        </div>
      )}

      {/* 策略列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {strategies.map((s: any) => (
          <div key={s.id} className="card">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-white font-semibold">{s.name}</h3>
                <p className="text-gray-500 text-xs mt-1">{s.description}</p>
              </div>
              <span className={`badge ${s.status === 'active' ? 'bg-green-900/30 text-green-400 border-green-800/50' : 'bg-gray-800 text-gray-400 border-gray-700'}`}>
                {s.status === 'active' ? '运行中' : s.status === 'draft' ? '草稿' : s.status}
              </span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex gap-2 flex-wrap">
                {(s.indicators || []).map((ind: string) => (
                  <span key={ind} className="px-2 py-0.5 bg-surface-hover rounded text-gray-400 border border-surface-border">{ind}</span>
                ))}
              </div>
              {s.buy_conditions?.length > 0 && (
                <div>
                  <span className="text-accent-red">买入:</span>
                  <span className="text-gray-400 ml-1">{s.buy_conditions.join(' | ')}</span>
                </div>
              )}
              {s.sell_conditions?.length > 0 && (
                <div>
                  <span className="text-accent-green">卖出:</span>
                  <span className="text-gray-400 ml-1">{s.sell_conditions.join(' | ')}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {strategies.length === 0 && !showForm && (
        <div className="text-center py-12 text-gray-500">
          <Target className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>暂无交易策略，点击"新建策略"开始创建</p>
        </div>
      )}
    </div>
  )
}
