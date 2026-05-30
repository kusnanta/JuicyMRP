import React, { useState, useRef, useEffect } from 'react'

interface Props {
  label: string
  options: string[]
  selected: string[]
  onChange: (sel: string[]) => void
  badge?: string
}

interface Action {
  label: string
  fn: () => void
}

export function MultiSelect({ label, options, selected, onChange, badge }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  const toggle = (v: string) => {
    const next = selected.includes(v)
      ? selected.filter(s => s !== v)
      : [...selected, v]
    onChange(next)
  }

  const actions: Action[] = [
    { label: 'Semua', fn: () => onChange([...options]) },
    { label: 'Hapus', fn: () => onChange([]) },
  ]

  const displayLabel =
    selected.length === options.length ? `Semua ${label.toLowerCase()}`
    : selected.length === 0            ? `Pilih ${label.toLowerCase()}`
    : selected.length === 1            ? selected[0]
    :                                    `${selected.length} ${label.toLowerCase()} dipilih`

  const btnBase: React.CSSProperties = {
    fontSize: 11, cursor: 'pointer', background: 'transparent',
    border: 'none', color: '#6b7280', flex: 1, padding: '5px 8px',
  }

  return (
    <div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4, fontWeight: 500 }}>
        {label}{badge && <span style={{ color: '#1a56db', marginLeft: 4 }}>{badge}</span>}
      </div>

      <div ref={ref} style={{ position: 'relative', display: 'inline-block', minWidth: 170 }}>
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            width: '100%', padding: '5px 10px', fontSize: 12,
            borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff',
            cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', gap: 6, whiteSpace: 'nowrap', overflow: 'hidden',
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{displayLabel}</span>
          <span style={{ flexShrink: 0, fontSize: 10 }}>▾</span>
        </button>

        {open && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 3px)', left: 0, minWidth: '100%',
            background: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, zIndex: 100,
            boxShadow: '0 4px 16px rgba(0,0,0,.1)', maxHeight: 200, overflowY: 'auto',
          }}>
            {/* Semua / Hapus action row */}
            <div style={{ display: 'flex', borderBottom: '1px solid #f3f4f6' }}>
              {actions.map(({ label: aLabel, fn }) => (
                <button
                  key={aLabel}
                  onClick={fn}
                  style={btnBase}
                  onMouseEnter={e => { e.currentTarget.style.background = '#f9fafb' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                >
                  {aLabel}
                </button>
              ))}
            </div>

            {/* Option checkboxes */}
            {options.map(opt => (
              <label
                key={opt}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 10px', cursor: 'pointer', fontSize: 12,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#f9fafb' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={() => toggle(opt)}
                  style={{ margin: 0, cursor: 'pointer', accentColor: '#1a56db' }}
                />
                {opt}
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
