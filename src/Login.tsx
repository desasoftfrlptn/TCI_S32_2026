import { ArrowRight, Factory } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { api, setToken, type Usuario } from './api'

export default function Login({ onLogin }: { onLogin: (usuario: Usuario) => void }) {
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSending(true)
    setError('')
    try {
      const sesion = await api.login(usuario.trim(), password)
      setToken(sesion.access_token)
      onLogin(sesion.usuario)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-navy px-4 py-10 text-white">
      <div className="pointer-events-none fixed inset-0 opacity-[0.06] blueprint-grid" />
      <section aria-labelledby="login-title" className="relative w-full max-w-sm">
        <div className="mb-8 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-mint text-navy" aria-hidden="true"><Factory size={21} /></span>
          <div>
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.19em] text-mint/80">Mantenimiento</p>
            <h1 id="login-title" className="text-xl font-semibold tracking-[-0.025em]">Planta en orden</h1>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-4 rounded-[1.6rem] bg-white p-6 text-navy shadow-2xl">
          <div>
            <label htmlFor="login-user" className="form-label">Usuario</label>
            <input id="login-user" required autoComplete="username" autoCapitalize="none" value={usuario} onChange={(event) => setUsuario(event.target.value)} className="form-control" />
          </div>
          <div>
            <label htmlFor="login-password" className="form-label">Contraseña</label>
            <input id="login-password" type="password" required autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="form-control" />
          </div>
          {error && <p role="alert" className="text-xs font-semibold text-coral">{error}</p>}
          <button type="submit" disabled={sending} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal px-4 py-3.5 text-sm font-extrabold text-navy transition hover:bg-[#20b7a4] disabled:opacity-50">
            {sending ? 'Ingresando…' : 'Ingresar'} <ArrowRight size={17} />
          </button>
        </form>
      </section>
    </main>
  )
}
