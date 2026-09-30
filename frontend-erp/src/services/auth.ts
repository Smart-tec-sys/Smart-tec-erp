export type AuthCompany = {
  id: number
  nome: string
  nome_fantasia?: string | null
  logo_url?: string | null
  slug?: string | null
  papel: string
}

export type AuthUser = {
  id: number
  email: string
  nome?: string | null
  foto_url?: string | null
}

export type AuthMe = {
  user: AuthUser
  empresas: AuthCompany[]
}

type StoredSession = {
  accessToken: string
  refreshToken: string
  expiresAt: number
  empresaId?: number
}

type SupabaseTokenResponse = {
  access_token?: string
  refresh_token?: string
  expires_in?: number
}

const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? 'dev'
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL ?? '').replace(/\/+$/, '')
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? ''
const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const SESSION_KEY = 'smarttec.erp.auth.v1'

export const authEnabled = AUTH_MODE === 'authenticated'

let refreshInFlight: Promise<StoredSession> | null = null

function requireConfig() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error('Autentica??o da Beta n?o configurada.')
  }
}

function readSession(): StoredSession | null {
  const raw = sessionStorage.getItem(SESSION_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as StoredSession
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
    return null
  }
}

function saveSession(session: StoredSession) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearAuthSession() {
  sessionStorage.removeItem(SESSION_KEY)
}

export function hasStoredAuthSession() {
  return Boolean(readSession())
}

export function getEmpresaId() {
  return readSession()?.empresaId ?? null
}

export function setEmpresaId(empresaId: number) {
  const session = readSession()
  if (!session) throw new Error('Sess?o n?o encontrada.')

  saveSession({
    ...session,
    empresaId,
  })
}

async function tokenRequest(
  grantType: 'password' | 'refresh_token',
  payload: Record<string, string>,
): Promise<StoredSession> {
  requireConfig()

  const response = await fetch(
    `${SUPABASE_URL}/auth/v1/token?grant_type=${grantType}`,
    {
      method: 'POST',
      headers: {
        apikey: SUPABASE_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  )

  const body = await response.json().catch(() => ({})) as
    SupabaseTokenResponse & {
      msg?: string
      error_description?: string
    error?: string
    }

  if (!response.ok) {
    const detail =
      body.msg ||
      body.error_description ||
      body.error ||
      `Falha no login Supabase (${response.status}).`

    if (detail.toLowerCase().includes('confirm')) {
      throw new Error('Confirme seu e-mail antes de entrar.')
    }

    throw new Error(detail)
  }

  if (!body.access_token || !body.refresh_token) {
    throw new Error('Resposta de autentica??o inv?lida.')
  }

  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    expiresAt: Date.now() + Number(body.expires_in || 0) * 1000,
  }
}

export async function loginWithPassword(email: string, password: string) {
  const normalizedEmail = email.trim().toLowerCase()

  if (!normalizedEmail || !password) {
    throw new Error('Informe e-mail e senha.')
  }

  const session = await tokenRequest('password', {
    email: normalizedEmail,
    password,
  })

  saveSession(session)
  return session
}

export async function requestPasswordRecovery(email: string) {
  requireConfig()

  const normalizedEmail = email.trim().toLowerCase()

  if (!normalizedEmail) {
    throw new Error('Informe seu e-mail.')
  }

  const redirectTo = `${window.location.origin}${window.location.pathname}`

  const response = await fetch(`${SUPABASE_URL}/auth/v1/recover`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: normalizedEmail,
      redirect_to: redirectTo,
    }),
  })

  /*
   * N?o revelar se o e-mail existe.
   * Mesmo em resposta de erro de usu?rio inexistente, a UI usa mensagem neutra.
   */
  if (!response.ok && response.status >= 500) {
    throw new Error('N?o foi poss?vel enviar o e-mail agora.')
  }
}

export function captureRecoverySessionFromUrl() {
  const hash = new URLSearchParams(
    window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash,
  )

  const accessToken = hash.get('access_token')
  const refreshToken = hash.get('refresh_token')
  const expiresIn = Number(hash.get('expires_in') || 0)
  const type = hash.get('type')

  if (type !== 'recovery' || !accessToken) {
    return false
  }

  saveSession({
    accessToken,
    refreshToken: refreshToken ?? '',
    expiresAt: Date.now() + expiresIn * 1000,
  })

  window.history.replaceState(
    {},
    document.title,
    window.location.pathname + window.location.search,
  )

  return true
}

export async function updateRecoveredPassword(password: string) {
  requireConfig()

  if (password.length < 8) {
    throw new Error('A nova senha deve ter pelo menos 8 caracteres.')
  }

  const session = readSession()

  if (!session?.accessToken) {
    throw new Error('Link de recupera??o inv?lido ou expirado.')
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: 'PUT',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      password,
    }),
  })

  if (!response.ok) {
    throw new Error('N?o foi poss?vel redefinir a senha. Solicite um novo link.')
  }

  clearAuthSession()
}


export async function updateAuthenticatedPassword(password: string) {
  requireConfig()

  if (password.length < 8) {
    throw new Error('A nova senha deve ter pelo menos 8 caracteres.')
  }

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: 'PUT',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      password,
    }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail =
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      ''

    throw new Error(
      detail || 'Não foi possível alterar a senha.'
    )
  }

  return body
}
async function refreshSession() {
  const current = readSession()

  if (!current?.refreshToken) {
    throw new Error('Sess?o expirada.')
  }

  const refreshed = await tokenRequest('refresh_token', {
    refresh_token: current.refreshToken,
  })

  const next = {
    ...refreshed,
    empresaId: current.empresaId,
  }

  saveSession(next)
  return next
}

export async function getAccessToken() {
  if (!authEnabled) return null

  let session = readSession()

  if (!session) {
    throw new Error('Sess?o n?o encontrada.')
  }

  if (session.expiresAt > Date.now() + 60_000) {
    return session.accessToken
  }

  if (!refreshInFlight) {
    refreshInFlight = refreshSession()
      .catch(error => {
        const detail =
          error instanceof Error ? error.message : String(error)

        throw new Error(`AUTH REFRESH: ${detail}`)
      })
      .finally(() => {
        refreshInFlight = null
      })
  }

  session = await refreshInFlight
  return session.accessToken
}

export async function getAuthMe(): Promise<AuthMe> {
  const token = await getAccessToken()

  if (!token) {
    throw new Error('Autentica??o n?o dispon?vel.')
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('Usu?rio sem acesso autorizado ? Smart-tec ERP.')
    }

    throw new Error(`Falha ao validar acesso (${response.status}).`)
  }

  return response.json() as Promise<AuthMe>
}

export async function initializeAuthenticatedSession() {
  const me = await getAuthMe()

  if (!me.empresas.length) {
    throw new Error('Usu?rio sem empresa autorizada.')
  }

  const currentEmpresaId = getEmpresaId()
  const empresa =
    me.empresas.find(item => item.id === currentEmpresaId) ??
    me.empresas[0]

  setEmpresaId(empresa.id)

  return {
    ...me,
    empresa,
  }
}


export async function requestEmailChange(newEmail: string) {
  requireConfig()

  const normalizedEmail = newEmail.trim().toLowerCase()

  if (!normalizedEmail || !normalizedEmail.includes('@')) {
    throw new Error('Informe um e-mail válido.')
  }

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: 'PUT',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: normalizedEmail,
    }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail =
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      ''

    if (String(detail).toLowerCase().includes('already')) {
      throw new Error('Este e-mail já está sendo utilizado.')
    }

    throw new Error(
      detail || 'Não foi possível solicitar a alteração do e-mail.'
    )
  }

  return body
}

export async function enrollTotpMfa(friendlyName = 'Smart-tec ERP') {
  requireConfig()

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/factors`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      factor_type: 'totp',
      friendly_name: friendlyName,
      issuer: 'Smart-tec Sistemas',
    }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      'Não foi possível iniciar a configuração da autenticação em duas etapas.'
    )
  }

  return body
}

export async function challengeTotpMfa(factorId: string) {
  requireConfig()

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  let response: Response

  try {
    response = await fetch(
      `${SUPABASE_URL}/auth/v1/factors/${factorId}/challenge`,
      {
        method: 'POST',
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      }
    )
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : String(error)

    throw new Error(`MFA CHALLENGE: ${detail}`)
  }

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      'Não foi possível criar o desafio de autenticação.'
    )
  }

  return body
}

export async function verifyTotpMfa(
  factorId: string,
  challengeId: string,
  code: string
) {
  requireConfig()

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const normalizedCode = code.trim()

  if (!/^\d{6}$/.test(normalizedCode)) {
    throw new Error('Informe o código de 6 dígitos.')
  }

  let response: Response

  try {
    response = await fetch(
      `${SUPABASE_URL}/auth/v1/factors/${factorId}/verify`,
      {
        method: 'POST',
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          challenge_id: challengeId,
          code: normalizedCode,
        }),
      }
    )
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : String(error)

    throw new Error(`MFA VERIFY: ${detail}`)
  }

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      'Código inválido ou expirado.'
    )
  }

  if (body?.access_token) {
    const current = readSession()

    saveSession({
      accessToken: body.access_token,
      refreshToken: body.refresh_token ?? current?.refreshToken ?? '',
      expiresAt:
        Date.now() + Number(body.expires_in ?? 3600) * 1000,
      empresaId: current?.empresaId ?? 1,
    })
  }

  return body
}

export async function listMfaFactors() {
  requireConfig()

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      'Não foi possível consultar a autenticação em duas etapas.'
    )
  }

  return Array.isArray(body?.factors) ? body.factors : []
}

export async function unenrollMfaFactor(factorId: string) {
  requireConfig()

  const accessToken = await getAccessToken()

  if (!accessToken) {
    throw new Error('Sessão autenticada não encontrada.')
  }

  const response = await fetch(
    `${SUPABASE_URL}/auth/v1/factors/${factorId}`,
    {
      method: 'DELETE',
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${accessToken}`,
      },
    }
  )

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      body?.msg ||
      body?.message ||
      body?.error_description ||
      body?.error ||
      'Não foi possível cancelar a configuração do 2FA.'
    )
  }

  return body
}
export async function getApiAuthHeaders(): Promise<Record<string, string>> {
  if (!authEnabled) {
    return {
      'X-Empresa-ID': '1',
    }
  }

  const token = await getAccessToken()
  const empresaId = getEmpresaId()

  if (!token || !empresaId) {
    throw new Error('Sess?o autenticada incompleta.')
  }

  return {
    Authorization: `Bearer ${token}`,
    'X-Empresa-ID': String(empresaId),
  }
}
