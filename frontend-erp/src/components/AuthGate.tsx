import { resolveLoginAccess } from '../utils/loginAccess'
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  type FormEvent,
  type ReactNode,
} from 'react'
import {
  authEnabled,
  AuthTokenError,
  captureRecoverySessionFromUrl,
  clearAuthSession,
  hasStoredAuthSession,
  getPendingLoginStage,
  setPendingLoginStage,
  initializeAuthenticatedSession,
  loginWithPassword,
  requestPasswordRecovery,
  updateRecoveredPassword,
  listMfaFactors,
  challengeTotpMfa,
  verifyTotpMfa,
} from '../services/auth'

type Props = {
  children: ReactNode
}

type AuthSession = Awaited<ReturnType<typeof initializeAuthenticatedSession>>

const AuthSessionContext = createContext<AuthSession | null>(null)

const AuthSessionRefreshContext =
  createContext<(() => Promise<void>) | null>(null)

export function useAuthSession() {
  return useContext(AuthSessionContext)
}

export function useRefreshAuthSession() {
  const refresh = useContext(AuthSessionRefreshContext)

  if (!refresh) {
    throw new Error('Atualização da sessão indisponível.')
  }

  return refresh
}

type AuthView = 'login' | 'forgot' | 'reset' | 'mfa' | 'access'

export function AuthGate({ children }: Props) {
  const [checking, setChecking] = useState(authEnabled)
  const [authenticated, setAuthenticated] = useState(!authEnabled)
  const [authSession, setAuthSession] = useState<AuthSession | null>(null)

  const refreshAuthSession = async () => {
    const session = await initializeAuthenticatedSession()
    setAuthSession(session)
  }
  const [view, setView] = useState<AuthView>('login')

  const [mfaFactorId, setMfaFactorId] = useState('')
  const [mfaChallengeId, setMfaChallengeId] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const loginInFlight = useRef(false)
  const [error, setError] = useState('')
  const [loginErrorStatus, setLoginErrorStatus] = useState<number | null>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!authEnabled) return

    const recovery = captureRecoverySessionFromUrl()

    if (recovery) {
      setView('reset')
      setChecking(false)
      return
    }

    if (!hasStoredAuthSession()) {
      setChecking(false)
      return
    }

    let cancelled = false
    void loadLoginAccess()
      .then(result => { if (!cancelled) applyLoginAccess(result) })
      .catch(err => {
        if (cancelled) return
        setAuthenticated(false)
        setView('access')
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => { if (!cancelled) setChecking(false) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!authenticated) return

    const handleFocus = () => {
      void refreshAuthSession().catch(() => {
        setMessage('Não foi possível atualizar o perfil agora. A sessão atual foi mantida.')
      })
    }

    window.addEventListener('focus', handleFocus)

    return () => {
      window.removeEventListener('focus', handleFocus)
    }
  }, [authenticated])
  function loadLoginAccess(verifiedAccessToken?: string) {
    return resolveLoginAccess({
      factors: listMfaFactors,
      challenge: challengeTotpMfa,
      profile: () => initializeAuthenticatedSession(verifiedAccessToken),
      markProfile: () => setPendingLoginStage('profile'),
    }, getPendingLoginStage() === 'security')
  }

  function applyLoginAccess(result: Awaited<ReturnType<typeof loadLoginAccess>>) {
    setError('')
    if (result.kind === 'mfa') {
      setMfaFactorId(result.factorId)
      setMfaChallengeId(result.challengeId)
      setMfaCode('')
      setView('mfa')
      return
    }
    setPendingLoginStage(undefined)
    setAuthSession(result.session)
    setAuthenticated(true)
  }

  async function resumeLoginAccess(verifiedAccessToken?: string) {
    try { applyLoginAccess(await loadLoginAccess(verifiedAccessToken)) }
    catch (err) {
      setAuthenticated(false)
      setView('access')
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loginInFlight.current) return
    loginInFlight.current = true
    setSubmitting(true)
    setError('')
    setLoginErrorStatus(null)
    setMessage('')
    // Password managers can update native controls before React's onChange runs.
    const form = new FormData(event.currentTarget)
    const submittedEmail = String(form.get('email') ?? email)
    const submittedPassword = String(form.get('password') ?? password)
    try {
      try { await loginWithPassword(submittedEmail, submittedPassword) }
      catch (err) {
        clearAuthSession()
        setAuthenticated(false)
        setLoginErrorStatus(err instanceof AuthTokenError ? err.status : null)
        setError(err instanceof Error ? err.message : String(err))
        return
      }
      setPassword('')
      setView('access')
      await resumeLoginAccess()
    } finally {
      loginInFlight.current = false
      setSubmitting(false)
    }
  }

  async function handleAccessRetry() {
    if (loginInFlight.current) return
    loginInFlight.current = true
    setSubmitting(true)
    setError('')
    try { await resumeLoginAccess() }
    finally { loginInFlight.current = false; setSubmitting(false) }
  }

  async function handleMfaVerification(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()
    if (loginInFlight.current) return
    loginInFlight.current = true
    setSubmitting(true)
    setError('')
    setMessage('')

    try {
      const code = mfaCode.trim()

      if (!/^\d{6}$/.test(code)) {
        throw new Error('Informe o código de 6 dígitos.')
      }

      if (!mfaFactorId) {
        throw new Error(
          'A confirmação de segurança expirou. Entre novamente.'
        )
      }

      const freshChallenge = await challengeTotpMfa(mfaFactorId)

      if (!freshChallenge?.id) {
        throw new Error(
          'Não foi possível iniciar uma nova confirmação de segurança.'
        )
      }

      setMfaChallengeId(freshChallenge.id)

      const verifiedSession = await verifyTotpMfa(
        mfaFactorId,
        freshChallenge.id,
        code
      )

      setPendingLoginStage('profile')
      setView('access')
      await resumeLoginAccess(verifiedSession.accessToken)

      setMfaFactorId('')
      setMfaChallengeId('')
      setMfaCode('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      loginInFlight.current = false
      setSubmitting(false)
    }
  }
  async function handleRecovery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setMessage('')

    try {
      await requestPasswordRecovery(email)

      setMessage(
        'Se o e-mail estiver cadastrado, enviaremos um link para redefinir sua senha.',
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setMessage('')

    try {
      if (newPassword !== confirmPassword) {
        throw new Error('As senhas n?o conferem.')
      }

      await updateRecoveredPassword(newPassword)

      setNewPassword('')
      setConfirmPassword('')
      setView('login')
      setMessage('Senha redefinida. Voc? j? pode entrar com a nova senha.')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (!authEnabled) {
    return children
  }

  if (checking) {
    return (
      <main className="auth-page">
        <section className="auth-card auth-loading">
          <strong>Smart-tec ERP</strong>
          <span>Validando acesso...</span>
        </section>
      </main>
    )
  }

  if (authenticated && authSession) {
    return (
      <AuthSessionRefreshContext.Provider value={refreshAuthSession}>
        <AuthSessionContext.Provider value={authSession}>
          {children}
        </AuthSessionContext.Provider>
      </AuthSessionRefreshContext.Provider>
    )
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <strong>smart-tec</strong>
          <span>Sistemas</span>
        </div>

        <div className="auth-copy">
          <span className="auth-beta">BETA INTERNA</span>

          {view === 'login' && (
            <>
              <h1>Entrar no Smart-tec ERP</h1>
              <p>Use seu acesso autorizado para continuar.</p>
            </>
          )}

          {view === 'mfa' && (
            <>
              <h1>Confirme sua identidade</h1>
              <p>
                Abra o aplicativo autenticador no celular e informe
                o código de 6 dígitos para continuar.
              </p>
            </>
          )}
        {view === 'forgot' && (
            <>
              <h1>Recuperar senha</h1>
              <p>Informe seu e-mail para receber o link de redefini??o.</p>
            </>
          )}

          {view === 'reset' && (
            <>
              <h1>Definir nova senha</h1>
              <p>Crie uma nova senha para continuar usando o ERP.</p>
            </>
          )}
        </div>

        {view === 'login' && (
          <form className="auth-form" onSubmit={handleLogin} autoComplete="off">
            <label>
              <span>E-mail</span>
              <input
                type="email"
                name="email"
                autoComplete="off"
                value={email}
                onChange={event => setEmail(event.target.value)}
                required
                autoFocus
              />
            </label>

            <label>
              <span>Senha</span>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={event => setPassword(event.target.value)}
                required
              />
            </label>

            <button
              type="button"
              className="auth-link"
              onClick={() => {
                setError('')
                setMessage('')
                setView('forgot')
              }}
            >
              Esqueci minha senha
            </button>

            {error && <div className="auth-error" role="alert" data-auth-phase="password" data-auth-status={loginErrorStatus ?? undefined}>{error}</div>}
            {message && <div className="auth-message">{message}</div>}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting}
            >
              {submitting ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        )}

        {view === 'access' && (
          <div className="auth-form">
            <h2>Concluir acesso</h2>
            <p>Seu login foi recebido. Estamos validando a segurança e o acesso ao ERP.</p>
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button type="button" className="primary-button auth-submit" disabled={submitting} onClick={() => void handleAccessRetry()}>
              {submitting ? 'Validando acesso...' : 'Tentar novamente'}
            </button>
            <button type="button" className="auth-link" disabled={submitting} onClick={() => {
              clearAuthSession(); setError(''); setMessage(''); setView('login')
            }}>Voltar para o login</button>
          </div>
        )}
        {view === 'mfa' && (
          <form
            className="auth-form"
            onSubmit={handleMfaVerification}
          >
            <label>
              <span>Código de segurança</span>

              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={mfaCode}
                onChange={(event) =>
                  setMfaCode(
                    event.target.value
                      .replace(/\D/g, '')
                      .slice(0, 6)
                  )
                }
                placeholder="000000"
                autoFocus
                required
              />
            </label>

            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting || mfaCode.length !== 6}
            >
              {submitting
                ? 'Confirmando...'
                : 'Confirmar acesso'}
            </button>

            <button
              type="button"
              className="auth-link"
              onClick={() => {
                clearAuthSession()
                setMfaFactorId('')
                setMfaChallengeId('')
                setMfaCode('')
                setError('')
                setMessage('')
                setView('login')
              }}
            >
              Voltar para o login
            </button>
          </form>
        )}
        {view === 'forgot' && (
          <form className="auth-form" onSubmit={handleRecovery}>
            <label>
              <span>E-mail</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={event => setEmail(event.target.value)}
                required
                autoFocus
              />
            </label>

            {error && <div className="auth-error" role="alert">{error}</div>}
            {message && <div className="auth-message">{message}</div>}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting}
            >
              {submitting ? 'Enviando...' : 'Enviar link de recupera??o'}
            </button>

            <button
              type="button"
              className="auth-link"
              onClick={() => {
                setError('')
                setMessage('')
                setView('login')
              }}
            >
              Voltar para entrar
            </button>
          </form>
        )}

        {view === 'reset' && (
          <form className="auth-form" onSubmit={handleReset}>
            <label>
              <span>Nova senha</span>
              <input
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={event => setNewPassword(event.target.value)}
                minLength={8}
                required
                autoFocus
              />
            </label>

            <label>
              <span>Confirmar nova senha</span>
              <input
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={event => setConfirmPassword(event.target.value)}
                minLength={8}
                required
              />
            </label>

            {error && <div className="auth-error" role="alert">{error}</div>}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting}
            >
              {submitting ? 'Salvando...' : 'Redefinir senha'}
            </button>
          </form>
        )}
      </section>
    </main>
  )
}
