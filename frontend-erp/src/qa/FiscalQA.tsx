import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { FiscalPage } from '../pages/FiscalPage'
import '../theme/tokens.css'
import '../styles.css'

function QA() {
  return <div style={{ minHeight: '100vh' }}>
    <div style={{
      background: '#222', color: '#fff', padding: '10px 20px',
      textAlign: 'center', fontSize: 13, fontWeight: 700,
    }}>
      PRÉVIA VISUAL ISOLADA — APENAS PRODUTOS FICTÍCIOS — SEM API, BANCO OU EMISSÃO FISCAL
    </div>
    <FiscalPage modoHomologacao />
  </div>
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><QA /></StrictMode>
)
