import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles, Zap, ToggleLeft, ToggleRight, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import api from '../services/api'

interface Message { role: 'user' | 'assistant'; content: string; timestamp: string; smartSkills?: string[] }

// Agent presets with default skill mappings
const agentPresets: Record<string, { label: string; icon: string; skills: string[] }> = {
  orchestrator: { label: '智能助手', icon: '🤖', skills: ['market-data-skill', 'analysis-skill', 'web-fetch-skill', 'trading-skill', 'quant-skill', 'notification-skill', 'crawler-skill', 'browser-crawler-skill', 'code-interpreter-skill'] },
  analyst: { label: '投资分析', icon: '📊', skills: ['market-data-skill', 'analysis-skill', 'web-fetch-skill', 'crawler-skill', 'browser-crawler-skill', 'code-interpreter-skill'] },
  trader: { label: '股票交易', icon: '💹', skills: ['market-data-skill', 'analysis-skill', 'trading-skill', 'notification-skill'] },
  quant: { label: '量化交易', icon: '📈', skills: ['market-data-skill', 'quant-skill', 'code-interpreter-skill'] },
}

const samplesByFocus: Record<string, string[]> = {
  'market-data-skill': ['查询贵州茅台实时行情', '批量查询宁德时代、比亚迪行情'],
  'analysis-skill': ['分析贵州茅台的技术指标', '评估宁德时代的投资价值'],
  'web-fetch-skill': ['搜索今日A股市场最新动态', '查找新能源行业最新政策'],
  'trading-skill': ['检查股票池的买卖信号', '制定一个稳健的交易策略'],
  'quant-skill': ['用双均线策略回测贵州茅台', '列出所有量化策略模板'],
  'crawler-skill': ['爬取东方财富固态电池新闻', '获取中际旭创券商研报'],
  'notification-skill': ['生成今日投资报告'],
  'browser-crawler-skill': ['使用浏览器获取动态网页数据'],
  'code-interpreter-skill': ['执行Python代码分析数据'],
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [agentType, setAgentType] = useState('orchestrator')
  const [sessionId] = useState(() => `chat-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`)
  const [allSkills, setAllSkills] = useState<any[]>([])
  const [enabledSkills, setEnabledSkills] = useState<Set<string>>(new Set())
  const [smartSelect, setSmartSelect] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    api.get('/api/skills/builtin').then(r => {
      const skills = r.data.skills || []
      setAllSkills(skills)
      setEnabledSkills(new Set(skills.map((s: any) => s.name.replace('技能', '-skill')
        .replace('行情数据', 'market-data').replace('投资分析', 'analysis')
        .replace('Web信息获取', 'web-fetch').replace('交易', 'trading')
        .replace('量化交易', 'quant').replace('通知', 'notification')
        .replace('专业财经爬虫', 'crawler').replace('浏览器爬虫', 'browser-crawler')
        .replace('代码执行', 'code-interpreter')
      )))
    }).catch(() => {})
  }, [])

  // When agent type changes, update enabled skills
  useEffect(() => {
    const preset = agentPresets[agentType]
    if (preset) {
      setEnabledSkills(new Set(preset.skills))
    }
  }, [agentType])

  const toggleSkill = (name: string) => {
    setEnabledSkills(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    const currentInput = input
    setInput('')
    setLoading(true)

    let smartSkills: string[] = []

    // Smart Select: search Registry for relevant skills
    if (smartSelect) {
      try {
        const sr = await api.post('/api/chat/smart-select', { query: currentInput, max_results: 5 })
        smartSkills = (sr.data.skills || []).map((s: any) => s.name)
      } catch {}
    }

    try {
      const res = await api.post('/api/chat/', {
        message: currentInput, session_id: sessionId, agent_type: agentType,
      }, { timeout: 600000 })

      setMessages(prev => [...prev, {
        role: 'assistant', content: res.data.response,
        timestamp: res.data.timestamp, smartSkills,
      }])
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant', content: `⚠️ ${err.message}`, timestamp: new Date().toISOString(),
      }])
    }
    setLoading(false)
  }

  // Get contextual samples based on enabled skills
  const activeSamples = Array.from(enabledSkills).flatMap(sk => samplesByFocus[sk] || []).slice(0, 6)

  // Map builtin skill names to registry-style names
  const skillNameMap: Record<string, string> = {
    '行情数据技能': 'market-data-skill', '投资分析技能': 'analysis-skill',
    'Web信息获取技能': 'web-fetch-skill', '交易技能': 'trading-skill',
    '量化交易技能': 'quant-skill', '通知技能': 'notification-skill',
    '专业财经爬虫技能': 'crawler-skill', '浏览器爬虫技能': 'browser-crawler-skill',
    '代码执行技能': 'code-interpreter-skill',
  }

  return (
    <div className="flex h-[calc(100vh-3rem)]">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-accent-gold" />
            <div>
              <h1 className="text-lg font-bold text-white">Agent Playground</h1>
              <p className="text-[10px] text-gray-500">
                {enabledSkills.size} skills enabled · AgentCore Memory · {smartSelect ? 'Smart Select ON' : 'Smart Select OFF'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Agent type selector */}
            {Object.entries(agentPresets).map(([key, preset]) => (
              <button key={key} onClick={() => setAgentType(key)}
                className={`px-2.5 py-1 rounded-lg text-[11px] ${agentType === key ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30' : 'text-gray-500 border border-surface-border hover:text-gray-300'}`}>
                {preset.icon} {preset.label}
              </button>
            ))}
            {/* Smart Select toggle */}
            <button onClick={() => setSmartSelect(!smartSelect)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] ${smartSelect ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30' : 'text-gray-500 border border-surface-border'}`}>
              <Zap className="w-3 h-3" /> Smart Select
              {smartSelect ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-14 h-14 text-gray-600 mb-4" />
              <h2 className="text-lg text-gray-400 mb-1">Agent Playground</h2>
              <p className="text-sm text-gray-600 mb-6">对话存储在AgentCore Memory，支持跨会话记忆</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {activeSamples.map(s => (
                  <button key={s} onClick={() => setInput(s)}
                    className="px-3 py-1.5 bg-surface-card border border-surface-border rounded-full text-xs text-gray-400 hover:text-white hover:border-primary-500/50 transition-colors">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-400" />
                </div>
              )}
              <div className={`max-w-[75%] rounded-xl px-4 py-3 ${msg.role === 'user' ? 'bg-primary-500/20 border border-primary-500/30' : 'bg-surface-card border border-surface-border'}`}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none prose-headings:text-accent-gold prose-headings:font-semibold prose-strong:text-white prose-p:text-gray-300 prose-p:leading-relaxed prose-table:text-xs prose-th:text-gray-400 prose-td:text-gray-300 prose-hr:border-surface-border text-sm">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm text-gray-200">{msg.content}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <p className="text-[10px] text-gray-600">{new Date(msg.timestamp).toLocaleTimeString()}</p>
                  {msg.smartSkills && msg.smartSkills.length > 0 && (
                    <div className="flex gap-1">
                      {msg.smartSkills.map(s => (
                        <span key={s} className="text-[8px] px-1 py-0.5 bg-accent-gold/10 text-accent-gold rounded">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-accent-gold/20 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-accent-gold" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-400 animate-pulse" />
              </div>
              <div className="bg-surface-card border border-surface-border rounded-xl px-4 py-3">
                <p className="text-xs text-gray-500">AgentCore Runtime 处理中...</p>
                <div className="flex gap-1 mt-1">
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-surface-border">
          <div className="flex gap-3">
            <input type="text" value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              className="input-field flex-1" placeholder="输入问题..." disabled={loading} />
            <button onClick={handleSend} disabled={loading || !input.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Right panel: Skill Control */}
      <div className="w-72 border-l border-surface-border bg-surface-card overflow-y-auto">
        <div className="p-4 border-b border-surface-border">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-white">Skill Control</h2>
            <span className="text-[10px] px-2 py-0.5 bg-primary-500/20 text-primary-300 rounded-full">
              {enabledSkills.size}/{allSkills.length}
            </span>
          </div>
          <p className="text-[10px] text-gray-500 mb-3">切换Skills控制Agent可用工具</p>
          <div className="flex gap-2">
            <button onClick={() => setEnabledSkills(new Set(allSkills.map((s: any) => skillNameMap[s.name] || s.id)))}
              className="flex-1 text-[10px] py-1 rounded bg-primary-500/20 text-primary-300 hover:bg-primary-500/30">
              Enable All
            </button>
            <button onClick={() => setEnabledSkills(new Set())}
              className="flex-1 text-[10px] py-1 rounded bg-red-900/20 text-red-400 hover:bg-red-900/30">
              Disable All
            </button>
          </div>
        </div>

        <div className="p-2 space-y-1">
          {allSkills.map((skill: any) => {
            const regName = skillNameMap[skill.name] || skill.id
            const isEnabled = enabledSkills.has(regName)
            return (
              <div key={skill.id}
                className={`p-2.5 rounded-lg border transition-all cursor-pointer ${isEnabled ? 'bg-surface-hover border-primary-500/30' : 'bg-surface-dark border-surface-border/30 opacity-50'}`}
                onClick={() => toggleSkill(regName)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isEnabled ? 'bg-green-400' : 'bg-gray-600'}`} />
                    <p className="text-xs text-white font-medium">{skill.name}</p>
                  </div>
                </div>
                <p className="text-[9px] text-gray-500 mt-1 ml-4">{skill.description?.slice(0, 50)}</p>
                {skill.tools?.length > 0 && (
                  <div className="flex gap-1 flex-wrap mt-1.5 ml-4">
                    {skill.tools.slice(0, 4).map((t: string) => (
                      <span key={t} className="text-[8px] px-1 py-0.5 bg-surface-dark rounded text-accent-gold font-mono">⚡ {t}</span>
                    ))}
                    {skill.tools.length > 4 && <span className="text-[8px] text-gray-600">+{skill.tools.length - 4}</span>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
