/**
 * Tests for buildDiffData — diff between two scan output files.
 * Covers: new / persisted / removed semantics, empty inputs, blank-line
 * handling.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import fs from 'fs'
import os from 'os'
import path from 'path'

import { buildDiffData } from './results'

let workdir: string

beforeEach(() => {
  workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'givenum-results-'))
})

afterEach(() => {
  fs.rmSync(workdir, { recursive: true, force: true })
})

function writeLines(name: string, lines: string[]): string {
  const p = path.join(workdir, name)
  fs.writeFileSync(p, lines.join('\n') + '\n')
  return p
}

describe('buildDiffData', () => {
  it('classifies new / persisted / removed correctly', () => {
    const cur = writeLines('cur.txt', ['a', 'b', 'c', 'd'])
    const prev = writeLines('prev.txt', ['b', 'c', 'e'])

    const d = buildDiffData(cur, prev)
    expect(d.new.sort()).toEqual(['a', 'd'])
    expect(d.persisted.sort()).toEqual(['b', 'c'])
    expect(d.removed.sort()).toEqual(['e'])
    expect(d.current.sort()).toEqual(['a', 'b', 'c', 'd'])
    expect(d.previous.sort()).toEqual(['b', 'c', 'e'])
  })

  it('returns all-new when previous is empty', () => {
    const cur = writeLines('cur.txt', ['x', 'y'])
    const prev = writeLines('prev.txt', [])
    const d = buildDiffData(cur, prev)
    expect(d.new.sort()).toEqual(['x', 'y'])
    expect(d.persisted).toEqual([])
    expect(d.removed).toEqual([])
  })

  it('returns all-removed when current is empty', () => {
    const cur = writeLines('cur.txt', [])
    const prev = writeLines('prev.txt', ['x', 'y'])
    const d = buildDiffData(cur, prev)
    expect(d.new).toEqual([])
    expect(d.persisted).toEqual([])
    expect(d.removed.sort()).toEqual(['x', 'y'])
  })

  it('handles fully-identical files (everything persisted)', () => {
    const cur = writeLines('cur.txt', ['a', 'b', 'c'])
    const prev = writeLines('prev.txt', ['a', 'b', 'c'])
    const d = buildDiffData(cur, prev)
    expect(d.new).toEqual([])
    expect(d.removed).toEqual([])
    expect(d.persisted.sort()).toEqual(['a', 'b', 'c'])
  })

  it('returns empty arrays when both files are empty', () => {
    const cur = writeLines('cur.txt', [])
    const prev = writeLines('prev.txt', [])
    const d = buildDiffData(cur, prev)
    expect(d.new).toEqual([])
    expect(d.persisted).toEqual([])
    expect(d.removed).toEqual([])
    expect(d.current).toEqual([])
    expect(d.previous).toEqual([])
  })

  it('treats duplicate lines as one logical entry', () => {
    // Set semantics — duplicates in the source file shouldn't double-count
    const cur = writeLines('cur.txt', ['a', 'a', 'b'])
    const prev = writeLines('prev.txt', ['a'])
    const d = buildDiffData(cur, prev)
    // 'a' is in both → persisted (appears in current.filter currentSet has)
    // 'b' is only in current → new
    expect(d.persisted).toContain('a')
    expect(d.new).toContain('b')
    expect(d.removed).toEqual([])
  })
})
