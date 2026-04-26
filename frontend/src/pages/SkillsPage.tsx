import { useEffect, useState } from 'react'
import { Puzzle, Plus, Upload, Trash2, Download, Package, Wrench, Globe, Code } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const typeColors: Record<string, string> = {
  market: 'bg-green-900/30 text-green-400',
  analysis: 'bg-blue-900/30 text-blue-400',
  web: 'bg-purple-900/30 text-purple-400',
  trading: 'bg-red-900/30 text-red-400',
  quant: 'bg-yellow-900/30 text-yellow-400',
  notification: 'bg-cyan-900/30 text-cyan-400',
  external: 'bg-orange-900/30 text-orange-400',
  custom: 'bg-gray-800 text-gray-400',
}

export default function SkillsPage() {
  const [builtinSkills, setBuiltinSkills] = useState<any[]>([])
  const [customSkills, setCustomSkills] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [tab, setTab] = useState<'all' | 'builtin' | 'custom'>('all')
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', description: '', skill_type: 'analysis', code: '', parameters_schema: '{}' })
  const [importForm, setImportForm] = useState({ name: '', description: '', source_type: 'mcp', source_url: '', package_name: '', skill_type: 'external' })

  useEffect(() => { loadSkills() }, [])

  const loadSkills = async () => {
    try {
      const res = await api.get('/api/skills/all')
      setBuiltinSkills(res.data.builtin || [])
      setCustomSkills(res.data.custom || [])
      setTotal(res.data.total || 0)
    } catch {}
  }

  const handleCreate = async () => {
    try {
      await api.post('/api/skills/', {
        name: form.name, description: form.description, skill_type: form.skill_type,
        code: form.code, parameters_schema: JSON.parse(form.parameters_schema || '{}'),
      })
      toast.success('Skill创建成功')
      setShowCreate(false)
      setForm({ name: '', description: '', skill_type: 'analysis', code: '', parameters_schema: '{}' })
      loadSkills()
    } catch (err: any) { toast.error(err.response?.data?.detail || '创建失败') }
  }

  const handleImport = async () => {
    if (!importForm.name) { toast.error('请输入Skill名称'); return }
    try {
      await api.post('/api/skills/import', importForm)
      toast.success('外部Skill导入成功')
      setShowImport(false)
      setImportForm({ name: '', description: '', source_type: 'mcp', source_url: '', package_name: '', skill_type: 'external' })
      loadSkills()
    } catch (err: any) { toast.error(err.response?.data?.detail || '导入失败') }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此Skill?')) return
    try { await api.delete(`/api/skills/${id}`); toast.success('已删除'); loadSkills() } catch {}
  }

  const handlePublish = async (id: string) => {
    try { await api.post(`/api/skills/${id}/publish`); toast.success('已发布到Registry'); loadSkills() } catch {}
  }

  const displaySkills = tab === 'builtin' ? builtinSkills : tab === 'custom' ? customSkills : [...builtinSkills, ...customSkills]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Puzzle className="w-6 h-6 text-accent-gold" /> Skills 管理
          </h1>
          <p className="text-gray-500 text-sm mt-1">共 {total} 个Skills (内置 {builtinSkills.length} + 自定义 {customSkills.length})</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setShowImport(!showImport); setShowCreate(false) }} className="btn-secondary flex items-center gap-2 text-sm">
            <Download className="w-4 h-4" /> 导入外部Skill
          </button>
          <button onClick={() => { setShowCreate(!showCreate); setShowImport(false) }} className="btn-primary flex items-center gap-2 text-sm">
            <Plus className="w-4 h-4" /> 新建Skill
          </button>
        </div>
      </div>

      {/* Tab切换 */}
      <div className="flex gap-2">
        {[
          { key: 'all', label: `全部 (${total})` },
          { key: 'builtin', label: `内置 (${builtinSkills.length})` },
          { key: 'custom', label: `自定义 (${customSkills.length})` },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${tab === t.key ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30' : 'bg-surface-hover text-gray-400 border border-surface-border'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* 导入外部Skill */}
      {showImport && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2"><Download className="w-5 h-5 text-blue-400" /> 导入外部Skill</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Skill名称</label>
              <input className="input-field" value={importForm.name} onChange={e => setImportForm({ ...importForm, name: e.target.value })} placeholder="如：自定义数据源" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">来源类型</label>
              <select className="input-field" value={importForm.source_type} onChange={e => setImportForm({ ...importForm, source_type: e.target.value })}>
                <option value="mcp">MCP Server</option>
                <option value="pip">Python包 (pip)</option>
                <option value="url">URL / Git仓库</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">描述</label>
            <input className="input-field" value={importForm.description} onChange={e => setImportForm({ ...importForm, description: e.target.value })} placeholder="Skill功能描述" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{importForm.source_type === 'pip' ? '包名' : 'URL'}</label>
              <input className="input-field" value={importForm.source_type === 'pip' ? importForm.package_name : importForm.source_url}
                onChange={e => importForm.source_type === 'pip' ? setImportForm({ ...importForm, package_name: e.target.value }) : setImportForm({ ...importForm, source_url: e.target.value })}
                placeholder={importForm.source_type === 'pip' ? 'strands-agents-tools' : importForm.source_type === 'mcp' ? 'https://mcp-server.example.com' : 'https://github.com/user/repo'} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">类型</label>
              <select className="input-field" value={importForm.skill_type} onChange={e => setImportForm({ ...importForm, skill_type: e.target.value })}>
                <option value="external">外部</option>
                <option value="analysis">分析</option>
                <option value="trading">交易</option>
                <option value="quant">量化</option>
                <option value="market">行情</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleImport} className="btn-primary">导入</button>
            <button onClick={() => setShowImport(false)} className="btn-secondary">取消</button>
          </div>
        </div>
      )}

      {/* 创建自定义Skill */}
      {showCreate && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold text-white">创建自定义Skill</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">名称</label>
              <input className="input-field" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="如：自定义RSI分析" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">类型</label>
              <select className="input-field" value={form.skill_type} onChange={e => setForm({ ...form, skill_type: e.target.value })}>
                <option value="analysis">分析</option><option value="trading">交易</option>
                <option value="quant">量化</option><option value="notification">通知</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">描述</label>
            <textarea className="input-field h-16" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">代码 (Python)</label>
            <textarea className="input-field h-40 font-mono text-xs" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })}
              placeholder={`from strands import tool\n\n@tool\ndef my_skill(param: str) -> dict:\n    """描述"""\n    return {"result": param}`} />
          </div>
          <div className="flex gap-3">
            <button onClick={handleCreate} className="btn-primary">创建</button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">取消</button>
          </div>
        </div>
      )}

      {/* Skills列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {displaySkills.map((skill: any) => (
          <div key={skill.id} className="card cursor-pointer" onClick={() => setExpandedSkill(expandedSkill === skill.id ? null : skill.id)}>
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                {skill.source === 'builtin' ? <Package className="w-4 h-4 text-blue-400" /> :
                 skill.source === 'custom' && skill.description?.startsWith('[') ? <Globe className="w-4 h-4 text-orange-400" /> :
                 <Code className="w-4 h-4 text-green-400" />}
                <div>
                  <h3 className="text-white font-semibold text-sm">{skill.name}</h3>
                  <p className="text-gray-500 text-[10px]">v{skill.version} · {skill.source === 'builtin' ? '内置' : '自定义'} · {skill.tools?.length || 0} tools</p>
                </div>
              </div>
              <span className={`badge text-[10px] ${typeColors[skill.skill_type] || typeColors.custom}`}>
                {skill.skill_type}
              </span>
            </div>
            <p className="text-xs text-gray-400 mb-2">{skill.description}</p>

            {/* 工具列表 */}
            {skill.tools && skill.tools.length > 0 && (
              <div className="flex gap-1 flex-wrap mb-2">
                {skill.tools.map((t: string) => (
                  <span key={t} className="px-1.5 py-0.5 bg-surface-dark rounded text-[9px] text-accent-gold font-mono">{t}</span>
                ))}
              </div>
            )}

            {/* 展开详情 */}
            {expandedSkill === skill.id && (
              <div className="mt-2 pt-2 border-t border-surface-border/30 space-y-2">
                {skill.used_by && skill.used_by.length > 0 && (
                  <div>
                    <p className="text-[10px] text-gray-600 mb-1">使用此Skill的Agent:</p>
                    <div className="flex gap-1 flex-wrap">
                      {skill.used_by.map((a: string) => (
                        <span key={a} className="px-1.5 py-0.5 bg-primary-500/10 rounded text-[10px] text-primary-300">{a}</span>
                      ))}
                    </div>
                  </div>
                )}
                {skill.tools && skill.tools.length > 0 && (
                  <div>
                    <p className="text-[10px] text-gray-600 mb-1">工具详情:</p>
                    {skill.tools.map((t: string) => (
                      <div key={t} className="bg-surface-dark rounded p-2 mb-1 border border-surface-border/30">
                        <code className="text-[10px] text-accent-gold">{t}</code>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-[9px] text-gray-600">点击收起</p>
              </div>
            )}

            {/* 代码预览 */}
            {skill.code && skill.source !== 'builtin' && (
              <pre className="bg-surface-dark rounded p-2 text-[10px] text-gray-500 font-mono overflow-x-auto max-h-20 mt-2 border border-surface-border/50">
                {skill.code.slice(0, 200)}{skill.code.length > 200 ? '...' : ''}
              </pre>
            )}

            {/* 操作按钮 */}
            {skill.source !== 'builtin' && (
              <div className="flex gap-3 mt-2 pt-2 border-t border-surface-border/30">
                {!skill.is_published && (
                  <button onClick={() => handlePublish(skill.id)} className="text-[10px] text-primary-400 hover:text-primary-300 flex items-center gap-1">
                    <Upload className="w-3 h-3" /> 发布到Registry
                  </button>
                )}
                {skill.is_published && <span className="text-[10px] text-green-400">✓ 已发布</span>}
                <button onClick={() => handleDelete(skill.id)} className="text-[10px] text-gray-500 hover:text-red-400 flex items-center gap-1 ml-auto">
                  <Trash2 className="w-3 h-3" /> 删除
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
