import { NextResponse } from 'next/server'
import { TOOL_REGISTRY, checkTool, type ToolStatus } from '@/lib/tools'

export const dynamic = 'force-dynamic'

export async function GET() {
  // Check tools in parallel (capped at 8 concurrent)
  const results: ToolStatus[] = []
  const chunk = 8

  for (let i = 0; i < TOOL_REGISTRY.length; i += chunk) {
    const batch = TOOL_REGISTRY.slice(i, i + chunk)
    const checked = await Promise.all(
      batch.map(async (tool) => ({
        ...tool,
        ...checkTool(tool),
      }))
    )
    results.push(...checked)
  }

  return NextResponse.json({ tools: results })
}
