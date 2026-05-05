import { Link, useLocation } from 'react-router-dom'
import { Shield, Lock, Cpu, Zap, Triangle } from 'lucide-react'
import styles from './Navbar.module.css'

const links = [
  { to: '/',           label: 'Accueil',     icon: <Shield size={15} /> },
  { to: '/rsa',        label: 'RSA Crypto',  icon: <Lock size={15} /> },
  { to: '/ecc',        label: 'ECC Crypto',  icon: <Cpu size={15} /> },
  { to: '/rsa-attack', label: 'RSA Attack',  icon: <Zap size={15} /> },
  { to: '/ecc-attack', label: 'ECC Attack',  icon: <Triangle size={15} /> },
]

export default function Navbar() {
  const { pathname } = useLocation()
  return (
    <nav className={styles.nav}>
      <div className={styles.brand}>
        <Shield size={20} />
        <span>CyberProject</span>
      </div>
      <div className={styles.links}>
        {links.map(l => (
          <Link
            key={l.to}
            to={l.to}
            className={`${styles.link} ${pathname === l.to ? styles.active : ''}`}
          >
            {l.icon}
            <span>{l.label}</span>
          </Link>
        ))}
      </div>
    </nav>
  )
}
