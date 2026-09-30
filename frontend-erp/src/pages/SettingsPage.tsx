import { ChangeEvent, useRef, useState } from 'react'
import { useAuthSession, useRefreshAuthSession } from '../components/AuthGate'
import { getApiAuthHeaders } from '../services/auth'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export function SettingsPage() {
  const authSession = useAuthSession()
  const refreshAuthSession = useRefreshAuthSession()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

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

  return (
    <section className="settings-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">CONFIGURAÇÕES</p>
          <h1>Configurações</h1>
          <p className="heading-subtitle">
            Gerencie os dados e a identidade visual da empresa.
          </p>
        </div>
      </div>

      <div className="settings-card">
        <div className="settings-card-header">
          <div>
            <h2>Dados da empresa</h2>
            <p>Informações exibidas no ambiente da empresa.</p>
          </div>
        </div>

        <div className="settings-company-grid">
          <div>
            <span>Nome</span>
            <strong>{company?.nome_fantasia || company?.nome || 'Empresa'}</strong>
          </div>

          <div>
            <span>Perfil</span>
            <strong>{company?.papel || '-'}</strong>
          </div>
        </div>

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