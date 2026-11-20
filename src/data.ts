export type Part = {
  id: string
  code: string
  name: string
  description: string
  physical: number
  reserved: number
  minimum: number
  location: string
  locationDetail: string
  machines: string[]
  lastMovement: string
}

export type Incident = {
  id: string
  machine: string
  machineCode: string
  title: string
  description: string
  priority: 'Alta' | 'Media' | 'Baja'
  status: 'Sin asignar' | 'En diagnóstico' | 'En reparación'
  shift: 'Mañana' | 'Tarde' | 'Noche'
  reportedAt: string
}

export const initialParts: Part[] = [
  {
    id: 'p-001',
    code: 'RP-2048',
    name: 'Sello mecánico 32 mm',
    description: 'Sello sanitario de carburo de silicio para bomba centrífuga.',
    physical: 4,
    reserved: 2,
    minimum: 3,
    location: 'A-03-12',
    locationDetail: 'Pasillo A · Estante 03 · Nivel 12',
    machines: ['Fraccionadora F-04', 'Bomba de proceso B-12'],
    lastMovement: 'Hoy, 08:42',
  },
  {
    id: 'p-002',
    code: 'RP-1190',
    name: 'Rodamiento 6205-2RS',
    description: 'Rodamiento rígido de bolas, sellado en ambos lados.',
    physical: 2,
    reserved: 0,
    minimum: 4,
    location: 'B-01-07',
    locationDetail: 'Pasillo B · Estante 01 · Nivel 07',
    machines: ['Banda transportadora BT-03', 'Motor mezclador M-08'],
    lastMovement: 'Ayer, 22:18',
  },
  {
    id: 'p-003',
    code: 'IN-4421',
    name: 'Filtro HEPA H14',
    description: 'Filtro absoluto para módulo de flujo laminar 610 × 610 mm.',
    physical: 8,
    reserved: 1,
    minimum: 2,
    location: 'C-02-04',
    locationDetail: 'Sector limpio C · Estante 02 · Nivel 04',
    machines: ['Cabina de flujo CF-02'],
    lastMovement: '03 oct, 14:06',
  },
  {
    id: 'p-004',
    code: 'RP-8870',
    name: 'Correa dentada T10',
    description: 'Correa de transmisión de poliuretano, ancho 25 mm.',
    physical: 0,
    reserved: 0,
    minimum: 2,
    location: 'A-06-02',
    locationDetail: 'Pasillo A · Estante 06 · Nivel 02',
    machines: ['Etiquetadora E-07'],
    lastMovement: '02 oct, 19:33',
  },
  {
    id: 'p-005',
    code: 'IN-3022',
    name: 'Aceite grado alimenticio',
    description: 'Lubricante sintético NSF H1, envase de 1 litro.',
    physical: 18,
    reserved: 4,
    minimum: 6,
    location: 'D-01-03',
    locationDetail: 'Depósito químico D · Estante 01 · Nivel 03',
    machines: ['Caldera C-01', 'Compresor CP-02'],
    lastMovement: '01 oct, 09:15',
  },
  {
    id: 'p-006',
    code: 'RP-5204',
    name: 'Electroválvula 1/2”',
    description: 'Electroválvula sanitaria de acero inoxidable, 24 VCC.',
    physical: 7,
    reserved: 0,
    minimum: 3,
    location: 'B-04-09',
    locationDetail: 'Pasillo B · Estante 04 · Nivel 09',
    machines: ['Fraccionadora F-04', 'Lavadora L-02'],
    lastMovement: '29 sep, 16:40',
  },
]

export const initialIncidents: Incident[] = [
  {
    id: 'INC-1042',
    machine: 'Fraccionadora F-04',
    machineCode: 'MAQ-F04',
    title: 'Pérdida en bomba de dosificación',
    description: 'Se observa goteo durante el ciclo de limpieza.',
    priority: 'Alta',
    status: 'En diagnóstico',
    shift: 'Mañana',
    reportedAt: 'Hace 18 min',
  },
  {
    id: 'INC-1041',
    machine: 'Banda transportadora BT-03',
    machineCode: 'MAQ-BT03',
    title: 'Vibración irregular en cabezal',
    description: 'La vibración aumenta al superar el 70% de velocidad.',
    priority: 'Media',
    status: 'En reparación',
    shift: 'Noche',
    reportedAt: 'Hace 2 h',
  },
  {
    id: 'INC-1040',
    machine: 'Etiquetadora E-07',
    machineCode: 'MAQ-E07',
    title: 'Desalineación del rollo',
    description: 'Las etiquetas quedan desplazadas hacia el borde derecho.',
    priority: 'Baja',
    status: 'Sin asignar',
    shift: 'Mañana',
    reportedAt: 'Hace 3 h',
  },
]

export const recentMovements = [
  { time: '08:42', label: 'Uso registrado', detail: '2 × Sello mecánico · Fraccionadora F-04', kind: 'salida' },
  { time: '07:15', label: 'Stock recibido', detail: '6 × Electroválvula · Ubicación B-04-09', kind: 'entrada' },
  { time: '23:51', label: 'Reserva creada', detail: '4 × Aceite grado alimenticio · Preventivo MP-088', kind: 'reserva' },
]
