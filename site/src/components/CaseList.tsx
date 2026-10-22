import { useCallback, useEffect, useRef, useState } from 'react'
import { Cloud, Download, FolderClosed, FolderLock, FolderOpen, Lock, LockOpen, Plus, Sparkles, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { CloudPanel } from '@/components/CloudPanel'
import { PassphraseDialog, StatTile } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { api, download, type CaseInfo } from '@/lib/api'

export function CaseList({ onOpen }: { onOpen: (c: CaseInfo) => void }) {
  const [cases, setCases] = useState<CaseInfo[] | null>(null)
  const archive = useRef<HTMLInputElement>(null)

  const load = useCallback(() => {
    api<CaseInfo[]>('/cases').then(setCases).catch((e) => toast.error(e.message))
  }, [])
  useEffect(load, [load])

  async function lock(c: CaseInfo) {
    await api(`/cases/${c.id}/lock`, { method: 'POST' }).catch((e) => toast.error(e.message))
    load()
  }

  async function restore(f: File | undefined) {
    if (!f) return
    const label = window.prompt('Code name for the restored case', f.name.replace(/\.nyaya$/i, ''))
    if (archive.current) archive.current.value = ''
    if (!label) return
    const form = new FormData()
    form.append('file', f)
    form.append('label', label)
    try {
      await api('/cases/import', { method: 'POST', body: form })
      toast.success('Case restored. Unlock it with its original passphrase.')
      load()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    }
  }

  const all = cases ?? []
  const unlocked = all.filter((c) => c.unlocked).length
  const inCloud = all.filter((c) => c.cloud_version).length

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Cases</h1>
          <p className="text-muted-foreground mt-1">Each case is encrypted on this laptop with its own passphrase.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => archive.current?.click()}><Upload /> Restore archive</Button>
          <input ref={archive} type="file" accept=".nyaya,.zip" hidden onChange={(e) => restore(e.target.files?.[0])} />
          <PassphraseDialog
            trigger={<Button variant="outline"><Sparkles /> Try the demo case</Button>}
            title="Demo case"
            description="Loads a fictional robbery case with planted errors, so you can see findings without a local model."
            submit="Create demo"
            confirm
            onSubmit={async (passphrase) => {
              const c = await api<{ id: string; label: string }>('/demo', { method: 'POST', json: { passphrase } })
              onOpen({ ...c, unlocked: true })
            }}
          />
          <PassphraseDialog
            trigger={<Button><Plus /> New case</Button>}
            title="New case"
            description="Documents and findings are encrypted on this laptop with the passphrase you choose."
            submit="Create case"
            withLabel
            confirm
            onSubmit={async (passphrase, label) => {
              const c = await api<{ id: string; label: string }>('/cases', { method: 'POST', json: { label, passphrase } })
              onOpen({ ...c, unlocked: true })
            }}
          />
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Cases on this laptop" value={all.length} icon={FolderClosed} hint="Encrypted, AES-256-GCM" />
        <StatTile label="Unlocked now" value={unlocked} icon={LockOpen} hint="Lock after 15 idle minutes" />
        <StatTile label="Locked" value={all.length - unlocked} icon={Lock} hint="Need the passphrase" tone="light" />
        <StatTile label="In the AWS locker" value={inCloud} icon={Cloud} tone="accent" hint="Only ciphertext uploaded" />
      </dl>

      {cases === null ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : cases.length === 0 ? (
        <Card className="items-center py-12 text-center">
          <CardTitle className="text-xl">No cases yet</CardTitle>
          <CardDescription className="text-base">Create a case, or open the demo case to see how findings look.</CardDescription>
        </Card>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {cases.map((c) => (
            <li key={c.id}>
              <Card className="h-full gap-4 p-5 transition-shadow hover:shadow-md">
                <div className="flex items-start gap-3">
                  <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${c.unlocked ? 'bg-emerald-100 text-emerald-800' : 'bg-muted text-muted-foreground'}`}>
                    {c.unlocked ? <FolderOpen className="size-5" aria-hidden /> : <FolderLock className="size-5" aria-hidden />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-lg font-semibold">{c.label}</p>
                    <p className="mt-1 flex flex-wrap gap-1.5">
                      <Badge variant={c.unlocked ? 'secondary' : 'outline'}>{c.unlocked ? 'Unlocked' : 'Locked'}</Badge>
                      {c.cloud_version ? <Badge variant="outline" className="border-orange-300 text-orange-800"><Cloud /> Cloud v{c.cloud_version}</Badge> : null}
                    </p>
                  </div>
                </div>
                <div className="mt-auto flex flex-wrap items-center gap-2">
                  {c.unlocked ? (
                    <>
                      <Button onClick={() => onOpen(c)}>Open</Button>
                      <Button variant="outline" onClick={() => lock(c)} aria-label={`Lock ${c.label}`}><Lock /> Lock</Button>
                    </>
                  ) : (
                    <PassphraseDialog
                      trigger={<Button>Unlock</Button>}
                      title={`Unlock ${c.label}`}
                      description="Enter this case's passphrase."
                      submit="Unlock"
                      onSubmit={async (passphrase) => {
                        await api(`/cases/${c.id}/unlock`, { method: 'POST', json: { passphrase } })
                        onOpen({ ...c, unlocked: true })
                      }}
                    />
                  )}
                  <Button variant="ghost" className="ml-auto" onClick={() => download(`/cases/${c.id}/export`).catch((e) => toast.error(e.message))} aria-label={`Export ${c.label} as an encrypted archive`} title="Export encrypted archive"><Download /></Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <div id="cloud-sync" className="scroll-mt-24">
        <CloudPanel onLocalChange={load} />
      </div>
    </div>
  )
}
