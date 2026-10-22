import { Link } from 'react-router-dom'
import { Code2, Download } from 'lucide-react'
import { Code, PageHeader, Section, useTitle } from '@/components/bits'
import { Button } from '@/components/ui/button'
import { REPO } from '@/content'

const REQS = [
  ['Windows 11', 'Any laptop. Snapdragon X (ARM64) is the target, but the CPU works everywhere.'],
  ['Python 3.11+', 'Runs the pipeline and the local app.'],
  ['Node 22+', 'Only to build the website, once.'],
  ['Ollama', 'Runs the language model on your laptop. Needed for your own cases, not for the demo.'],
]

export default function GetStarted() {
  useTitle('Get started')
  return (
    <>
      <PageHeader eyebrow="Get started" title="Running in a few minutes" lead="There is no installer yet. Nyaya AI is free and open source, and you run it from source." />
      <Section title="What you need">
        <dl className="grid gap-3 sm:grid-cols-2">
          {REQS.map(([t, d]) => (
            <div key={t} className="bg-card rounded-xl border p-5">
              <dt className="font-semibold">{t}</dt>
              <dd className="text-muted-foreground mt-1 text-sm">{d}</dd>
            </div>
          ))}
        </dl>
      </Section>
      <Section tone="muted" title="Three commands to the demo case">
        <ol className="grid max-w-3xl grid-cols-[minmax(0,1fr)] gap-6">
          <li>
            <h3 className="mb-2 font-semibold">1. Get the code and install</h3>
            <Code>{`git clone ${REPO}.git
cd nyaya-ai
pip install -r requirements.txt`}</Code>
          </li>
          <li>
            <h3 className="mb-2 font-semibold">2. Build the website, once</h3>
            <Code>{`cd site
npm install
npm run build
cd ..`}</Code>
          </li>
          <li>
            <h3 className="mb-2 font-semibold">3. Launch</h3>
            <Code>python -m nyaya</Code>
            <p className="text-muted-foreground mt-2 text-sm">Your browser opens this website from your laptop, on the app page. Choose “Try the demo case”, pick a passphrase, and open the Findings tab. The demo needs no AI model.</p>
          </li>
        </ol>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild><a href={`${REPO}/archive/refs/heads/main.zip`}><Download /> Download source (zip)</a></Button>
          <Button asChild variant="outline"><a href={REPO} rel="noreferrer" target="_blank"><Code2 /> View on GitHub</a></Button>
          <Button asChild variant="outline"><Link to="/docs">Read the docs</Link></Button>
        </div>
      </Section>
      <Section title="Then use your own case">
        <ol className="text-muted-foreground grid max-w-3xl list-decimal gap-2 pl-5">
          <li>Install Ollama and run <code className="bg-muted rounded px-1.5 py-0.5 text-sm">ollama pull llama3.2:3b</code> and <code className="bg-muted rounded px-1.5 py-0.5 text-sm">ollama pull all-minilm</code>.</li>
          <li>Create a case with a code name (not the client’s name) and a passphrase you will not lose.</li>
          <li>Add each witness’s earlier statement and court testimony.</li>
          <li>Run the analysis and review every finding yourself.</li>
        </ol>
        <p className="text-muted-foreground mt-6 max-w-3xl text-sm">A one-click Windows installer is planned. Until then, the steps above are the supported route.</p>
      </Section>
    </>
  )
}
