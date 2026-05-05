import { useState } from "react";
import styles from "./RSAAttackPage.module.css";

const API = "http://localhost:8000/api/rsa-attack";

async function apiFetch(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erreur API");
  return data;
}

function Alert({ type, message }) {
  if (!message) return null;
  return (
    <div className={`${styles.alert} ${styles[`alert_${type}`]}`}>
      {type === "error" ? "⛔ " : type === "success" ? "✅ " : "⚠️ "}
      {message}
    </div>
  );
}

function StepList({ steps }) {
  if (!steps?.length) return null;
  return (
    <div className={styles.stepList}>
      <div className={styles.stepTitle}>📋 Étapes de l'attaque</div>
      {steps.map((s, i) => (
        <div key={i} className={styles.step} style={{ animationDelay: `${i * 60}ms` }}>
          <span className={styles.stepIndex}>{String(i + 1).padStart(2, "0")}</span>
          <span className={styles.stepText}>{s}</span>
        </div>
      ))}
    </div>
  );
}

function ResultBox({ data }) {
  if (!data) return null;
  return (
    <div className={styles.resultBox}>
      <div className={styles.resultTitle}>🔓 Résultat</div>
      <pre className={styles.resultPre}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

function ExplanationBox({ text, complexity }) {
  if (!text) return null;
  return (
    <div className={styles.explanationBox}>
      <div className={styles.explanationTitle}>
        📖 Analyse &nbsp;
        {complexity && <span className={styles.badge}>{complexity}</span>}
      </div>
      <p>{text}</p>
    </div>
  );
}

// ── Composant réutilisable : sélecteur de mode input ────────────
function ModeInput({ mode, setMode, children }) {
  return (
    <div>
      <div className={styles.modeSelector}>
        <button className={`${styles.modeBtn} ${mode==="auto"?"${styles.modeBtnActive}":""}`} onClick={() => setMode("auto")}>🎲 Aléatoire</button>
        <button className={`${styles.modeBtn} ${mode==="manual"?"${styles.modeBtnActive}":""}`} onClick={() => setMode("manual")}>✏️ Mes valeurs</button>
        <button className={`${styles.modeBtn} ${mode==="file"?"${styles.modeBtnActive}":""}`} onClick={() => setMode("file")}>📄 Fichier / Message</button>
      </div>
      {children}
    </div>
  );
}

function TabFactorize() {
  const [mode, setMode] = useState("auto");
  const [n, setN] = useState("");
  const [msgInput, setMsgInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [weakKey, setWeakKey] = useState(null);

  async function generateWeak() {
    setLoading(true); setError("");
    try {
      const data = await apiFetch("/generate-weak-key", { bits: 16, attack_type: "factorize" });
      setWeakKey(data);
      setN(String(data.public_key.n));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      // Cherche un nombre dans le fichier
      const text = ev.target.result;
      const match = text.match(/n\s*=\s*(\d+)/i) || text.match(/(\d{4,})/);
      if (match) setN(match[1]);
      else setError("Aucun nombre trouvé dans le fichier");
    };
    reader.readAsText(file);
  }

  function handleMsgToN() {
    if (!msgInput) return;
    // Convertit le message en nombre via code ASCII
    const num = BigInt("0x" + [...msgInput].map(c => c.charCodeAt(0).toString(16).padStart(2,"0")).join(""));
    setN(num.toString());
  }

  async function attack() {
    if (!n) return;
    setLoading(true); setError(""); setResult(null);
    try {
      // Mode manuel → route dédiée qui accepte e optionnel
      const route = mode === "manual" ? "/manual-factorize" : "/factorize";
      const body = mode === "manual" ? { n: parseInt(n), e: null } : { n: parseInt(n) };
      const data = await apiFetch(route, body);
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.attackHeader}>
        <div className={styles.attackIcon}>🔢</div>
        <div>
          <h2 className={styles.attackTitle}>Factorisation de n</h2>
          <p className={styles.attackSubtitle}>Retrouver p et q à partir de n — algorithme de Fermat</p>
        </div>
      </div>
      <div className={styles.vulnBadge}>Vulnérabilité : clés de trop petite taille (p, q &lt; 2²⁰)</div>

      <div className={styles.modeSelector}>
        <button className={`${styles.modeBtn} ${mode==="auto" ? styles.modeBtnActive : ""}`} onClick={() => setMode("auto")}>🎲 Aléatoire</button>
        <button className={`${styles.modeBtn} ${mode==="manual" ? styles.modeBtnActive : ""}`} onClick={() => setMode("manual")}>✏️ Mes valeurs</button>
        <button className={`${styles.modeBtn} ${mode==="file" ? styles.modeBtnActive : ""}`} onClick={() => setMode("file")}>📄 Fichier / Message</button>
      </div>

      {mode === "auto" && (
        <div className={styles.demoSection}>
          <button className={styles.btnSecondary} onClick={generateWeak} disabled={loading}>🎲 Générer une clé faible</button>
          {weakKey && (
            <div className={styles.weakKeyPreview}>
              <span>n = <b>{weakKey.public_key.n}</b></span>
              <span>e = <b>{weakKey.public_key.e}</b></span>
              <span className={styles.warningText}>⚠️ {weakKey.warning}</span>
            </div>
          )}
        </div>
      )}

      {mode === "file" && (
        <div className={styles.fileSection}>
          <div className={styles.fileBlock}>
            <label className={styles.label}>📁 Importer un fichier (texte avec n=...)</label>
            <input type="file" accept=".txt,.pem,.key,.json" onChange={handleFile} className={styles.fileInput} />
          </div>
          <div className={styles.orDivider}>— ou —</div>
          <div className={styles.fileBlock}>
            <label className={styles.label}>💬 Entrer un message (converti en nombre)</label>
            <div className={styles.inputRowInline}>
              <input className={styles.input} value={msgInput} onChange={e => setMsgInput(e.target.value)} placeholder="ex: hello" />
              <button className={styles.btnSecondary} onClick={handleMsgToN}>Convertir →</button>
            </div>
          </div>
        </div>
      )}

      <div className={styles.inputGroup}>
        <label className={styles.label}>Valeur de n à factoriser</label>
        <input className={styles.input} type="number" value={n} onChange={(e) => setN(e.target.value)} placeholder="Ex : 3233" />
      </div>

      <button className={styles.btnAttack} onClick={attack} disabled={loading || !n}>
        {loading ? <span className={styles.spinner} /> : "⚡ Lancer l'attaque"}
      </button>
      <Alert type="error" message={error} />
      {result && (
        <>
          <Alert type={result.success?"success":"warning"} message={result.success ? `Clé cassée ! p=${result.result.p}, q=${result.result.q}` : "Factorisation échouée"} />
          <StepList steps={result.steps} />
          <ResultBox data={result.result} />
          <ExplanationBox text={result.explanation} complexity={result.complexity} />
        </>
      )}
    </div>
  );
}

function WienerTable({ rows }) {
  if (!rows?.length) return null;
  return (
    <div className={styles.wienerTableWrap}>
      <div className={styles.stepTitle}>📊 Tableau des fractions continues</div>
      <div className={styles.wienerScroll}>
        <table className={styles.wienerTable}>
          <thead>
            <tr>
              <th>Étape i</th>
              <th>Coeff aᵢ</th>
              <th>Calcul kᵢ (numérateur)</th>
              <th>Calcul dᵢ (dénominateur)</th>
              <th>Convergent kᵢ/dᵢ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.i} className={r.found ? styles.rowFound : r.is_candidate ? styles.rowCandidate : ""}>
                <td>{r.i}</td>
                <td>{r.a}</td>
                <td className={styles.mono}>{r.k_calc}</td>
                <td className={styles.mono}>{r.d_calc}</td>
                <td className={styles.mono}>
                  {r.fraction}
                  {r.found && " ✅"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TabWiener() {
  const [mode, setMode] = useState("auto"); // "auto" | "manual"
  const [e, setE] = useState("");
  const [n, setN] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [weakKey, setWeakKey] = useState(null);

  async function generateWeak() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiFetch("/generate-weak-key", { bits: 24, attack_type: "wiener" });
      setWeakKey(data);
      setE(String(data.public_key.e));
      setN(String(data.public_key.n));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const [p, setP] = useState("");
  const [q, setQ] = useState("");

  async function attack() {
    if (!e || !n) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const route = mode === "manual" ? "/manual-wiener" : "/wiener";
      const body = { e: parseInt(e), n: parseInt(n) };
      if (mode === "manual" && p && q) { body.p = parseInt(p); body.q = parseInt(q); }
      const data = await apiFetch(route, body);
      setResult(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.attackHeader}>
        <div className={styles.attackIcon}>📐</div>
        <div>
          <h2 className={styles.attackTitle}>Attaque de Wiener</h2>
          <p className={styles.attackSubtitle}>Fractions continues sur e/n — exploite d &lt; n^0.25/3</p>
        </div>
      </div>
      <div className={styles.vulnBadge}>Vulnérabilité : clé privée d trop petite (d &lt; n^¼ / 3)</div>

      {/* Mode selector */}
      <div className={styles.modeSelector}>
        <button className={`${styles.modeBtn} ${mode==="auto" ? styles.modeBtnActive : ""}`} onClick={() => setMode("auto")}>
          🎲 Clé aléatoire faible
        </button>
        <button className={`${styles.modeBtn} ${mode==="manual" ? styles.modeBtnActive : ""}`} onClick={() => setMode("manual")}>
          ✏️ Entrer mes valeurs
        </button>
      </div>

      {mode === "auto" && (
        <div className={styles.demoSection}>
          <button className={styles.btnSecondary} onClick={generateWeak} disabled={loading}>
            🎲 Générer une clé Wiener-vulnérable
          </button>
          {weakKey && (
            <div className={styles.weakKeyPreview}>
              <span>n = <b>{weakKey.public_key.n}</b></span>
              <span>e = <b>{weakKey.public_key.e}</b></span>
              <span>d réel = <b>{weakKey.private_key.d}</b></span>
              <span className={styles.warningText}>⚠️ {weakKey.warning}</span>
            </div>
          )}
        </div>
      )}

      <div className={styles.inputRow}>
        <div className={styles.inputGroup}>
          <label className={styles.label}>Exposant public e</label>
          <input className={styles.input} type="number" value={e}
            onChange={(ev) => setE(ev.target.value)} placeholder="ex: 17993" />
        </div>
        <div className={styles.inputGroup}>
          <label className={styles.label}>Module n</label>
          <input className={styles.input} type="number" value={n}
            onChange={(ev) => setN(ev.target.value)} placeholder="ex: 90581" />
        </div>
      </div>
      {mode === "manual" && (
        <div className={styles.inputRow}>
          <div className={styles.inputGroup}>
            <label className={styles.label}>p (optionnel — pour vérifier)</label>
            <input className={styles.input} type="number" value={p}
              onChange={(ev) => setP(ev.target.value)} placeholder="premier p" />
          </div>
          <div className={styles.inputGroup}>
            <label className={styles.label}>q (optionnel)</label>
            <input className={styles.input} type="number" value={q}
              onChange={(ev) => setQ(ev.target.value)} placeholder="premier q" />
          </div>
        </div>
      )}

      <button className={styles.btnAttack} onClick={attack} disabled={loading || !e || !n}>
        {loading ? <span className={styles.spinner} /> : "⚡ Lancer Wiener"}
      </button>
      <Alert type="error" message={error} />

      {result && (
        <>
          <Alert
            type={result.success ? "success" : "warning"}
            message={result.success
              ? `✅ d trouvé = ${result.result.d} (convergent #${result.result.convergent_index})`
              : "⚠️ Wiener échoue — d est suffisamment grand"}
          />
          <WienerTable rows={result.table} />
          <StepList steps={result.steps} />
          <ResultBox data={result.result} />
          <ExplanationBox text={result.explanation} complexity={result.complexity} />
        </>
      )}
    </div>
  );
}

function TabHastad() {
  const [mode, setMode] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [scenario, setScenario] = useState(null);
  const [attackResult, setAttackResult] = useState(null);
  const [error, setError] = useState("");
  // Manual mode fields
  const [manualC, setManualC] = useState(["","",""]);
  const [manualN, setManualN] = useState(["","",""]);
  const [manualMsg, setManualMsg] = useState("");

  async function generateScenario() {
    setLoading(true); setError(""); setAttackResult(null);
    try {
      const data = await apiFetch("/generate-weak-key", { bits: 24, attack_type: "hastad" });
      setScenario(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target.result);
        if (parsed.ciphertexts && parsed.moduli) {
          setScenario({ ciphertexts: parsed.ciphertexts, moduli: parsed.moduli, e: parsed.e || 3, message: "?" });
        } else setError("Format attendu : { ciphertexts:[c1,c2,c3], moduli:[n1,n2,n3], e:3 }");
      } catch { setError("Fichier JSON invalide"); }
    };
    reader.readAsText(file);
  }

  function handleMsgEncrypt() {
    if (!manualMsg) return;
    const m = [...manualMsg].reduce((acc, c) => acc * 256n + BigInt(c.charCodeAt(0)), 0n);
    setManualMsg(m.toString());
  }

  async function attack() {
    let ct, mod, eVal;
    if (mode === "manual") {
      ct = manualC.map(Number); mod = manualN.map(Number); eVal = 3;
      setScenario({ ciphertexts: ct, moduli: mod, e: eVal, message: "?" });
    } else {
      if (!scenario) return;
      ct = scenario.ciphertexts; mod = scenario.moduli; eVal = scenario.e;
    }
    setLoading(true); setError("");
    try {
      const route = mode === "manual" ? "/manual-hastad" : "/hastad";
      const data = await apiFetch(route, { ciphertexts: ct, moduli: mod, e: eVal });
      setAttackResult(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  const canAttack = mode === "manual"
    ? manualC.every(Boolean) && manualN.every(Boolean)
    : !!scenario;

  return (
    <div className={styles.tabContent}>
      <div className={styles.attackHeader}>
        <div className={styles.attackIcon}>📡</div>
        <div>
          <h2 className={styles.attackTitle}>Attaque de Håstad</h2>
          <p className={styles.attackSubtitle}>Broadcast attack — CRT + racine cubique pour e=3</p>
        </div>
      </div>
      <div className={styles.vulnBadge}>Vulnérabilité : même message m chiffré avec e=3 vers ≥3 destinataires</div>

      <div className={styles.hastadFlow}>
        <div className={styles.flowBox}><div className={styles.flowIcon}>👤</div><div className={styles.flowLabel}>Émetteur</div><div className={styles.flowDesc}>envoie m à 3 destinataires avec e=3</div></div>
        <div className={styles.flowArrow}>→</div>
        <div className={styles.flowBox}><div className={styles.flowIcon}>🕵️</div><div className={styles.flowLabel}>Attaquant</div><div className={styles.flowDesc}>intercepte c1, c2, c3</div></div>
        <div className={styles.flowArrow}>→</div>
        <div className={styles.flowBox}><div className={styles.flowIcon}>🔓</div><div className={styles.flowLabel}>CRT + ∛</div><div className={styles.flowDesc}>retrouve m en clair !</div></div>
      </div>

      <div className={styles.modeSelector}>
        <button className={`${styles.modeBtn} ${mode==="auto" ? styles.modeBtnActive : ""}`} onClick={() => setMode("auto")}>🎲 Aléatoire</button>
        <button className={`${styles.modeBtn} ${mode==="manual" ? styles.modeBtnActive : ""}`} onClick={() => setMode("manual")}>✏️ Mes valeurs</button>
        <button className={`${styles.modeBtn} ${mode==="file" ? styles.modeBtnActive : ""}`} onClick={() => setMode("file")}>📄 Fichier / Message</button>
      </div>

      {mode === "auto" && (
        <div className={styles.demoSection}>
          <button className={styles.btnSecondary} onClick={generateScenario} disabled={loading}>🎲 Générer le scénario</button>
        </div>
      )}

      {mode === "manual" && (
        <div className={styles.manualGrid}>
          {[0,1,2].map(i => (
            <div key={i} className={styles.manualRow}>
              <div className={styles.inputGroup}>
                <label className={styles.label}>Chiffré c{i+1}</label>
                <input className={styles.input} type="number" value={manualC[i]}
                  onChange={e => { const a=[...manualC]; a[i]=e.target.value; setManualC(a); }} placeholder={`c${i+1}`} />
              </div>
              <div className={styles.inputGroup}>
                <label className={styles.label}>Module n{i+1}</label>
                <input className={styles.input} type="number" value={manualN[i]}
                  onChange={e => { const a=[...manualN]; a[i]=e.target.value; setManualN(a); }} placeholder={`n${i+1}`} />
              </div>
            </div>
          ))}
        </div>
      )}

      {mode === "file" && (
        <div className={styles.fileSection}>
          <div className={styles.fileBlock}>
            <label className={styles.label}>📁 Fichier JSON avec ciphertexts & moduli</label>
            <input type="file" accept=".json,.txt" onChange={handleFile} className={styles.fileInput} />
            <span className={styles.fileHint}>Format : {"{"} "ciphertexts":[c1,c2,c3], "moduli":[n1,n2,n3], "e":3 {"}"}</span>
          </div>
          <div className={styles.orDivider}>— ou —</div>
          <div className={styles.fileBlock}>
            <label className={styles.label}>💬 Message texte → nombre</label>
            <div className={styles.inputRowInline}>
              <input className={styles.input} value={manualMsg} onChange={e => setManualMsg(e.target.value)} placeholder="ex: hello" />
              <button className={styles.btnSecondary} onClick={handleMsgEncrypt}>→ Nombre</button>
            </div>
          </div>
        </div>
      )}

      {scenario && mode !== "manual" && (
        <div className={styles.hastadScenario}>
          <div className={styles.scenarioTitle}>Données interceptées</div>
          {scenario.ciphertexts.map((c, i) => (
            <div key={i} className={styles.scenarioRow}>
              <span className={styles.scenarioLabel}>c{i+1} =</span>
              <span className={styles.scenarioValue}>{c}</span>
              <span className={styles.scenarioLabel}>mod n{i+1} =</span>
              <span className={styles.scenarioValue}>{scenario.moduli[i]}</span>
            </div>
          ))}
          {scenario.message !== "?" && <div className={styles.secretHint}>Message secret : <b className={styles.hidden}>{"?".repeat(8)}</b></div>}
        </div>
      )}

      <button className={styles.btnAttack} onClick={attack} disabled={loading || !canAttack}>
        {loading ? <span className={styles.spinner} /> : "⚡ Lancer Håstad"}
      </button>
      <Alert type="error" message={error} />
      {attackResult && (
        <>
          <Alert type="success" message={`Message récupéré : m = ${attackResult.result.message}`} />
          <StepList steps={attackResult.steps} />
          <ResultBox data={attackResult.result} />
          <ExplanationBox text={attackResult.explanation} complexity={attackResult.complexity} />
        </>
      )}
    </div>
  );
}

const TABS = [
  { id: "factorize", label: "Factorisation", icon: "🔢" },
  { id: "wiener", label: "Wiener", icon: "📐" },
  { id: "hastad", label: "Håstad", icon: "📡" },
];

export default function RSAAttackPage() {
  const [activeTab, setActiveTab] = useState("factorize");

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroTag}>Module 3 — Red Team</div>
        <h1 className={styles.heroTitle}>
          <span className={styles.heroAccent}>RSA</span> Attaques
        </h1>
        <p className={styles.heroDesc}>
          Démonstration interactive des vulnérabilités RSA classiques.
          Générez des clés intentionnellement faibles et observez comment elles sont cassées.
        </p>
      </div>
      <div className={styles.container}>
        <div className={styles.tabs}>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`${styles.tab} ${activeTab === t.id ? styles.tabActive : ""}`}
              onClick={() => setActiveTab(t.id)}
            >
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
        </div>
        <div className={styles.panel}>
          {activeTab === "factorize" && <TabFactorize />}
          {activeTab === "wiener" && <TabWiener />}
          {activeTab === "hastad" && <TabHastad />}
        </div>
      </div>
    </div>
  );
}
