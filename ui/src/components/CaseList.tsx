import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, FolderLock, FolderOpen, Lock, Plus, Sparkles, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { PassphraseDialog } from '@/components/common'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Cases</h1>
          <p className="text-muted-foreground text-sm">Each case is encrypted with its own passphrase.</p>
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

      {cases === null ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : cases.length === 0 ? (
        <Card className="items-center py-12 text-center">
          <CardTitle>No cases yet</CardTitle>
          <CardDescription>Create a case, or open the demo case to see how findings look.</CardDescription>
        </Card>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {cases.map((c) => (
            <li key={c.id}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {c.unlocked ? <FolderOpen className="size-4" aria-hidden /> : <FolderLock className="size-4" aria-hidden />}
                    {c.label}
                  </CardTitle>
                  <CardDescription>
                    <Badge variant={c.unlocked ? 'secondary' : 'outline'}>{c.unlocked ? 'Unlocked' : 'Locked'}</Badge>
                  </CardDescription>
                  <CardAction className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => download(`/cases/${c.id}/export`).catch((e) => toast.error(e.message))} aria-label={`Export ${c.label} as an encrypted archive`} title="Export encrypted archive"><Download /></Button>
                    {c.unlocked ? (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => lock(c)} aria-label={`Lock ${c.label}`}><Lock /></Button>
                        <Button size="sm" onClick={() => onOpen(c)}>Open</Button>
                      </>
                    ) : (
                      <PassphraseDialog
                        trigger={<Button size="sm">Unlock</Button>}
                        title={`Unlock ${c.label}`}
                        description="Enter this case's passphrase."
                        submit="Unlock"
                        onSubmit={async (passphrase) => {
                          await api(`/cases/${c.id}/unlock`, { method: 'POST', json: { passphrase } })
                          onOpen({ ...c, unlocked: true })
                        }}
                      />
                    )}
                  </CardAction>
                </CardHeader>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
