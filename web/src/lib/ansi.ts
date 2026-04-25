/**
 * Shared ANSI escape-code renderer — returns React-renderable spans.
 * Used by JobLogViewer and ToolUpdateConsole.
 */

export type AnsiState = {
  fg: string | null
  bg: string | null
  bold: boolean
  dim: boolean
}

export const ANSI_PATTERN = /\u001b\[([0-9;]*)m/g
export const ANSI_CONTROL_PATTERN = /\u001b\[[0-9;?]*[A-Za-z]/g
export const ANSI_OSC_PATTERN = /\u001b\][^\u0007]*(\u0007|\u001b\\)/g

export const ANSI_FG: Record<number, string> = {
  30: '#111827', 31: '#f87171', 32: '#86efac', 33: '#fde047',
  34: '#93c5fd', 35: '#e879f9', 36: '#67e8f9', 37: '#e5e7eb',
  90: '#6b7280', 91: '#fca5a5', 92: '#bbf7d0', 93: '#fef08a',
  94: '#bfdbfe', 95: '#f5d0fe', 96: '#a5f3fc', 97: '#ffffff',
}

export const ANSI_BG: Record<number, string> = {
  40: '#111827', 41: '#7f1d1d', 42: '#14532d', 43: '#713f12',
  44: '#1e3a8a', 45: '#701a75', 46: '#164e63', 47: '#e5e7eb',
  100: '#374151', 101: '#991b1b', 102: '#166534', 103: '#854d0e',
  104: '#1e40af', 105: '#86198f', 106: '#155e75', 107: '#f3f4f6',
}

export function applyAnsiCode(codes: number[], state: AnsiState): AnsiState {
  const next = { ...state }
  let i = 0
  while (i < codes.length) {
    const code = codes[i]
    if (code === 0)  { next.fg = null; next.bg = null; next.bold = false; next.dim = false }
    else if (code === 1) next.bold = true
    else if (code === 2) next.dim = true
    else if (code === 22) { next.bold = false; next.dim = false }
    else if (code === 39) next.fg = null
    else if (code === 49) next.bg = null
    else if (ANSI_FG[code]) next.fg = ANSI_FG[code]
    else if (ANSI_BG[code]) next.bg = ANSI_BG[code]
    else if (code === 38 && codes[i + 1] === 5) { next.fg = `#${codes[i + 2]?.toString(16).padStart(2, '0') ?? '00'}0000`; i += 2 }
    else if (code === 48 && codes[i + 1] === 5) { next.bg = `#${codes[i + 2]?.toString(16).padStart(2, '0') ?? '00'}0000`; i += 2 }
    i++
  }
  return next
}

export function stateToStyle(state: AnsiState): React.CSSProperties {
  return {
    color: state.fg ?? undefined,
    background: state.bg ?? undefined,
    fontWeight: state.bold ? 700 : undefined,
    opacity: state.dim ? 0.6 : undefined,
  }
}

export type AnsiSpan = { text: string; style: React.CSSProperties }

/** Parse a raw log string into styled spans for rendering */
export function parseAnsi(raw: string): AnsiSpan[][] {
  const lines = raw.split('\n')
  return lines.map((line) => {
    const cleaned = line
      .replace(ANSI_OSC_PATTERN, '')
      .replace(ANSI_CONTROL_PATTERN, '')
    const spans: AnsiSpan[] = []
    let state: AnsiState = { fg: null, bg: null, bold: false, dim: false }
    let lastIndex = 0
    const re = new RegExp(ANSI_PATTERN.source, 'g')
    let match: RegExpExecArray | null
    while ((match = re.exec(cleaned)) !== null) {
      if (match.index > lastIndex) {
        spans.push({ text: cleaned.slice(lastIndex, match.index), style: stateToStyle(state) })
      }
      const codes = match[1].split(';').map(Number).filter((n) => !isNaN(n))
      state = applyAnsiCode(codes.length ? codes : [0], state)
      lastIndex = match.index + match[0].length
    }
    if (lastIndex < cleaned.length) {
      spans.push({ text: cleaned.slice(lastIndex), style: stateToStyle(state) })
    }
    return spans
  })
}
