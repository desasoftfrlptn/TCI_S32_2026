// Cliente de la API. Vite redirige /api al backend (ver vite.config.ts).

export type Rol = 'operario' | 'mantenimiento' | 'encargado' | 'gerencia'

export type Usuario = { id: number; usuario: string; nombre: string; email: string; rol: Rol }

// Autenticación: el token JWT se guarda en el navegador y viaja como Bearer.
const CLAVE_TOKEN = 'planta.token'

function leerToken() {
  try {
    return localStorage.getItem(CLAVE_TOKEN)
  } catch {
    return null
  }
}

let token = leerToken()

export function hayToken() {
  return Boolean(token)
}

export function setToken(nuevo: string | null) {
  token = nuevo
  try {
    if (nuevo) localStorage.setItem(CLAVE_TOKEN, nuevo)
    else localStorage.removeItem(CLAVE_TOKEN)
  } catch {
    // sin almacenamiento: la sesión dura lo que la pestaña
  }
}

// La app se suscribe para volver al login cuando el token vence.
let alVencerSesion: () => void = () => {}
export function onSesionVencida(handler: () => void) {
  alVencerSesion = handler
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

function mensajeDeError(status: number, cuerpo: unknown): string {
  const detail = (cuerpo as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return `Dato inválido: ${detail[0].msg}`
  return `Error ${status} al comunicarse con el servidor`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
  if (typeof init.body === 'string') headers['Content-Type'] = 'application/json'
  const res = await fetch(`/api${path}`, { ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } })
  const cuerpo = await res.json().catch(() => null)
  if (res.status === 401 && token) {
    setToken(null)
    alVencerSesion()
  }
  if (!res.ok) throw new ApiError(res.status, mensajeDeError(res.status, cuerpo))
  return cuerpo as T
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })

// --- Tipos de la API -----------------------------------------------------------

export type Referencia = { id: number; codigo: string; nombre: string }

export type RepuestoApi = {
  id: number
  codigo: string
  nombre: string
  descripcion: string
  stock_fisico: number
  stock_reservado: number
  stock_disponible: number
  umbral_minimo: number
  bajo_umbral: boolean
  ubicacion_codigo: string | null
  ubicacion_descripcion: string | null
  maquinas: Referencia[]
}

export type Maquina = { id: number; codigo: string; nombre: string; tipo: string; estado: string; repuestos: Referencia[] }

export type IncidenciaApi = {
  id: number
  maquina_id: number
  titulo: string
  descripcion: string
  prioridad: 'baja' | 'media' | 'alta'
  estado: 'abierta' | 'en_reparacion' | 'resuelta'
  turno: 'mañana' | 'tarde' | 'noche'
  reportada_en: string
  reportada_por_id: number
}

export type Reparacion = {
  id: number
  tipo: 'correctiva' | 'preventiva'
  descripcion: string
  incidencia_id: number | null
  estado: 'abierta' | 'finalizada'
}

export type Movimiento = {
  id: number
  repuesto_id: number
  tipo: 'entrada' | 'salida' | 'reserva' | 'liberacion' | 'consumo'
  cantidad: number
  fecha: string
  usuario_id: number
  referencia: string
}

export type Sesion = { access_token: string; token_type: string; usuario: Usuario }

export type ItemListaCompras = {
  origen: 'umbral' | 'especifico' | 'prevision'
  repuesto: RepuestoApi
  cantidad_sugerida: number
  motivo: string
  requerimiento_id: number | null
}

export type Pedido = {
  id: number
  urgencia: 'normal' | 'urgente'
  estado: 'pendiente' | 'recibido' | 'verificado'
  observaciones: string
  creado_en: string
  creado_por_id: number
  delegado_a_id: number | null
  recibido_por_id: number | null
  recibido_en: string | null
  verificado_por_id: number | null
  verificado_en: string | null
  lineas: { id: number; repuesto_id: number; cantidad: number }[]
}

export type NuevoPedido = {
  urgencia: Pedido['urgencia']
  observaciones?: string
  lineas: { repuesto_id: number; cantidad: number }[]
  requerimiento_ids?: number[]
}

export type NuevoRequerimiento = { repuesto_id: number; cantidad: number; origen: 'especifico' | 'prevision'; motivo: string }

export type LineaRecepcion = { repuesto_id: number; cantidad: number; ubicacion_codigo: string }

export type NuevaIncidencia = { maquina_codigo: string; titulo: string; descripcion: string; prioridad: IncidenciaApi['prioridad'] }

// --- Endpoints -----------------------------------------------------------------

function fotoForm(foto: File) {
  const form = new FormData()
  form.append('foto', foto)
  return form
}

export const api = {
  login: (usuario: string, password: string) =>
    request<Sesion>('/auth/login', {
      method: 'POST',
      body: new URLSearchParams({ username: usuario, password }),
    }),
  yo: () => request<Usuario>('/me'),
  delegables: () => request<Usuario[]>('/usuarios/delegables'),
  repuestos: () => request<RepuestoApi[]>('/repuestos'),
  repuestoPorCodigo: (codigo: string) => request<RepuestoApi>(`/repuestos/codigo/${encodeURIComponent(codigo)}`),
  reconocerRepuesto: (foto: File) => request<RepuestoApi>('/repuestos/reconocer', { method: 'POST', body: fotoForm(foto) }),
  movimientosDeRepuesto: (id: number) => request<Movimiento[]>(`/repuestos/${id}/movimientos`),
  movimientosRecientes: (limite = 6) => request<Movimiento[]>(`/movimientos?limite=${limite}`),
  ingresarStock: (id: number, cantidad: number, ubicacion_codigo: string) =>
    post<RepuestoApi>(`/repuestos/${id}/ingresos`, { cantidad, ubicacion_codigo }),
  maquinas: () => request<Maquina[]>('/maquinas'),
  incidencias: () => request<IncidenciaApi[]>('/incidencias'),
  reportarIncidencia: (datos: NuevaIncidencia) => post<IncidenciaApi>('/incidencias', datos),
  subirFoto: (incidenciaId: number, foto: File) =>
    request<unknown>(`/incidencias/${incidenciaId}/fotos`, { method: 'POST', body: fotoForm(foto) }),
  reparaciones: () => request<Reparacion[]>('/reparaciones'),
  iniciarReparacion: (incidencia_id: number, descripcion: string) =>
    post<Reparacion>('/reparaciones', { tipo: 'correctiva', incidencia_id, descripcion }),
  registrarUso: (reparacionId: number, repuesto_codigo: string, cantidad: number) =>
    post<unknown>(`/reparaciones/${reparacionId}/usos`, { repuesto_codigo, cantidad }),
  listaCompras: () => request<ItemListaCompras[]>('/lista-compras'),
  crearRequerimiento: (datos: NuevoRequerimiento) => post<unknown>('/requerimientos', datos),
  pedidos: () => request<Pedido[]>('/pedidos'),
  crearPedido: (datos: NuevoPedido) => post<Pedido>('/pedidos', datos),
  delegarRecepcion: (pedidoId: number, usuario_id: number) => post<Pedido>(`/pedidos/${pedidoId}/delegar`, { usuario_id }),
  recibirPedido: (pedidoId: number, lineas: LineaRecepcion[]) => post<Pedido>(`/pedidos/${pedidoId}/recepcion`, { lineas }),
  verificarRecepcion: (pedidoId: number) => request<Pedido>(`/pedidos/${pedidoId}/verificar`, { method: 'POST' }),
}

// --- Adaptación a los modelos de la vista --------------------------------------

export type Part = {
  id: number
  code: string
  name: string
  description: string
  physical: number
  reserved: number
  minimum: number
  location: string
  locationDetail: string
  machines: string[]
}

export type Incident = {
  id: number
  machine: string
  machineCode: string
  title: string
  description: string
  priority: 'Alta' | 'Media' | 'Baja'
  status: 'Abierta' | 'En reparación' | 'Resuelta'
  shift: 'Mañana' | 'Tarde' | 'Noche'
  reportedAt: string
}

export function toPart(r: RepuestoApi): Part {
  return {
    id: r.id,
    code: r.codigo,
    name: r.nombre,
    description: r.descripcion,
    physical: r.stock_fisico,
    reserved: r.stock_reservado,
    minimum: r.umbral_minimo,
    location: r.ubicacion_codigo ?? 'Sin ubicación',
    locationDetail: r.ubicacion_descripcion ?? r.ubicacion_codigo ?? 'Sin ubicación asignada',
    machines: r.maquinas.map((m) => m.nombre),
  }
}

const PRIORIDAD = { alta: 'Alta', media: 'Media', baja: 'Baja' } as const
const ESTADO = { abierta: 'Abierta', en_reparacion: 'En reparación', resuelta: 'Resuelta' } as const
const TURNO = { mañana: 'Mañana', tarde: 'Tarde', noche: 'Noche' } as const

export function toIncident(i: IncidenciaApi, maquinas: Maquina[]): Incident {
  const maquina = maquinas.find((m) => m.id === i.maquina_id)
  return {
    id: i.id,
    machine: maquina?.nombre ?? `Máquina ${i.maquina_id}`,
    machineCode: maquina?.codigo ?? '',
    title: i.titulo,
    description: i.descripcion,
    priority: PRIORIDAD[i.prioridad],
    status: ESTADO[i.estado],
    shift: TURNO[i.turno],
    reportedAt: i.reportada_en,
  }
}
