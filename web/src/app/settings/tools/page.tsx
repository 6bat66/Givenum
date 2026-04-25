import { TOOL_REGISTRY, checkTool, type ToolStatus } from '@/lib/tools'
import ToolUpdateConsole from '@/components/ToolUpdateConsole'

export const dynamic = 'force-dynamic'

export default function ToolsSettingsPage() {
  // Check all tools synchronously at render time (parallelised via Promise.all not possible in RSC sync)
  const tools: ToolStatus[] = TOOL_REGISTRY.map((tool) => ({
    ...tool,
    ...checkTool(tool),
  }))

  const installed = tools.filter((t) => t.installed).length

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--text)' }}>Tools</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Update recon tools via <code style={{ color: 'var(--cyan)' }}>go install</code>.{' '}
          <span style={{ color: 'var(--text-subtle)' }}>{installed}/{tools.length} installed</span>
        </p>
      </div>

      <ToolUpdateConsole tools={tools} />
    </div>
  )
}
