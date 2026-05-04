import { useEffect, useState } from 'react'
import { Settings, Cpu, Database, Check, Sliders } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const TOKEN_PRESETS = [
  { label: '4K', value: 4096 },
  { label: '8K', value: 8192 },
  { label: '16K', value: 16384 },
  { label: '32K', value: 32768 },
  { label: '64K', value: 65536 },
]

export default function SettingsPage() {
  const [models, setModels] = useState<any[]>([])
  const [activeModel, setActiveModel] = useState('')
  const [maxTokens, setMaxTokens] = useState(16384)
  const [sources, setSources] = useState<any[]>([])
  const [switching, setSwitching] = useState(false)
  const [notifyEmail, setNotifyEmail] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [sesStatus, setSesStatus] = useState<{ verified: boolean; status: string }>({ verified: false, status: '' })

  useEffect(() => { loadSettings() }, [])

  const loadSesStatus = async () => {
    try { const r = await api.get('/api/settings/ses-status'); setSesStatus(r.data) } catch {}
  }

  const loadSettings = async () => {
    try {
      const [modelsRes, sourcesRes, userRes] = await Promise.all([
        api.get('/api/settings/models'),
        api.get('/api/settings/data-sources'),
        api.get('/api/auth/me'),
      ])
      setModels(modelsRes.data.models || [])
      setActiveModel(modelsRes.data.active || '')
      setMaxTokens(modelsRes.data.max_tokens || 16384)
      setSources(sourcesRes.data.sources || [])
      setUserEmail(userRes.data.email || '')
      setNotifyEmail(userRes.data.notification_email_address || userRes.data.email || '')
      loadSesStatus()
    } catch {}
  }

  const handleSwitchModel = async (key: string) => {
    setSwitching(true)
    try {
      await api.post('/api/settings/models/switch', { model_key: key })
      setActiveModel(key)
      toast.success(`已切换到 ${models.find(m => m.key === key)?.name || key}`)
      loadSettings()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '切换失败')
    }
    setSwitching(false)
  }

  const handleUpdateMaxTokens = async (value: number) => {
    setMaxTokens(value)
    try {
      await api.post('/api/settings/models/max-tokens', { max_tokens: value })
      toast.success(`Max Tokens 已更新为 ${value.toLocaleString()}`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '更新失败')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <Settings className="w-6 h-6 text-accent-gold" />
        系统设置
      </h1>

      {/* Max Tokens 配置 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Sliders className="w-5 h-5 text-yellow-400" />
          Max Tokens
        </h2>
        <p className="text-xs text-gray-500 mb-4">
          控制LLM单次响应的最大token数。更大的值允许更详细的分析报告，但会增加延迟和成本。
          分析任务建议 16K+，简单对话 4K-8K 即可。
        </p>
        <div className="space-y-3">
          {/* 快捷预设 */}
          <div className="flex gap-2">
            {TOKEN_PRESETS.map(p => (
              <button
                key={p.value}
                onClick={() => handleUpdateMaxTokens(p.value)}
                className={`px-4 py-2 rounded-lg text-sm font-mono transition-all ${
                  maxTokens === p.value
                    ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/50'
                    : 'bg-surface-hover text-gray-400 border border-surface-border hover:border-accent-gold/30'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {/* 滑块 */}
          <div className="flex items-center gap-4">
            <input
              type="range"
              min={1024}
              max={65536}
              step={1024}
              value={maxTokens}
              onChange={e => setMaxTokens(parseInt(e.target.value))}
              onMouseUp={() => handleUpdateMaxTokens(maxTokens)}
              onTouchEnd={() => handleUpdateMaxTokens(maxTokens)}
              className="flex-1 h-2 bg-surface-hover rounded-lg appearance-none cursor-pointer accent-accent-gold"
            />
            <span className="text-sm font-mono text-accent-gold w-20 text-right">{maxTokens.toLocaleString()}</span>
          </div>
          <p className="text-[10px] text-gray-600">范围: 1,024 - 65,536 tokens</p>
        </div>
      </div>

      {/* LLM模型切换 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-blue-400" />
          LLM 模型
        </h2>
        <p className="text-xs text-gray-500 mb-4">选择Agent使用的大语言模型，默认使用 Bedrock Claude Sonnet 4.6</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {models.map((m: any) => (
            <button
              key={m.key}
              onClick={() => handleSwitchModel(m.key)}
              disabled={switching || m.key === activeModel}
              className={`text-left p-4 rounded-lg border transition-all ${
                m.key === activeModel
                  ? 'bg-primary-500/20 border-primary-500/50'
                  : 'bg-surface-hover border-surface-border hover:border-primary-500/30'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{m.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{m.provider}</p>
                </div>
                {m.key === activeModel && (
                  <div className="p-1 bg-primary-500 rounded-full">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </div>
              <p className="text-[10px] text-gray-600 mt-2">{m.description}</p>
              <div className="flex gap-2 mt-1.5">
                {m.context_window && <span className="text-[9px] px-1.5 py-0.5 bg-surface-dark rounded text-gray-500">CTX {m.context_window}</span>}
                {m.max_output && <span className="text-[9px] px-1.5 py-0.5 bg-surface-dark rounded text-gray-500">OUT {m.max_output}</span>}
              </div>
              <p className="text-[9px] text-gray-700 font-mono mt-1">{m.id}</p>
            </button>
          ))}
        </div>
      </div>

      {/* 通知邮箱设置 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent-gold" />
          通知邮箱 (SES)
        </h2>
        <p className="text-xs text-gray-500 mb-3">定期任务执行结果将以HTML格式邮件发送到此邮箱。首次使用需要验证邮箱。</p>

        {/* SES verification status */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg mb-4 text-xs ${
          sesStatus.verified
            ? 'bg-green-900/20 border border-green-800/30 text-green-400'
            : sesStatus.status === 'Pending'
            ? 'bg-yellow-900/20 border border-yellow-800/30 text-yellow-400'
            : 'bg-gray-800/50 border border-surface-border text-gray-500'
        }`}>
          <span className={`w-2 h-2 rounded-full ${sesStatus.verified ? 'bg-green-400' : sesStatus.status === 'Pending' ? 'bg-yellow-400 animate-pulse' : 'bg-gray-600'}`} />
          {sesStatus.verified
            ? `✅ ${notifyEmail} 已验证，可以接收HTML邮件`
            : sesStatus.status === 'Pending'
            ? `⏳ ${notifyEmail} 验证待确认，请查收邮件并点击确认链接`
            : '未验证 — 请输入邮箱并点击"验证邮箱"'}
        </div>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-400 mb-1 block">通知邮箱地址</label>
            <input className="input-field" value={notifyEmail} onChange={e => setNotifyEmail(e.target.value)} placeholder="your@email.com" />
          </div>
          <button onClick={async () => {
            try {
              await api.put('/api/auth/profile', { notification_email_address: notifyEmail })
              setUserEmail(notifyEmail)
              toast.success('通知邮箱已更新')
              loadSesStatus()
            } catch (err: any) { toast.error(err.response?.data?.detail || err.response?.data?.error || '更新失败') }
          }} className="btn-primary text-sm">保存</button>
          <button onClick={async () => {
            if (!notifyEmail) { toast.error('请先输入邮箱'); return }
            try {
              toast.loading('处理中...')
              const res = await api.post('/api/settings/test-email', { to_email: notifyEmail })
              toast.dismiss()
              if (res.data.status === 'sent') {
                toast.success(res.data.message)
              } else if (res.data.status === 'verification_sent') {
                toast.success(res.data.message, { duration: 10000 })
                setSesStatus({ verified: false, status: 'Pending' })
              } else if (res.data.status === 'pending') {
                toast.success(res.data.message, { duration: 8000 })
              } else {
                toast.error(res.data.message || '操作失败')
              }
              loadSesStatus()
            } catch (err: any) { toast.dismiss(); toast.error(err.response?.data?.detail || '操作失败') }
          }} className={`text-sm ${sesStatus.verified ? 'btn-secondary' : 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30 px-3 py-1.5 rounded-lg hover:bg-accent-gold/30'}`}>
            {sesStatus.verified ? '发送测试邮件' : '验证邮箱'}
          </button>
        </div>

        <div className="mt-3 text-[10px] text-gray-600 space-y-1">
          <p>使用流程: ① 输入邮箱 → ② 点击"验证邮箱" → ③ 查收AWS验证邮件并点击确认 → ④ 发送测试邮件</p>
          <p>当前配置: AWS SES (us-east-1) · {sesStatus.verified ? 'HTML邮件已就绪' : '待验证'}</p>
        </div>
      </div>

      {/* 行情数据源 */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-green-400" />
          行情数据源
        </h2>
        <p className="text-xs text-gray-500 mb-4">可用的行情数据接口，在行情页面和分析页面可选择使用</p>
        <div className="space-y-2">
          {sources.map((s: any) => (
            <div key={s.id} className="flex items-center justify-between bg-surface-hover rounded-lg p-3 border border-surface-border/50">
              <div>
                <p className="text-sm text-white font-medium">{s.name}</p>
                <p className="text-xs text-gray-500">{s.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-600 font-mono">{s.type}</span>
                <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-green-500' : 'bg-gray-600'}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
