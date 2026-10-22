import { useCallback, useEffect, useState } from 'react'
import { Cloud, CloudDownload, CloudOff, Copy, Eye, LogOut, ShieldCheck, ShieldX, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { ConfirmAction } from '@/components/common'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError } from '@/lib/api'

type Status = {
  configured: boolean
  signed_in: boolean
  user: string | null
  config: { api_url: string; region: string; client_id: string } | null
}
type Step = { state: 'mfa' } | { state: 'mfa_setup'; secret: string; uri: string } | null
type CloudCase = { id: string; version: number; size: number; updated: string; local: boolean; label: string | null; synced_version: number | null }
type Inspection = {
  version: number
  size: number
  index: Record<string, unknown> | null
  files: { name: string; size: number; starts: string }[]
  words_checked: number
  found: string[]
}

const size = (n: number) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`)
const say = (e: unknown) => toast.error(e instanceof Error ? e.message : String(e))

export function CloudPanel({ onLocalChange }: { onLocalChange: () => void }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [cases, setCases] = useState<CloudCase[]>([])
  const [step, setStep] = useState<Step>(null)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ api_url: '', region: 'ap-south-1', client_id: '' })
  const [login, setLogin] = useState({ username: '', password: '' })
  const [code, setCode] = useState('')

  const loadCases = useCallback(() => {
    api<CloudCase[]>('/cloud/cases').then(setCases).catch(say)
  }, [])
  const refresh = useCallback(async () => {
    const s = await api<Status>('/cloud')
    setStatus(s)
    if (s.signed_in) loadCases()
  }, [loadCases])
  useEffect(() => {
    refresh().catch(say)
  }, [refresh])
  useEffect(() => {  // the app sidebar shows the sign-in state
    if (status) window.dispatchEvent(new CustomEvent('nyaya-cloud', { detail: status }))
  }, [status])

  async function run(fn: () => Promise<unknown>) {
    setBusy(true)
    try {
      await fn()
    } catch (e) {
      say(e)
    } finally {
      setBusy(false)
    }
  }

  const connect = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      setStatus(await api<Status>('/cloud/config', { method: 'PUT', json: form }))
    })
  }
  const signIn = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      const r = await api<NonNullable<Step> | { state: 'ok' }>('/cloud/login', { method: 'POST', json: login })
      setLogin({ ...login, password: '' })
      if (r.state === 'ok') await refresh()
      else setStep(r)
    })
  }
  const submitCode = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      await api('/cloud/mfa', { method: 'POST', json: { code } })
      setStep(null)
      setCode('')
      await refresh()
    })
  }
  const signOut = () =>
    run(async () => {
      setStatus(await api<Status>('/cloud/logout', { method: 'POST' }))
      setCases([])
      setStep(null)
    })
  const disconnect = () => run(async () => setStatus(await api<Status>('/cloud/config', { method: 'DELETE' })))

  async function pull(c: CloudCase, force = false) {
    try {
      await api(`/cloud/cases/${c.id}/pull`, { method: 'POST', json: { label: c.label ?? `Cloud case ${c.id.slice(0, 4)}`, force } })
      toast.success('Downloaded. Unlock it with the case passphrase.')
      loadCases()
      onLocalChange()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.message.includes('never uploaded') && !force) {
        if (window.confirm(`${e.message}\n\nReplace this laptop's copy with the cloud version?`)) return pull(c, true)
        return
      }
      say(e)
    }
  }

  if (!status) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {status.signed_in ? <Cloud className="size-4" aria-hidden /> : <CloudOff className="size-4" aria-hidden />}
          Cloud sync
          <Badge variant={status.signed_in ? 'secondary' : 'outline'}>
            {!status.configured ? 'Not set up' : status.signed_in ? `Signed in as ${status.user}` : 'Signed out'}
          </Badge>
        </CardTitle>
        <CardDescription>
          Optional. Only encrypted case archives are uploaded; your passphrase and the readable text never leave this laptop.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {!status.configured && (
          <form onSubmit={connect} className="grid gap-3 sm:grid-cols-3">
            <div className="grid gap-2 sm:col-span-3">
              <Label htmlFor="api-url">API address</Label>
              <Input id="api-url" value={form.api_url} onChange={(e) => setForm({ ...form, api_url: e.target.value })} placeholder="https://abc123.execute-api.ap-south-1.amazonaws.com" required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="region">Region</Label>
              <Input id="region" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} required />
            </div>
            <div className="grid gap-2 sm:col-span-2">
              <Label htmlFor="client-id">App client id</Label>
              <Input id="client-id" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} required />
            </div>
            <p className="text-muted-foreground text-sm sm:col-span-3">Your administrator gives you these three values (the ApiUrl, Region and ClientId from the deployment).</p>
            <Button type="submit" disabled={busy} className="w-fit">Save</Button>
          </form>
        )}

        {status.configured && !status.signed_in && !step && (
          <form onSubmit={signIn} className="grid gap-3 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="cloud-user">Email</Label>
              <Input id="cloud-user" type="email" autoComplete="username" value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="cloud-pass">Cloud password</Label>
              <Input id="cloud-pass" type="password" autoComplete="current-password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} required />
            </div>
            <p className="text-muted-foreground text-sm sm:col-span-2">This is your account password for the cloud, not a case passphrase.</p>
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={busy}>Sign in</Button>
              <ConfirmAction
                trigger={<Button type="button" variant="ghost">Change cloud settings</Button>}
                title="Remove the cloud settings?" description="You will need the API address, region and client id again to reconnect." action="Remove" onConfirm={disconnect}
              />
            </div>
          </form>
        )}

        {step && (
          <form onSubmit={submitCode} className="grid gap-3">
            {step.state === 'mfa_setup' ? (
              <Alert>
                <AlertTitle>Set up your authenticator app (first sign-in)</AlertTitle>
                <AlertDescription className="grid gap-2">
                  <p>In an authenticator app choose “Enter a setup key” and type this key, then enter the 6-digit code it shows.</p>
                  <p className="flex flex-wrap items-center gap-2">
                    <code className="bg-muted rounded px-2 py-1 font-mono text-sm break-all">{step.secret}</code>
                    <Button type="button" size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(step.secret).then(() => toast.success('Copied'))}><Copy /> Copy</Button>
                  </p>
                </AlertDescription>
              </Alert>
            ) : (
              <p className="text-sm">Enter the 6-digit code from your authenticator app.</p>
            )}
            <div className="flex max-w-xs items-end gap-2">
              <div className="grid flex-1 gap-2">
                <Label htmlFor="mfa-code">Code</Label>
                <Input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
              </div>
              <Button type="submit" disabled={busy}>Verify</Button>
            </div>
            <Button type="button" variant="link" className="w-fit px-0" onClick={() => { setStep(null); setCode('') }}>Start over</Button>
          </form>
        )}

        {status.signed_in && (
          <>
            {cases.length === 0 ? (
              <p className="text-muted-foreground text-sm">Nothing in the cloud yet. Open a case, then Settings, then “Upload to cloud”.</p>
            ) : (
              <ul className="divide-y rounded-lg border">
                {cases.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2 text-sm">
                    <span className="min-w-0 flex-1">
                      <span className="font-medium">{c.label ?? 'Not on this laptop'}</span>{' '}
                      <span className="text-muted-foreground font-mono text-sm">{c.id.slice(0, 8)}</span>
                    </span>
                    <span className="text-muted-foreground tabular-nums">v{c.version} · {size(c.size)} · {new Date(c.updated).toLocaleString()}</span>
                    {c.local && c.synced_version === c.version && <Badge variant="secondary">Up to date</Badge>}
                    {c.local && c.synced_version !== c.version && <Badge variant="outline">Cloud has a different version</Badge>}
                    <Button size="sm" variant="outline" onClick={() => pull(c)}><CloudDownload /> Download</Button>
                    <ConfirmAction
                      trigger={<Button size="icon-sm" variant="ghost" aria-label="Delete from cloud"><Trash2 /></Button>}
                      title="Delete from the cloud?" description="Removes every cloud version of this case. The copy on this laptop is kept."
                      action="Delete from cloud"
                      onConfirm={() => api(`/cloud/cases/${c.id}`, { method: 'DELETE' }).then(() => { loadCases(); onLocalChange() }).catch(say)}
                    />
                  </li>
                ))}
              </ul>
            )}
            <Button variant="outline" size="sm" className="w-fit" onClick={signOut} disabled={busy}><LogOut /> Sign out of the cloud</Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// Per-case card for the Settings tab.
export function CaseCloud({ base, onError }: { base: string; onError: (e: unknown) => void }) {
  const [info, setInfo] = useState<{ version: number | null; dirty: boolean } | null>(null)
  const [signedIn, setSignedIn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [seen, setSeen] = useState<Inspection | null>(null)
  const load = useCallback(() => {
    api<{ version: number | null; dirty: boolean }>(`${base}/cloud`).then(setInfo).catch(onError)
    api<Status>('/cloud').then((s) => setSignedIn(s.signed_in)).catch(onError)
  }, [base, onError])
  useEffect(load, [load])

  async function push() {
    setBusy(true)
    try {
      const r = await api<{ version: number }>(`${base}/cloud/push`, { method: 'POST' })
      toast.success(`Uploaded as version ${r.version}.`)
      setSeen(null)
      load()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function inspect() {
    setBusy(true)
    try {
      setSeen(await api<Inspection>(`${base}/cloud/inspect`))
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
    <Card>
      <CardHeader>
        <CardTitle>Cloud sync</CardTitle>
        <CardDescription>
          Uploads the encrypted case so you can open it on another laptop with the same passphrase. Lose the passphrase and the cloud copy cannot be opened either.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-3">
        <Button variant="outline" onClick={push} disabled={busy || !signedIn || (info !== null && !info.dirty && info.version !== null)}>
          <Cloud /> {busy ? 'Uploading…' : 'Upload to cloud'}
        </Button>
        <span className="text-muted-foreground text-sm">
          {info === null ? '' : info.version === null ? 'Never uploaded.' : info.dirty ? `Last uploaded v${info.version}. Changes since then are not uploaded.` : `Up to date with cloud v${info.version}.`}
        </span>
        {!signedIn && <span className="text-muted-foreground text-sm">Sign in from the case list first.</span>}
        {signedIn && info?.version != null && (
          <Button variant="ghost" onClick={inspect} disabled={busy}><Eye /> Show what the cloud stores</Button>
        )}
      </CardContent>
    </Card>
    {seen && <CloudProof seen={seen} />}
    </>
  )
}

// Downloads the latest cloud copy (on the server side) and shows it as AWS holds it.
function CloudProof({ seen }: { seen: Inspection }) {
  const clean = seen.found.length === 0
  return (
    <Card>
      <CardHeader>
        <CardTitle>What AWS stores for this case (version {seen.version})</CardTitle>
        <CardDescription>Fetched from the cloud just now. This is everything AWS holds; it has no key to read any of it.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm">
        <Alert variant={clean ? 'default' : 'destructive'}>
          {clean ? <ShieldCheck /> : <ShieldX />}
          <AlertTitle>{clean ? 'No readable case text in the cloud copy' : 'Readable words found in the cloud copy'}</AlertTitle>
          <AlertDescription>
            {clean
              ? `Searched the encrypted files for all ${seen.words_checked} words and file names of this case: none found.`
              : seen.found.join(', ')}
          </AlertDescription>
        </Alert>

        <div className="grid gap-1">
          <h3 className="font-medium">Index row (DynamoDB)</h3>
          <p className="text-muted-foreground text-sm">All the cloud knows about the case: ids, version, size, time.</p>
          <pre className="bg-muted overflow-x-auto rounded p-3 font-mono text-sm">{JSON.stringify(seen.index, null, 2)}</pre>
        </div>

        <div className="grid gap-1">
          <h3 className="font-medium">Archive object (S3), {size(seen.size)}</h3>
          <p className="text-muted-foreground text-sm">
            Each file starts with random-looking bytes: AES-256-GCM ciphertext. <code>vault.json</code> is readable on purpose: it holds the key-derivation
            settings and the wrapped key, useless without the passphrase.
          </p>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm">
              <thead className="bg-muted text-left">
                <tr><th className="px-3 py-2 font-medium">File</th><th className="px-3 py-2 text-right font-medium">Bytes</th><th className="px-3 py-2 font-medium">First bytes (hex)</th></tr>
              </thead>
              <tbody className="divide-y font-mono">
                {seen.files.map((f) => (
                  <tr key={f.name}>
                    <td className="px-3 py-1.5 break-all">{f.name}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{f.size}</td>
                    <td className="text-muted-foreground px-3 py-1.5">{f.starts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
