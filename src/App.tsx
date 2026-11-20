import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Barcode,
  Bell,
  Boxes,
  Camera,
  Check,
  ChevronRight,
  CircleAlert,
  ClipboardPlus,
  Clock3,
  Factory,
  FileText,
  Filter,
  Gauge,
  History,
  LayoutDashboard,
  MapPin,
  Minus,
  PackageCheck,
  Plus,
  QrCode,
  ScanLine,
  Search,
  ShieldCheck,
  Upload,
  Wrench,
  X,
} from 'lucide-react'
import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react'
import { initialIncidents, initialParts, recentMovements, type Incident, type Part } from './data'

type View = 'dashboard' | 'inventory' | 'incidents'
type Toast = { title: string; detail: string } | null

const navItems: { id: View; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'Tablero', icon: LayoutDashboard },
  { id: 'inventory', label: 'Inventario', icon: Boxes },
  { id: 'incidents', label: 'Incidencias', icon: Wrench },
]

function available(part: Part) {
  return part.physical - part.reserved
}

function isLow(part: Part) {
  return available(part) <= part.minimum
}

function App() {
  const [view, setView] = useState<View>('dashboard')
  const [parts, setParts] = useState(initialParts)
  const [incidents, setIncidents] = useState(initialIncidents)
  const [scanOpen, setScanOpen] = useState(false)
  const [selectedPartId, setSelectedPartId] = useState<string | null>(null)
  const [toast, setToast] = useState<Toast>(null)

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(null), 4200)
    return () => window.clearTimeout(timeout)
  }, [toast])

  const selectedPart = parts.find((part) => part.id === selectedPartId) ?? null

  const registerUse = (partId: string, quantity: number) => {
    setParts((current) =>
      current.map((part) =>
        part.id === partId
          ? { ...part, physical: part.physical - quantity, lastMovement: 'Ahora' }
          : part,
      ),
    )
    setToast({
      title: 'Uso registrado',
      detail: `Se descontaron ${quantity} ${quantity === 1 ? 'unidad' : 'unidades'} del stock físico.`,
    })
  }

  const addStock = (partId: string, quantity: number, location: string) => {
    setParts((current) =>
      current.map((part) =>
        part.id === partId
          ? {
              ...part,
              physical: part.physical + quantity,
              location: location || part.location,
              lastMovement: 'Ahora',
            }
          : part,
      ),
    )
    setToast({
      title: 'Ingreso guardado',
      detail: `${quantity} ${quantity === 1 ? 'unidad cargada' : 'unidades cargadas'} al inventario.`,
    })
  }

  const addIncident = (incident: Incident) => {
    setIncidents((current) => [incident, ...current])
    setToast({ title: 'Incidencia reportada', detail: `${incident.id} se notificó al equipo de mantenimiento.` })
  }

  return (
    <div className="min-h-dvh bg-canvas text-ink selection:bg-teal/20">
      <Sidebar view={view} onNavigate={setView} onScan={() => setScanOpen(true)} />

      <div className="min-h-dvh lg:pl-[17rem]">
        <TopBar view={view} onScan={() => setScanOpen(true)} />

        <main id="main-content" className="mx-auto w-full max-w-[1560px] px-4 pb-28 pt-5 sm:px-6 lg:px-9 lg:pb-10 lg:pt-8">
          <div key={view} className="page-enter">
            {view === 'dashboard' && (
              <Dashboard
                parts={parts}
                incidents={incidents}
                onNavigate={setView}
                onSelectPart={setSelectedPartId}
                onScan={() => setScanOpen(true)}
              />
            )}
            {view === 'inventory' && (
              <Inventory parts={parts} onSelectPart={setSelectedPartId} onScan={() => setScanOpen(true)} />
            )}
            {view === 'incidents' && <Incidents incidents={incidents} onAdd={addIncident} />}
          </div>
        </main>
      </div>

      <MobileNav view={view} onNavigate={setView} onScan={() => setScanOpen(true)} />

      <ScanPanel
        open={scanOpen}
        parts={parts}
        onClose={() => setScanOpen(false)}
        onRegister={registerUse}
      />

      <PartPanel
        part={selectedPart}
        onClose={() => setSelectedPartId(null)}
        onAddStock={addStock}
      />

      {toast && <ToastMessage toast={toast} onClose={() => setToast(null)} />}
    </div>
  )
}

function Sidebar({
  view,
  onNavigate,
  onScan,
}: {
  view: View
  onNavigate: (view: View) => void
  onScan: () => void
}) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[17rem] flex-col overflow-hidden bg-navy text-white lg:flex">
      <div className="pointer-events-none absolute inset-0 opacity-[0.06] blueprint-grid" />
      <div className="relative flex h-[5.25rem] items-center gap-3 border-b border-white/10 px-7">
        <LogoMark />
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.19em] text-mint/80">Mantenimiento</p>
          <p className="text-[1.06rem] font-semibold tracking-[-0.025em]">Planta en orden</p>
        </div>
      </div>

      <nav aria-label="Navegación principal" className="relative flex-1 px-4 py-7">
        <p className="mb-3 px-3 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-white/35">Operación</p>
        <div className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = view === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                aria-current={active ? 'page' : undefined}
                className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${
                  active ? 'bg-white text-navy shadow-sm' : 'text-white/65 hover:bg-white/8 hover:text-white'
                }`}
              >
                <span className={`grid size-8 place-items-center rounded-lg ${active ? 'bg-mint/45 text-navy' : 'bg-white/8'}`}>
                  <Icon size={17} strokeWidth={2.1} />
                </span>
                {item.label}
                {active && <span className="ml-auto size-1.5 rounded-full bg-teal" />}
              </button>
            )
          })}
        </div>

        <div className="my-7 h-px bg-white/10" />

        <button
          type="button"
          onClick={onScan}
          className="group relative w-full overflow-hidden rounded-2xl bg-teal px-4 py-4 text-left text-navy shadow-[0_14px_30px_rgba(25,168,150,0.18)] transition hover:-translate-y-0.5 hover:bg-[#20b7a4]"
        >
          <span className="absolute -right-4 -top-5 size-20 rounded-full border border-navy/10" />
          <ScanLine className="mb-7" size={24} />
          <span className="block text-base font-bold tracking-[-0.02em]">Escanear repuesto</span>
          <span className="mt-1 block text-xs font-medium text-navy/65">Registrar uso en segundos</span>
          <ArrowRight className="absolute bottom-4 right-4 transition-transform group-hover:translate-x-1" size={18} />
        </button>
      </nav>

      <div className="relative border-t border-white/10 p-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2">
          <span className="grid size-9 place-items-center rounded-full bg-[#dcebe8] text-xs font-bold text-navy">ML</span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">Marina López</p>
            <p className="truncate text-xs text-white/45">Mantenimiento · Mañana</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

function TopBar({ view, onScan }: { view: View; onScan: () => void }) {
  const labels: Record<View, string> = {
    dashboard: 'Centro de operación',
    inventory: 'Inventario de repuestos',
    incidents: 'Gestión de incidencias',
  }

  return (
    <header className="sticky top-0 z-20 flex h-[4.5rem] items-center justify-between border-b border-line/80 bg-canvas/90 px-4 backdrop-blur-xl sm:px-6 lg:h-[5.25rem] lg:px-9">
      <div className="flex items-center gap-3">
        <div className="lg:hidden"><LogoMark dark /></div>
        <div>
          <p className="text-[0.63rem] font-bold uppercase tracking-[0.2em] text-slate">Planta Norte</p>
          <h1 className="text-base font-bold tracking-[-0.025em] text-navy sm:text-lg">{labels[view]}</h1>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-line bg-white px-3 py-2 text-xs font-semibold text-slate sm:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-teal opacity-50" />
            <span className="relative inline-flex size-2 rounded-full bg-teal" />
          </span>
          Turno mañana activo
        </div>
        <button type="button" aria-label="Ver notificaciones" className="relative grid size-10 place-items-center rounded-xl border border-line bg-white text-navy transition hover:border-steel/40">
          <Bell size={18} />
          <span className="absolute right-2 top-2 size-1.5 rounded-full bg-coral ring-2 ring-white" />
        </button>
        <button type="button" onClick={onScan} className="hidden items-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-steel md:flex lg:hidden xl:flex">
          <ScanLine size={17} />
          Escanear
        </button>
      </div>
    </header>
  )
}

function Dashboard({
  parts,
  incidents,
  onNavigate,
  onSelectPart,
  onScan,
}: {
  parts: Part[]
  incidents: Incident[]
  onNavigate: (view: View) => void
  onSelectPart: (id: string) => void
  onScan: () => void
}) {
  const lowParts = parts.filter(isLow)
  const criticalParts = parts.filter((part) => available(part) === 0)

  return (
    <section aria-labelledby="dashboard-title">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-1 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-steel">Lunes 5 de octubre · 09:12</p>
          <h2 id="dashboard-title" className="text-2xl font-extrabold tracking-[-0.045em] text-navy sm:text-[2rem]">Buen día, Marina.</h2>
          <p className="mt-1.5 text-sm text-slate">Esto necesita atención en el turno actual.</p>
        </div>
        <button type="button" onClick={() => onNavigate('incidents')} className="inline-flex w-fit items-center gap-2 text-sm font-bold text-steel transition hover:text-navy">
          Ver todas las incidencias <ArrowRight size={16} />
        </button>
      </div>

      <div className="mb-5 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <div className="plant-line-card relative min-h-[18.5rem] overflow-hidden rounded-[1.6rem] bg-navy p-6 text-white shadow-[0_24px_60px_rgba(23,49,79,0.12)] sm:p-8">
          <div className="pointer-events-none absolute inset-0 opacity-[0.08] blueprint-grid" />
          <div className="relative z-10 flex h-full flex-col justify-between">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/8 px-3 py-1.5 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-mint">
                  <Activity size={13} /> Pulso de planta
                </span>
                <h3 className="max-w-[31rem] text-[1.75rem] font-bold leading-[1.08] tracking-[-0.045em] sm:text-[2.35rem]">
                  Dos frentes abiertos. <span className="text-mint">El stock crítico puede resolverse primero.</span>
                </h3>
              </div>
              <div className="hidden size-16 place-items-center rounded-full border border-white/15 sm:grid">
                <Gauge size={28} className="text-mint" />
              </div>
            </div>

            <div className="mt-9 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div className="flex items-center gap-7">
                <div>
                  <p className="font-mono text-3xl font-medium text-white">{criticalParts.length}</p>
                  <p className="mt-1 text-xs text-white/50">sin disponibilidad</p>
                </div>
                <div className="h-9 w-px bg-white/15" />
                <div>
                  <p className="font-mono text-3xl font-medium text-white">{incidents.filter((item) => item.priority === 'Alta').length}</p>
                  <p className="mt-1 text-xs text-white/50">incidencia prioritaria</p>
                </div>
              </div>
              <button type="button" onClick={onScan} className="inline-flex items-center justify-center gap-2 rounded-xl bg-mint px-4 py-3 text-sm font-extrabold text-navy transition hover:bg-white">
                <ScanLine size={17} /> Registrar uso
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <MetricCard icon={<Boxes />} value={parts.reduce((sum, part) => sum + available(part), 0)} label="Unidades disponibles" hint="6 familias activas" tone="teal" />
          <MetricCard icon={<AlertTriangle />} value={lowParts.length} label="Bajo mínimo" hint="Revisar compras" tone="amber" />
          <MetricCard icon={<Wrench />} value={incidents.length} label="Incidencias activas" hint="1 de prioridad alta" tone="blue" />
          <MetricCard icon={<ShieldCheck />} value="98%" label="Trazabilidad" hint="Últimos 30 días" tone="mint" />
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <Panel className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
            <div>
              <h3 className="font-bold tracking-[-0.02em] text-navy">Stock que requiere atención</h3>
              <p className="mt-0.5 text-xs text-slate">Disponible igual o menor al umbral definido</p>
            </div>
            <button type="button" onClick={() => onNavigate('inventory')} className="grid size-9 place-items-center rounded-lg border border-line text-steel transition hover:bg-cloud" aria-label="Ver inventario">
              <ArrowRight size={16} />
            </button>
          </div>
          <div className="divide-y divide-line/70">
            {lowParts.slice(0, 3).map((part) => (
              <button key={part.id} type="button" onClick={() => onSelectPart(part.id)} className="group flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-cloud/70 sm:px-6">
                <StockIcon part={part} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-bold text-navy">{part.name}</p>
                    {available(part) === 0 && <span className="rounded-full bg-coral/10 px-2 py-0.5 text-[0.62rem] font-bold uppercase tracking-wide text-coral">Sin stock</span>}
                  </div>
                  <p className="mt-1 truncate font-mono text-[0.68rem] text-slate">{part.code} · {part.location}</p>
                </div>
                <div className="text-right">
                  <p className={`font-mono text-lg font-medium ${available(part) === 0 ? 'text-coral' : 'text-amber-dark'}`}>{available(part)}</p>
                  <p className="text-[0.64rem] text-slate">mín. {part.minimum}</p>
                </div>
                <ChevronRight size={16} className="text-slate/40 transition group-hover:translate-x-0.5 group-hover:text-steel" />
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
            <div>
              <h3 className="font-bold tracking-[-0.02em] text-navy">Últimos movimientos</h3>
              <p className="mt-0.5 text-xs text-slate">Trazabilidad del turno</p>
            </div>
            <History size={18} className="text-steel" />
          </div>
          <div className="px-5 py-3 sm:px-6">
            {recentMovements.map((movement, index) => (
              <div key={movement.time} className="relative flex gap-4 py-3.5">
                {index < recentMovements.length - 1 && <span className="absolute left-[0.42rem] top-8 h-[calc(100%-1rem)] w-px bg-line" />}
                <span className={`relative mt-1.5 size-3.5 shrink-0 rounded-full border-[3px] border-white ${movement.kind === 'entrada' ? 'bg-teal' : movement.kind === 'reserva' ? 'bg-steel' : 'bg-amber'}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-bold text-navy">{movement.label}</p>
                    <time className="font-mono text-[0.65rem] text-slate">{movement.time}</time>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate">{movement.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </section>
  )
}

function Inventory({ parts, onSelectPart, onScan }: { parts: Part[]; onSelectPart: (id: string) => void; onScan: () => void }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'low' | 'reserved'>('all')

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return parts.filter((part) => {
      const matchesQuery = !normalized || [part.name, part.code, part.description, part.location, ...part.machines].some((value) => value.toLowerCase().includes(normalized))
      const matchesFilter = filter === 'all' || (filter === 'low' && isLow(part)) || (filter === 'reserved' && part.reserved > 0)
      return matchesQuery && matchesFilter
    })
  }, [filter, parts, query])

  return (
    <section aria-labelledby="inventory-title">
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="mb-1 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-steel">Almacén central · Actualizado ahora</p>
          <h2 id="inventory-title" className="text-2xl font-extrabold tracking-[-0.045em] text-navy sm:text-[2rem]">Inventario de repuestos</h2>
          <p className="mt-1.5 max-w-xl text-sm text-slate">Existencia, reservas y ubicación en una sola vista.</p>
        </div>
        <button type="button" onClick={onScan} className="inline-flex w-fit items-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-steel">
          <Barcode size={17} /> Escanear código
        </button>
      </div>

      <div className="mb-5 grid grid-cols-3 gap-3 sm:max-w-xl">
        <MiniStat label="Repuestos" value={parts.length} />
        <MiniStat label="Bajo mínimo" value={parts.filter(isLow).length} alert />
        <MiniStat label="Reservados" value={parts.filter((part) => part.reserved > 0).length} />
      </div>

      <Panel className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row md:items-center md:justify-between">
          <label className="relative block w-full md:max-w-md">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate" size={17} />
            <span className="sr-only">Buscar repuestos</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por nombre, código, máquina o ubicación"
              className="h-11 w-full rounded-xl border border-line bg-cloud/60 pl-10 pr-4 text-sm text-navy outline-none transition placeholder:text-slate/65 focus:border-teal focus:bg-white focus:ring-3 focus:ring-teal/10"
            />
          </label>
          <div className="flex items-center gap-1 overflow-x-auto rounded-xl bg-cloud p-1" aria-label="Filtros de inventario">
            <Filter size={15} className="ml-2 mr-1 shrink-0 text-slate" />
            {([
              ['all', 'Todos'],
              ['low', 'Bajo mínimo'],
              ['reserved', 'Con reserva'],
            ] as const).map(([id, label]) => (
              <button key={id} type="button" onClick={() => setFilter(id)} aria-pressed={filter === id} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-bold transition ${filter === id ? 'bg-white text-navy shadow-sm' : 'text-slate hover:text-navy'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="hidden grid-cols-[1.7fr_0.62fr_0.62fr_0.7fr_0.95fr_2rem] gap-4 border-b border-line bg-cloud/60 px-6 py-3 text-[0.64rem] font-bold uppercase tracking-[0.12em] text-slate md:grid">
          <span>Repuesto</span><span>Disponible</span><span>Reservado</span><span>Mínimo</span><span>Ubicación</span><span />
        </div>

        <div className="divide-y divide-line/70">
          {filtered.map((part) => (
            <button key={part.id} type="button" onClick={() => onSelectPart(part.id)} className="group block w-full px-4 py-4 text-left transition hover:bg-cloud/65 md:grid md:grid-cols-[1.7fr_0.62fr_0.62fr_0.7fr_0.95fr_2rem] md:items-center md:gap-4 md:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <StockIcon part={part} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-navy">{part.name}</p>
                  <p className="mt-1 truncate font-mono text-[0.66rem] text-slate">{part.code} · {part.machines[0]}</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-2 border-t border-line/70 pt-3 md:mt-0 md:block md:border-0 md:pt-0">
                <MobileLabel label="Disponible" />
                <div className="flex items-center gap-2 md:block">
                  <span className={`font-mono text-base font-medium ${isLow(part) ? (available(part) === 0 ? 'text-coral' : 'text-amber-dark') : 'text-navy'}`}>{available(part)}</span>
                  {isLow(part) && <span className={`inline-block size-1.5 rounded-full md:ml-2 ${available(part) === 0 ? 'bg-coral' : 'bg-amber'}`} />}
                </div>
              </div>
              <div className="mt-4 hidden md:block"><span className="font-mono text-sm text-steel">{part.reserved}</span></div>
              <div className="mt-4 hidden md:block"><span className="font-mono text-sm text-slate">{part.minimum}</span></div>
              <div className="mt-4 hidden items-center gap-1.5 md:flex"><MapPin size={14} className="text-teal" /><span className="font-mono text-xs font-medium text-navy">{part.location}</span></div>
              <ChevronRight size={17} className="hidden text-slate/35 transition group-hover:translate-x-0.5 group-hover:text-steel md:block" />

              <div className="-mt-[1.6rem] ml-[33.333%] grid grid-cols-2 gap-2 md:hidden">
                <div><MobileLabel label="Reservado" /><span className="font-mono text-sm text-steel">{part.reserved}</span></div>
                <div><MobileLabel label="Ubicación" /><span className="font-mono text-xs font-medium text-navy">{part.location}</span></div>
              </div>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="px-6 py-14 text-center">
              <Search className="mx-auto mb-3 text-slate/45" size={30} />
              <p className="font-bold text-navy">No encontramos repuestos</p>
              <p className="mt-1 text-sm text-slate">Probá con otro nombre, código o filtro.</p>
            </div>
          )}
        </div>
        <div className="border-t border-line bg-cloud/55 px-5 py-3 text-xs text-slate">
          Mostrando <strong className="text-navy">{filtered.length}</strong> de {parts.length} repuestos
        </div>
      </Panel>
    </section>
  )
}

function Incidents({ incidents, onAdd }: { incidents: Incident[]; onAdd: (incident: Incident) => void }) {
  const [machine, setMachine] = useState('')
  const [priority, setPriority] = useState<Incident['priority']>('Media')
  const [fileName, setFileName] = useState('')

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const [machineCode, machineName] = machine.split('|')
    const count = incidents.length + 1040
    onAdd({
      id: `INC-${count}`,
      machine: machineName,
      machineCode,
      title: String(form.get('title')),
      description: String(form.get('description')),
      priority,
      status: 'Sin asignar',
      shift: 'Mañana',
      reportedAt: 'Ahora',
    })
    event.currentTarget.reset()
    setMachine('')
    setPriority('Media')
    setFileName('')
  }

  return (
    <section aria-labelledby="incidents-title">
      <div className="mb-6">
        <p className="mb-1 font-mono text-[0.68rem] uppercase tracking-[0.16em] text-steel">Triage · Turno mañana</p>
        <h2 id="incidents-title" className="text-2xl font-extrabold tracking-[-0.045em] text-navy sm:text-[2rem]">Incidencias de planta</h2>
        <p className="mt-1.5 text-sm text-slate">Reportá una falla y seguí el trabajo técnico hasta su resolución.</p>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[0.95fr_1.35fr]">
        <Panel className="overflow-hidden xl:sticky xl:top-[7.25rem]">
          <div className="border-b border-line bg-navy px-5 py-5 text-white sm:px-6">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-mint text-navy"><ClipboardPlus size={20} /></span>
              <div>
                <h3 className="font-bold tracking-[-0.02em]">Reportar una incidencia</h3>
                <p className="mt-0.5 text-xs text-white/55">Los campos marcados son obligatorios</p>
              </div>
            </div>
          </div>
          <form onSubmit={submit} className="space-y-5 p-5 sm:p-6">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="machine" className="form-label">Máquina *</label>
                <button type="button" onClick={() => setMachine('MAQ-F04|Fraccionadora F-04')} className="inline-flex items-center gap-1.5 text-xs font-bold text-steel hover:text-navy"><QrCode size={14} /> Simular escaneo</button>
              </div>
              <select id="machine" required value={machine} onChange={(event) => setMachine(event.target.value)} className="form-control">
                <option value="">Seleccionar máquina</option>
                <option value="MAQ-F04|Fraccionadora F-04">Fraccionadora F-04 · MAQ-F04</option>
                <option value="MAQ-BT03|Banda transportadora BT-03">Banda transportadora BT-03 · MAQ-BT03</option>
                <option value="MAQ-E07|Etiquetadora E-07">Etiquetadora E-07 · MAQ-E07</option>
                <option value="MAQ-C01|Caldera C-01">Caldera C-01 · MAQ-C01</option>
              </select>
            </div>

            <div>
              <label htmlFor="title" className="form-label">¿Qué ocurre? *</label>
              <input id="title" name="title" required maxLength={80} className="form-control" placeholder="Ej. Pérdida en la bomba de dosificación" />
            </div>

            <div>
              <label htmlFor="description" className="form-label">Detalle *</label>
              <textarea id="description" name="description" required rows={3} className="form-control resize-none" placeholder="Describí qué observaste y cuándo comenzó." />
            </div>

            <fieldset>
              <legend className="form-label">Prioridad</legend>
              <div className="grid grid-cols-3 gap-2">
                {(['Baja', 'Media', 'Alta'] as const).map((level) => (
                  <button key={level} type="button" onClick={() => setPriority(level)} aria-pressed={priority === level} className={`rounded-xl border px-3 py-2.5 text-xs font-bold transition ${priority === level ? level === 'Alta' ? 'border-coral bg-coral/8 text-coral' : level === 'Media' ? 'border-amber bg-amber/10 text-amber-dark' : 'border-teal bg-teal/8 text-teal-dark' : 'border-line text-slate hover:border-steel/35'}`}>
                    {level}
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <span className="form-label">Foto</span>
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-steel/35 bg-cloud/55 p-3.5 transition hover:border-teal hover:bg-mint/20">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-white text-steel shadow-sm"><Camera size={17} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-bold text-navy">{fileName || 'Adjuntar una foto'}</span>
                  <span className="mt-0.5 block text-[0.68rem] text-slate">JPG o PNG · opcional</span>
                </span>
                <Upload size={16} className="text-slate" />
                <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={(event) => setFileName(event.target.files?.[0]?.name ?? '')} />
              </label>
            </div>

            <button type="submit" className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal px-4 py-3.5 text-sm font-extrabold text-navy transition hover:bg-[#20b7a4]">
              Reportar incidencia <ArrowRight size={17} />
            </button>
          </form>
        </Panel>

        <Panel className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
            <div>
              <h3 className="font-bold tracking-[-0.02em] text-navy">Reportes activos</h3>
              <p className="mt-0.5 text-xs text-slate">{incidents.length} requieren seguimiento</p>
            </div>
            <span className="rounded-full bg-mint/55 px-3 py-1.5 font-mono text-[0.68rem] font-medium text-teal-dark">EN VIVO</span>
          </div>
          <div className="divide-y divide-line/70">
            {incidents.map((incident) => (
              <article key={incident.id} className="p-5 transition hover:bg-cloud/55 sm:p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex min-w-0 gap-3.5">
                    <span className={`mt-0.5 grid size-10 shrink-0 place-items-center rounded-xl ${incident.priority === 'Alta' ? 'bg-coral/10 text-coral' : incident.priority === 'Media' ? 'bg-amber/15 text-amber-dark' : 'bg-mint/50 text-teal-dark'}`}>
                      {incident.priority === 'Alta' ? <CircleAlert size={19} /> : <Wrench size={18} />}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[0.66rem] font-medium text-steel">{incident.id}</span>
                        <PriorityPill priority={incident.priority} />
                      </div>
                      <h4 className="mt-2 font-bold tracking-[-0.015em] text-navy">{incident.title}</h4>
                      <p className="mt-1 text-sm leading-relaxed text-slate">{incident.description}</p>
                    </div>
                  </div>
                  <StatusPill status={incident.status} />
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line/65 pt-3.5 text-[0.7rem] text-slate sm:ml-[3.4rem]">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-navy"><Factory size={13} className="text-teal" />{incident.machine}</span>
                  <span className="inline-flex items-center gap-1.5"><Clock3 size={13} />{incident.reportedAt}</span>
                  <span>Turno {incident.shift.toLowerCase()}</span>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </section>
  )
}

function ScanPanel({
  open,
  parts,
  onClose,
  onRegister,
}: {
  open: boolean
  parts: Part[]
  onClose: () => void
  onRegister: (partId: string, quantity: number) => void
}) {
  const [step, setStep] = useState<'scan' | 'confirm' | 'done'>('scan')
  const [partId, setPartId] = useState('')
  const [quantity, setQuantity] = useState(1)
  const part = parts.find((item) => item.id === partId)

  useEffect(() => {
    if (open) {
      setStep('scan')
      setPartId('')
      setQuantity(1)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const close = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onClose, open])

  if (!open) return null

  const simulateScan = () => {
    setPartId('p-001')
    setStep('confirm')
  }

  const confirm = () => {
    if (!part || quantity < 1 || quantity > available(part)) return
    onRegister(part.id, quantity)
    setStep('done')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy/55 p-0 backdrop-blur-sm sm:items-center sm:p-6" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section role="dialog" aria-modal="true" aria-labelledby="scan-title" className="sheet-enter max-h-[94dvh] w-full overflow-y-auto rounded-t-[1.75rem] bg-white shadow-2xl sm:max-w-lg sm:rounded-[1.75rem]">
        <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            {step !== 'scan' && step !== 'done' && <button type="button" onClick={() => setStep('scan')} aria-label="Volver" className="grid size-9 place-items-center rounded-lg border border-line text-navy"><ArrowLeft size={17} /></button>}
            <div>
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.15em] text-steel">Registrar uso</p>
              <h2 id="scan-title" className="font-bold tracking-[-0.02em] text-navy">{step === 'scan' ? 'Escanear repuesto' : step === 'confirm' ? 'Confirmar salida' : 'Movimiento guardado'}</h2>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="grid size-9 place-items-center rounded-lg text-slate transition hover:bg-cloud hover:text-navy"><X size={19} /></button>
        </div>

        {step === 'scan' && (
          <div className="p-5 sm:p-6">
            <div className="scanner-view relative aspect-[4/3] overflow-hidden rounded-2xl bg-navy">
              <div className="pointer-events-none absolute inset-0 opacity-10 blueprint-grid" />
              <div className="absolute inset-[12%] rounded-xl border border-white/25">
                <span className="scan-corner left-0 top-0 border-l-2 border-t-2" />
                <span className="scan-corner right-0 top-0 border-r-2 border-t-2" />
                <span className="scan-corner bottom-0 left-0 border-b-2 border-l-2" />
                <span className="scan-corner bottom-0 right-0 border-b-2 border-r-2" />
                <span className="scan-beam absolute left-[5%] right-[5%] top-1/2 h-px bg-mint shadow-[0_0_12px_2px_rgba(159,226,215,0.55)]" />
              </div>
              <div className="absolute inset-0 grid place-items-center">
                <QrCode size={62} className="text-white/18" strokeWidth={1.2} />
              </div>
              <p className="absolute inset-x-4 bottom-5 text-center text-xs font-medium text-white/60">Ubicá el código dentro del recuadro</p>
            </div>
            <div className="mt-5 rounded-xl border border-steel/15 bg-cloud p-3.5 text-xs leading-relaxed text-slate">
              <span className="font-bold text-navy">Prototipo sin cámara:</span> usá la lectura simulada para recorrer el flujo completo.
            </div>
            <button type="button" onClick={simulateScan} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal px-4 py-3.5 text-sm font-extrabold text-navy transition hover:bg-[#20b7a4]">
              <ScanLine size={18} /> Simular lectura de RP-2048
            </button>
          </div>
        )}

        {step === 'confirm' && part && (
          <div className="p-5 sm:p-6">
            <div className="flex gap-3 rounded-2xl border border-line bg-cloud/60 p-4">
              <StockIcon part={part} large />
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[0.65rem] font-medium text-steel">{part.code}</p>
                <h3 className="mt-1 font-bold tracking-[-0.02em] text-navy">{part.name}</h3>
                <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-slate"><MapPin size={13} className="text-teal" /> {part.location}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-xl font-medium text-navy">{available(part)}</p>
                <p className="text-[0.62rem] text-slate">disponibles</p>
              </div>
            </div>

            <div className="mt-5">
              <label htmlFor="repair" className="form-label">Reparación asociada *</label>
              <select id="repair" className="form-control" defaultValue="INC-1042">
                <option value="INC-1042">INC-1042 · Fraccionadora F-04</option>
                <option value="INC-1041">INC-1041 · Banda transportadora BT-03</option>
              </select>
            </div>

            <div className="mt-5">
              <span className="form-label">Cantidad utilizada</span>
              <div className="flex items-center justify-between rounded-xl border border-line p-2">
                <button type="button" aria-label="Restar una unidad" onClick={() => setQuantity((value) => Math.max(1, value - 1))} className="grid size-10 place-items-center rounded-lg bg-cloud text-navy transition hover:bg-mint"><Minus size={17} /></button>
                <span className="font-mono text-xl font-medium text-navy">{quantity}</span>
                <button type="button" aria-label="Sumar una unidad" onClick={() => setQuantity((value) => Math.min(available(part), value + 1))} className="grid size-10 place-items-center rounded-lg bg-cloud text-navy transition hover:bg-mint"><Plus size={17} /></button>
              </div>
            </div>

            {available(part) - quantity <= part.minimum && (
              <div className="mt-4 flex gap-3 rounded-xl bg-amber/12 p-3.5 text-xs leading-relaxed text-amber-dark">
                <AlertTriangle className="mt-0.5 shrink-0" size={16} />
                <p>Después de este uso quedarán <strong>{available(part) - quantity} unidades disponibles</strong>, por debajo del mínimo de {part.minimum}.</p>
              </div>
            )}

            <button type="button" onClick={confirm} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-navy px-4 py-3.5 text-sm font-extrabold text-white transition hover:bg-steel">
              Confirmar y descontar stock <ArrowRight size={17} />
            </button>
          </div>
        )}

        {step === 'done' && (
          <div className="px-6 py-10 text-center sm:px-10">
            <span className="mx-auto grid size-16 place-items-center rounded-full bg-mint text-teal-dark"><Check size={30} strokeWidth={2.5} /></span>
            <h3 className="mt-5 text-xl font-extrabold tracking-[-0.035em] text-navy">Stock actualizado</h3>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate">El movimiento quedó asociado a INC-1042 y ya forma parte de la trazabilidad del repuesto.</p>
            <button type="button" onClick={onClose} className="mt-7 inline-flex w-full items-center justify-center rounded-xl bg-navy px-4 py-3.5 text-sm font-extrabold text-white transition hover:bg-steel">Volver al tablero</button>
          </div>
        )}
      </section>
    </div>
  )
}

function PartPanel({ part, onClose, onAddStock }: { part: Part | null; onClose: () => void; onAddStock: (partId: string, quantity: number, location: string) => void }) {
  const [entryOpen, setEntryOpen] = useState(false)
  const [quantity, setQuantity] = useState(1)
  const [location, setLocation] = useState('')

  useEffect(() => {
    setEntryOpen(false)
    setQuantity(1)
    setLocation(part?.location ?? '')
  }, [part])

  if (!part) return null

  const submitEntry = (event: FormEvent) => {
    event.preventDefault()
    onAddStock(part.id, quantity, location)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-navy/35 backdrop-blur-[2px]" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside role="dialog" aria-modal="true" aria-labelledby="part-title" className="sheet-right-enter h-full w-full max-w-md overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-white/92 px-5 py-4 backdrop-blur-xl sm:px-6">
          <div>
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.15em] text-steel">Ficha de repuesto</p>
            <h2 id="part-title" className="font-bold tracking-[-0.02em] text-navy">{part.code}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="grid size-9 place-items-center rounded-lg text-slate transition hover:bg-cloud hover:text-navy"><X size={19} /></button>
        </div>

        <div className="p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <StockIcon part={part} large />
            <div>
              <h3 className="text-xl font-extrabold leading-tight tracking-[-0.035em] text-navy">{part.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate">{part.description}</p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-3 divide-x divide-line rounded-2xl border border-line bg-cloud/45 py-4 text-center">
            <div><p className="font-mono text-xl font-medium text-navy">{part.physical}</p><p className="mt-1 text-[0.64rem] text-slate">Físico</p></div>
            <div><p className="font-mono text-xl font-medium text-steel">{part.reserved}</p><p className="mt-1 text-[0.64rem] text-slate">Reservado</p></div>
            <div><p className={`font-mono text-xl font-medium ${isLow(part) ? 'text-amber-dark' : 'text-teal-dark'}`}>{available(part)}</p><p className="mt-1 text-[0.64rem] text-slate">Disponible</p></div>
          </div>

          {isLow(part) && (
            <div className="mt-4 flex gap-3 rounded-xl bg-amber/12 p-3.5 text-xs leading-relaxed text-amber-dark"><AlertTriangle className="mt-0.5 shrink-0" size={16} /><p>Este repuesto alcanzó su umbral mínimo de <strong>{part.minimum} unidades</strong>.</p></div>
          )}

          <div className="mt-6 space-y-5">
            <DetailRow icon={<MapPin />} label="Ubicación" value={part.locationDetail} code={part.location} />
            <DetailRow icon={<Factory />} label="Aplicable a" value={part.machines.join(' · ')} />
            <DetailRow icon={<History />} label="Último movimiento" value={part.lastMovement} />
          </div>

          <div className="my-6 h-px bg-line" />

          {!entryOpen ? (
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={() => setEntryOpen(true)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white transition hover:bg-steel"><PackageCheck size={17} /> Ingresar stock</button>
              <button type="button" className="inline-flex items-center justify-center gap-2 rounded-xl border border-line px-4 py-3 text-sm font-bold text-navy transition hover:bg-cloud"><FileText size={17} /> Ver historial</button>
            </div>
          ) : (
            <form onSubmit={submitEntry} className="rounded-2xl border border-line bg-cloud/45 p-4">
              <div className="mb-4 flex items-center justify-between"><h4 className="font-bold text-navy">Ingresar stock recibido</h4><button type="button" onClick={() => setEntryOpen(false)} className="text-xs font-bold text-slate hover:text-navy">Cancelar</button></div>
              <div className="grid grid-cols-[0.7fr_1.3fr] gap-3">
                <label><span className="form-label">Cantidad</span><input type="number" required min={1} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} className="form-control" /></label>
                <label><span className="form-label">Ubicación</span><input required value={location} onChange={(event) => setLocation(event.target.value.toUpperCase())} className="form-control font-mono" /></label>
              </div>
              <button type="submit" className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal px-4 py-3 text-sm font-extrabold text-navy transition hover:bg-[#20b7a4]"><Check size={17} /> Guardar ingreso</button>
            </form>
          )}
        </div>
      </aside>
    </div>
  )
}

function MobileNav({ view, onNavigate, onScan }: { view: View; onNavigate: (view: View) => void; onScan: () => void }) {
  return (
    <nav aria-label="Navegación móvil" className="fixed inset-x-3 bottom-3 z-30 grid grid-cols-[1fr_1fr_4.25rem_1fr] items-end rounded-2xl border border-white/10 bg-navy px-2 pb-2 pt-2 text-white shadow-[0_14px_40px_rgba(23,49,79,0.28)] lg:hidden">
      {navItems.slice(0, 2).map((item) => <MobileNavButton key={item.id} item={item} active={view === item.id} onClick={() => onNavigate(item.id)} />)}
      <button type="button" onClick={onScan} aria-label="Escanear repuesto" className="-mt-7 mx-auto grid size-14 place-items-center rounded-2xl border-[5px] border-canvas bg-teal text-navy shadow-lg transition active:scale-95"><ScanLine size={23} /></button>
      <MobileNavButton item={navItems[2]} active={view === 'incidents'} onClick={() => onNavigate('incidents')} />
    </nav>
  )
}

function MobileNavButton({ item, active, onClick }: { item: (typeof navItems)[number]; active: boolean; onClick: () => void }) {
  const Icon = item.icon
  return <button type="button" onClick={onClick} aria-current={active ? 'page' : undefined} className={`flex min-w-0 flex-col items-center gap-1 rounded-xl px-1 py-1.5 text-[0.61rem] font-semibold transition ${active ? 'text-mint' : 'text-white/50'}`}><Icon size={18} /><span className="truncate">{item.label}</span></button>
}

function MetricCard({ icon, value, label, hint, tone }: { icon: ReactNode; value: string | number; label: string; hint: string; tone: 'teal' | 'amber' | 'blue' | 'mint' }) {
  const colors = {
    teal: 'bg-teal/10 text-teal-dark',
    amber: 'bg-amber/15 text-amber-dark',
    blue: 'bg-steel/10 text-steel',
    mint: 'bg-mint/55 text-teal-dark',
  }
  return (
    <Panel className="flex min-h-[8.8rem] flex-col justify-between p-4 sm:p-5">
      <span className={`grid size-9 place-items-center rounded-xl [&>svg]:size-[17px] ${colors[tone]}`}>{icon}</span>
      <div className="mt-4"><p className="font-mono text-2xl font-medium text-navy">{value}</p><p className="mt-1 text-xs font-bold text-navy">{label}</p><p className="mt-0.5 hidden text-[0.65rem] text-slate sm:block">{hint}</p></div>
    </Panel>
  )
}

function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-white shadow-[0_8px_30px_rgba(23,49,79,0.035)] ${className}`}>{children}</div>
}

function LogoMark({ dark = false }: { dark?: boolean }) {
  return (
    <span className={`relative grid size-9 shrink-0 place-items-center rounded-xl ${dark ? 'bg-navy text-mint' : 'bg-mint text-navy'}`} aria-hidden="true">
      <Factory size={18} strokeWidth={2.2} />
      <span className={`absolute -right-0.5 -top-0.5 size-2.5 rounded-full border-2 ${dark ? 'border-canvas' : 'border-navy'} bg-teal`} />
    </span>
  )
}

function StockIcon({ part, large = false }: { part: Part; large?: boolean }) {
  const state = available(part) === 0 ? 'bg-coral/10 text-coral' : isLow(part) ? 'bg-amber/15 text-amber-dark' : 'bg-mint/50 text-teal-dark'
  return <span className={`grid shrink-0 place-items-center rounded-xl ${large ? 'size-12' : 'size-10'} ${state}`}><Boxes size={large ? 21 : 18} /></span>
}

function MiniStat({ label, value, alert = false }: { label: string; value: number; alert?: boolean }) {
  return <div className="rounded-xl border border-line bg-white px-3 py-3"><p className={`font-mono text-xl font-medium ${alert ? 'text-amber-dark' : 'text-navy'}`}>{value}</p><p className="mt-0.5 truncate text-[0.65rem] font-semibold text-slate">{label}</p></div>
}

function MobileLabel({ label }: { label: string }) {
  return <span className="mb-1 block text-[0.58rem] font-bold uppercase tracking-[0.1em] text-slate md:hidden">{label}</span>
}

function PriorityPill({ priority }: { priority: Incident['priority'] }) {
  const style = priority === 'Alta' ? 'bg-coral/10 text-coral' : priority === 'Media' ? 'bg-amber/15 text-amber-dark' : 'bg-mint/55 text-teal-dark'
  return <span className={`rounded-full px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide ${style}`}>{priority}</span>
}

function StatusPill({ status }: { status: Incident['status'] }) {
  const style = status === 'En reparación' ? 'bg-steel/10 text-steel' : status === 'En diagnóstico' ? 'bg-amber/15 text-amber-dark' : 'bg-cloud text-slate'
  return <span className={`w-fit shrink-0 rounded-full px-3 py-1.5 text-[0.65rem] font-bold ${style}`}>{status}</span>
}

function DetailRow({ icon, label, value, code }: { icon: ReactNode; label: string; value: string; code?: string }) {
  return <div className="flex gap-3"><span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-cloud text-steel [&>svg]:size-4">{icon}</span><div><p className="text-[0.64rem] font-bold uppercase tracking-[0.1em] text-slate">{label}</p><p className="mt-1 text-sm leading-relaxed text-navy">{value}</p>{code && <p className="mt-1 font-mono text-xs font-medium text-teal-dark">{code}</p>}</div></div>
}

function ToastMessage({ toast, onClose }: { toast: Exclude<Toast, null>; onClose: () => void }) {
  return (
    <div role="status" className="toast-enter fixed bottom-24 left-1/2 z-[60] flex w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 items-start gap-3 rounded-2xl bg-navy p-4 text-white shadow-2xl lg:bottom-7 lg:left-auto lg:right-7 lg:translate-x-0">
      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-mint text-teal-dark"><Check size={17} /></span>
      <div className="min-w-0 flex-1"><p className="text-sm font-bold">{toast.title}</p><p className="mt-1 text-xs leading-relaxed text-white/60">{toast.detail}</p></div>
      <button type="button" onClick={onClose} aria-label="Cerrar mensaje" className="text-white/45 hover:text-white"><X size={16} /></button>
    </div>
  )
}

export default App
