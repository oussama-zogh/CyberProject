import { useNavigate } from 'react-router-dom'
import { Lock, Cpu, Zap, Triangle, Shield, ArrowRight, ChevronRight } from 'lucide-react'
import styles from './Home.module.css'

const modules = [
  {
    id: 'rsa',
    path: '/rsa',
    label: 'RSA Cryptography',
    shortLabel: 'RSA',
    icon: Lock,
    color: '#2584e8',
    glow: 'rgba(37, 132, 232, 0.25)',
    description: 'Génération de clés, chiffrement et déchiffrement de fichiers avec l\'algorithme RSA.',
    tag: 'Asymétrique',
    details: ['Génération p, q', 'Clé publique & privée', 'Chiffrement', 'Déchiffrement', 'Signature'],
  },
  {
    id: 'ecc',
    path: '/ecc',
    label: 'Elliptic Curve',
    shortLabel: 'ECC',
    icon: Cpu,
    color: '#00c896',
    glow: 'rgba(0, 200, 150, 0.25)',
    description: 'Cryptographie sur courbes elliptiques — sécurité maximale avec des clés compactes.',
    tag: 'Courbes elliptiques',
    details: ['Paramètres de courbe', 'Points de clé', 'ECDH / ECDSA', 'Opérations sur points'],
  },
  {
    id: 'rsa-attack',
    path: '/rsa-attack',
    label: 'RSA Attack',
    shortLabel: 'RSA⚡',
    icon: Zap,
    color: '#ff6b35',
    glow: 'rgba(255, 107, 53, 0.25)',
    description: 'Démonstration des vulnérabilités RSA.',
    tag: 'Attaque',
    details: ['Factorisation de n', 'Attaque de Wiener', 'Attaque de Håstad'],
  },
  {
    id: 'ecc-attack',
    path: '/ecc-attack',
    label: 'ECC Attack',
    shortLabel: 'ECC⚡',
    icon: Triangle,
    color: '#c084fc',
    glow: 'rgba(192, 132, 252, 0.25)',
    description: 'Attaques sur les courbes elliptiques.',
    tag: 'Attaque avancée',
    details: ['BSGS', 'Pohlig-Hellman', 'Courbes faibles'],
  },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <main className={styles.main}>
      {/* Background grid */}
      <div className={styles.gridBg} aria-hidden />

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroBadge}>
          <Shield size={14} />
          <span>Application Éducative en Cybersécurité</span>
        </div>
        <h1 className={styles.heroTitle}>
          <span className={styles.cyber}>Cyber</span>
          <span className={styles.project}>Project</span>
        </h1>
        <p className={styles.heroSub}>
          Explorez la cryptographie moderne —<br />
          chiffrement, courbes elliptiques et analyse d'attaques.
        </p>
        <div className={styles.heroDivider} />
      </section>

      {/* Module cards */}
      <section className={styles.cards}>
        {modules.map((mod, i) => {
          const Icon = mod.icon
          return (
            <button
              key={mod.id}
              className={styles.card}
              style={{ '--card-color': mod.color, '--card-glow': mod.glow, animationDelay: `${i * 0.08}s` }}
              onClick={() => navigate(mod.path)}
            >
              {/* Top row */}
              <div className={styles.cardTop}>
                <div className={styles.iconWrap}>
                  <Icon size={22} />
                </div>
                <span className={styles.tag}>{mod.tag}</span>
              </div>

              {/* Title */}
              <h2 className={styles.cardTitle}>{mod.label}</h2>
              <p className={styles.cardDesc}>{mod.description}</p>

              {/* Feature list */}
              <ul className={styles.featureList}>
                {mod.details.map(d => (
                  <li key={d}>
                    <ChevronRight size={12} />
                    {d}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <div className={styles.cardCta}>
                <span>Explorer</span>
                <ArrowRight size={15} />
              </div>

              {/* Hover glow */}
              <div className={styles.cardGlow} aria-hidden />
            </button>
          )
        })}
      </section>

      {/* Footer note */}
      <footer className={styles.footer}>
        <Shield size={13} /> Projet universitaire — Équipe de 4 développeurs
      </footer>
    </main>
  )
}
