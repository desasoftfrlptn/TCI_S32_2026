import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

describe('Planta en orden', () => {
  it('permite buscar un repuesto en el inventario', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getAllByRole('button', { name: 'Inventario' })[0])
    const search = screen.getByRole('searchbox', { name: 'Buscar repuestos' })
    await user.type(search, 'HEPA')

    expect(screen.getByText('Filtro HEPA H14')).toBeInTheDocument()
    expect(screen.queryByText('Rodamiento 6205-2RS')).not.toBeInTheDocument()
  })

  it('recorre el registro de uso y descuenta el stock', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getAllByRole('button', { name: /escanear repuesto/i })[0])
    await user.click(screen.getByRole('button', { name: /simular lectura de RP-2048/i }))

    expect(screen.getByText('Confirmar salida')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /confirmar y descontar stock/i }))

    expect(screen.getByText('Stock actualizado')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Uso registrado')
  })
})
