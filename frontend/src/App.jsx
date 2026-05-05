import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/home/Home'
import RSAPage from './pages/rsa/RSAPage'
import ECCPage from './pages/ecc/ECCPage'
import RSAAttackPage from './pages/rsa_attack/RSAAttackPage'
import ECCAttackPage from './pages/ecc_attack/ECCAttackPage'

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/"            element={<Home />} />
        <Route path="/rsa"         element={<RSAPage />} />
        <Route path="/ecc"         element={<ECCPage />} />
        <Route path="/rsa-attack"  element={<RSAAttackPage />} />
        <Route path="/ecc-attack"  element={<ECCAttackPage />} />
      </Routes>
    </>
  )
}
