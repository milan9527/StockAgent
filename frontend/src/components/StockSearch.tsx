import { useState, useEffect, useRef } from 'react'
import { Search } from 'lucide-react'
import api from '../services/api'

interface StockSuggestion {
  code: string
  name: string
  market: string
  full_code: string
}

interface Props {
  onSelect: (stock: StockSuggestion) => void
  placeholder?: string
  className?: string
}

export default function StockSearch({ onSelect, placeholder = '输入股票代码或名称...', className = '' }: Props) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<any>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleChange = (value: string) => {
    setQuery(value)
    if (timerRef.current) clearTimeout(timerRef.current)
    if (!value.trim()) { setSuggestions([]); setShowDropdown(false); return }
    timerRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await api.get(`/api/watchlist/search-suggest?q=${encodeURIComponent(value)}`)
        setSuggestions(res.data.suggestions || [])
        setShowDropdown(true)
      } catch {}
      setLoading(false)
    }, 300)
  }

  const handleSelect = (stock: StockSuggestion) => {
    setQuery(`${stock.name}（${stock.market.toUpperCase()}${stock.code}）`)
    setShowDropdown(false)
    onSelect(stock)
  }

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input type="text" value={query} onChange={e => handleChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          className="input-field pl-10" placeholder={placeholder} />
        {loading && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 animate-pulse">搜索中...</span>}
      </div>
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-surface-card border border-surface-border rounded-lg shadow-xl max-h-64 overflow-y-auto">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => handleSelect(s)}
              className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-surface-hover transition-colors text-left border-b border-surface-border/30 last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-white font-medium">{s.name}</span>
                <span className="text-xs text-gray-500 font-mono">{s.market.toUpperCase()}{s.code}</span>
              </div>
              <span className="text-[10px] text-gray-600">{s.market === 'sh' ? '上海' : '深圳'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
