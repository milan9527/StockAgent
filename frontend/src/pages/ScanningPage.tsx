import { useState, useEffect } from 'react'
import { Shield, Play, AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const SCORE_COLORS: Record<string, string> = {
  high: 'text-green-400 bg-green-900/30 border-green-800/50',
  medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-800/50',
  low: 'text-red-400 bg-red-900/30 border-red-800/50',
}

const SEVERITY_ICONS: Record<string, any> = {
  critical: { icon: XCircle, color: 'text-red-500' },
  high: { icon: AlertTriangle, color: 'text-red-400' },
  medium: { icon: AlertTriangle, color: 'text-yellow-400' },
  low: { icon: Info, color: 'text-blue-400' },
  info: { icon: Info, color: 'text-gray-400' },
}

export default function ScanningPage() {
  const [builtinSkills, setBuiltinSkills] = useState<any[]>([])
  const [customSkills, setCustomSkills] = useState<any[]>([])
  const [dimensions, setDimensions] = useState<any[]>([])
  const [selectedSkill, setSelectedSkill] = useState<any>(null)
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>(['security', 'compliance', 'compatibility', 'license'])
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<any>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [skillsRes, dimsRes] = await Promise.all([
        api.get('/api/skills/all'),
        api.get('/api/scanning/dimensions'),
      ])
      setBuiltinSkills(skillsRes.data.builtin || [])
      setCustomSkills(skillsRes.data.custom || [])
      setDimensions(dimsRes.data.dimensions || [])
    } catch {}
  }

  const handleScan = async () => {
    if (!selectedSkill) { toast.error('请选择要扫描的Skill'); return }
    setScanning(true)
    setScanResult(null)

    try {
      let res
      if (selectedSkill.source === 'builtin') {
        // Scan builtin skill by name
        const skillName = selectedSkill.name.replace('技能', '-skill')
          .replace('行情数据', 'market-data').replace('投资分析', 'analysis')
          .replace('Web信息获取', 'web-fetch').replace('交易', 'trading')
          .replace('量化交易', 'quant').replace('通知', 'notification')
          .replace('专业财经爬虫', 'crawler').replace('浏览器爬虫', 'browser-crawler')
          .replace('代码执行', 'code-interpreter')
        // Map to actual file names
        const nameMap: Record<string, string> = {
          '行情数据技能': 'market-data-skill', '投资分析技能': 'analysis-skill',
          'Web信息获取技能': 'web-fetch-skill', '交易技能': 'trading-skill',
          '量化交易技能': 'quant-skill', '通知技能': 'notification-skill',
          '专业财经爬虫技能': 'crawler-skill',
        }
        const scanName = nameMap[selectedSkill.name] || selectedSkill.id.replace('builtin-', '') + '-skill'
        res = await api.post(`/api/scanning/scan-builtin/${scanName}`, {}, { timeout: 300000 })
      } else {
        // Scan custom skill by ID
        res = await api.post('/api/scanning/scan', {
          skill_id: selectedSkill.id,
          scan_types: selectedDimensions,
        }, { timeout: 300000 })
      }
      setScanResult(res.data)
      toast.success('扫描完成')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '扫描失败')
    }
    setScanning(false)
  }

  const toggleDimension = (id: string) => {
    setSelectedDimensions(prev =>
      prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]
    )
  }

  const getScoreLevel = (score: number) => score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'
  const getScoreLabel = (score: number) => score >= 70 ? '低风险' : score >= 40 ? '中风险' : '高风险'

  const allSkills = [...builtinSkills.map(s => ({ ...s, source: 'builtin' })), ...customSkills.map(s => ({ ...s, source: 'custom' }))]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <Shield className="w-6 h-6 text-accent-gold" /> Skill 安全扫描
      </h1>
      <p className="text-gray-500 text-sm -mt-4">使用 Claude Sonnet 4.6 对Skill进行多维度风险评估</p>

      {/* Skill selector + Dimension selector */}
      <div className="grid grid-cols-3 gap-4">
        {/* Skill list */}
        <div className="col-span-2 card">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">选择要扫描的Skill</h2>
          <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
            {allSkills.map(s => (
              <button key={s.id} onClick={() => setSelectedSkill(s)}
                className={`text-left p-3 rounded-lg border transition-all ${
                  selectedSkill?.id === s.id
                    ? 'bg-primary-500/20 border-primary-500/50'
                    : 'bg-surface-hover border-surface-border hover:border-primary-500/30'
                }`}>
                <p className="text-sm text-white font-medium">{s.name}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">
                  {s.source === 'builtin' ? '内置' : '自定义'} · {s.tools?.length || 0} tools
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Dimensions + Run */}
        <div className="card space-y-4">
          <h2 className="text-sm font-semibold text-gray-400">扫描维度</h2>
          <div className="space-y-2">
            {dimensions.map(d => (
              <label key={d.id} className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" checked={selectedDimensions.includes(d.id)}
                  onChange={() => toggleDimension(d.id)}
                  className="mt-1 rounded border-surface-border bg-surface-dark" />
                <div>
                  <p className="text-sm text-white">{d.name}</p>
                  <p className="text-[10px] text-gray-500">{d.description}</p>
                </div>
              </label>
            ))}
          </div>

          <button onClick={handleScan} disabled={scanning || !selectedSkill}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50">
            <Play className="w-4 h-4" />
            {scanning ? 'Claude 扫描中...' : '开始扫描'}
          </button>

          {selectedSkill && (
            <p className="text-[10px] text-gray-600 text-center">
              已选: {selectedSkill.name}
            </p>
          )}
        </div>
      </div>

      {/* Scan Results */}
      {scanResult && (
        <div className="space-y-4">
          {/* Overall score */}
          <div className="card flex items-center gap-6">
            <div className={`text-center px-6 py-4 rounded-xl border ${SCORE_COLORS[getScoreLevel(scanResult.overall_score)]}`}>
              <p className="text-4xl font-bold font-mono">{scanResult.overall_score}</p>
              <p className="text-xs mt-1">{getScoreLabel(scanResult.overall_score)}</p>
            </div>
            <div>
              <h2 className="text-lg text-white font-semibold">{scanResult.skill_name || selectedSkill?.name}</h2>
              <p className="text-sm text-gray-400">
                风险等级: <span className={`font-medium ${getScoreLevel(scanResult.overall_score) === 'high' ? 'text-green-400' : getScoreLevel(scanResult.overall_score) === 'medium' ? 'text-yellow-400' : 'text-red-400'}`}>
                  {scanResult.risk_level}
                </span>
              </p>
              {scanResult.scanned_at && <p className="text-xs text-gray-600 mt-1">扫描时间: {scanResult.scanned_at}</p>}
            </div>
          </div>

          {/* Dimension scores */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(scanResult.results || {}).map(([key, val]: [string, any]) => (
              <div key={key} className="card text-center">
                <div className={`inline-block px-4 py-2 rounded-lg border mb-2 ${SCORE_COLORS[getScoreLevel(val.score)]}`}>
                  <p className="text-2xl font-bold font-mono">{val.score}</p>
                </div>
                <p className="text-sm text-white font-medium">{val.dimension}</p>
                <p className="text-[10px] text-gray-500">{val.findings?.length || 0} findings</p>
              </div>
            ))}
          </div>

          {/* Detailed findings */}
          {Object.entries(scanResult.results || {}).map(([key, val]: [string, any]) => (
            val.findings?.length > 0 && (
              <div key={key} className="card">
                <h3 className="text-sm font-semibold text-white mb-3">{val.dimension} — 详细发现</h3>
                <div className="space-y-2">
                  {val.findings.map((f: any, i: number) => {
                    const sev = SEVERITY_ICONS[f.severity] || SEVERITY_ICONS.info
                    const Icon = sev.icon
                    return (
                      <div key={i} className="flex items-start gap-2 bg-surface-hover rounded-lg p-3 border border-surface-border/50">
                        <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${sev.color}`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm text-white font-medium">{f.title}</p>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                              f.severity === 'critical' ? 'bg-red-900/50 text-red-400' :
                              f.severity === 'high' ? 'bg-red-900/30 text-red-300' :
                              f.severity === 'medium' ? 'bg-yellow-900/30 text-yellow-400' :
                              f.severity === 'low' ? 'bg-blue-900/30 text-blue-400' :
                              'bg-gray-800 text-gray-400'
                            }`}>{f.severity}</span>
                          </div>
                          <p className="text-xs text-gray-400 mt-1">{f.description}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          ))}
        </div>
      )}
    </div>
  )
}
