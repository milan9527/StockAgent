import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Bot, TrendingUp, Shield, Zap } from 'lucide-react'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) { toast.error('请输入用户名和密码'); return }
    setLoading(true)
    try {
      await login(username, password)
      toast.success('登录成功')
      navigate('/')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left brand area */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-900 via-primary-800 to-surface-dark items-center justify-center p-12">
        <div className="max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <Bot className="w-12 h-12 text-accent-gold" />
            <div>
              <h1 className="text-3xl font-bold text-white">证券交易助手</h1>
              <p className="text-primary-300 text-sm">Securities Trading Assistant</p>
            </div>
          </div>
          <p className="text-gray-300 text-lg mb-10 leading-relaxed">
            智能证券交易平台，AI驱动的投资分析、交易策略和量化回测。
          </p>
          <div className="space-y-4">
            {[
              { icon: TrendingUp, title: '投资分析', desc: '基本面+技术面全方位分析，AI生成投资报告' },
              { icon: Shield, title: '智能交易', desc: '实时监控买卖信号，模拟盘交易验证' },
              { icon: Zap, title: '量化回测', desc: '预置量化模板，自定义策略，历史回测验证' },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex items-start gap-3">
                <div className="p-2 bg-primary-500/20 rounded-lg">
                  <Icon className="w-5 h-5 text-accent-gold" />
                </div>
                <div>
                  <h3 className="text-white font-medium text-sm">{title}</h3>
                  <p className="text-gray-400 text-xs">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-surface-dark">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <Bot className="w-8 h-8 text-accent-gold" />
            <h1 className="text-xl font-bold text-white">证券交易助手</h1>
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">登录</h2>
          <p className="text-gray-500 text-sm mb-8">登录您的账户开始使用</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">用户名</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                className="input-field" placeholder="输入用户名" required autoComplete="username" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">密码</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className="input-field" placeholder="输入密码" required autoComplete="current-password" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 disabled:opacity-50">
              {loading ? '登录中...' : '登录'}
            </button>
          </form>

          <p className="text-center text-xs text-gray-600 mt-6">
            账户由管理员创建和管理
          </p>
        </div>
      </div>
    </div>
  )
}
