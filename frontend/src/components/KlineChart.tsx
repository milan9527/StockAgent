import { useEffect, useState } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, BarChart, ReferenceLine, LineChart,
} from 'recharts'
import api from '../services/api'

interface Props {
  stockCode: string
  source?: string
}

/* ── Candlestick shape ── */
const Candlestick = (props: any) => {
  const { x, width, payload } = props
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
      <line x1={cx} y1={wickTop} x2={cx} y2={bodyTop} stroke={color} strokeWidth={1} />
      <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 2)} height={bodyHeight}
        fill={color} stroke={color} strokeWidth={0.5} />
      <line x1={cx} y1={bodyBottom} x2={cx} y2={wickBottom} stroke={color} strokeWidth={1} />
    </g>
  )
}

/* ── Compute indicators ── */
function computeIndicators(raw: any[]) {
  return raw.map((d: any, i: number) => {
    // MA
    const ma5 = i >= 4 ? raw.slice(i - 4, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 5 : null
    const ma10 = i >= 9 ? raw.slice(i - 9, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 10 : null
    const ma20 = i >= 19 ? raw.slice(i - 19, i + 1).reduce((s: number, x: any) => s + x.close, 0) / 20 : null

    return {
      ...d,
      dateLabel: d.date?.slice(5),
      ma5: ma5 ? +ma5.toFixed(2) : null,
      ma10: ma10 ? +ma10.toFixed(2) : null,
      ma20: ma20 ? +ma20.toFixed(2) : null,
      vol: d.volume ? +(d.volume / 10000).toFixed(1) : 0,
      candleRange: [d.low, d.high],
    }
  })
}

function computeMACD(data: any[]) {
  // EMA helper
  const ema = (arr: number[], period: number) => {
    const k = 2 / (period + 1)
    const result: number[] = [arr[0]]
    for (let i = 1; i < arr.length; i++) {
      result.push(arr[i] * k + result[i - 1] * (1 - k))
    }
    return result
  }

  const closes = data.map(d => d.close)
  const ema12 = ema(closes, 12)
  const ema26 = ema(closes, 26)
  const dif = ema12.map((v, i) => +(v - ema26[i]).toFixed(3))
  const dea = ema(dif, 9).map(v => +v.toFixed(3))
  const macd = dif.map((v, i) => +((v - dea[i]) * 2).toFixed(3))

  return data.map((d, i) => ({
    ...d,
    dif: i >= 25 ? dif[i] : null,
    dea: i >= 25 ? dea[i] : null,
    macd_bar: i >= 25 ? macd[i] : null,
  }))
}

function computeKDJ(data: any[]) {
  const period = 9
  let k = 50, d = 50
  return data.map((item, i) => {
    if (i < period - 1) return { ...item, k_val: null, d_val: null, j_val: null }
    const slice = data.slice(i - period + 1, i + 1)
    const low9 = Math.min(...slice.map(s => s.low))
    const high9 = Math.max(...slice.map(s => s.high))
    const rsv = high9 === low9 ? 50 : ((item.close - low9) / (high9 - low9)) * 100
    k = 2 / 3 * k + 1 / 3 * rsv
    d = 2 / 3 * d + 1 / 3 * k
    const j = 3 * k - 2 * d
    return { ...item, k_val: +k.toFixed(2), d_val: +d.toFixed(2), j_val: +j.toFixed(2) }
  })
}

export default function KlineChart({ stockCode, source = 'sina' }: Props) {
  const [data, setData] = useState<any[]>([])
  const [period, setPeriod] = useState('day')
  const [loading, setLoading] = useState(false)
  const [subIndicator, setSubIndicator] = useState<'macd' | 'kdj'>('macd')

  useEffect(() => {
    if (stockCode) loadKline()
  }, [stockCode, period, source])

  const loadKline = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/api/market/kline/${stockCode}?period=${period}&count=80&source=${source}`)
      const raw = res.data.data || []
      setData(raw)
    } catch {}
    setLoading(false)
  }

  if (loading) return <div className="text-center py-8 text-gray-500 text-sm">加载K线数据...</div>
  if (!data.length) return null

  // Compute all indicators
  const enriched = computeIndicators(data)
  const macdData = computeMACD(data)
  const kdjData = computeKDJ(data)

  const allLows = data.map(d => d.low)
  const allHighs = data.map(d => d.high)
  const minPrice = Math.min(...allLows) * 0.997
  const maxPrice = Math.max(...allHighs) * 1.003

  const chartHeight = 280
  const marginTop = 5, marginBottom = 20
  const plotHeight = chartHeight - marginTop - marginBottom
  const yRange = maxPrice - minPrice
  const yScale = (val: number) => marginTop + plotHeight * (1 - (val - minPrice) / yRange)
  const enrichedWithScale = enriched.map(d => ({ ...d, _yScale: yScale }))

  const xInterval = Math.floor(data.length / 8)

  return (
    <div className="space-y-1">
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
          {[{ key: 'macd', label: 'MACD' }, { key: 'kdj', label: 'KDJ' }].map(ind => (
            <button key={ind.key} onClick={() => setSubIndicator(ind.key as any)}
              className={`px-2.5 py-1 rounded text-xs ${subIndicator === ind.key ? 'bg-accent-gold/20 text-accent-gold' : 'text-gray-500 hover:text-gray-300'}`}>
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main K-line chart with MA */}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={enrichedWithScale} margin={{ top: marginTop, right: 5, bottom: marginBottom, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 9, fill: '#6b7280' }} interval={xInterval} />
          <YAxis domain={[minPrice, maxPrice]} tick={{ fontSize: 9, fill: '#6b7280' }} width={60}
            tickFormatter={(v: number) => v.toFixed(1)} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null
              const d = payload[0]?.payload
              if (!d) return null
              const change = d.close - d.open
              const changePct = d.open ? ((change / d.open) * 100) : 0
              const isUp = change >= 0
              return (
                <div style={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '8px', padding: '10px 14px', fontSize: '11px', lineHeight: '1.8' }}>
                  <p style={{ color: '#9ca3af', marginBottom: 4, fontWeight: 600 }}>{d.date}</p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto auto', gap: '2px 12px' }}>
                    <span style={{ color: '#9ca3af' }}>开盘</span><span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{d.open?.toFixed(2)}</span>
                    <span style={{ color: '#9ca3af' }}>收盘</span><span style={{ color: isUp ? '#ef4444' : '#22c55e', fontFamily: 'monospace', fontWeight: 600 }}>{d.close?.toFixed(2)}</span>
                    <span style={{ color: '#9ca3af' }}>最高</span><span style={{ color: '#ef4444', fontFamily: 'monospace' }}>{d.high?.toFixed(2)}</span>
                    <span style={{ color: '#9ca3af' }}>最低</span><span style={{ color: '#22c55e', fontFamily: 'monospace' }}>{d.low?.toFixed(2)}</span>
                    <span style={{ color: '#9ca3af' }}>涨跌</span><span style={{ color: isUp ? '#ef4444' : '#22c55e', fontFamily: 'monospace' }}>{isUp ? '+' : ''}{change.toFixed(2)}</span>
                    <span style={{ color: '#9ca3af' }}>幅度</span><span style={{ color: isUp ? '#ef4444' : '#22c55e', fontFamily: 'monospace', fontWeight: 600 }}>{isUp ? '+' : ''}{changePct.toFixed(2)}%</span>
                    <span style={{ color: '#9ca3af' }}>成交量</span><span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{d.vol ? `${d.vol}万手` : '-'}</span>
                  </div>
                  {(d.ma5 || d.ma10 || d.ma20) && (
                    <div style={{ borderTop: '1px solid #2d3f52', marginTop: 6, paddingTop: 4, display: 'flex', gap: 10 }}>
                      {d.ma5 && <span style={{ color: '#ef4444', fontSize: 10 }}>MA5: {d.ma5}</span>}
                      {d.ma10 && <span style={{ color: '#3b82f6', fontSize: 10 }}>MA10: {d.ma10}</span>}
                      {d.ma20 && <span style={{ color: '#a855f7', fontSize: 10 }}>MA20: {d.ma20}</span>}
                    </div>
                  )}
                </div>
              )
            }}
          />
          <Bar dataKey="candleRange" shape={<Candlestick />} isAnimationActive={false}>
            {enrichedWithScale.map((_, i) => <Cell key={i} />)}
          </Bar>
          <Line type="monotone" dataKey="open" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="close" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="high" stroke="transparent" dot={false} />
          <Line type="monotone" dataKey="low" stroke="transparent" dot={false} />
          {/* MA lines always shown */}
          <Line type="monotone" dataKey="ma5" stroke="#ef4444" strokeWidth={1} dot={false} connectNulls />
          <Line type="monotone" dataKey="ma10" stroke="#3b82f6" strokeWidth={1} dot={false} connectNulls />
          <Line type="monotone" dataKey="ma20" stroke="#a855f7" strokeWidth={1} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Volume chart - always shown */}
      <ResponsiveContainer width="100%" height={60}>
        <BarChart data={enriched} margin={{ top: 0, right: 5, bottom: 0, left: 5 }}>
          <XAxis dataKey="dateLabel" tick={false} />
          <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} width={60} tickFormatter={(v: number) => `${v}万`} />
          <Tooltip contentStyle={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '6px', fontSize: '10px' }}
            formatter={(v: any) => [`${v}万手`, '成交量']} />
          <Bar dataKey="vol" isAnimationActive={false}>
            {enriched.map((entry, i) => (
              <Cell key={i} fill={entry.close >= entry.open ? '#ef444480' : '#22c55e80'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* MACD sub-chart */}
      {subIndicator === 'macd' && (
        <ResponsiveContainer width="100%" height={90}>
          <ComposedChart data={macdData} margin={{ top: 5, right: 5, bottom: 0, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="dateLabel" tick={false} />
            <YAxis tick={{ fontSize: 8, fill: '#6b7280' }} width={60} />
            <Tooltip contentStyle={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '6px', fontSize: '10px' }}
              formatter={(v: any, name: string) => {
                const labels: Record<string, string> = { dif: 'DIF', dea: 'DEA', macd_bar: 'MACD' }
                return [typeof v === 'number' ? v.toFixed(3) : v, labels[name] || name]
              }} />
            <ReferenceLine y={0} stroke="#4b5563" strokeDasharray="2 2" />
            <Bar dataKey="macd_bar" isAnimationActive={false}>
              {macdData.map((entry, i) => (
                <Cell key={i} fill={(entry.macd_bar || 0) >= 0 ? '#ef4444' : '#22c55e'} />
              ))}
            </Bar>
            <Line type="monotone" dataKey="dif" stroke="#d4a843" strokeWidth={1.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="dea" stroke="#3b82f6" strokeWidth={1.5} dot={false} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* KDJ sub-chart */}
      {subIndicator === 'kdj' && (
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={kdjData} margin={{ top: 5, right: 5, bottom: 0, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="dateLabel" tick={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 8, fill: '#6b7280' }} width={60} />
            <Tooltip contentStyle={{ background: '#0f1419', border: '1px solid #2d3f52', borderRadius: '6px', fontSize: '10px' }}
              formatter={(v: any, name: string) => {
                const labels: Record<string, string> = { k_val: 'K', d_val: 'D', j_val: 'J' }
                return [typeof v === 'number' ? v.toFixed(1) : v, labels[name] || name]
              }} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="2 2" strokeOpacity={0.5} />
            <ReferenceLine y={20} stroke="#22c55e" strokeDasharray="2 2" strokeOpacity={0.5} />
            <Line type="monotone" dataKey="k_val" stroke="#d4a843" strokeWidth={1.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="d_val" stroke="#3b82f6" strokeWidth={1.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="j_val" stroke="#a855f7" strokeWidth={1.5} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* Legend */}
      <div className="flex gap-3 text-[10px] text-gray-500 justify-center flex-wrap">
        <span><span className="inline-block w-3 h-2 bg-red-500 mr-1 rounded-sm" />阳线</span>
        <span><span className="inline-block w-3 h-2 bg-green-500 mr-1 rounded-sm" />阴线</span>
        <span><span className="inline-block w-3 h-0.5 bg-red-500 mr-1" />MA5</span>
        <span><span className="inline-block w-3 h-0.5 bg-blue-500 mr-1" />MA10</span>
        <span><span className="inline-block w-3 h-0.5 bg-purple-500 mr-1" />MA20</span>
        {subIndicator === 'macd' && <>
          <span className="text-accent-gold">DIF</span>
          <span className="text-blue-400">DEA</span>
          <span className="text-gray-400">MACD柱</span>
        </>}
        {subIndicator === 'kdj' && <>
          <span className="text-accent-gold">K</span>
          <span className="text-blue-400">D</span>
          <span className="text-purple-400">J</span>
        </>}
      </div>
    </div>
  )
}
