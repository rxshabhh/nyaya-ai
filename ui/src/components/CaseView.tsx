import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowLeft, KeyRound, Lock, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { ConfirmAction, PassphraseDialog } from '@/components/common'
import { Documents } from '@/components/Documents'
import { Findings, Rejected } from '@/components/Findings'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api, ApiError, type CaseInfo, type DocInfo, type Job, type Results } from '@/lib/api'

export type StartAnalysis = (body: { mode: 'ollama'; model?: string } | { mode: 'import'; claims: unknown[] }) => Promise<void>

export function CaseView({ info, onClose }: { info: CaseInfo; onClose: () => void }) {
  const [tab, setTab] = useState('documents')
  const [docs, setDocs] = useState<DocInfo[]>([])
  const [results, setResults] = useState<Results | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const base = `/cases/${info.id}`

  // A locked case (idle timeout or lock elsewhere) sends the advocate back to the list.
  const fail = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 423) {
      toast.info(`${info.label}: ${e.message}`)
      onClose()
    } else {
      toast.error(e instanceof Error ? e.message : String(e))
    }
  }, [info.label, onClose])

  const refresh = useCallback(async () => {
    try {
      const [d, r] = await Promise.all([api<DocInfo[]>(`${base}/documents`), api<Results>(`${base}/results`)])
      setDocs(d)
      setResults(r)
    } catch (e) {
      fail(e)
    }
  }, [base, fail])

  useEffect(() => {
    refresh()
    return () => window.clearTimeout(timer.current)
  }, [refresh])

  const poll = useCallback((id: string) => {
    api<Job>(`${base}/jobs/${id}`).then((j) => {
      setJob(j)
      if (j.state === 'running') {
        timer.current = window.setTimeout(() => poll(id), 700)
      } else if (j.state === 'done') {
        toast.success(j.errors.length ? `Analysis done. ${j.errors.length} paragraph(s) could not be read by the model.` : 'Analysis done.')
        refresh().then(() => setTab('findings'))
      }
    }).catch(fail)
  }, [base, fail, refresh])

  const start: StartAnalysis = async (body) => {
    try {
      const { job: id } = await api<{ job: string }>(`${base}/analyze`, { method: 'POST', json: body })
      setJob({ state: 'running', done: 0, total: 0, message: '', errors: [] })
      poll(id)
    } catch (e) {
      fail(e)
    }
  }

  async function lock() {
    await api(`${base}/lock`, { method: 'POST' }).catch(() => {})
    onClose()
  }

  const open = results?.findings.filter((f) => !f.stale && f.state === 'open').length ?? 0

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}><ArrowLeft /> All cases</Button>
          <h1 className="text-2xl font-semibold tracking-tight">{info.label}</h1>
        </div>
        <Button variant="outline" size="sm" onClick={lock}><Lock /> Lock case</Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="print:hidden">
          <TabsTrigger value="documents">Documents ({docs.length})</TabsTrigger>
          <TabsTrigger value="findings">Findings{open ? ` (${open} to review)` : ''}</TabsTrigger>
          <TabsTrigger value="rejected">Rejected claims</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="documents" className="pt-4">
          <Documents base={base} docs={docs} job={job} onChange={refresh} onError={fail} onAnalyze={start} />
        </TabsContent>
        <TabsContent value="findings" className="pt-4">
          <Findings base={base} label={info.label} docs={docs} results={results} onChange={setResults} onError={fail} />
        </TabsContent>
        <TabsContent value="rejected" className="pt-4">
          <Rejected claims={results?.rejected ?? []} />
        </TabsContent>
        <TabsContent value="settings" className="grid gap-4 pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Passphrase</CardTitle>
              <CardDescription>Changing it re-wraps the case key; documents are not re-encrypted.</CardDescription>
            </CardHeader>
            <CardContent>
              <PassphraseDialog
                trigger={<Button variant="outline"><KeyRound /> Change passphrase</Button>}
                title="Change passphrase"
                description="The old passphrase stops working immediately."
                submit="Change"
                confirm
                onSubmit={async (passphrase) => {
                  try {
                    await api(`${base}/passphrase`, { method: 'POST', json: { passphrase } })
                    toast.success('Passphrase changed.')
                  } catch (e) {
                    if (e instanceof ApiError && e.status === 423) fail(e)
                    else throw e
                  }
                }}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Delete case</CardTitle>
              <CardDescription>Removes every document, finding and decision for this case from this laptop.</CardDescription>
            </CardHeader>
            <CardContent>
              <ConfirmAction
                trigger={<Button variant="destructive"><Trash2 /> Delete case</Button>}
                title={`Delete ${info.label}?`}
                description="This cannot be undone. The encrypted files are removed from disk."
                action="Delete case"
                onConfirm={() => api(base, { method: 'DELETE' }).then(() => { toast.success('Case deleted.'); onClose() }).catch(fail)}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
