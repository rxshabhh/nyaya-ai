import { useRef, useState } from 'react'
import { ChevronDown, FileText, Play, Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import type { StartAnalysis } from '@/components/CaseView'
import { ConfirmAction } from '@/components/common'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api, DOCTYPES, type DocInfo, type Doctype, type Job } from '@/lib/api'

// Filename hints prefill the form; the advocate confirms (INPUT_SPEC: metadata is never guessed silently).
export function hintDoctype(name: string): Doctype | '' {
  const n = name.toLowerCase()
  if (n.includes('cross')) return 'cross_examination'
  if (/chief|deposition|court|evidence/.test(n)) return 'examination_in_chief'
  if (n.includes('charge')) return 'chargesheet'
  if (/(^|[^a-z])fir([^a-z]|$)/.test(n)) return 'fir'
  if (/police|161|180|statement/.test(n)) return 'police_statement'
  return ''
}

export function hintDate(name: string): string { // yyyy-mm-dd for <input type="date">
  const m = name.match(/(\d{2})[.\-_](\d{2})[.\-_](\d{4})/) ?? name.match(/(\d{4})[.\-_](\d{2})[.\-_](\d{2})/)
  if (!m) return ''
  return m[1].length === 4 ? `${m[1]}-${m[2]}-${m[3]}` : `${m[3]}-${m[2]}-${m[1]}`
}

const toApiDate = (iso: string) => iso.split('-').reverse().join('.') // yyyy-mm-dd -> DD.MM.YYYY

export function Documents(props: {
  base: string
  docs: DocInfo[]
  job: Job | null
  onChange: () => void
  onError: (e: unknown) => void
  onAnalyze: StartAnalysis
}) {
  const { base, docs, job } = props
  const fileRef = useRef<HTMLInputElement>(null)
  const claimsRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [witness, setWitness] = useState('')
  const [doctype, setDoctype] = useState<Doctype | ''>('')
  const [date, setDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [model, setModel] = useState('')
  const running = job?.state === 'running'
  const witnesses = [...new Set(docs.map((d) => d.witness))].sort()

  function pick(f: File | null) {
    setFile(f)
    if (f) {
      setDoctype(hintDoctype(f.name) || doctype)
      setDate(hintDate(f.name) || date)
    }
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !doctype) return
    const form = new FormData()
    form.append('file', file)
    form.append('witness', witness)
    form.append('doctype', doctype)
    form.append('date', toApiDate(date))
    setBusy(true)
    try {
      await api(`${base}/documents`, { method: 'POST', body: form })
      toast.success(`${file.name} added.`)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
      props.onChange()
    } catch (err) {
      props.onError(err)
    } finally {
      setBusy(false)
    }
  }

  async function importClaims(f: File | undefined) {
    if (!f) return
    try {
      const claims = JSON.parse(await f.text())
      if (!Array.isArray(claims)) throw new Error('The claims file must hold a JSON list.')
      await props.onAnalyze({ mode: 'import', claims })
    } catch (err) {
      props.onError(err instanceof SyntaxError ? new Error(`${f.name} is not valid JSON.`) : err)
    } finally {
      if (claimsRef.current) claimsRef.current.value = ''
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <div className="grid content-start gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Add a document</CardTitle>
            <CardDescription>Text (.txt), digital PDF or Word (.docx), up to 50 MB. Scanned PDFs are refused: there is no OCR yet.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={upload} className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-2 sm:col-span-2">
                <Label htmlFor="doc-file">File</Label>
                <Input id="doc-file" ref={fileRef} type="file" accept=".txt,.pdf,.docx" required onChange={(e) => pick(e.target.files?.[0] ?? null)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="doc-witness">Witness</Label>
                <Input id="doc-witness" list="witnesses" value={witness} onChange={(e) => setWitness(e.target.value)} placeholder="Full name, e.g. Ramesh Kumar" required />
                <datalist id="witnesses">{witnesses.map((w) => <option key={w} value={w} />)}</datalist>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="doc-type">Document type</Label>
                <Select value={doctype} onValueChange={(v) => setDoctype(v as Doctype)} required>
                  <SelectTrigger id="doc-type" className="w-full"><SelectValue placeholder="Choose…" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(DOCTYPES).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="doc-date">Date of statement</Label>
                <Input id="doc-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={busy || !file || !doctype} className="w-full"><Upload /> {busy ? 'Reading…' : 'Add document'}</Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Documents by witness</CardTitle>
            <CardDescription>Each witness needs an earlier statement and court testimony to be compared.</CardDescription>
          </CardHeader>
          <CardContent>
            {docs.length === 0 ? (
              <p className="text-muted-foreground text-sm">No documents yet.</p>
            ) : (
              <div className="grid gap-5">
                {witnesses.map((w) => (
                  <section key={w} aria-label={w}>
                    <h3 className="mb-2 text-sm font-medium">{w}</h3>
                    <ul className="divide-y rounded-lg border">
                      {docs.filter((d) => d.witness === w).map((d) => (
                        <li key={d.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                          <FileText className="text-muted-foreground size-4 shrink-0" aria-hidden />
                          <span className="min-w-0 flex-1 truncate" title={d.name}>{d.name}</span>
                          <Badge variant={d.kind === 'court' ? 'default' : 'secondary'}>{DOCTYPES[d.doctype]}</Badge>
                          <span className="text-muted-foreground tabular-nums">{d.date}</span>
                          <ConfirmAction
                            trigger={<Button size="icon-sm" variant="ghost" aria-label={`Remove ${d.name}`}><Trash2 /></Button>}
                            title={`Remove ${d.name}?`}
                            description="The document is deleted from this case. Findings already made from it stay until the next analysis."
                            action="Remove"
                            onConfirm={() => api(`${base}/documents/${d.id}`, { method: 'DELETE' }).then(props.onChange).catch(props.onError)}
                          />
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="content-start">
        <CardHeader>
          <CardTitle>Analyse</CardTitle>
          <CardDescription>A local model reads each paragraph and pulls out claims. Every quote is checked against the document before it is used.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="model">Ollama model</Label>
            <Input id="model" value={model} onChange={(e) => setModel(e.target.value)} placeholder="llama3.2:3b" disabled={running} />
          </div>
          <Button disabled={running || docs.length === 0} onClick={() => props.onAnalyze({ mode: 'ollama', model: model.trim() || undefined })}>
            <Play /> Run analysis
          </Button>
          <Button variant="outline" disabled={running || docs.length === 0} onClick={() => claimsRef.current?.click()}>
            Import claims file (.json)
          </Button>
          <input ref={claimsRef} type="file" accept=".json,application/json" hidden onChange={(e) => importClaims(e.target.files?.[0])} />

          {running && (
            <div className="grid gap-2" aria-live="polite">
              <Progress value={job.total ? (job.done / job.total) * 100 : 0} />
              <p className="text-muted-foreground text-xs">{job.total ? `Paragraph ${job.done} of ${job.total}` : 'Starting…'}</p>
            </div>
          )}
          {job?.state === 'failed' && (
            <Alert variant="destructive">
              <AlertTitle>Analysis stopped</AlertTitle>
              <AlertDescription>
                <p>{job.message}</p>
                {/ollama/i.test(job.message) && <p className="mt-1">Install Ollama, run <code>ollama pull llama3.2:3b</code>, and try again.</p>}
              </AlertDescription>
            </Alert>
          )}
          {job?.state === 'done' && job.errors.length > 0 && (
            <Collapsible>
              <CollapsibleTrigger className="text-muted-foreground flex items-center gap-1 text-xs hover:underline">
                <ChevronDown className="size-3" aria-hidden /> {job.errors.length} paragraph(s) the model could not read
              </CollapsibleTrigger>
              <CollapsibleContent>
                <ul className="text-muted-foreground mt-2 grid gap-1 text-xs">
                  {job.errors.map((e, i) => <li key={i}>{e.doc}, p. {e.page}, para {e.para}: {e.error}</li>)}
                </ul>
              </CollapsibleContent>
            </Collapsible>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
