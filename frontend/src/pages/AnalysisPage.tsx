import { useState, useEffect } from 'react'
import { FileSearch, TrendingUp, Globe, AlertTriangle, Newspaper, Sparkles, LayoutTemplate, Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import StockSearch from '../components/StockSearch'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function AnalysisPage() {
  const [stockCode, setStockCode] = useState('')
  const [stockName, setStockName] = useState('')
  const [source, setSource] = useState('tencent')
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [reports, setReports] = useState<any[]>([])
  const [templates, setTemplates] = useState<any[]>([])
  const [newsQuery, setNewsQuery] = useState('')
  const [newsResults, setNewsResults] = useState<any[]>([])
  const [newsLoading, setNewsLoading] = useState(false)
  // Agent analysis
  const [agentPrompt, setAgentPrompt] = useState('')
  const [agentResult, setAgentResult] = useState('')
  const [agentLoading, setAgentLoading] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [viewReport, setViewReport] = useState<any>(null)

  useEffect(() => {
    loadReports()
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      const res = await api.get('/api/analysis/templates')
      setTemplates(res.data.templates || [])
    } catch {}
  }

  const loadReports = async () => {
    try {
      const res = await api.get('/api/analysis/reports')
      setReports(res.data.reports || [])
    } catch {}
  }

  const handleQuickAnalysis = async () => {
    if (!stockCode.trim()) { toast.error('请输入股票代码'); return }
    setLoading(true)
    setAnalysisResult(null)
    try {
      const res = await api.post('/api/analysis/stock', { stock_code: stockCode, stock_name: stockName, source })
      setAnalysisResult(res.data)
      toast.success('分析完成')
      loadReports()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.response?.data?.error || '分析失败')
    }
    setLoading(false)
  }

  const handleSelectTemplate = (tmpl: any) => {
    setSelectedTemplate(tmpl.id)
    let prompt = tmpl.prompt_template
    if (stockCode) prompt = prompt.replace('{stock_code}', stockCode)
    if (stockName) prompt = prompt.replace('{stock_name}', stockName)
    prompt = prompt.replace('{sector}', '').replace('{stock_list}', '')
    setAgentPrompt(prompt)
  }

  const handleAgentAnalysis = async () => {
    if (!agentPrompt.trim()) { toast.error('请输入分析需求'); return }
    setAgentLoading(true)
    setAgentResult('')
    try {
      const res = await api.post('/api/analysis/agent', {
        template_id: selectedTemplate,
        prompt: agentPrompt,
        stock_code: stockCode,
        stock_name: stockName,
      }, { timeout: 600000 })  // 10 min for deep analysis
      if (res.data.error) {
        setAgentResult(`⚠️ ${res.data.error}\n\n${res.data.detail || ''}`)
      } else {
        setAgentResult(res.data.response || '')
        toast.success('AI分析完成')
      }
      loadReports()
    } catch (err: any) {
      setAgentResult(`⚠️ 请求失败: ${err.message}`)
    }
    setAgentLoading(false)
  }

  const handleNewsSearch = async () => {
    if (!newsQuery.trim()) return
    setNewsLoading(true)
    try {
      const res = await api.post('/api/analysis/news', { query: newsQuery, max_results: 8 })
      setNewsResults(res.data.results || [])
    } catch { toast.error('搜索失败') }
    setNewsLoading(false)
  }

  const report = analysisResult?.report
  const tech = analysisResult?.technical
  const quote = analysisResult?.quote

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <FileSearch className="w-6 h-6 text-accent-gold" />
        投资分析
      </h1>

      {/* 快速技术分析 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" /> 快速技术分析
        </h2>
        <div className="grid grid-cols-5 gap-3 items-end">
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 mb-1">搜索股票</label>
            <StockSearch
              onSelect={(stock) => { setStockCode(stock.code); setStockName(stock.name) }}
              placeholder="输入股票代码或名称..."
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">数据源</label>
            <select className="input-field" value={source} onChange={e => setSource(e.target.value)}>
              <option value="tencent">腾讯证券</option>
              <option value="sina">新浪财经</option>
              <option value="yahoo">Yahoo Finance</option>
            </select>
          </div>
          <button onClick={handleQuickAnalysis} disabled={loading} className="btn-primary col-span-2 flex items-center justify-center gap-2 disabled:opacity-50">
            <TrendingUp className="w-4 h-4" />
            {loading ? '分析中...' : '快速分析'}
          </button>
        </div>
        {stockCode && <p className="text-xs text-gray-600 mt-2">已选: {stockName}（{stockCode}）</p>}
      </div>

      {/* 快速分析结果 */}
      {analysisResult && (
        <div className="space-y-4">
          {quote && !quote.error && (
            <div className="card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="text-xl font-bold text-white">{quote.name}</h2>
                  <p className="text-gray-500 text-xs font-mono">{quote.code} · {quote.source}</p>
                </div>
                <div className="text-right">
                  <p className={`text-3xl font-bold font-mono ${(quote.change_pct||0) > 0 ? 'stock-up' : (quote.change_pct||0) < 0 ? 'stock-down' : 'text-white'}`}>
                    ¥{quote.current_price?.toFixed(2)}
                  </p>
                  <p className={`text-sm font-mono ${(quote.change_pct||0) > 0 ? 'stock-up' : (quote.change_pct||0) < 0 ? 'stock-down' : 'text-gray-400'}`}>
                    {(quote.change_pct||0) > 0 ? '+' : ''}{quote.change_pct?.toFixed(2)}%
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-4 md:grid-cols-8 gap-2 text-xs">
                {[
                  { l: '今开', v: quote.open?.toFixed(2) }, { l: '昨收', v: quote.prev_close?.toFixed(2) },
                  { l: '最高', v: quote.high?.toFixed(2) }, { l: '最低', v: quote.low?.toFixed(2) },
                  { l: '成交量', v: `${quote.volume?.toLocaleString()}手` }, { l: '成交额', v: `${quote.amount?.toLocaleString()}万` },
                  { l: '市盈率', v: quote.pe_ratio?.toFixed(1) || '-' }, { l: '换手率', v: quote.turnover_rate || '-' },
                ].map(({ l, v }) => (
                  <div key={l} className="bg-surface-hover rounded p-2">
                    <p className="text-gray-600">{l}</p><p className="text-gray-300 font-mono mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {tech && !tech.error && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3">📊 技术指标</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-surface-hover rounded-lg p-3">
                  <p className="text-xs text-gray-500">趋势</p>
                  <p className={`text-sm font-medium mt-1 ${tech.trend?.includes('多头') ? 'stock-up' : tech.trend?.includes('空头') ? 'stock-down' : 'text-yellow-400'}`}>{tech.trend}</p>
                </div>
                <div className="bg-surface-hover rounded-lg p-3">
                  <p className="text-xs text-gray-500">MACD</p>
                  <p className={`text-sm font-medium mt-1 ${tech.macd?.signal === '金叉' ? 'stock-up' : tech.macd?.signal === '死叉' ? 'stock-down' : 'text-gray-300'}`}>{tech.macd?.signal} (DIF:{tech.macd?.dif})</p>
                </div>
                <div className="bg-surface-hover rounded-lg p-3">
                  <p className="text-xs text-gray-500">RSI(14)</p>
                  <p className={`text-sm font-medium mt-1 ${tech.rsi?.status === '超卖' ? 'stock-up' : tech.rsi?.status === '超买' ? 'stock-down' : 'text-gray-300'}`}>{tech.rsi?.rsi14} ({tech.rsi?.status})</p>
                </div>
                <div className="bg-surface-hover rounded-lg p-3">
                  <p className="text-xs text-gray-500">布林带</p>
                  <p className="text-sm font-medium mt-1 text-gray-300">{tech.bollinger?.position}</p>
                </div>
              </div>
            </div>
          )}
          {report && (
            <div className="card">
              <div className="flex items-center gap-4 mb-3">
                <div className={`text-center px-4 py-2 rounded-lg ${report.composite_score >= 70 ? 'bg-red-900/30 border border-red-800/50' : report.composite_score >= 50 ? 'bg-yellow-900/30 border border-yellow-800/50' : 'bg-green-900/30 border border-green-800/50'}`}>
                  <p className="text-2xl font-bold font-mono">{report.composite_score}</p>
                  <p className="text-[10px] text-gray-400">综合评分</p>
                </div>
                <div className={`px-4 py-2 rounded-lg text-lg font-bold ${report.recommendation === '买入' ? 'badge-buy text-base' : report.recommendation === '建议卖出' ? 'badge-sell text-base' : 'badge-hold text-base'}`}>
                  {report.recommendation}
                </div>
              </div>
              <div className="bg-surface-hover rounded-lg p-3 text-xs text-gray-400 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                <p>{report.risk_warning}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Agent 深度分析 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent-gold" /> AI Agent 深度分析
          <span className="text-[10px] text-gray-600 font-normal">使用Web搜索 + 行情数据 + 技术分析</span>
        </h2>

        {/* 分析模板 */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2 flex items-center gap-1"><LayoutTemplate className="w-3 h-3" /> 选择分析模板</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {templates.map((tmpl: any) => (
              <button
                key={tmpl.id}
                onClick={() => handleSelectTemplate(tmpl)}
                className={`text-left p-3 rounded-lg border transition-all text-xs ${selectedTemplate === tmpl.id ? 'bg-primary-500/20 border-primary-500/50' : 'bg-surface-hover border-surface-border hover:border-primary-500/30'}`}
              >
                <p className="text-white font-medium">{tmpl.name}</p>
                <p className="text-gray-500 mt-0.5 text-[10px]">{tmpl.description}</p>
                <div className="flex gap-1 mt-1.5 flex-wrap">
                  {tmpl.skills_used?.map((s: string) => (
                    <span key={s} className="px-1.5 py-0.5 bg-surface-dark rounded text-[9px] text-gray-500">{s}</span>
                  ))}
                  {tmpl.requires_agent && <span className="px-1.5 py-0.5 bg-accent-gold/20 rounded text-[9px] text-accent-gold">需要LLM</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 自定义分析需求 */}
        <div className="flex gap-3">
          <textarea
            className="input-field flex-1 h-20 text-sm"
            value={agentPrompt}
            onChange={e => setAgentPrompt(e.target.value)}
            placeholder="输入分析需求，或选择上方模板自动填充...&#10;例如：分析贵州茅台的投资价值，搜索最新财报和行业动态"
          />
          <button onClick={handleAgentAnalysis} disabled={agentLoading} className="btn-primary self-end flex items-center gap-2 disabled:opacity-50 h-10">
            <Send className="w-4 h-4" />
            {agentLoading ? '深度分析中(约2-5分钟)...' : '开始分析'}
          </button>
        </div>

        {/* Agent分析结果 */}
        {agentResult && (
          <div className="mt-4 bg-surface-hover rounded-lg p-4 border border-surface-border/50">
            <h3 className="text-xs text-gray-500 mb-2">📋 AI分析结果</h3>
            <div className="prose prose-invert prose-sm max-w-none text-gray-300 text-sm">
              <ReactMarkdown>{agentResult}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {/* 财经新闻搜索 */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Newspaper className="w-4 h-4" /> 财经新闻搜索
        </h2>
        <div className="flex gap-3">
          <input className="input-field flex-1" value={newsQuery} onChange={e => setNewsQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleNewsSearch()} placeholder="搜索财经新闻..." />
          <button onClick={handleNewsSearch} disabled={newsLoading} className="btn-secondary flex items-center gap-2">
            <Globe className="w-4 h-4" />{newsLoading ? '搜索中...' : '搜索'}
          </button>
        </div>
        {newsResults.length > 0 && (
          <div className="mt-3 space-y-2">
            {newsResults.map((item: any, i: number) => (
              <div key={i} className="bg-surface-hover rounded-lg p-3 border border-surface-border/50">
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary-300 hover:text-primary-200 font-medium">{item.title}</a>
                <p className="text-xs text-gray-500 mt-1">{item.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 历史报告 */}
      {reports.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">历史分析报告 ({reports.length})</h2>
          <div className="space-y-2">
            {reports.map((r: any) => (
              <div key={r.id} className="flex items-center justify-between py-2 border-b border-surface-border/50 cursor-pointer hover:bg-surface-hover/50 px-2 rounded" onClick={() => setViewReport(viewReport?.id === r.id ? null : r)}>
                <div className="flex-1">
                  <p className="text-sm text-white">{r.title}</p>
                  <p className="text-xs text-gray-500">{r.summary?.slice(0, 100)}</p>
                </div>
                <div className="text-right flex-shrink-0 ml-4">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.report_type === 'agent' ? 'bg-accent-gold/20 text-accent-gold' : 'bg-surface-hover text-gray-500'}`}>
                    {r.report_type === 'agent' ? 'AI分析' : '快速分析'}
                  </span>
                  <p className="text-[10px] text-gray-600 mt-1">{r.created_at?.split('T')[0]}</p>
                </div>
              </div>
            ))}
          </div>
          {viewReport && (
            <div className="mt-3 bg-surface-hover rounded-lg p-4 border border-surface-border/50">
              <h3 className="text-sm text-white font-medium mb-2">{viewReport.title}</h3>
              <div className="prose prose-invert prose-sm max-w-none text-gray-300 text-xs max-h-96 overflow-y-auto">
                <ReactMarkdown>{viewReport.content || viewReport.summary}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
