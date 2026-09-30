import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { getAllProducts } from '../services/api'
import type { ApiProduct } from '../types/budget'

const INITIAL_BACKGROUND_DELAY_MS = 3000
const FOCUS_REFRESH_INTERVAL_MS = 5 * 60 * 1000

export function useStockNotifications(
  _activeView: string,
  refreshKey: number,
) {
  const [products, setProducts] =
    useState<ApiProduct[]>([])

  const [loading, setLoading] =
    useState(false)

  const [error, setError] =
    useState('')

  const mountedRef = useRef(true)
  const loadingRef = useRef(false)
  const lastLoadedAtRef = useRef(0)
  const lastRefreshKeyRef =
    useRef(refreshKey)

  const load = useCallback(async () => {
    if (loadingRef.current) return

    loadingRef.current = true

    if (mountedRef.current) {
      setLoading(true)
      setError('')
    }

    try {
      const data = await getAllProducts()

      if (!mountedRef.current) return

      setProducts(data)
      lastLoadedAtRef.current = Date.now()
    } catch (err) {
      if (!mountedRef.current) return

      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível carregar os produtos.',
      )
    } finally {
      loadingRef.current = false

      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  /*
   * Carga inicial em segundo plano.
   *
   * Não bloqueia a abertura do ERP e não dispara
   * imediatamente junto com autenticação, agenda,
   * orçamentos e demais cargas iniciais.
   */
  useEffect(() => {
    mountedRef.current = true

    const timer = window.setTimeout(
      () => {
        void load()
      },
      INITIAL_BACKGROUND_DELAY_MS,
    )

    return () => {
      mountedRef.current = false
      window.clearTimeout(timer)
    }
  }, [load])

  /*
   * Atualiza quando alguma operação real informa
   * mudança através de refreshKey.
   *
   * Trocar apenas de tela NÃO recarrega o catálogo.
   */
  useEffect(() => {
    if (
      refreshKey ===
      lastRefreshKeyRef.current
    ) {
      return
    }

    lastRefreshKeyRef.current =
      refreshKey

    void load()
  }, [refreshKey, load])

  /*
   * Ao voltar para a janela, só atualiza se os dados
   * estiverem antigos. Evita milhares de produtos
   * sendo baixados em cada Alt+Tab/foco.
   */
  useEffect(() => {
    const handleFocus = () => {
      const age =
        Date.now() -
        lastLoadedAtRef.current

      if (
        lastLoadedAtRef.current > 0 &&
        age < FOCUS_REFRESH_INTERVAL_MS
      ) {
        return
      }

      void load()
    }

    window.addEventListener(
      'focus',
      handleFocus,
    )

    return () => {
      window.removeEventListener(
        'focus',
        handleFocus,
      )
    }
  }, [load])

  const refresh = useCallback(() => {
    void load()
  }, [load])

  return {
    products,
    loading,
    error,
    refresh,
  }
}

export type StockNotificationsState =
  ReturnType<typeof useStockNotifications>