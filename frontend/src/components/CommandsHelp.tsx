import { useState, useEffect } from 'react'

const COMMANDS = [
  { action: 'Crear temporizador', verbs: '—', example: '"10 minutos para la pasta"' },
  { action: 'Pausar', verbs: 'pausar', example: '"pausar nombre del temporizador"' },
  { action: 'Reanudar', verbs: 'reanudar', example: '"reanudar nombre del temporizador"' },
  { action: 'Cancelar', verbs: 'cancelar', example: '"cancelar nombre del temporizador"' },
  { action: 'Añadir tiempo', verbs: 'añadir / extender', example: '"agregar 5 minutos a la pasta"' },
  { action: 'Quitar tiempo', verbs: 'quitar / reducir / restar', example: '"quitar 2 minutos a la pasta"' },
  { action: 'Renombrar', verbs: 'renombrar', example: '"renombrar nombre temporizador a papas"' },
]

export function CommandsHelp() {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen])

  return (
    <>
      <button
        className="info-btn"
        onClick={() => setIsOpen(true)}
        aria-label="Ver comandos de voz disponibles"
        title="Comandos de voz"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </button>

      {isOpen && (
        <div className="commands-overlay" onClick={() => setIsOpen(false)}>
          <div className="commands-modal" onClick={e => e.stopPropagation()}>
            <div className="commands-modal__header">
              <h2 className="commands-modal__title">Comandos de voz</h2>
              <button
                className="commands-modal__close"
                onClick={() => setIsOpen(false)}
                aria-label="Cerrar"
              >
                ✕
              </button>
            </div>
            <ul className="commands-modal__list">
              {COMMANDS.map(cmd => (
                <li key={cmd.action} className="commands-modal__item">
                  <span className="commands-modal__action">{cmd.action}</span>
                  <span className="commands-modal__verbs">{cmd.verbs}</span>
                  <span className="commands-modal__example">{cmd.example}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  )
}
