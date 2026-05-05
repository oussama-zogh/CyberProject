import { useState, useEffect } from 'react'
import {
  Key, Lock, Unlock, FileUp, FileDown, MessageSquare, MessageSquareOff,
  CheckCircle, XCircle, Loader, Info, Clock, Shield, ChevronRight, Copy
} from 'lucide-react'
import styles from './RSAPage.module.css'

const API = '/api/rsa'

// ── Fetch securise ─────────────────────────────────────────────────────────
async function safeFetch(url, opts) {
  let res
  try { res = await fetch(url, opts) }
  catch { throw new Error('Impossible de contacter le serveur backend (port 8000).') }
  const text = await res.text()
  let data = {}
  try { data = JSON.parse(text) } catch {}
  if (!res.ok) throw new Error(data.detail || `Erreur serveur ${res.status}`)
  return data
}

// ── Composants UI ──────────────────────────────────────────────────────────

function Alert({ type, msg }) {
  if (!msg) return null
  return (
    <div className={`${styles.alert} ${styles[type]}`}>
      {type === 'success' ? <CheckCircle size={15}/> : <XCircle size={15}/>}
      <span>{msg}</span>
    </div>
  )
}

function Spinner() {
  return <span className={styles.spinner}><Loader size={15}/></span>
}

function SigBadge({ valid }) {
  return valid
    ? <div className={`${styles.sigBadge} ${styles.sigOk}`}><CheckCircle size={14}/> Signature valide — integrite confirmee</div>
    : <div className={`${styles.sigBadge} ${styles.sigFail}`}><XCircle size={14}/> Signature invalide — fichier potentiellement altere</div>
}

function KeyBox({ label, color, pairs }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(pairs.map(([k,v]) => `${k} = ${v}`).join('\n'))
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className={styles.keyBox} style={{'--kc': color}}>
      <div className={styles.keyBoxHeader}>
        <span className={styles.keyBoxLabel}>{label}</span>
        <button className={styles.copyBtn} onClick={copy}><Copy size={11}/>{copied ? 'Copie!' : 'Copier'}</button>
      </div>
      {pairs.map(([k,v]) => (
        <div key={k} className={styles.keyPair}>
          <span className={styles.keyName}>{k}</span>
          <span className={styles.keyVal}>{String(v)}</span>
        </div>
      ))}
    </div>
  )
}

// Affiche les temps + formules apres chaque operation
function TimingBlock({ timing, formulas }) {
  if (!timing) return null
  return (
    <div className={styles.timingBlock}>
      <div className={styles.timingTitle}><Clock size={13}/> Temps d'execution</div>
      <div className={styles.timingRows}>
        {Object.entries(timing).map(([k, ms]) => (
          <div key={k} className={styles.timingRow}>
            <span className={styles.timingLabel}>{k.replace(/_ms$/, '').replace(/_/g, ' ')}</span>
            <span className={styles.timingVal}>{ms} ms</span>
          </div>
        ))}
      </div>
      {formulas && Object.keys(formulas).length > 0 && (
        <div className={styles.formulasBlock}>
          <div className={styles.formulasTitle}>Formules appliquees</div>
          {Object.entries(formulas).map(([k, f]) => (
            <div key={k} className={styles.formulaRow}>
              <span className={styles.formulaKey}>{k}</span>
              <span className={styles.formulaVal}>{f}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Etapes RSA — uniquement pour la generation de cle
function StepsList({ steps }) {
  if (!steps?.length) return null
  return (
    <div className={styles.steps}>
      <div className={styles.stepsTitle}><Info size={13}/> Etapes RSA</div>
      {steps.map((s, i) => <div key={i} className={styles.step}>{s}</div>)}
    </div>
  )
}

function DropZone({ id, label, file, onFile, accept }) {
  const [drag, setDrag] = useState(false)
  return (
    <div
      className={`${styles.dropZone} ${drag ? styles.dragging : ''} ${file ? styles.hasFile : ''}`}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) onFile(f) }}
      onClick={() => document.getElementById(id).click()}
    >
      <input id={id} type="file" accept={accept} hidden onChange={e => { if(e.target.files[0]) onFile(e.target.files[0]) }} />
      <FileUp size={22} className={styles.dropIcon}/>
      {file
        ? <div className={styles.fileInfo}><strong>{file.name}</strong><span>{(file.size/1024).toFixed(1)} KB</span></div>
        : <><p>{label}</p><p className={styles.dropHint}>ou cliquez pour selectionner</p></>
      }
    </div>
  )
}

function CopyField({ label, value, rows = 2 }) {
  const [copied, setCopied] = useState(false)
  const copy = () => { navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500) }
  return (
    <div className={styles.cipherField}>
      <div className={styles.cipherFieldHeader}>
        <span>{label}</span>
        <button className={styles.copyBtn} onClick={copy}><Copy size={11}/>{copied ? 'Copie!' : 'Copier'}</button>
      </div>
      <textarea readOnly className={styles.cipherText} value={value} rows={rows}/>
    </div>
  )
}

function dlText(content, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }))
  a.download = filename; a.click()
}

// ── SECTION 0: Cle Statique ────────────────────────────────────────────────

function StaticKeySection() {
  const [key, setKey] = useState(null)
  useEffect(() => {
    fetch(`${API}/static-key`).then(r => r.json()).then(setKey).catch(() => {})
  }, [])
  if (!key) return null
  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon} style={{background:'rgba(192,132,252,0.12)',color:'#c084fc'}}>
          <Shield size={18}/>
        </div>
        <div>
          <h2 className={styles.sectionTitle}>Cle Statique — Expediteur (Signature)</h2>
          <p className={styles.sectionSub}>Cle fixe du systeme utilisee pour signer les messages et fichiers</p>
        </div>
      </div>
      <div className={styles.staticNote}>
        <Info size={13}/>
        La cle <strong>privee signe</strong>, la cle <strong>publique verifie</strong>.
      </div>
      <div className={styles.keyGrid3}>
        <KeyBox label="Parametres" color="#c084fc"
          pairs={[['p', key.p], ['q', key.q], ['n', key.n], ['phi(n)', key.phi]]}/>
        <KeyBox label="Cle Publique — verifier" color="#c084fc"
          pairs={[['e', key.e], ['n', key.n]]}/>
        <KeyBox label="Cle Privee — signer" color="#c084fc"
          pairs={[['d', key.d], ['n', key.n]]}/>
      </div>
    </section>
  )
}

// ── SECTION 1: Generation cle dynamique ───────────────────────────────────

function KeyGenSection({ onKeyGenerated }) {
  const [p, setP] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [alert, setAlert] = useState(null)

  const handle = async () => {
    setAlert(null); setResult(null)
    if (!p || !q) { setAlert({ type:'error', msg:'Entrez p et q.' }); return }
    setLoading(true)
    try {
      const data = await safeFetch(`${API}/generate-key`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ p: parseInt(p), q: parseInt(q) }),
      })
      setResult(data)
      setAlert({ type:'success', msg: data.message })
      onKeyGenerated(data)
    } catch (err) { setAlert({ type:'error', msg: err.message }) }
    finally { setLoading(false) }
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon}><Key size={18}/></div>
        <div>
          <h2 className={styles.sectionTitle}>Generation de Cle RSA Dynamique</h2>
          <p className={styles.sectionSub}>Entrez p et q — e est choisi automatiquement</p>
        </div>
      </div>
      <div className={styles.infoStrip}>
        <Info size={12}/>
        Exemples : p=101, q=103 &nbsp;|&nbsp; p=211, q=7 &nbsp;|&nbsp; p=61, q=53
      </div>
      <div className={styles.inputRow2}>
        {[['p (nombre premier)', p, setP, 'ex. 101'], ['q (nombre premier)', q, setQ, 'ex. 103']].map(([lbl,val,set,ph]) => (
          <div key={lbl} className={styles.field}>
            <label className={styles.fieldLabel}>{lbl}</label>
            <input type="number" className={styles.input} placeholder={ph}
              value={val} onChange={ev => set(ev.target.value)}/>
          </div>
        ))}
      </div>
      <div className={styles.autoNote}>
        <ChevronRight size={12}/>
        e choisi parmi [65537, 257, 17, 7, 5, 3] tel que gcd(e, phi(n)) = 1
      </div>
      <button className={styles.btnPrimary} onClick={handle} disabled={loading}>
        {loading ? <Spinner/> : <Key size={15}/>}
        {loading ? 'Generation...' : 'Generer la cle'}
      </button>
      <Alert type={alert?.type} msg={alert?.msg}/>

      {result && (
        <>
          <div className={styles.timingBlock} style={{marginTop:12}}>
            <div className={styles.timingTitle}><Clock size={13}/> Temps d'execution</div>
            <div className={styles.timingRows}>
              <div className={styles.timingRow}>
                <span className={styles.timingLabel}>generation cle</span>
                <span className={styles.timingVal}>{result.elapsed_ms} ms</span>
              </div>
            </div>
          </div>
          <div className={styles.keyGrid3} style={{marginTop:16}}>
            <KeyBox label="Parametres" color="#ffb347"
              pairs={[['p', result.p], ['q', result.q], ['n', result.n], ['phi(n)', result.phi]]}/>
            <KeyBox label="Cle Publique — chiffrer" color="#2584e8"
              pairs={[['e', result.e], ['n', result.n]]}/>
            <KeyBox label="Cle Privee — dechiffrer" color="#00c896"
              pairs={[['d', result.d], ['n', result.n]]}/>
          </div>
          <StepsList steps={result.steps}/>
        </>
      )}
    </section>
  )
}

// ── SECTION 2: Chiffrement Fichier ─────────────────────────────────────────

function EncryptFileSection({ hasKey }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [alert, setAlert] = useState(null)

  const handle = async () => {
    if (!hasKey) { setAlert({ type:'error', msg:"Generez d'abord une cle dynamique." }); return }
    if (!file)   { setAlert({ type:'error', msg:'Selectionnez un fichier.' }); return }
    setLoading(true); setAlert(null); setResult(null)
    try {
      const fd = new FormData(); fd.append('file', file)
      const data = await safeFetch(`${API}/encrypt-file`, { method:'POST', body:fd })
      setResult(data)
      setAlert({ type:'success', msg: data.message })
    } catch (err) { setAlert({ type:'error', msg: err.message }) }
    finally { setLoading(false) }
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon} style={{background:'rgba(37,132,232,0.1)',color:'#2584e8'}}>
          <FileUp size={18}/>
        </div>
        <div>
          <h2 className={styles.sectionTitle}>Chiffrement de Fichier</h2>
          <p className={styles.sectionSub}>Cle publique dynamique · Signature cle privee statique</p>
        </div>
      </div>
      {!hasKey && <div className={styles.warningBanner}><ChevronRight size={12}/>Generez d'abord une cle dynamique.</div>}
      <DropZone id="enc-file" label="Glissez un fichier ici" file={file}
        onFile={f => { setFile(f); setResult(null); setAlert(null) }}/>
      <button className={styles.btnPrimary} onClick={handle} disabled={loading || !hasKey}>
        {loading ? <Spinner/> : <Lock size={15}/>}
        {loading ? 'Chiffrement...' : 'Chiffrer le fichier'}
      </button>
      <Alert type={alert?.type} msg={alert?.msg}/>
      {result && (
        <div className={styles.resultBlock}>
          <div className={styles.hashLine}>
            <span className={styles.hashLabel}>SHA-256 (original)</span>
            <span className={styles.hashVal}>{result.file_hash}</span>
          </div>
          <TimingBlock timing={result.timing} formulas={result.formulas}/>
          <div className={styles.downloadRow}>
            <button className={styles.btnDownload}
              onClick={() => dlText(result.ciphertext, `encrypted_${result.filename}.enc`)}>
              <FileDown size={14}/> Fichier chiffre (.enc)
            </button>
            <button className={`${styles.btnDownload} ${styles.btnSig}`}
              onClick={() => dlText(result.signature, `signature_${result.filename}.sig`)}>
              <Shield size={14}/> Signature (.sig)
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// ── SECTION 3: Dechiffrement Fichier ──────────────────────────────────────

function DecryptFileSection({ hasKey }) {
  const [file, setFile]       = useState(null)
  const [sigFile, setSigFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [alert, setAlert]     = useState(null)

  const handle = async () => {
    if (!hasKey)  { setAlert({ type:'error', msg:"Generez d'abord une cle dynamique." }); return }
    if (!file)    { setAlert({ type:'error', msg:'Selectionnez le fichier chiffre (.enc).' }); return }
    if (!sigFile) { setAlert({ type:'error', msg:'Selectionnez le fichier signature (.sig).' }); return }
    setLoading(true); setAlert(null); setResult(null)
    try {
      const sigText = await sigFile.text()
      const fd = new FormData()
      fd.append('file', file)
      fd.append('signature', sigText.trim())
      const data = await safeFetch(`${API}/decrypt-file`, { method:'POST', body:fd })
      setResult(data)
      setAlert({ type:'success', msg: data.message })
    } catch (err) { setAlert({ type:'error', msg: err.message }) }
    finally { setLoading(false) }
  }

  // Telecharger le fichier dechiffre depuis le base64 retourne par le serveur
  const downloadDecrypted = () => {
    if (!result?.decrypted_b64) return
    const bytes = Uint8Array.from(atob(result.decrypted_b64), c => c.charCodeAt(0))
    const blob = new Blob([bytes])
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `decrypted_${result.filename}`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon} style={{background:'rgba(0,200,150,0.1)',color:'#00c896'}}>
          <FileDown size={18}/>
        </div>
        <div>
          <h2 className={styles.sectionTitle}>Dechiffrement de Fichier</h2>
          <p className={styles.sectionSub}>Cle privee dynamique · Verification signature statique</p>
        </div>
      </div>
      {!hasKey && <div className={styles.warningBanner}><ChevronRight size={12}/>Generez d'abord une cle dynamique.</div>}
      <div className={styles.twoDrops}>
        <div>
          <p className={styles.dropLabel}>Fichier chiffre (.enc)</p>
          <DropZone id="dec-file" label="Fichier chiffre" file={file}
            onFile={f => { setFile(f); setResult(null); setAlert(null) }} accept=".enc"/>
        </div>
        <div>
          <p className={styles.dropLabel}>Signature (.sig)</p>
          <DropZone id="dec-sig" label="Fichier signature" file={sigFile}
            onFile={f => { setSigFile(f); setResult(null); setAlert(null) }} accept=".sig"/>
        </div>
      </div>
      <button className={`${styles.btnPrimary} ${styles.btnGreen}`} onClick={handle} disabled={loading || !hasKey}>
        {loading ? <Spinner/> : <Unlock size={15}/>}
        {loading ? 'Dechiffrement...' : 'Dechiffrer et verifier'}
      </button>
      <Alert type={alert?.type} msg={alert?.msg}/>
      {result && (
        <div className={styles.resultBlock}>
          <div className={styles.hashLine}>
            <span className={styles.hashLabel}>SHA-256 (dechiffre)</span>
            <span className={styles.hashVal}>{result.file_hash}</span>
          </div>
          <TimingBlock timing={result.timing} formulas={result.formulas}/>
          <SigBadge valid={result.signature_valid}/>
          <div className={styles.downloadRow} style={{marginTop:12}}>
            <button className={styles.btnDownload} onClick={downloadDecrypted}>
              <FileDown size={14}/> Telecharger le fichier dechiffre
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// ── SECTION 4: Chiffrement Message ────────────────────────────────────────

function EncryptMessageSection({ hasKey }) {
  const [msg, setMsg]         = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [alert, setAlert]     = useState(null)

  const handle = async () => {
    if (!hasKey)    { setAlert({ type:'error', msg:"Generez d'abord une cle dynamique." }); return }
    if (!msg.trim()) { setAlert({ type:'error', msg:'Entrez un message.' }); return }
    setLoading(true); setAlert(null); setResult(null)
    try {
      const data = await safeFetch(`${API}/encrypt-message`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ message: msg }),
      })
      setResult(data)
      setAlert({ type:'success', msg: data.message })
    } catch (err) { setAlert({ type:'error', msg: err.message }) }
    finally { setLoading(false) }
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon} style={{background:'rgba(255,179,71,0.1)',color:'#ffb347'}}>
          <MessageSquare size={18}/>
        </div>
        <div>
          <h2 className={styles.sectionTitle}>Chiffrement de Message</h2>
          <p className={styles.sectionSub}>Hash · Signature statique · Chiffrement dynamique</p>
        </div>
      </div>
      {!hasKey && <div className={styles.warningBanner}><ChevronRight size={12}/>Generez d'abord une cle dynamique.</div>}
      <textarea className={styles.textarea} rows={4}
        placeholder="Entrez votre message ici..."
        value={msg} onChange={e => { setMsg(e.target.value); setResult(null); setAlert(null) }}/>
      <button className={`${styles.btnPrimary} ${styles.btnOrange}`} onClick={handle} disabled={loading || !hasKey}>
        {loading ? <Spinner/> : <Lock size={15}/>}
        {loading ? 'Chiffrement...' : 'Chiffrer le message'}
      </button>
      <Alert type={alert?.type} msg={alert?.msg}/>
      {result && (
        <div className={styles.resultBlock}>
          <div className={styles.hashLine}>
            <span className={styles.hashLabel}>SHA-256 (message)</span>
            <span className={styles.hashVal}>{result.message_hash}</span>
          </div>
          <TimingBlock timing={result.timing} formulas={result.formulas}/>
          <div className={styles.cipherOutputs}>
            <CopyField label="Message chiffre (Base64)" value={result.ciphertext_b64} rows={3}/>
            <CopyField label="Signature (Base64)" value={result.signature} rows={2}/>
          </div>
        </div>
      )}
    </section>
  )
}

// ── SECTION 5: Dechiffrement Message ──────────────────────────────────────

function DecryptMessageSection({ hasKey }) {
  const [cipher, setCipher]   = useState('')
  const [sig, setSig]         = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [alert, setAlert]     = useState(null)

  const handle = async () => {
    if (!hasKey)       { setAlert({ type:'error', msg:"Generez d'abord une cle dynamique." }); return }
    if (!cipher.trim()) { setAlert({ type:'error', msg:'Collez le message chiffre (Base64).' }); return }
    if (!sig.trim())    { setAlert({ type:'error', msg:'Collez la signature (Base64).' }); return }
    setLoading(true); setAlert(null); setResult(null)
    try {
      const data = await safeFetch(`${API}/decrypt-message`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ ciphertext_b64: cipher.trim(), signature_b64: sig.trim() }),
      })
      setResult(data)
      setAlert({ type:'success', msg: data.message })
    } catch (err) { setAlert({ type:'error', msg: err.message }) }
    finally { setLoading(false) }
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <div className={styles.sectionIcon} style={{background:'rgba(0,212,255,0.1)',color:'#00d4ff'}}>
          <MessageSquareOff size={18}/>
        </div>
        <div>
          <h2 className={styles.sectionTitle}>Dechiffrement de Message</h2>
          <p className={styles.sectionSub}>Dechiffrement dynamique · Verification signature statique</p>
        </div>
      </div>
      {!hasKey && <div className={styles.warningBanner}><ChevronRight size={12}/>Generez d'abord une cle dynamique.</div>}
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Message chiffre (Base64)</label>
        <textarea className={styles.textarea} rows={3}
          placeholder="Collez le ciphertext base64 ici..."
          value={cipher} onChange={e => { setCipher(e.target.value); setResult(null); setAlert(null) }}/>
      </div>
      <div className={styles.field} style={{marginTop:12}}>
        <label className={styles.fieldLabel}>Signature (Base64)</label>
        <textarea className={styles.textarea} rows={2}
          placeholder="Collez la signature base64 ici..."
          value={sig} onChange={e => { setSig(e.target.value); setResult(null); setAlert(null) }}/>
      </div>
      <button className={`${styles.btnPrimary} ${styles.btnCyan}`} onClick={handle} disabled={loading || !hasKey}>
        {loading ? <Spinner/> : <Unlock size={15}/>}
        {loading ? 'Dechiffrement...' : 'Dechiffrer et verifier'}
      </button>
      <Alert type={alert?.type} msg={alert?.msg}/>
      {result && (
        <div className={styles.resultBlock}>
          <div className={styles.decryptedMsg}>
            <span className={styles.decLabel}>Message dechiffre</span>
            <div className={styles.decText}>{result.original_message}</div>
          </div>
          <div className={styles.hashLine}>
            <span className={styles.hashLabel}>SHA-256 (verifie)</span>
            <span className={styles.hashVal}>{result.message_hash}</span>
          </div>
          <TimingBlock timing={result.timing} formulas={result.formulas}/>
          <SigBadge valid={result.signature_valid}/>
        </div>
      )}
    </section>
  )
}

// ── PAGE PRINCIPALE ────────────────────────────────────────────────────────

export default function RSAPage() {
  const [hasKey, setHasKey]   = useState(false)
  const [keyData, setKeyData] = useState(null)

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div className={styles.pageIconWrap}><Lock size={24}/></div>
        <div>
          <h1 className={styles.pageTitle}>RSA Cryptography</h1>
          <p className={styles.pageSub}>Generation · Chiffrement · Dechiffrement · Signature · Performance</p>
        </div>
        {hasKey && (
          <div className={styles.keyStatus}>
            <span className={styles.keyDot}/>
            Cle active — n={keyData?.n}
          </div>
        )}
      </div>

      <div className={styles.howStrip}>
        {['(1) p,q premiers','(2) n=pxq','(3) phi=(p-1)(q-1)','(4) e auto','(5) d=e^-1 mod phi','(6) C=M^e mod n','(7) M=C^d mod n','(8) sigma=h^d mod n','(9) verif sigma^e mod n'].map(s =>
          <div key={s} className={styles.howStep}>{s}</div>
        )}
      </div>

      <div className={styles.sections}>
        <StaticKeySection/>
        <KeyGenSection onKeyGenerated={d => { setHasKey(true); setKeyData(d) }}/>
        <EncryptFileSection hasKey={hasKey}/>
        <DecryptFileSection hasKey={hasKey}/>
        <EncryptMessageSection hasKey={hasKey}/>
        <DecryptMessageSection hasKey={hasKey}/>
      </div>
    </div>
  )
}
