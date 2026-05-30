import { useState, type FormEvent } from 'react'

interface CommandInputProps {
  onSend: (text: string) => void
  disabled: boolean
}

export function CommandInput({ onSend, disabled }: CommandInputProps) {
  const [text, setText] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form className="command-input" onSubmit={handleSubmit}>
      <input
        className="command-input__field"
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder='Ej: "poné 10 minutos para la pasta"'
        disabled={disabled}
      />
      <button className="command-input__btn" type="submit" disabled={disabled || !text.trim()}>
        Enviar
      </button>
    </form>
  )
}
