// Thin client for the local API. The launcher opens the page as /#token=...; the token is moved
// into sessionStorage and stripped from the address bar so it is not bookmarked or shared.
const KEY = 'nyaya-token'

function takeToken(): string | null {
  const m = location.hash.match(/token=([^&]+)/)
  if (m) {
    sessionStorage.setItem(KEY, decodeURIComponent(m[1]))
    history.replaceState(null, '', location.pathname + location.search)
  }
  return sessionStorage.getItem(KEY)
}

export const token = takeToken()

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init
  const headers: Record<string, string> = { 'X-Nyaya-Token': token ?? '' }
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`/api${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : `request failed (${res.status})`
    if (res.status === 401 && detail.includes('token')) window.dispatchEvent(new Event('nyaya-token-expired'))
    throw new ApiError(res.status, detail)
  }
  return body as T
}

export type CaseInfo = { id: string; label: string; unlocked: boolean }

export const DOCTYPES = {
  police_statement: 'Police statement',
  fir: 'FIR',
  chargesheet: 'Chargesheet',
  examination_in_chief: 'Examination-in-chief',
  cross_examination: 'Cross-examination',
} as const
export type Doctype = keyof typeof DOCTYPES

export type DocInfo = { id: string; name: string; witness: string; doctype: Doctype; kind: 'earlier' | 'court'; date: string }

export type Claim = {
  doc: string
  page: number
  para: number
  actor?: string
  event: string
  event_text?: string
  date?: string
  time?: string
  place?: string
  amount?: string
  exact_quote: string
  status?: string
  reason?: string
}

type FindingBase = { key: string; state: 'open' | 'confirmed' | 'dismissed'; stale: boolean; updated: string; witness: string }
export type Contradiction = FindingBase & { kind: 'contradiction'; fields: string[]; a: Claim; b: Claim }
export type Omission = FindingBase & { kind: 'omission'; omission: 'court_only' | 'earlier_only'; material: boolean; claim: Claim }
export type Finding = Contradiction | Omission

export type Results = {
  counts: { verified: number; rejected: number; contradictions: number; omissions: number }
  findings: Finding[]
  rejected: Claim[]
}

export type Job = { state: 'running' | 'done' | 'failed'; done: number; total: number; message: string; errors: { doc: string; page: number; para: number; error: string }[] }

export const cite = (c: Claim) => `${c.doc}, p. ${c.page}, para ${c.para}`
export const eventName = (c: Claim) => (c.event === 'other' && c.event_text ? c.event_text : c.event.replaceAll('_', ' '))

// Saves the encrypted case archive (.nyaya). The archive holds only ciphertext.
export async function download(path: string) {
  const res = await fetch(`/api${path}`, { headers: { 'X-Nyaya-Token': token ?? '' } })
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({}))).detail ?? 'download failed')
  const name = /filename="?([^";]+)/.exec(res.headers.get('content-disposition') ?? '')?.[1] ?? 'case.nyaya'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(await res.blob())
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}
