import { ClipboardList, PackageCheck, Send, ShoppingCart, UserCheck } from 'lucide-react'
import { FormEvent, ReactNode, useCallback, useEffect, useState } from 'react'
import {
  api,
  type ItemListaCompras,
  type NuevoRequerimiento,
  type Part,
  type Pedido,
  type Usuario,
} from './api'

const ORIGEN: Record<ItemListaCompras['origen'], string> = {
  umbral: 'Bajo umbral',
  especifico: 'Requerimiento',
  prevision: 'Previsión',
}

const ESTADO_PEDIDO: Record<Pedido['estado'], string> = {
  pendiente: 'Pendiente de recepción',
  recibido: 'Recibido · a supervisar',
  verificado: 'Verificado',
}

function Card({ title, subtitle, icon, children }: { title: string; subtitle: string; icon: ReactNode; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-[0_8px_30px_rgba(23,49,79,0.035)]">
      <div className="flex items-center gap-3 border-b border-line px-5 py-4 sm:px-6">
        <span className="grid size-9 place-items-center rounded-xl bg-cloud text-steel [&>svg]:size-[17px]">{icon}</span>
        <div>
          <h3 className="font-bold tracking-[-0.02em] text-navy">{title}</h3>
          <p className="mt-0.5 text-xs text-slate">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  )
}

const button = 'inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2.5 text-xs font-extrabold transition disabled:cursor-not-allowed disabled:opacity-50'

export default function Compras({
  user,
  parts,
  onChanged,
  onError,
  onNotice,
}: {
  user: Usuario
  parts: Part[]
  onChanged: () => Promise<void>
  onError: (error: unknown) => void
  onNotice: (title: string, detail: string) => void
}) {
  const isManager = user.rol === 'encargado'
  const canSeeList = isManager || user.rol === 'gerencia'
  const canOrder = isManager || user.rol === 'mantenimiento'

  const [items, setItems] = useState<ItemListaCompras[]>([])
  const [orders, setOrders] = useState<Pedido[]>([])
  const [delegates, setDelegates] = useState<Usuario[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [urgency, setUrgency] = useState<Pedido['urgencia']>('normal')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const [list, pedidos, users] = await Promise.all([
      canSeeList ? api.listaCompras() : Promise.resolve([]),
      api.pedidos(),
      isManager ? api.delegables() : Promise.resolve([]),
    ])
    setItems(list)
    setOrders(pedidos)
    setDelegates(users)
    setSelected(new Set())
  }, [canSeeList, isManager])

  useEffect(() => {
    load().catch(onError)
  }, [load, onError])

  const run = async (action: () => Promise<unknown>, title: string, detail: string) => {
    setBusy(true)
    try {
      await action()
      await Promise.all([load(), onChanged()])
      onNotice(title, detail)
      return true
    } catch (error) {
      onError(error)
      return false
    } finally {
      setBusy(false)
    }
  }

  const itemKey = (item: ItemListaCompras) => item.requerimiento_id ? `r${item.requerimiento_id}` : `u${item.repuesto.id}`
  const partName = (id: number) => parts.find((part) => part.id === id)?.name ?? `Repuesto ${id}`
  const userName = (id: number | null) => {
    if (id === null) return ''
    if (id === user.id) return 'vos'
    return delegates.find((item) => item.id === id)?.nombre ?? `usuario ${id}`
  }

  const toggle = (key: string) => {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const orderFromList = () => {
    const chosen = items.filter((item) => selected.has(itemKey(item)))
    const quantities = new Map<number, number>()
    chosen.forEach((item) => quantities.set(item.repuesto.id, (quantities.get(item.repuesto.id) ?? 0) + item.cantidad_sugerida))
    return run(
      () =>
        api.crearPedido({
          urgencia: urgency,
          lineas: [...quantities].map(([repuesto_id, cantidad]) => ({ repuesto_id, cantidad })),
          requerimiento_ids: chosen.flatMap((item) => (item.requerimiento_id ? [item.requerimiento_id] : [])),
        }),
      'Pedido de compra generado',
      'Se notificó a los encargados y a la gerencia.',
    )
  }

  return (
    <section aria-labelledby="purchases-title">
      <div className="mb-6">
        <p className="mb-1 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-steel">Reposición · Recepción</p>
        <h2 id="purchases-title" className="text-2xl font-extrabold tracking-[-0.045em] text-navy sm:text-[2rem]">Compras</h2>
        <p className="mt-1.5 text-sm text-slate">Lista de compras, pedidos y recepción de lo comprado.</p>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-5">
          {canSeeList && (
            <Card title="Lista de compras" subtitle="Bajo umbral + requerimientos cargados por el encargado" icon={<ShoppingCart />}>
              <div className="divide-y divide-line/70">
                {items.length === 0 && <p className="px-6 py-10 text-center text-sm text-slate">No hay nada para comprar.</p>}
                {items.map((item) => (
                  <label key={itemKey(item)} className="flex items-start gap-3 px-5 py-3.5 sm:px-6">
                    {isManager && (
                      <input type="checkbox" checked={selected.has(itemKey(item))} onChange={() => toggle(itemKey(item))} className="mt-1 size-4 accent-teal" aria-label={`Incluir ${item.repuesto.nombre}`} />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-navy">{item.repuesto.nombre}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide ${item.origen === 'umbral' ? 'bg-amber/15 text-amber-dark' : 'bg-steel/10 text-steel'}`}>{ORIGEN[item.origen]}</span>
                      </span>
                      <span className="mt-1 block text-xs text-slate">{item.repuesto.codigo} · {item.motivo}</span>
                    </span>
                    <span className="text-right font-mono text-sm text-navy">{item.cantidad_sugerida} u</span>
                  </label>
                ))}
              </div>
              {isManager && items.length > 0 && (
                <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-cloud/55 px-5 py-3">
                  <select aria-label="Urgencia del pedido" value={urgency} onChange={(event) => setUrgency(event.target.value as Pedido['urgencia'])} className="h-10 rounded-xl border border-line bg-white px-3 text-xs font-bold text-navy">
                    <option value="normal">Urgencia normal</option>
                    <option value="urgente">Urgente</option>
                  </select>
                  <button type="button" disabled={busy || selected.size === 0} onClick={orderFromList} className={`${button} bg-navy text-white hover:bg-steel`}>
                    <Send size={15} /> Generar pedido ({selected.size})
                  </button>
                </div>
              )}
            </Card>
          )}

          <Card title="Pedidos de compra" subtitle="Recepción, delegación y supervisión (RN-08)" icon={<PackageCheck />}>
            <div className="divide-y divide-line/70">
              {orders.length === 0 && <p className="px-6 py-10 text-center text-sm text-slate">Todavía no hay pedidos.</p>}
              {orders.map((order) => (
                <OrderRow
                  key={order.id}
                  order={order}
                  user={user}
                  delegates={delegates}
                  busy={busy}
                  partName={partName}
                  userName={userName}
                  parts={parts}
                  run={run}
                />
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-5">
          {canOrder && <ShortageForm parts={parts} busy={busy} run={run} />}
          {isManager && <RequirementForm parts={parts} busy={busy} run={run} />}
        </div>
      </div>
    </section>
  )
}

type Run = (action: () => Promise<unknown>, title: string, detail: string) => Promise<boolean>

function OrderRow({
  order,
  user,
  delegates,
  busy,
  partName,
  userName,
  parts,
  run,
}: {
  order: Pedido
  user: Usuario
  delegates: Usuario[]
  busy: boolean
  partName: (id: number) => string
  userName: (id: number | null) => string
  parts: Part[]
  run: Run
}) {
  const isManager = user.rol === 'encargado'
  const canReceive = order.estado === 'pendiente' && (isManager || order.delegado_a_id === user.id)
  const [delegate, setDelegate] = useState<number | ''>('')
  const [receiving, setReceiving] = useState(false)
  const [locations, setLocations] = useState<Record<number, string>>({})

  const receive = async (event: FormEvent) => {
    event.preventDefault()
    const ok = await run(
      () =>
        api.recibirPedido(
          order.id,
          order.lineas.map((line) => ({
            repuesto_id: line.repuesto_id,
            cantidad: line.cantidad,
            ubicacion_codigo: (locations[line.id] ?? parts.find((part) => part.id === line.repuesto_id)?.location ?? '').toUpperCase(),
          })),
        ),
      'Recepción registrada',
      `El stock del pedido #${order.id} ya está cargado.`,
    )
    if (ok) setReceiving(false)
  }

  return (
    <article className="px-5 py-4 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-steel">Pedido #{order.id}</span>
          {order.urgencia === 'urgente' && <span className="rounded-full bg-coral/10 px-2 py-0.5 text-[0.6rem] font-bold uppercase text-coral">Urgente</span>}
        </div>
        <span className={`rounded-full px-3 py-1 text-[0.65rem] font-bold ${order.estado === 'verificado' ? 'bg-mint/55 text-teal-dark' : order.estado === 'recibido' ? 'bg-steel/10 text-steel' : 'bg-amber/15 text-amber-dark'}`}>{ESTADO_PEDIDO[order.estado]}</span>
      </div>
      <ul className="mt-2 text-sm text-navy">
        {order.lineas.map((line) => <li key={line.id}>{line.cantidad} × {partName(line.repuesto_id)}</li>)}
      </ul>
      <p className="mt-1.5 text-xs text-slate">
        {order.delegado_a_id !== null && `Recepción delegada en ${userName(order.delegado_a_id)}. `}
        {order.recibido_por_id !== null && `Recibió ${userName(order.recibido_por_id)}. `}
        {order.verificado_por_id !== null && `Verificó ${userName(order.verificado_por_id)}.`}
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {isManager && order.estado === 'pendiente' && (
          <>
            <select aria-label={`Delegar recepción del pedido ${order.id}`} value={delegate} onChange={(event) => setDelegate(Number(event.target.value))} className="h-9 rounded-xl border border-line bg-white px-2 text-xs text-navy">
              <option value="">Delegar en…</option>
              {delegates.filter((item) => item.id !== user.id).map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
            </select>
            <button type="button" disabled={busy || delegate === ''} onClick={() => run(() => api.delegarRecepcion(order.id, Number(delegate)), 'Recepción delegada', `Se avisó por correo a quien recibe el pedido #${order.id}.`)} className={`${button} border border-line text-navy hover:bg-cloud`}>
              <UserCheck size={15} /> Delegar
            </button>
          </>
        )}
        {canReceive && !receiving && (
          <button type="button" onClick={() => setReceiving(true)} className={`${button} bg-teal text-navy hover:bg-[#20b7a4]`}>
            <PackageCheck size={15} /> Registrar recepción
          </button>
        )}
        {isManager && order.estado === 'recibido' && (
          <button type="button" disabled={busy} onClick={() => run(() => api.verificarRecepcion(order.id), 'Recepción verificada', `El pedido #${order.id} quedó supervisado.`)} className={`${button} bg-navy text-white hover:bg-steel`}>
            <ClipboardList size={15} /> Verificar recepción
          </button>
        )}
      </div>

      {receiving && (
        <form onSubmit={receive} className="mt-3 space-y-2 rounded-xl border border-line bg-cloud/45 p-3">
          {order.lineas.map((line) => (
            <label key={line.id} className="flex items-center justify-between gap-3 text-xs text-navy">
              <span>{line.cantidad} × {partName(line.repuesto_id)}</span>
              <input
                required
                aria-label={`Ubicación de ${partName(line.repuesto_id)}`}
                pattern="[A-Za-z0-9]+(-[A-Za-z0-9]+)*"
                placeholder="A-03-12"
                defaultValue={parts.find((part) => part.id === line.repuesto_id)?.location.replace('Sin ubicación', '')}
                onChange={(event) => setLocations((current) => ({ ...current, [line.id]: event.target.value }))}
                className="form-control h-9 w-32 font-mono uppercase"
              />
            </label>
          ))}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setReceiving(false)} className={`${button} text-slate hover:text-navy`}>Cancelar</button>
            <button type="submit" disabled={busy} className={`${button} bg-teal text-navy hover:bg-[#20b7a4]`}>Guardar recepción</button>
          </div>
        </form>
      )}
    </article>
  )
}

function PartSelect({ parts, value, onChange, id }: { parts: Part[]; value: number | ''; onChange: (id: number) => void; id: string }) {
  return (
    <select id={id} required value={value} onChange={(event) => onChange(Number(event.target.value))} className="form-control">
      <option value="">Seleccionar repuesto</option>
      {parts.map((part) => <option key={part.id} value={part.id}>{part.code} · {part.name}</option>)}
    </select>
  )
}

function ShortageForm({ parts, busy, run }: { parts: Part[]; busy: boolean; run: Run }) {
  const [partId, setPartId] = useState<number | ''>('')
  const [quantity, setQuantity] = useState(1)
  const [urgency, setUrgency] = useState<Pedido['urgencia']>('normal')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (partId === '') return
    const ok = await run(
      () => api.crearPedido({ urgencia: urgency, lineas: [{ repuesto_id: partId, cantidad: quantity }], observaciones: 'Faltante reportado' }),
      'Pedido de compra generado',
      'Se notificó a los encargados de todos los turnos y a la gerencia.',
    )
    if (ok) {
      setPartId('')
      setQuantity(1)
    }
  }

  return (
    <Card title="Reportar faltante" subtitle="Genera un pedido de compra (RN-03, RN-04)" icon={<Send />}>
      <form onSubmit={submit} className="space-y-4 p-5 sm:p-6">
        <div><label htmlFor="shortage-part" className="form-label">Repuesto *</label><PartSelect id="shortage-part" parts={parts} value={partId} onChange={setPartId} /></div>
        <div className="grid grid-cols-2 gap-3">
          <label><span className="form-label">Cantidad</span><input type="number" min={1} required value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} className="form-control" /></label>
          <label><span className="form-label">Urgencia</span>
            <select value={urgency} onChange={(event) => setUrgency(event.target.value as Pedido['urgencia'])} className="form-control">
              <option value="normal">Normal</option>
              <option value="urgente">Urgente</option>
            </select>
          </label>
        </div>
        <button type="submit" disabled={busy} className={`${button} w-full bg-navy py-3 text-white hover:bg-steel`}>Generar pedido de compra</button>
      </form>
    </Card>
  )
}

function RequirementForm({ parts, busy, run }: { parts: Part[]; busy: boolean; run: Run }) {
  const empty: Omit<NuevoRequerimiento, 'repuesto_id'> & { repuesto_id: number | '' } = { repuesto_id: '', cantidad: 1, origen: 'especifico', motivo: '' }
  const [data, setData] = useState(empty)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (data.repuesto_id === '') return
    const payload = { ...data, repuesto_id: data.repuesto_id }
    if (await run(() => api.crearRequerimiento(payload), 'Requerimiento agregado', 'Ya figura en la lista de compras.')) setData(empty)
  }

  return (
    <Card title="Agregar a la lista de compras" subtitle="Requerimiento específico o previsión de necesidades" icon={<ClipboardList />}>
      <form onSubmit={submit} className="space-y-4 p-5 sm:p-6">
        <div><label htmlFor="req-part" className="form-label">Repuesto *</label><PartSelect id="req-part" parts={parts} value={data.repuesto_id} onChange={(repuesto_id) => setData({ ...data, repuesto_id })} /></div>
        <div className="grid grid-cols-2 gap-3">
          <label><span className="form-label">Cantidad</span><input type="number" min={1} required value={data.cantidad} onChange={(event) => setData({ ...data, cantidad: Number(event.target.value) })} className="form-control" /></label>
          <label><span className="form-label">Tipo</span>
            <select value={data.origen} onChange={(event) => setData({ ...data, origen: event.target.value as NuevoRequerimiento['origen'] })} className="form-control">
              <option value="especifico">Requerimiento específico</option>
              <option value="prevision">Previsión</option>
            </select>
          </label>
        </div>
        <label className="block"><span className="form-label">Motivo *</span><input required value={data.motivo} onChange={(event) => setData({ ...data, motivo: event.target.value })} placeholder="Ej. Parada anual de planta" className="form-control" /></label>
        <button type="submit" disabled={busy} className={`${button} w-full bg-navy py-3 text-white hover:bg-steel`}>Agregar requerimiento</button>
      </form>
    </Card>
  )
}
