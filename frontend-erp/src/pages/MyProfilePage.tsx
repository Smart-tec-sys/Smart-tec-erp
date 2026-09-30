import { ChangeEvent, useEffect, useRef, useState } from 'react'
import { useAuthSession, useRefreshAuthSession } from '../components/AuthGate'
import { getAccessToken, requestEmailChange, updateAuthenticatedPassword, enrollTotpMfa, challengeTotpMfa, verifyTotpMfa, listMfaFactors, unenrollMfaFactor } from '../services/auth'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export function MyProfilePage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const authSession = useAuthSession()
  const refreshAuthSession = useRefreshAuthSession()

  const sessionName =
    authSession?.user.nome?.trim() ||
    authSession?.user.email ||
    'Usuário'

  const userEmail = authSession?.user.email || ''
  const userRole = authSession?.empresa.papel || 'USUARIO'

  const displayUserRole =
    userRole === 'OWNER'
      ? 'Proprietário'
      : userRole === 'ADMIN'
        ? 'Administrador'
        : userRole === 'USUARIO'
          ? 'Usuário'
          : userRole
  const [photoPath, setPhotoPath] = useState<string | null>(
    authSession?.user.foto_url ?? null
  )

  const photoUrl = photoPath
    ? `${API_URL}${photoPath}`
    : null

  const [name, setName] = useState(sessionName)
  const [savedName, setSavedName] = useState(sessionName)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [emailEditing, setEmailEditing] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [changingEmail, setChangingEmail] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [securityMessage, setSecurityMessage] = useState('')
  const [photoMessage, setPhotoMessage] = useState('')
  const [passwordEditing, setPasswordEditing] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  const [mfaConfigured, setMfaConfigured] = useState(false)
  const [mfaEditing, setMfaEditing] = useState(false)
  const [mfaLoading, setMfaLoading] = useState(false)
  const [mfaFactorId, setMfaFactorId] = useState('')
  const [mfaChallengeId, setMfaChallengeId] = useState('')
  const [mfaQrCode, setMfaQrCode] = useState('')
  const [mfaSecret, setMfaSecret] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [verifiedMfaFactorId, setVerifiedMfaFactorId] = useState('')
  const [mfaManageOpen, setMfaManageOpen] = useState(false)
  const [mfaActionLoading, setMfaActionLoading] = useState(false)
  const [mfaReplacing, setMfaReplacing] = useState(false)
  const [previousMfaFactorId, setPreviousMfaFactorId] = useState('')

  useEffect(() => {
    setName(sessionName)
    setSavedName(sessionName)
  }, [sessionName])

  useEffect(() => {
    setPhotoPath(authSession?.user.foto_url ?? null)
  }, [authSession?.user.foto_url])

  useEffect(() => {
    let cancelled = false

    const loadMfaStatus = async () => {
      try {
        const factors = await listMfaFactors()

        if (cancelled) return

        const verifiedTotp = factors.find(
          (factor: any) =>
            factor?.factor_type === 'totp' &&
            factor?.status === 'verified'
        )

        setMfaConfigured(Boolean(verifiedTotp))
        setVerifiedMfaFactorId(verifiedTotp?.id ?? '')
      } catch (err) {
        if (cancelled) return

        console.error('Falha ao consultar proteção extra:', err)
      }
    }

    void loadMfaStatus()

    const handleRemovePhoto = async () => {
    if (!photoPath || uploading) return

    setUploading(true)
    setMessage('')
    setError('')

    try {
      const accessToken = await getAccessToken()

      if (!accessToken) {
        throw new Error('Sessão autenticada não encontrada.')
      }

      const response = await fetch(`${API_URL}/auth/me/photo`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Não foi possível remover a foto (${response.status}).`
        )
      }

      setPhotoPath(null)
      await refreshAuthSession()
      setPhotoMessage('Foto removida com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível remover a foto.'
      )
    } finally {
      setUploading(false)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  return () => {
      cancelled = true
    }
  }, [])

  const initials = savedName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part: string) => part[0]?.toUpperCase())
    .join('')

  const hasChanges = name.trim() !== savedName.trim()

  const handleSave = async () => {
    const normalizedName = name.trim()

    setMessage('')
    setError('')

    if (normalizedName.length < 2) {
      setError('Informe um nome válido.')
      return
    }

    setSaving(true)

    try {
      const accessToken = await getAccessToken()

      const response = await fetch('http://127.0.0.1:8000/auth/me', {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nome: normalizedName,
        }),
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Não foi possível salvar (${response.status}).`
        )
      }

      const nextName = body?.user?.nome?.trim() || normalizedName

      setName(nextName)
      setSavedName(nextName)
      setMessage('Nome atualizado com sucesso.')

      window.location.reload()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível atualizar o nome.'
      )
    } finally {
      setSaving(false)
    }
  }





  const handleStartMfa = async () => {
    setMessage('')
    setError('')
    setMfaLoading(true)

    try {
      const factors = await listMfaFactors()

      const verifiedFactor = factors.find(
        (factor: any) =>
          factor?.factor_type === 'totp' &&
          factor?.status === 'verified'
      )

      if (verifiedFactor) {
        setMfaConfigured(true)
        setMessage('A proteção extra já está ativada nesta conta.')
        return
      }

      const pendingFactors = factors.filter(
        (factor: any) =>
          factor?.factor_type === 'totp' &&
          factor?.status !== 'verified'
      )

      for (const factor of pendingFactors) {
        if (factor?.id) {
          try {
            await unenrollMfaFactor(factor.id)
          } catch {
            // Se não conseguir remover um fator antigo,
            // seguimos e deixamos o servidor informar.
          }
        }
      }

      const enrolled = await enrollTotpMfa()

      if (!enrolled?.id || !enrolled?.totp?.qr_code) {
        throw new Error(
          'Não foi possível gerar o código para configurar a proteção.'
        )
      }

      const challenge = await challengeTotpMfa(enrolled.id)

      if (!challenge?.id) {
        throw new Error(
          'Não foi possível iniciar a confirmação da proteção.'
        )
      }

      setMfaFactorId(enrolled.id)
      setMfaChallengeId(challenge.id)
      setMfaQrCode(enrolled.totp.qr_code)
      setMfaSecret(enrolled.totp.secret ?? '')
      setMfaCode('')
      setMfaEditing(true)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível iniciar a verificação em duas etapas.'
      )
    } finally {
      setMfaLoading(false)
    }
  }

  const handleCancelMfaSetup = async () => {
    setMessage('')
    setError('')
    setMfaLoading(true)

    try {
      if (
        mfaFactorId &&
        mfaFactorId !== previousMfaFactorId
      ) {
        try {
          await unenrollMfaFactor(mfaFactorId)
        } catch {
          // O fator novo pode já ter expirado ou ter sido removido.
          // O cancelamento local continua normalmente.
        }
      }

      setMfaEditing(false)
      setMfaFactorId('')
      setMfaChallengeId('')
      setMfaQrCode('')
      setMfaSecret('')
      setMfaCode('')

      setMfaReplacing(false)
      setPreviousMfaFactorId('')

      if (mfaConfigured) {
        setMessage(
          'Alteração cancelada. Sua proteção atual continua ativa.'
        )
      }
    } finally {
      setMfaLoading(false)
    }
  }
  const handleVerifyMfa = async () => {
    setMessage('')
    setError('')

    if (!mfaFactorId) {
      setError('Configuração de autenticação incompleta.')
      return
    }

    if (!/^\d{6}$/.test(mfaCode.trim())) {
      setError('Informe o código de 6 dígitos.')
      return
    }

    setMfaLoading(true)

    try {
      const freshChallenge = await challengeTotpMfa(mfaFactorId)

      if (!freshChallenge?.id) {
        throw new Error(
          'Não foi possível iniciar a confirmação do autenticador.'
        )
      }

      await verifyTotpMfa(
        mfaFactorId,
        freshChallenge.id,
        mfaCode
      )

      const factorsAfterVerify = await listMfaFactors()

      const newlyVerifiedFactor = factorsAfterVerify.find(
        (factor: any) =>
          factor?.id === mfaFactorId &&
          factor?.factor_type === 'totp' &&
          factor?.status === 'verified'
      )

      if (!newlyVerifiedFactor) {
        throw new Error(
          'O novo autenticador ainda não foi confirmado. Tente novamente com um código atual.'
        )
      }

      if (
        mfaReplacing &&
        previousMfaFactorId &&
        previousMfaFactorId !== mfaFactorId
      ) {
        await unenrollMfaFactor(previousMfaFactorId)
      }

      setMfaConfigured(true)
      setVerifiedMfaFactorId(mfaFactorId)
      setMfaEditing(false)
      setMfaFactorId('')
      setMfaChallengeId('')
      setMfaQrCode('')
      setMfaSecret('')
      setMfaCode('')

      if (mfaReplacing) {
        setMfaReplacing(false)
        setPreviousMfaFactorId('')
        setSecurityMessage('Aplicativo autenticador trocado com sucesso.')
      } else {
        setSecurityMessage('Proteção extra ativada com sucesso.')
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível validar o código.'
      )
    } finally {
      setMfaLoading(false)
    }
  }

  const resolveVerifiedMfaFactorId = async () => {
    if (verifiedMfaFactorId) {
      return verifiedMfaFactorId
    }

    const factors = await listMfaFactors()

    const verified = factors.find(
      (factor: any) =>
        factor?.factor_type === 'totp' &&
        factor?.status === 'verified'
    )

    return verified?.id ?? ''
  }

  const handleDisableMfa = async () => {
    setMessage('')
    setError('')
    setMfaActionLoading(true)

    try {
      const factorId = await resolveVerifiedMfaFactorId()

      if (!factorId) {
        throw new Error(
          'Não foi encontrada uma proteção ativa para desativar.'
        )
      }

      await unenrollMfaFactor(factorId)

      setMfaConfigured(false)
      setVerifiedMfaFactorId('')
      setMfaManageOpen(false)

      setSecurityMessage('Proteção extra desativada com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível desativar a proteção extra.'
      )
    } finally {
      setMfaActionLoading(false)
    }
  }

  const handleReplaceMfa = async () => {
    setMessage('')
    setError('')
    setMfaActionLoading(true)

    try {
      const factorId = await resolveVerifiedMfaFactorId()

      if (!factorId) {
        throw new Error(
          'Não foi encontrada uma proteção ativa para substituir.'
        )
      }

      setPreviousMfaFactorId(factorId)
      setMfaReplacing(true)
      setMfaManageOpen(false)

      const enrolled = await enrollTotpMfa(
        `Smart-tec ERP novo ${Date.now()}`
      )

      if (!enrolled?.id || !enrolled?.totp?.qr_code) {
        throw new Error(
          'Não foi possível gerar o novo autenticador.'
        )
      }

      const challenge = await challengeTotpMfa(enrolled.id)

      if (!challenge?.id) {
        throw new Error(
          'Não foi possível iniciar a confirmação do novo autenticador.'
        )
      }

      setMfaFactorId(enrolled.id)
      setMfaChallengeId(challenge.id)
      setMfaQrCode(enrolled.totp.qr_code)
      setMfaSecret(enrolled.totp.secret ?? '')
      setMfaCode('')
      setMfaEditing(true)

    } catch (err) {
      setMfaReplacing(false)
      setPreviousMfaFactorId('')

      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível trocar o aplicativo autenticador.'
      )
    } finally {
      setMfaActionLoading(false)
    }
  }
  const handlePasswordChange = async () => {
    setMessage('')
    setError('')

    if (newPassword.length < 8) {
      setError('A nova senha deve ter pelo menos 8 caracteres.')
      return
    }

    if (newPassword !== confirmNewPassword) {
      setError('As senhas não conferem.')
      return
    }

    setChangingPassword(true)

    try {
      await updateAuthenticatedPassword(newPassword)

      setMessage('Senha alterada com sucesso.')
      setNewPassword('')
      setConfirmNewPassword('')
      setPasswordEditing(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível alterar a senha.'
      )
    } finally {
      setChangingPassword(false)
    }
  }
  const handleEmailChange = async () => {
    const normalizedEmail = newEmail.trim().toLowerCase()

    setMessage('')
    setError('')

    if (!normalizedEmail || !normalizedEmail.includes('@')) {
      setError('Informe um e-mail válido.')
      return
    }

    if (normalizedEmail === userEmail.toLowerCase()) {
      setError('Informe um e-mail diferente do atual.')
      return
    }

    setChangingEmail(true)

    try {
      await requestEmailChange(normalizedEmail)

      setMessage(
        'Solicitação enviada. Confirme o novo e-mail para concluir a alteração.'
      )

      setNewEmail('')
      setEmailEditing(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível solicitar a alteração do e-mail.'
      )
    } finally {
      setChangingEmail(false)
    }
  }
  const handlePhotoSelected = async (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0]

    if (!file) return

    setMessage('')
    setError('')

    const allowed = ['image/jpeg', 'image/png', 'image/webp']

    if (!allowed.includes(file.type)) {
      setError('Use uma imagem JPG, PNG ou WEBP.')
      event.target.value = ''
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('A imagem deve ter no máximo 5 MB.')
      event.target.value = ''
      return
    }

    setUploading(true)

    try {
      const accessToken = await getAccessToken()
      const formData = new FormData()

      formData.append('file', file)

      const response = await fetch(`${API_URL}/auth/me/photo`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Não foi possível enviar a foto (${response.status}).`
        )
      }

      if (!body?.foto_url) {
        throw new Error('O servidor não retornou a nova foto.')
      }

      setPhotoPath(body.foto_url)
      await refreshAuthSession()
      setPhotoMessage('Foto atualizada com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível enviar a foto.'
      )
    } finally {
      setUploading(false)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  const handleRemovePhoto = async () => {
    if (!photoPath || uploading) return

    setUploading(true)
    setMessage('')
    setError('')

    try {
      const accessToken = await getAccessToken()

      if (!accessToken) {
        throw new Error('Sessão autenticada não encontrada.')
      }

      const response = await fetch(`${API_URL}/auth/me/photo`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      const body = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Não foi possível remover a foto (${response.status}).`
        )
      }

      setPhotoPath(null)
      await refreshAuthSession()
      setPhotoMessage('Foto removida com sucesso.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível remover a foto.'
      )
    } finally {
      setUploading(false)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  return (
    <section className="profile-page">
      <div className="profile-heading">
        <div>
          <p className="eyebrow">CONTA</p>
          <h1>Meus dados</h1>
          <p>Gerencie suas informações pessoais e de acesso.</p>
        </div>
      </div>

      <div className="profile-card">
        <div className="profile-card-header">
          <div className="profile-avatar-large">
            {photoUrl ? (
              <img src={photoUrl} alt={savedName} />
            ) : (
              initials || '?'
            )}
          </div>

          <div>
            <h2>{savedName}</h2>
            <p>{userEmail}</p>
            <span>{displayUserRole}</span>
          </div>
        </div>

        <div className="profile-grid">
          <div className="profile-field">
            <label>Nome</label>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
            />
          </div>

          <div className="profile-field profile-email-field">
            <label>E-mail</label>

            <div className="profile-email-current">
              <input value={userEmail} readOnly />

              {!emailEditing && (
                <button
                  type="button"
                  className="profile-secondary-button"
                  onClick={() => {
                    setEmailEditing(true)
                    setNewEmail('')
                    setMessage('')
                    setError('')
                  }}
                >
                  Alterar e-mail
                </button>
              )}
            </div>

            {emailEditing && (
              <div className="profile-email-editor">
                <input
                  type="email"
                  placeholder="Novo e-mail"
                  value={newEmail}
                  onChange={(event) => setNewEmail(event.target.value)}
                />

                <div className="profile-email-actions">
                  <button
                    type="button"
                    className="profile-secondary-button"
                    onClick={() => {
                      setEmailEditing(false)
                      setNewEmail('')
                      setMessage('')
                      setError('')
                    }}
                  >
                    Cancelar
                  </button>

                  <button
                    type="button"
                    className="primary-button"
                    disabled={changingEmail}
                    onClick={handleEmailChange}
                  >
                    {changingEmail
                      ? 'Enviando...'
                      : 'Confirmar novo e-mail'}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="profile-field">
            <label>Perfil</label>
            <input value={displayUserRole} readOnly />
          </div>
        </div>

        <div className="profile-actions">
          <div>
            {message && (
              <span className="profile-message profile-message-success">
                {message}
              </span>
            )}

            {error && (
              <span className="profile-message profile-message-error">
                {error}
              </span>
            )}
          </div>

          <button
            type="button"
            className="primary-button"
            disabled={!hasChanges || saving}
            onClick={handleSave}
          >
            {saving ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>

        <div className="profile-security-section">
          <div className="profile-security-copy">
            <strong>Acesso e segurança</strong>
            <p>Gerencie sua senha de acesso ao sistema.</p>
          </div>

          <div className="profile-security-content">
          {securityMessage && (
            <div className="profile-security-message" role="status">
              {securityMessage}
            </div>
          )}
            {!passwordEditing ? (
              <button
                type="button"
                className="profile-secondary-button"
                onClick={() => {
                  setPasswordEditing(true)
                  setMessage('')
                  setError('')
                }}
              >
                Alterar senha
              </button>
            ) : (
              <div className="profile-password-editor">
                <input
                  type="password"
                  placeholder="Nova senha"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />

                <input
                  type="password"
                  placeholder="Confirmar nova senha"
                  value={confirmNewPassword}
                  onChange={(event) => setConfirmNewPassword(event.target.value)}
                />

                <div className="profile-password-actions">
                  <button
                    type="button"
                    className="profile-secondary-button"
                    onClick={() => {
                      setPasswordEditing(false)
                      setNewPassword('')
                      setConfirmNewPassword('')
                      setMessage('')
                      setError('')
                    }}
                  >
                    Cancelar
                  </button>

                  <button
                    type="button"
                    className="primary-button"
                    disabled={changingPassword}
                    onClick={handlePasswordChange}
                  >
                    {changingPassword ? 'Salvando...' : 'Salvar nova senha'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="profile-mfa-section">
          <div className="profile-mfa-copy">
            <strong>Verificação em duas etapas</strong>
            <p>Adicione uma proteção extra à sua conta. Ao entrar, além da senha, você confirma um código pelo celular.</p>
          </div>

          {!mfaConfigured && !mfaEditing && (
            <button
              type="button"
              className="profile-secondary-button"
              disabled={mfaLoading}
              onClick={handleStartMfa}
            >
              {mfaLoading ? 'Preparando...' : 'Ativar proteção extra'}
            </button>
          )}

          {mfaConfigured && !mfaEditing && (
            <div className="profile-mfa-active">
              <div className="profile-mfa-active-status">
                <span className="profile-mfa-enabled">
                  Proteção extra ativada
                </span>

                <p>
                  Sua conta está protegida com verificação em duas etapas.
                </p>
              </div>

              <button
                type="button"
                className="profile-secondary-button"
                onClick={() =>
                  setMfaManageOpen((current) => !current)
                }
              >
                {mfaManageOpen
                  ? 'Fechar gerenciamento'
                  : 'Gerenciar proteção'}
              </button>

              {mfaManageOpen && (
                <div className="profile-mfa-manage-panel">
                  <div>
                    <strong>Aplicativo autenticador</strong>
                    <p>
                      Você pode trocar o aplicativo usado para gerar
                      os códigos ou desativar a proteção desta conta.
                    </p>
                  </div>

                  <div className="profile-mfa-manage-actions">
                    <button
                      type="button"
                      className="profile-secondary-button"
                      disabled={mfaActionLoading}
                      onClick={handleReplaceMfa}
                    >
                      {mfaActionLoading
                        ? 'Aguarde...'
                        : 'Trocar aplicativo autenticador'}
                    </button>

                    <button
                      type="button"
                      className="profile-danger-button"
                      disabled={mfaActionLoading}
                      onClick={handleDisableMfa}
                    >
                      Desativar proteção extra
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {mfaEditing && (
            <div className="profile-mfa-editor">
              <div className="profile-mfa-instructions">
                Abra no celular um aplicativo autenticador, como Google Authenticator
                ou Microsoft Authenticator. Depois, escaneie o QR Code abaixo e
                digite o código de 6 dígitos gerado pelo aplicativo.
              </div>

              {mfaQrCode && (
                <div className="profile-mfa-qr">
                  <img
                    src={(() => {
                      const qr = mfaQrCode.trim()

                      if (qr.startsWith('data:image/')) {
                        return qr
                      }

                      if (
                        qr.startsWith('<svg') ||
                        qr.startsWith('<?xml') ||
                        qr.includes('<svg')
                      ) {
                        return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qr)}`
                      }

                      return qr
                    })()}
                    alt="QR Code da autenticação em duas etapas"
                  />
                </div>
              )}

              {mfaSecret && (
                <div className="profile-mfa-secret">
                  <span>Chave para configuração manual:</span>
                  <code>{mfaSecret}</code>
                </div>
              )}

              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="Código de 6 dígitos"
                value={mfaCode}
                onChange={(event) =>
                  setMfaCode(
                    event.target.value.replace(/\D/g, '').slice(0, 6)
                  )
                }
              />

              <div className="profile-mfa-actions">
                <button
                  type="button"
                  className="profile-secondary-button"
                  disabled={mfaLoading}
                  onClick={() => {
                    setMfaEditing(false)
                    setMfaFactorId('')
                    setMfaChallengeId('')
                    setMfaQrCode('')
                    setMfaSecret('')
                    setMfaCode('')
                    setMessage('')
                    setError('')
                  }}
                >
                  Cancelar
                </button>

                <button
                  type="button"
                  className="primary-button"
                  disabled={mfaLoading || mfaCode.length !== 6}
                  onClick={handleVerifyMfa}
                >
                  {mfaLoading ? 'Validando...' : 'Confirmar e ativar'}
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="profile-photo-section">
          {photoMessage && (
            <div className="profile-photo-message" role="status">
              {photoMessage}
            </div>
          )}

          <div className="profile-photo-box">
          <div className="profile-photo-info">
            <div className="profile-photo-preview">
              {photoUrl ? (
                <img src={photoUrl} alt="Foto do perfil" />
              ) : (
                <span>{initials}</span>
              )}
            </div>

            <div>
              <strong>Foto do perfil</strong>
              <p>JPG, PNG ou WEBP de até 5 MB.</p>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handlePhotoSelected}
            hidden
          />

          <div className="profile-photo-actions">
            <button
              type="button"
              className="profile-secondary-button"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading
                ? 'Enviando...'
                : photoUrl
                  ? 'Alterar foto'
                  : 'Selecionar foto'}
            </button>

            {photoUrl && (
              <button
                type="button"
                className="profile-photo-remove"
                disabled={uploading}
                onClick={handleRemovePhoto}
              >
                Remover foto
              </button>
            )}
          </div>
        </div>
      </div>
          </div>
</section>
  )
}