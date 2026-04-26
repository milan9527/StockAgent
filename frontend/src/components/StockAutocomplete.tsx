import { useState, useRef, useEffect } from 'react'
import { Search } from 'lucide-react'
import api from '../services/api'

interface Suggestion {
  code: string
  name: string
  market: string
  full_code: string
  label: string
}

interface Props {
  onSelect: (item: Suggestion) => void
  placeholder?: string
  className?: string
}

export default function StockAutocomplete({ onSelect, placeholder = '输入股票代码或名称', className = '' }: Props) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<any>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setShow(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const doSearch = async (q: string) => {
    if (q.length < 1) { setSuggestions([]); return }
    setLoading(true)
    try {
      const res = await api.get(`/api/watchlist/autocomplete?q=${encodeURIComponent(q)}`)
      setSuggestions(res.data.suggestions || [])
      setShow(true)
    } catch {}
    setLoading(false)
  }

  const handleChange = (val: string) => {
    setQuery(val)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => doSearch(val), 200)
  }

  const handleSelect = (item: Suggestion) => {
    setQuery(`${item.code} ${item.name}`)
    setShow(false)
    onSelect(item)
  }

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={query}
          onChange={e => handleChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setShow(true)}
          className="input-field pl-10"
          placeholder={placeholder}
        />
        {loading && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">...</span>}
      </div>
      {show && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-surface-card border border-surface-border rounded-lg shadow-xl max-h-60 overflow-y-auto">
          {suggestions.map((item, i) => (
            <button
              key={i}
              onClick={() => handleSelect(item)}
              className="w-full flex items-center gap-3 px-3 py-2 hover:bg-surface-hover transition-colors text-left border-b border-surface-border/30 last:border-0"
            >
              <span className="text-[10px] text-gray-600 font-mono uppercase w-5">{item.market}</span>
              <span className="text-sm text-white font-medium">{item.name}</span>
              <span className="text-xs text-gray-500 font-mono">{item.code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
