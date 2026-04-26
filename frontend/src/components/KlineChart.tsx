import { useEffect, useState, useCallback } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, BarChart, ReferenceLine,
} from 'recharts'
import api from '../services/api'

interface Props {
  stockCode: string
  source?: string
}

/* ── Candlestick shape for Recharts ── */
const Candlestick = (props: any) => {
  const { x, y, width, height, payload } = props
  if (!payload) return null
  const { open, close, high, low, _yScale } = payload
  if (!_yScale) return null

  const isUp = close >= open
  const color = isUp ? '#ef4444' : '#22c55e'
  const bodyTop = _yScale(Math.max(open, close))
  const bodyBottom = _yScale(Math.min(open, close))
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1)
  const wickTop = _yScale(high)
  const wickBottom = _yScale(low)
  const cx = x + width / 2

  return (
    <g>
      {/* Upper wick */}
      <line x1={cx} y1={wickTop} x2={cx} y2={bodyTop} stroke={color} strokeWidth={1} />
      {/* Body */}
      <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 2)} height={bodyHeight}
        fill={isUp ? color : color} stroke={color} strokeWidth={0.5} />
      {/* Lower wick */}
      <line x1={cx} y1={bodyBottom} x2={cx} y2={wickBottom} stroke={color} strokeWidth={1} />
    </g>
  )
}

export default function KlineChart({ stockCode, source = 'sina' }: Props) {
  const [data, setData] = useState<any[]>([])
  const [period, setPeriod] = useState('day')
  const [loading, setLoading] = useState(false)
  const [indicator, setIndicator] = useState<'ma' | 'boll' | 'vol'>('ma')

  useEffect(() => {
    if (stockCode) loadKline()
  }, [stockCode, period, source])

  const loadKline = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/api/market/kline/${stockCode}?period=${period}&count=60&source=${source}`)
      const raw = res.data.data || []
      const enriched = raw.map((d: any, i: number) => {
        const ma5 = i >= 4 ? raw.slice(i - 4, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 5 : null
        const ma10 = i >= 9 ? raw.slice(i - 9, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 10 : null
        const ma20 = i >= 19 ? raw.slice(i - 19, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 20 : null
        let boll_upper = null, boll_lower = null, boll_mid = null
        if (i >= 19) {
          const c20 = raw.slice(i - 19, i + 1).map((x: any) => x.close)
          const mean = c20.reduce((a: number, b: number) => a + b, 0) / 20
          const std = Math.sqrt(c20.reduce((a: number, b: number) => a + (b - mean) ** 2, 0) / 20)
          boll_mid = mean; boll_upper = mean + 2 * std; boll_lower = mean - 2 * std
        }
        return {
          ...d,
          dateLabel: d.date?.slice(5),
          ma5: ma5 ? +ma5.toFixed(2) : null,
          ma10: ma10 ? +ma10.toFixed(2) : null,
          ma20: ma20 ? +ma20.toFixed(2) : null,
          boll_upper: boll_upper ? +boll_upper.toFixed(2) : null,
          boll_mid: boll_mid ? +boll_mid.toFixed(2) : null,
          boll_lower: boll_lower ? +boll_lower.toFixed(2) : null,
          vol: d.volume ? +(d.volume / 10000).toFixed(1) : 0,
          // For candlestick: use "range" as a dummy bar height spanning low→high
          candleRange: [d.low, d.high],
        }
      })
      setData(enriched)
    } catch {}
    setLoading(false)
  }

  if (loading) return <div className="text-center py-8 text-gray-500 text-sm">加载K线数据...</div>
  if (!data.length) return null

  const allLows = data.map(d => d.low)
  const allHighs = data.map(d => d.high)
  const minPrice = Math.min(...allLows) * 0.997
  const maxPrice = Math.max(...allHighs) * 1.003

  // We need to pass yScale to each candlestick. We'll compute it from domain.
  const yRange = maxPrice - minPrice
  const chartHeight = 320
  const marginTop = 5, marginBottom = 25
  const plotHeight = chartHeight - marginTop - marginBottom

  const yScale = (val: number) => marginTop + plotHeight * (1 - (val - minPrice) / yRange)

  const enrichedWithScale = data.map(d => ({ ...d, _yScale: yScale }))

  return (
    <div className="space-y-2">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {['day', 'week', 'month'].map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 rounded text-xs ${period === p ? 'bg-primary-500/20 text-primary-300' : 'text-gray-500 hover:text-gray-300'}`}>
              {p === 'day' ? '日K' : p === 'week' ? '周K' : '月K'}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {[{ key: 'ma', label: 'MA均线' }, { key: 'boll', label: '布林带' }, { key: 'vol', label: '成交量' }].map(ind => (
            <button key={ind.key} onClick={() => setIndicator(ind.key as any)}
              className={`px-2.5 py-1 rounded text-xs ${indicator === ind.key ? 'bg-accent-gold/20 text-accent-gold' : 'text-gray-500 hover:text-gray-300'}`}>
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {/* Candlestick Chart */}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={enrichedWithScale} margin={{ top: marginTop, right: 5, bottom: marginBottom, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 9, fill: '#6b7280' }} interval={Math.floor(data.length / 8)} />
          <YAxis domain={[minPrice, maxPrice]} tick={{ fontSize: 9, fill: '#6b7280' }} width={65}
            tickFormatter={(v: number) => v.toFixed(1)} />
          <Tooltip
            contentStyle={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '8px', fontSize: '11px', padding: '8px 12px' }}
            labelStyle={{ color: '#9ca3af', marginBottom: 4 }}
            formatter={(value: any, name: string) => {
              const labels: Record<string, string> = {
                open: '开盘', close: '收盘', high: '最高', low: '最低',
                ma5: 'MA5', ma10: 'MA10', ma20: 'MA20',
                boll_upper: '上轨', boll_mid: '中轨', boll_lower: '下轨',
              }
              if (name === 'candleRange') return [null, null]
              return [typeof value === 'number' ? value.toFixed(2) : value, labels[name] || name]
            }}
            itemSorter={() => 0}
          />

          {/* Invisible bar just to create the x-axis slots for candlesticks */}
          <Bar dataKey="candleRange" shape={<Candlestick />} isAnimationActive={false}>
            {enrichedWithScale.map((entry, index) => (
              <Cell key={index} />
            ))}
          </Bar>

          {/* Overlay lines for tooltip data */}
          <Line type="monotone" dataKey="open" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="close" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="high" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="low" stroke="transparent" dot={false} />

          {/* MA lines */}
          {indicator === 'ma' && <>
            <Line type="monotone" dataKey="ma5" stroke="#ef4444" strokeWidth={1} dot={false} connectNulls />
            <Line type="monotone" dataKey="ma10" stroke="#3b82f6" strokeWidth={1} dot={false} connectNulls />
            <Line type="monotone" dataKey="ma20" stroke="#a855f7" strokeWidth={1} dot={false} connectNulls />
          </>}

          {/* Bollinger Bands */}
          {indicator === 'boll' && <>
            <Line type="monotone" dataKey="boll_upper" stroke="#ef4444" strokeWidth={1} dot={false} strokeDasharray="4 2" connectNulls />
            <Line type="monotone" dataKey="boll_mid" stroke="#6b7280" strokeWidth={1} dot={false} connectNulls />
            <Line type="monotone" dataKey="boll_lower" stroke="#22c55e" strokeWidth={1} dot={false} strokeDasharray="4 2" connectNulls />
          </>}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Volume chart */}
      {indicator === 'vol' && (
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={data} margin={{ top: 0, right: 5, bottom: 0, left: 5 }}>
            <XAxis dataKey="dateLabel" tick={false} />
            <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} width={65} tickFormatter={(v: number) => `${v}`} />
            <Tooltip contentStyle={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '8px', fontSize: '11px' }}
              formatter={(v: any) => [`${v}万手`, '成交量']} />
            <Bar dataKey="vol" isAnimationActive={false}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.close >= entry.open ? '#ef444480' : '#22c55e80'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* Legend */}
      <div className="flex gap-4 text-[10px] text-gray-500 justify-center">
        <span><span className="inline-block w-3 h-2 bg-red-500 mr-1 rounded-sm" />阳线(涨)</span>
        <span><span className="inline-block w-3 h-2 bg-green-500 mr-1 rounded-sm" />阴线(跌)</span>
        {indicator === 'ma' && <>
          <span><span className="inline-block w-3 h-0.5 bg-red-500 mr-1" />MA5</span>
          <span><span className="inline-block w-3 h-0.5 bg-blue-500 mr-1" />MA10</span>
          <span><span className="inline-block w-3 h-0.5 bg-purple-500 mr-1" />MA20</span>
        </>}
        {indicator === 'boll' && <>
          <span className="text-red-400">上轨</span>
          <span className="text-gray-400">中轨</span>
          <span className="text-green-400">下轨</span>
        </>}
      </div>
    </div>
  )
}
