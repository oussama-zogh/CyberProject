import { useState, useRef, useEffect } from "react";
import styles from "./ECCAttackPage.module.css";

// ─── Presets pédagogiques ───────────────────────────────────────────────────
const PRESETS = {
  bsgs: {
    label: "Courbe toy (ordre 17)",
    a: 2, b: 2, p: 17,
    Gx: 5, Gy: 1,
    Qx: 10, Qy: 6,
    n: 19,
    note: "Courbe y²=x³+2x+2 mod 17, G=(5,1), Q=(10,6)"
  },
  pohlig: {
    label: "Ordre composé (n=105 = 3×5×7)",
    a: 1, b: 1, p: 107,
    Gx: 2, Gy: 24,
    Qx: 54, Qy: 28,
    n: 105,
    note: "n=3×5×7, Pohlig-Hellman très efficace"
  },
  anomalous: {
    label: "Courbe anomale mod 11",
    a: 0, b: 3, p: 11,
    Gx: 1, Gy: 5,
    Qx: 4, Qy: 7,
    note: "#E(F₁₁) = 11 (anomale)"
  }
};

const API = "http://localhost:8000";

// ─── Composant principal ────────────────────────────────────────────────────
export default function ECCAttackPage() {
  const [activeTab, setActiveTab] = useState("bsgs");

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <div className={styles.headerGlow} />
        <div className={styles.headerContent}>
          <span className={styles.badge}>CRYPTANALYSE</span>
          <h1 className={styles.title}>
            <span className={styles.titleAccent}>ECC</span> Attack Lab
          </h1>
          <p className={styles.subtitle}>
            Explorez les vulnérabilités des courbes elliptiques : BSGS, Pohlig-Hellman &amp; Courbes Anomales
          </p>
        </div>
        <div className={styles.headerOrbs} aria-hidden>
          <div className={styles.orb1} />
          <div className={styles.orb2} />
          <div className={styles.orb3} />
        </div>
      </header>

      {/* ── Tabs ── */}
      <nav className={styles.tabs}>
        {[
          { id: "bsgs", label: "Baby-step Giant-step", icon: "🔢" },
          { id: "pohlig", label: "Pohlig-Hellman", icon: "🧩" },
          { id: "anomalous", label: "Courbes Anomales", icon: "⚡" }
        ].map(t => (
          <button
            key={t.id}
            className={`${styles.tab} ${activeTab === t.id ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </nav>

      {/* ── Panels ── */}
      <main className={styles.main}>
        {activeTab === "bsgs"      && <BSGSPanel />}
        {activeTab === "pohlig"    && <PohligPanel />}
        {activeTab === "anomalous" && <AnomalousPanel />}
      </main>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
//  PANEL 1 — BABY-STEP GIANT-STEP
// ═══════════════════════════════════════════════════════════════════════════════
function BSGSPanel() {
  const preset = PRESETS.bsgs;
  const [form, setForm] = useState({
    a: preset.a, b: preset.b, p: preset.p,
    Gx: preset.Gx, Gy: preset.Gy,
    Qx: preset.Qx, Qy: preset.Qy,
    n: preset.n
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = e => setForm({ ...form, [e.target.name]: Number(e.target.value) });

  const run = async () => {
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch(`${API}/api/ecc-attack/bsgs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur serveur");
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className={styles.panel}>
      <ExplainCard
        icon="🔢"
        title="Baby-step Giant-step"
        color="#c084fc"
        complexity="O(√n)"
        desc="Résout le problème du logarithme discret Q = k·G en O(√n) au lieu de O(n). L'astuce : écrire k = i·m + j et précalculer toutes les baby-steps dans une table de hachage."
      />

      <div className={styles.formCard}>
        <h3 className={styles.formTitle}>Paramètres de la courbe</h3>
        <p className={styles.formNote}>📌 {preset.note}</p>

        <div className={styles.grid3}>
          <Field label="a" name="a" value={form.a} onChange={handleChange} />
          <Field label="b" name="b" value={form.b} onChange={handleChange} />
          <Field label="p (module)" name="p" value={form.p} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Gx" name="Gx" value={form.Gx} onChange={handleChange} />
          <Field label="Gy" name="Gy" value={form.Gy} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Qx (cible)" name="Qx" value={form.Qx} onChange={handleChange} />
          <Field label="Qy (cible)" name="Qy" value={form.Qy} onChange={handleChange} />
        </div>
        <Field label="n (ordre de G)" name="n" value={form.n} onChange={handleChange} full />

        <button className={styles.btn} onClick={run} disabled={loading}>
          {loading ? <Spinner /> : "⚔️ Lancer BSGS"}
        </button>
      </div>

      {error && <Alert type="error" msg={error} />}
      {result && <BSGSResult data={result} params={form} />}
    </div>
  );
}

function BSGSResult({ data, params }) {
  return (
    <div className={styles.resultCard}>
      <div className={styles.resultHeader}>
        <span className={styles.resultIcon}>✅</span>
        <div>
          <div className={styles.resultTitle}>Clé privée retrouvée</div>
          <div className={styles.resultK}>k = <span>{data.result.k}</span></div>
        </div>
        <div className={styles.complexityBadge}>{data.complexity}</div>
      </div>

      {/* Visualisation BSGS */}
      <BSGSVisualization result={data.result} n={params.n} />

      {/* Stats */}
      <div className={styles.statsRow}>
        <Stat label="Baby-steps" value={data.result.baby_steps_computed} icon="👶" />
        <Stat label="Giant-steps" value={data.result.giant_steps_computed} icon="🦕" />
        <Stat label="Total étapes" value={data.result.total_steps} icon="🔢" />
        <Stat label="Force brute" value={params.n} icon="💀" />
      </div>

      <StepsLog steps={data.steps} />
    </div>
  );
}

function BSGSVisualization({ result, n }) {
  const canvasRef = useRef(null);
  const m = Math.ceil(Math.sqrt(n)) + 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const cols = Math.min(m, 20);
    const rows = Math.ceil(m / cols);
    const cellW = W / cols;
    const cellH = Math.min(36, H / rows);

    for (let i = 0; i < Math.min(m, cols * rows); i++) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const x = col * cellW + 2;
      const y = row * cellH + 2;
      const w = cellW - 4;
      const h = cellH - 4;

      // Colorier la collision
      const isK = i === result.k;
      const isBaby = i < result.baby_steps_computed;
      const isGiant = i < result.giant_steps_computed;

      let fill = "rgba(192,132,252,0.08)";
      if (isK) fill = "rgba(192,132,252,0.9)";
      else if (isBaby && isGiant) fill = "rgba(192,132,252,0.3)";
      else if (isBaby) fill = "rgba(96,165,250,0.2)";

      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, 4);
      ctx.fill();

      if (isK) {
        ctx.strokeStyle = "#c084fc";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, 4);
        ctx.stroke();
      }

      ctx.fillStyle = isK ? "#fff" : "rgba(255,255,255,0.5)";
      ctx.font = `${Math.max(9, cellW * 0.3)}px JetBrains Mono, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(i, x + w / 2, y + h / 2);
    }

    // Légende
    ctx.font = "11px DM Sans, sans-serif";
    ctx.fillStyle = "#c084fc";
    ctx.textAlign = "left";
    ctx.fillText(`k=${result.k} trouvé ici`, 8, H - 10);
  }, [result, n, m]);

  return (
    <div className={styles.vizContainer}>
      <div className={styles.vizTitle}>Visualisation de l'espace de recherche (n={n})</div>
      <div className={styles.vizLegend}>
        <LegendDot color="rgba(96,165,250,0.3)" label="Baby-steps" />
        <LegendDot color="rgba(192,132,252,0.3)" label="Giant-steps" />
        <LegendDot color="rgba(192,132,252,0.9)" label="Collision k" />
      </div>
      <canvas ref={canvasRef} width={600} height={120} className={styles.canvas} />
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <span className={styles.legendItem}>
      <span className={styles.legendDot} style={{ background: color }} />
      {label}
    </span>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
//  PANEL 2 — POHLIG-HELLMAN
// ═══════════════════════════════════════════════════════════════════════════════
function PohligPanel() {
  const preset = PRESETS.pohlig;
  const [form, setForm] = useState({
    a: preset.a, b: preset.b, p: preset.p,
    Gx: preset.Gx, Gy: preset.Gy,
    Qx: preset.Qx, Qy: preset.Qy,
    n: preset.n
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = e => setForm({ ...form, [e.target.name]: Number(e.target.value) });

  const run = async () => {
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch(`${API}/api/ecc-attack/pohlig-hellman`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur serveur");
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className={styles.panel}>
      <ExplainCard
        icon="🧩"
        title="Pohlig-Hellman"
        color="#a78bfa"
        complexity="O(Σ √pᵢ)"
        desc="Exploite la structure de l'ordre de groupe quand n = p₁^e₁ · p₂^e₂ · … Résout le DLP dans chaque petit sous-groupe, puis applique le Théorème Chinois des Restes."
      />

      <div className={styles.formCard}>
        <h3 className={styles.formTitle}>Paramètres</h3>
        <p className={styles.formNote}>📌 {preset.note}</p>
        <div className={styles.grid3}>
          <Field label="a" name="a" value={form.a} onChange={handleChange} />
          <Field label="b" name="b" value={form.b} onChange={handleChange} />
          <Field label="p" name="p" value={form.p} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Gx" name="Gx" value={form.Gx} onChange={handleChange} />
          <Field label="Gy" name="Gy" value={form.Gy} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Qx" name="Qx" value={form.Qx} onChange={handleChange} />
          <Field label="Qy" name="Qy" value={form.Qy} onChange={handleChange} />
        </div>
        <Field label="n (ordre composé)" name="n" value={form.n} onChange={handleChange} full />
        <button className={styles.btn} onClick={run} disabled={loading}>
          {loading ? <Spinner /> : "⚔️ Lancer Pohlig-Hellman"}
        </button>
      </div>

      {error && <Alert type="error" msg={error} />}
      {result && <PohligResult data={result} />}
    </div>
  );
}

function PohligResult({ data }) {
  const factors = data.result.factors_used;
  const residues = data.result.residues;

  return (
    <div className={styles.resultCard}>
      <div className={styles.resultHeader}>
        <span className={styles.resultIcon}>✅</span>
        <div>
          <div className={styles.resultTitle}>Clé retrouvée via CRT</div>
          <div className={styles.resultK}>k = <span>{data.result.k}</span></div>
        </div>
        <div className={styles.complexityBadge}>{data.complexity}</div>
      </div>

      {/* Facteurs */}
      <div className={styles.crtViz}>
        <div className={styles.crtTitle}>Décomposition &amp; CRT</div>
        <div className={styles.crtFlow}>
          {residues.map(([r, m], i) => (
            <div key={i} className={styles.crtBlock}>
              <div className={styles.crtMod}>mod {m}</div>
              <div className={styles.crtRes}>k ≡ {r}</div>
            </div>
          ))}
          <div className={styles.crtArrow}>⟶ CRT ⟶</div>
          <div className={`${styles.crtBlock} ${styles.crtFinal}`}>
            <div className={styles.crtMod}>résultat</div>
            <div className={styles.crtRes}>k = {data.result.k}</div>
          </div>
        </div>
      </div>

      <StepsLog steps={data.steps} />
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
//  PANEL 3 — COURBES ANOMALES
// ═══════════════════════════════════════════════════════════════════════════════
function AnomalousPanel() {
  const preset = PRESETS.anomalous;
  const [form, setForm] = useState({
    a: preset.a, b: preset.b, p: preset.p,
    Gx: preset.Gx, Gy: preset.Gy,
    Qx: preset.Qx, Qy: preset.Qy
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = e => setForm({ ...form, [e.target.name]: Number(e.target.value) });

  const run = async () => {
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch(`${API}/api/ecc-attack/anomalous`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur serveur");
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className={styles.panel}>
      <ExplainCard
        icon="⚡"
        title="Smart's Attack — Courbes Anomales"
        color="#e879f9"
        complexity="O(log p)"
        desc="Quand #E(Fp) = p (courbe anomale), on peut lifter les points vers Z/p²Z et utiliser un homomorphisme φ pour transférer le DLP vers Fp additif — trivial à résoudre !"
      />

      <div className={styles.formCard}>
        <h3 className={styles.formTitle}>Paramètres (courbe anomale)</h3>
        <p className={styles.formNote}>📌 {preset.note}</p>
        <div className={styles.grid3}>
          <Field label="a" name="a" value={form.a} onChange={handleChange} />
          <Field label="b" name="b" value={form.b} onChange={handleChange} />
          <Field label="p (= #E)" name="p" value={form.p} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Gx" name="Gx" value={form.Gx} onChange={handleChange} />
          <Field label="Gy" name="Gy" value={form.Gy} onChange={handleChange} />
        </div>
        <div className={styles.grid2}>
          <Field label="Qx" name="Qx" value={form.Qx} onChange={handleChange} />
          <Field label="Qy" name="Qy" value={form.Qy} onChange={handleChange} />
        </div>
        <button className={styles.btn} onClick={run} disabled={loading}>
          {loading ? <Spinner /> : "⚔️ Lancer Smart's Attack"}
        </button>
      </div>

      {error && <Alert type="error" msg={error} />}
      {result && <AnomalousResult data={result} />}
    </div>
  );
}

function AnomalousResult({ data }) {
  return (
    <div className={styles.resultCard}>
      <div className={styles.resultHeader}>
        <span className={styles.resultIcon}>⚡</span>
        <div>
          <div className={styles.resultTitle}>DLP résolu trivialement</div>
          <div className={styles.resultK}>k = <span>{data.result.k}</span></div>
        </div>
        <div className={`${styles.complexityBadge} ${styles.complexityDanger}`}>{data.complexity}</div>
      </div>

      <div className={styles.smartFlow}>
        <SmartStep n={1} label="Lift vers Z/p²Z" desc={`φ(G) = ${data.result.phi_G}`} />
        <div className={styles.flowArrow}>→</div>
        <SmartStep n={2} label="Homomorphisme φ" desc={`φ(Q) = ${data.result.phi_Q}`} />
        <div className={styles.flowArrow}>→</div>
        <SmartStep n={3} label="Division dans Fp" desc={`k = φ(Q)/φ(G) = ${data.result.k}`} />
      </div>

      <StepsLog steps={data.steps} />
    </div>
  );
}

function SmartStep({ n, label, desc }) {
  return (
    <div className={styles.smartStep}>
      <div className={styles.smartStepN}>{n}</div>
      <div className={styles.smartStepLabel}>{label}</div>
      <div className={styles.smartStepDesc}>{desc}</div>
    </div>
  );
}


// ─── Composants partagés ────────────────────────────────────────────────────

function ExplainCard({ icon, title, color, complexity, desc }) {
  return (
    <div className={styles.explainCard} style={{ "--accent-local": color }}>
      <div className={styles.explainLeft}>
        <span className={styles.explainIcon}>{icon}</span>
        <div>
          <div className={styles.explainTitle}>{title}</div>
          <div className={styles.explainComplexity}>Complexité : {complexity}</div>
        </div>
      </div>
      <p className={styles.explainDesc}>{desc}</p>
    </div>
  );
}

function Field({ label, name, value, onChange, full }) {
  return (
    <div className={`${styles.field} ${full ? styles.fieldFull : ""}`}>
      <label className={styles.label}>{label}</label>
      <input
        className={styles.input}
        type="number"
        name={name}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}

function Stat({ label, value, icon }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statIcon}>{icon}</span>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}

function StepsLog({ steps }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.stepsLog}>
      <button className={styles.stepsToggle} onClick={() => setOpen(!open)}>
        {open ? "▲" : "▼"} Journal des étapes ({steps.length})
      </button>
      {open && (
        <div className={styles.stepsBody}>
          {steps.map((s, i) => (
            <div key={i} className={styles.step}>
              <span className={styles.stepNum}>{String(i + 1).padStart(2, "0")}</span>
              <span className={styles.stepText}>{s}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Alert({ type, msg }) {
  return (
    <div className={`${styles.alert} ${styles[`alert_${type}`]}`}>
      {type === "error" ? "❌" : "✅"} {msg}
    </div>
  );
}

function Spinner() {
  return <span className={styles.spinner} />;
}
