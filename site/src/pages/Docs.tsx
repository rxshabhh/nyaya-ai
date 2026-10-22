import { Link } from 'react-router-dom'
import { Code, PageHeader, useTitle } from '@/components/bits'

const CLAIM = `{"doc": "PW1_court_deposition.txt", "page": 1, "para": 2, "actor": "Suresh",
 "event": "accused_arrives", "date": "12.03.2021", "time": "9 pm", "place": "house",
 "exact_quote": "On 12.03.2021 at about 9 pm I was at my house when the accused Suresh came there."}`

const TXT = `[page 1]

I am Ramesh Kumar. I run a grocery shop in Anna Nagar.

On the intervening night of 12/13.03.2021 at about 11 pm, I was closing my shop...

[page 2]

I went to the Anna Nagar police station the next morning...`

const SECTIONS = [
  { id: 'install', title: 'Install and launch' },
  { id: 'documents', title: 'Adding documents' },
  { id: 'analysis', title: 'Running an analysis' },
  { id: 'findings', title: 'Reading findings' },
  { id: 'backup', title: 'Backup and restore' },
  { id: 'cloud', title: 'Cloud sync' },
  { id: 'format', title: 'Claims file format' },
  { id: 'troubleshooting', title: 'Troubleshooting' },
]

const H = ({ id, children }: { id: string; children: string }) => (
  <h2 id={id} className="scroll-mt-20 pt-10 text-2xl font-semibold tracking-tight first:pt-0">{children}</h2>
)
const P = ({ children }: { children: React.ReactNode }) => <p className="text-muted-foreground mt-3 leading-relaxed">{children}</p>
const K = ({ children }: { children: string }) => <code className="bg-muted rounded px-1.5 py-0.5 text-sm">{children}</code>

export default function Docs() {
  useTitle('Documentation')
  return (
    <>
      <PageHeader eyebrow="Documentation" title="Using Nyaya AI" lead="From installing to reading your first finding." />
      <div className="grid w-full gap-10 px-6 lg:px-10 py-12 grid-cols-[minmax(0,1fr)] lg:grid-cols-[14rem_minmax(0,1fr)]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-20 grid gap-1 text-sm">
            {SECTIONS.map((s) => <li key={s.id}><a href={`#${s.id}`} className="text-muted-foreground hover:text-foreground block rounded px-2 py-1">{s.title}</a></li>)}
          </ul>
        </nav>

        <article className="max-w-3xl">
          <H id="install">Install and launch</H>
          <P>You need Python 3.11 or newer and Node 22 or newer (Node is only needed once, to build the screen). Windows is the target; the app runs on the CPU, with no special hardware.</P>
          <div className="mt-4"><Code>{`git clone https://github.com/rxshabhh/nyaya-ai.git
cd nyaya-ai
pip install -r requirements.txt
cd site
npm install
npm run build
cd ..
python -m nyaya`}</Code></div>
          <P>Your browser opens this website on the <strong>Open app</strong> page, served from your own laptop. The address contains a one-time key that is created on every launch, so the app works only in the window the launcher opened. Run <K>python -m nyaya --no-browser</K> to print the address without opening it.</P>
          <P>For a first look, choose <strong>Try the demo case</strong>. It loads a fictional case with planted errors and needs no AI model.</P>

          <H id="documents">Adding documents</H>
          <P>Create a case with a code name and a passphrase, then add each document with its witness, type and date. Filename hints prefill the form, and you confirm them.</P>
          <ul className="text-muted-foreground mt-3 list-disc space-y-1 pl-5">
            <li><strong>Formats:</strong> text (<K>.txt</K>), digital PDF, Word (<K>.docx</K>), up to 50 MB each, in English.</li>
            <li><strong>Types:</strong> police statement, FIR, chargesheet, examination-in-chief, cross-examination. The first three count as earlier statements; the last two as court testimony.</li>
            <li><strong>Dates:</strong> the date of the statement.</li>
            <li><strong>Scans:</strong> a scanned PDF is refused with the page numbers that have no text. Version 1 has no OCR.</li>
            <li><strong>Pages:</strong> PDFs use their real pages. Word files count as page 1 unless they have hard page breaks. In text files, mark pages with a line <K>[page N]</K>.</li>
          </ul>
          <div className="mt-4"><Code>{TXT}</Code></div>
          <P>A chargesheet holds many witnesses. For now, add it once per witness, with that witness’s extract. Automatic splitting is planned.</P>

          <H id="analysis">Running an analysis</H>
          <P>Install <a className="text-foreground underline" href="https://ollama.com" rel="noreferrer" target="_blank">Ollama</a>, then fetch a model for extraction and one for matching:</P>
          <div className="mt-3"><Code>{`ollama pull llama3.2:3b
ollama pull all-minilm`}</Code></div>
          <P>Choose <strong>Run analysis</strong> on the Documents tab. A progress bar shows paragraph by paragraph. Paragraphs the model could not read are listed, and one bad paragraph never stops the case. You can type another Ollama model name in the box. If you already have claims, choose <strong>Import claims file</strong> and use the format below.</P>

          <H id="findings">Reading findings</H>
          <ul className="text-muted-foreground mt-3 list-disc space-y-2 pl-5">
            <li><strong>Contradiction:</strong> same witness, same event, different documents, and a differing date, time, place or amount. Earlier statement on the left, court testimony on the right.</li>
            <li><strong>Omission:</strong> an event in one statement that is absent from the other. “Likely material” is a keyword ranking only.</li>
            <li><strong>Confirm / Dismiss / Reopen:</strong> your decision is saved with the case and kept when you re-run the analysis.</li>
            <li><strong>Not in latest analysis:</strong> findings an earlier run produced and the latest run did not. They are kept in a collapsed list with your decision.</li>
            <li><strong>Rejected claims:</strong> claims the gate threw out, each with the reason.</li>
          </ul>
          <P>Use <strong>Print or save as PDF</strong> on the Findings tab for a copy for your notes.</P>

          <H id="backup">Backup and restore</H>
          <P>Use the download button on a case to save an encrypted <K>.nyaya</K> archive. It holds only ciphertext and needs the same passphrase to open. To restore, choose <strong>Restore archive</strong> on the case list, give it a code name, and unlock it with its original passphrase.</P>

          <H id="cloud">Cloud sync (optional)</H>
          <P>To open the same case on another laptop, enter the API address, region and client id from your administrator in the <strong>Cloud sync</strong> card, then sign in with your email, password and authenticator code. Open a case, go to <strong>Settings</strong> and choose <strong>Upload to cloud</strong>. Only the encrypted archive is uploaded.</P>
          <P>Choose <strong>Show what the cloud stores</strong> to fetch the cloud copy back and see it as AWS holds it: the index row, each encrypted file with its first bytes, and a search for every word of the case. It should say none were found.</P>

          <H id="format">Claims file format</H>
          <P>Each claim must carry a citation and an exact quote. Date, time, place and amount are optional and, if present, must appear inside the quote.</P>
          <div className="mt-3"><Code>{CLAIM}</Code></div>

          <H id="troubleshooting">Troubleshooting</H>
          <ul className="text-muted-foreground mt-3 list-disc space-y-2 pl-5">
            <li><strong>“Start Nyaya AI on your laptop”:</strong> the page has no key. Close the tab and use the window <K>python -m nyaya</K> opens, or open the printed address.</li>
            <li><strong>“Website not built yet”:</strong> run <K>npm install</K> and <K>npm run build</K> in the <K>site</K> folder.</li>
            <li><strong>Analysis stopped, Ollama not answering:</strong> start Ollama and check that the model is pulled.</li>
            <li><strong>A document was refused:</strong> it is scanned, an unsupported type, over 50 MB, or a document with that name is already in the case.</li>
            <li><strong>“Case locked after being idle”:</strong> cases lock after 15 idle minutes. Unlock again with the passphrase.</li>
            <li><strong>Wrong passphrase:</strong> there is no recovery. See <Link className="text-foreground underline" to="/security">Security</Link>.</li>
          </ul>
        </article>
      </div>
    </>
  )
}
