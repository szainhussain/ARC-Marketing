import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { useState } from 'react'
import { ConfirmDialog, DataTable, ErrorState, KpiCard, Tabs } from './ui'
import WorkflowGraph from './WorkflowGraph'
import WorkflowDemo from './marketing/WorkflowDemo'
import AgentDetailDialog from './marketing/AgentDetailDialog'
import ThemeToggle from './ThemeToggle'
import CostByAgentChart from './CostByAgentChart'
import { costTick } from '../lib/chartTheme'
import { ThemeProvider } from '../context/ThemeContext'
import type { PublicAgent } from '../lib/agentMeta'
import type { Task } from '../api/types'

function task(id: string, agent: string, status: string, deps: string[] = [], seq = 0): Task {
  return {
    id, campaign_id: 'c', workflow_run_id: 'r', agent_id: agent, agent_name: agent, agent_number: seq + 1,
    task_type: null, title: null, stage: agent, status, priority: 1, sequence_index: seq, attempt_count: 1,
    max_attempts: 5, next_attempt_at: null, last_error_code: null, error_summary: null, deliverable_id: null,
    depends_on: deps, started_at: null, completed_at: null, created_at: null,
  }
}

describe('KpiCard', () => {
  it('shows an explicit unavailable state instead of a number', () => {
    render(<KpiCard label="Revenue" value={1234} unavailable="Not connected" />)
    expect(screen.getByText('—')).toBeTruthy()
    expect(screen.getByText('Not connected')).toBeTruthy()
    expect(screen.queryByText('1234')).toBeNull()
  })

  it('labels estimates and links to drill-down', () => {
    render(<MemoryRouter><KpiCard label="AI cost" value={0.27} basis="estimate" to="/app/settings/usage" format={(v) => `$${v}`} /></MemoryRouter>)
    expect(screen.getByText('est.')).toBeTruthy()
    expect(screen.getByRole('link', { name: /AI cost/ }).getAttribute('href')).toBe('/app/settings/usage')
  })
})

describe('Tabs', () => {
  it('moves selection with arrow keys', () => {
    function Harness() {
      const [v, setV] = useState('a')
      return <Tabs label="T" value={v} onChange={setV} tabs={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]} />
    }
    render(<Harness />)
    const a = screen.getByRole('tab', { name: 'A' })
    expect(a.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(a, { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'B' }).getAttribute('aria-selected')).toBe('true')
  })
})

describe('ConfirmDialog', () => {
  it('calls confirm and closes on Escape', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(<ConfirmDialog open title="Delete?" body="Sure?" confirmLabel="Delete" onConfirm={onConfirm} onCancel={onCancel} />)
    expect(screen.getByRole('dialog', { name: 'Delete?' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(onConfirm).toHaveBeenCalled()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalled()
  })
})

describe('ErrorState and DataTable', () => {
  it('offers retry', () => {
    const retry = vi.fn()
    render(<ErrorState message="Boom" onRetry={retry} />)
    expect(screen.getByRole('alert').textContent).toContain('Boom')
    fireEvent.click(screen.getByRole('button', { name: /Try again/ }))
    expect(retry).toHaveBeenCalled()
  })

  it('renders an empty state when there are no rows', () => {
    render(<DataTable rows={[]} rowKey={() => 'x'} columns={[]} empty={<p>Nothing</p>} />)
    expect(screen.getByText('Nothing')).toBeTruthy()
  })
})

describe('WorkflowGraph', () => {
  it('draws one node per task and one edge per dependency, from data', () => {
    const tasks = [task('1', 'cmo', 'succeeded', [], 0), task('2', 'research', 'running', ['1'], 1), task('3', 'manager', 'waiting_for_dependency', ['1', '2'], 2)]
    const onSelect = vi.fn()
    const { container } = render(<WorkflowGraph tasks={tasks} onSelect={onSelect} />)
    expect(container.querySelectorAll('.wf-node').length).toBe(3)
    expect(container.querySelectorAll('.wf-edge').length).toBe(3)
    expect(container.querySelectorAll('.wf-edge.done').length).toBe(2)
    fireEvent.click(screen.getByRole('button', { name: /research: Running/ }))
    expect(onSelect).toHaveBeenCalledWith(tasks[1])
  })
})

describe('WorkflowDemo', () => {
  it('is labelled as a local demo and can start, pause and reset', () => {
    vi.useFakeTimers()
    render(<WorkflowDemo />)
    expect(screen.getByText(/LOCAL DEMO · NO REAL ACTIONS/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Start/ }))
    expect(screen.getByRole('button', { name: /Pause/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Reset/ }))
    expect(screen.getByRole('button', { name: /Start/ })).toBeTruthy()
    vi.useRealTimers()
  })
})

describe('AgentDetailDialog video', () => {
  const agent: PublicAgent = {
    agent_id: 'social_media', number: 3, name: 'Social Media & Community Manager', version: '1.1.0', role: 'Organic calendars.',
    responsibilities: ['Build a calendar'], task_type: 'social_calendar', depends_on: [], reads: [], outputs: ['Social calendar'],
    kpis: [], escalates: [], allowed_tools: [], allowed_integrations: [], approval_policy: { external_actions: 'approval_required' }, evaluation_checks: [],
  }

  it('opens on Read and switches to the 30s video on Watch', () => {
    render(<AgentDetailDialog agent={agent} all={[agent]} onClose={() => {}} />)
    expect(screen.getByText('What it does')).toBeTruthy()
    expect(document.querySelector('video')).toBeNull()
    fireEvent.click(screen.getByRole('tab', { name: /Watch/ }))
    const video = document.querySelector('video')!
    expect(video.getAttribute('poster')).toBe('/videos/agents/social_media.jpg')
    expect(video.querySelector('source')!.getAttribute('src')).toBe('/videos/agents/social_media.mp4')
    expect(screen.queryByText('What it does')).toBeNull()
  })

  it('shows no Watch tab for an agent without a video', () => {
    render(<AgentDetailDialog agent={{ ...agent, agent_id: 'unknown_agent' }} all={[]} onClose={() => {}} />)
    expect(screen.queryByRole('tab', { name: /Watch/ })).toBeNull()
  })
})

describe('ThemeToggle', () => {
  it('switches theme, remembers it, and restores "Match my device"', () => {
    localStorage.clear()
    render(<ThemeProvider><ThemeToggle /></ThemeProvider>)
    fireEvent.click(screen.getByRole('button', { name: /Theme:/ }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Light' }))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('arc-theme')).toBe('light')
    expect(document.documentElement.style.getPropertyValue('--color-accent')).toBe('#0369a1')

    fireEvent.click(screen.getByRole('button', { name: 'Theme: Light' }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Dark' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.style.getPropertyValue('--color-accent')).toBe('#9fd8ff')

    fireEvent.click(screen.getByRole('button', { name: 'Theme: Dark' }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Match my device' }))
    expect(localStorage.getItem('arc-theme')).toBeNull()
  })
})

describe('CostByAgentChart', () => {
  const row = (agent_id: string, number: number, cost_usd: number, executions = 1) =>
    ({ agent_id, agent_name: agent_id, number, executions, cost_usd })

  it('says so when no agent ran', () => {
    render(<CostByAgentChart rows={[]} />)
    expect(screen.getByText('No agent activity in this period')).toBeTruthy()
  })

  it('explains a $0 period instead of drawing empty bars', () => {
    render(<CostByAgentChart rows={[row('cmo', 1, 0, 2), row('social_media', 3, 0, 1)]} />)
    expect(screen.getByText('No AI cost in this period')).toBeTruthy()
    expect(screen.getByText(/2 agents ran 3 times, all estimated at \$0\.00/)).toBeTruthy()
  })

  it('formats tiny costs so axis ticks stay distinct', () => {
    expect(costTick(0)).toBe('$0')
    expect(costTick(0.004)).toBe('$0.004')
    expect(costTick(0.015)).toBe('$0.015')
    expect(costTick(0.03)).toBe('$0.03')
    expect(costTick(1.5)).toBe('$1.50')
  })
})
