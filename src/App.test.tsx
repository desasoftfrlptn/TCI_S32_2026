import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { setToken } from './api'

// Backend simulado: responde por método + ruta y registra lo que se envió.
const usuario = { id: 3, usuario: 'encargado', nombre: 'Encargado Demo', email: 'e@planta.local', rol: 'encargado' }

function repuesto(id: number, codigo: string, nombre: string, fisico: number, reservado: number, umbral: number) {
  return {
    id, codigo, nombre, descripcion: '', stock_fisico: fisico, stock_reservado: reservado,
    stock_disponible: fisico - reservado, umbral_minimo: umbral, bajo_umbral: fisico - reservado <= umbral,
    ubicacion_codigo: 'A-03-12', ubicacion_descripcion: null, maquinas: [{ id: 1, codigo: 'MAQ-F04', nombre: 'Fraccionadora F-04' }],
  }
}

let repuestos = [repuesto(1, 'RP-2048', 'Sello mecánico 32 mm', 4, 0, 1), repuesto(2, 'IN-4421', 'Filtro HEPA H14', 8, 1, 2)]
const enviados: { method: string; path: string; body: unknown }[] = []

const rutas: Record<string, (body: unknown) => [number, unknown]> = {
  'POST /auth/login': () => [200, { access_token: 'token-de-prueba', token_type: 'bearer', usuario }],
  'GET /me': () => [200, usuario],
  'GET /repuestos': () => [200, repuestos],
  'GET /repuestos/codigo/RP-2048': () => [200, repuestos[0]],
  'GET /repuestos/codigo/NO-EXISTE': () => [404, { detail: 'Repuesto no encontrado' }],
  'GET /incidencias': () => [200, [{ id: 7, maquina_id: 1, titulo: 'Pérdida', descripcion: 'Gotea', prioridad: 'alta', estado: 'en_reparacion', turno: 'tarde', reportada_en: new Date().toISOString(), reportada_por_id: 1 }]],
  'GET /maquinas': () => [200, [{ id: 1, codigo: 'MAQ-F04', nombre: 'Fraccionadora F-04', tipo: 'fraccionador', estado: 'operativa', repuestos: [] }]],
  'GET /reparaciones': () => [200, [{ id: 5, tipo: 'correctiva', descripcion: 'Cambio de sello', incidencia_id: 7, estado: 'abierta' }]],
  'GET /movimientos?limite=6': () => [200, []],
  'POST /reparaciones/5/usos': (body) => {
    const { cantidad } = body as { cantidad: number }
    repuestos = [repuesto(1, 'RP-2048', 'Sello mecánico 32 mm', 4 - cantidad, 0, 1), repuestos[1]]
    return [201, {}]
  },
}

beforeEach(() => {
  setToken(null)
  enviados.length = 0
  repuestos = [repuesto(1, 'RP-2048', 'Sello mecánico 32 mm', 4, 0, 1), repuesto(2, 'IN-4421', 'Filtro HEPA H14', 8, 1, 2)]
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
    const method = init.method ?? 'GET'
    const path = url.replace(/^\/api/, '')
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body
    enviados.push({ method, path, body })
    const handler = rutas[`${method} ${path}`]
    const [status, data] = handler ? handler(body) : [404, { detail: `Sin ruta simulada: ${method} ${path}` }]
    return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

async function ingresar() {
  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText('Usuario'), 'encargado')
  await user.type(screen.getByLabelText('Contraseña'), 'planta123')
  await user.click(screen.getByRole('button', { name: /ingresar/i }))
  await screen.findByText('Hola, Encargado Demo.')
  return user
}

describe('Planta en orden', () => {
  it('pide iniciar sesión y usa el token en las llamadas siguientes', async () => {
    await ingresar()

    const login = enviados.find((call) => call.path === '/auth/login')
    expect(login?.body).toBeInstanceOf(URLSearchParams)
    const llamadaConToken = vi.mocked(fetch).mock.calls.find(([url]) => url === '/api/repuestos')
    expect((llamadaConToken?.[1]?.headers as Record<string, string>).Authorization).toBe('Bearer token-de-prueba')
  })

  it('permite buscar un repuesto en el inventario', async () => {
    const user = await ingresar()

    await user.click(screen.getAllByRole('button', { name: 'Inventario' })[0])
    const search = screen.getByRole('searchbox', { name: 'Buscar repuestos' })
    await user.type(search, 'HEPA')

    expect(screen.getByText('Filtro HEPA H14')).toBeInTheDocument()
    expect(screen.queryByText('Sello mecánico 32 mm')).not.toBeInTheDocument()
  })

  it('escanea un código, registra el uso en la reparación elegida y refresca el stock', async () => {
    const user = await ingresar()

    await user.click(screen.getAllByRole('button', { name: /escanear repuesto/i })[0])
    await user.type(screen.getByLabelText(/escribí el código/i), 'rp-2048')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(await screen.findByText('Confirmar salida')).toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).getByRole('combobox')).toHaveDisplayValue('#5 · INC-7 · Fraccionadora F-04')
    await user.click(screen.getByRole('button', { name: 'Sumar una unidad' }))
    await user.click(screen.getByRole('button', { name: /confirmar y descontar stock/i }))

    expect(await screen.findByText('Stock actualizado')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Uso registrado')
    expect(enviados.find((call) => call.path === '/reparaciones/5/usos')?.body).toEqual({ repuesto_codigo: 'RP-2048', cantidad: 2 })
    await waitFor(() => expect(enviados.filter((call) => call.path === '/repuestos')).toHaveLength(2))
  })

  it('muestra el error del backend cuando el código no existe', async () => {
    const user = await ingresar()

    await user.click(screen.getAllByRole('button', { name: /escanear repuesto/i })[0])
    await user.type(screen.getByLabelText(/escribí el código/i), 'no-existe')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Repuesto no encontrado')
  })
})
