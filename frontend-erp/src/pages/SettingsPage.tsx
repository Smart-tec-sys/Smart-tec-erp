import { commercialDisplayText } from '../utils/commercialDisplay'
import { GradesVariacoesPage } from './GradesVariacoesPage'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { useAuthSession, useRefreshAuthSession } from '../components/AuthGate'
import { authEnabled, getApiAuthHeaders } from '../services/auth'
import { getCurrentCompany, updateCurrentCompany, type CurrentCompany, type CompanyPublicProfile } from '../services/api'

const publicFields: Array<{ key: keyof CompanyPublicProfile; label: string; max: number; type?: string }> = [
  { key: 'logradouro', label: 'Logradouro', max: 255 }, { key: 'numero', label: 'Número', max: 30 },
  { key: 'complemento', label: 'Complemento', max: 150 }, { key: 'bairro', label: 'Bairro', max: 100 },
  { key: 'cidade', label: 'Cidade', max: 100 }, { key: 'estado', label: 'UF', max: 2 },
  { key: 'cep', label: 'CEP', max: 9 }, { key: 'telefone_comercial', label: 'Telefone comercial', max: 30, type: 'tel' },
  { key: 'telefone_celular', label: 'Celular / WhatsApp', max: 30, type: 'tel' },
  { key: 'email', label: 'E-mail comercial', max: 255, type: 'email' }, { key: 'site', label: 'Site', max: 255 },
]

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export function SettingsPage() {
  const [showGrades, setShowGrades] = useState(false)
  const authSession = useAuthSession()
  const refreshAuthSession = useRefreshAuthSession()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [profile, setProfile] = useState<CurrentCompany | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [profileMessage, setProfileMessage] = useState('')
  const activeCompanyId = authSession?.empresa.id
  const profileGeneration = useRef(0)

  useEffect(() => {
    const generation = ++profileGeneration.current
    let cancelled = false
    setProfileLoading(true)
    setProfile(null)
    setProfileError('')
    setProfileMessage('')
    void getCurrentCompany().then(data => {
      if (!cancelled && generation === profileGeneration.current) setProfile(data)
    }).catch(err => {
      if (!cancelled) setProfileError(err instanceof Error ? err.message : String(err))
    }).finally(() => { if (!cancelled) setProfileLoading(false) })
    return () => { cancelled = true; profileGeneration.current++ }
  }, [activeCompanyId])

  async function handleSaveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!profile || profileSaving) return
    const generation = profileGeneration.current
    setProfileSaving(true)
    setProfileError('')
    setProfileMessage('')
    try {
      const headers = await getApiAuthHeaders()
      if (Number(headers['X-Empresa-ID']) !== profile.id) throw new Error('A empresa ativa mudou. Reabra as configurações.')
      const updated = await updateCurrentCompany({
        nome: profile.nome, nome_fantasia: profile.nome_fantasia, documento: profile.documento,
        perfil_publico: profile.perfil_publico,
      }, profile.id)
      if (generation !== profileGeneration.current) return
      setProfile(updated)
      setProfileMessage('Dados públicos da empresa salvos. Os próximos PDFs usarão estas informações.')
      if (authEnabled) await refreshAuthSession()
    } catch (err) {
      if (generation === profileGeneration.current) setProfileError(err instanceof Error ? err.message : String(err))
    } finally { setProfileSaving(false) }
  }


  const company = authSession?.empresa
  const logoPath = company?.logo_url || null
  const logoUrl = logoPath
    ? logoPath.startsWith('http')
      ? logoPath
      : `${API_URL}${logoPath}`
    : null

  async function handleLogoSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setMessage('')
    setError('')

    try {
      const headers = await getApiAuthHeaders()
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_URL}/empresa/logo`, {
        method: 'POST',
        headers,
        body: formData,
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail || `Não foi possível enviar a logo (${response.status}).`
        )
      }

      await refreshAuthSession()
      setMessage('Logo da empresa atualizada com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível atualizar a logo da empresa.'
      )
    } finally {
      setUploading(false)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  async function handleRemoveLogo() {
    setUploading(true)
    setMessage('')
    setError('')

    try {
      const headers = await getApiAuthHeaders()

      const response = await fetch(`${API_URL}/empresa/logo`, {
        method: 'DELETE',
        headers,
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail || `Não foi possível remover a logo (${response.status}).`
        )
      }

      await refreshAuthSession()
      setMessage('Logo da empresa removida com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível remover a logo da empresa.'
      )
    } finally {
      setUploading(false)
    }
  }

  if (showGrades) return <GradesVariacoesPage onBack={() => setShowGrades(false)} />

  return (
    <section className="settings-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">CONFIGURAÇÕES</p>
          <h1 className="commercial-title">Configurações</h1>
          <p className="heading-subtitle">
            Gerencie os dados e a identidade visual da empresa.
          </p>
        </div>
      </div>

      <div className="settings-card">
        <div className="settings-card-header"><div><h2 className="commercial-title">Opções auxiliares</h2><p>Cadastros gerais reutilizáveis do ERP.</p></div></div>
        <button type="button" className="profile-secondary-button" onClick={() => setShowGrades(true)}>Grades/Variações</button>
      </div>
      <div className="settings-card">
        <div className="settings-card-header">
          <div>
            <h2 className="commercial-title">Dados da empresa</h2>
            <p>Informações exibidas no ambiente da empresa.</p>
          </div>
        </div>

        {profileLoading ? <p role="status">Carregando dados da empresa...</p> : profile && (
          <form onSubmit={handleSaveCompany}>
            <p>Preencha somente os dados públicos que devem aparecer no cabeçalho dos orçamentos.</p>
            <div className="settings-company-grid">
              <label className="field"><span>Razão social</span><input className={commercialDisplayText(profile.nome) === profile.nome.toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} required maxLength={255} value={profile.nome}
                disabled={profileSaving} onChange={event => setProfile({ ...profile, nome: event.target.value })} /></label>
              <label className="field"><span>Nome fantasia</span><input className={commercialDisplayText(profile.nome_fantasia ?? '') === (profile.nome_fantasia ?? '').toLocaleUpperCase('pt-BR') ? 'commercial-name' : undefined} maxLength={255} value={profile.nome_fantasia ?? ''}
                disabled={profileSaving} onChange={event => setProfile({ ...profile, nome_fantasia: event.target.value })} /></label>
              <label className="field"><span>CPF / CNPJ</span><input maxLength={50} value={profile.documento ?? ''}
                disabled={profileSaving} onChange={event => setProfile({ ...profile, documento: event.target.value })} /></label>
              {publicFields.map(field => <label className="field" key={field.key}>
                <span>{field.label}</span><input className={['logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'].includes(field.key) && commercialDisplayText(profile.perfil_publico[field.key] ?? '') === (profile.perfil_publico[field.key] ?? '').toLocaleUpperCase('pt-BR') ? 'commercial-address' : undefined} type={field.type ?? 'text'} maxLength={field.max}
                  disabled={profileSaving} value={profile.perfil_publico[field.key] ?? ''}
                  onChange={event => setProfile({ ...profile, perfil_publico: { ...profile.perfil_publico, [field.key]: event.target.value } })} />
              </label>)}
            </div>
            {profileMessage && <div className="settings-message" role="status">{profileMessage}</div>}
            <button type="submit" className="profile-secondary-button" disabled={profileSaving}>
              {profileSaving ? 'Salvando...' : 'Salvar dados da empresa'}
            </button>
          </form>
        )}
        {profileError && <div className="settings-error" role="alert">{profileError}</div>}

        <div className="settings-logo-section">
          {message && (
            <div className="settings-message" role="status">
              {message}
            </div>
          )}

          {error && (
            <div className="settings-error" role="alert">
              {error}
            </div>
          )}

          <div className="settings-logo-row">
            <div className="settings-logo-preview">
              {logoUrl ? (
                <img src={logoUrl} alt="Logo da empresa" />
              ) : (
                <span>ST</span>
              )}
            </div>

            <div className="settings-logo-copy">
              <strong>Logo da empresa</strong>
              <p>JPG, PNG ou WEBP de até 5 MB.</p>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleLogoSelected}
              hidden
            />

            <div className="settings-logo-actions">
              <button
                type="button"
                className="profile-secondary-button"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading
                  ? 'Enviando...'
                  : logoUrl
                    ? 'Alterar logo'
                    : 'Selecionar logo'}
              </button>

              {logoUrl && (
                <button
                  type="button"
                  className="profile-danger-button"
                  disabled={uploading}
                  onClick={handleRemoveLogo}
                >
                  Remover logo
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}