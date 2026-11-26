
import { type ApiProduct, type BudgetProduct } from '../types/budget'
import { normalizeRoloDrive } from '../types/rolo'
import { useEffect, useState } from 'react'
import { getRoloMotors } from '../services/api'
import type { RoloMotor } from '../types/rolo'
import { parseDecimal } from '../types/budget'

type Props = {
    product: BudgetProduct
    catalog: ApiProduct[]
    onChange: (product: BudgetProduct) => void
}

export function RoloMotorSelector({ product, catalog, onChange }: Props) {
    const [fornecedor, setFornecedor] = useState('')

    const motorized = normalizeRoloDrive(
        product.acionamento ??
        (product.roloKind === 'MOTORIZADA' ? 'motorizado' : 'manual')
    ) === 'motorizado'

    const [consulta, setConsulta] = useState<{
        chave: string
        motores: RoloMotor[]
        erro?: string
    } | null>(null)

    const chave = JSON.stringify([
        product.productId,
        product.width,
        product.height,
        product.quantity,
        product.color || '',
        motorized
    ])

    useEffect(() => {
        const [produto_id, width, height, quantidade, cor, ativo] =
            JSON.parse(chave)

        const largura = parseDecimal(width)
        const altura = parseDecimal(height)

        if (!ativo || !produto_id || largura <= 0 || altura <= 0
            || !Number.isInteger(quantidade) || quantidade <= 0) return

        let cancelado = false

        const timer = setTimeout(() => {
            getRoloMotors({
                produto_id,
                largura,
                altura,
                quantidade,
                desconto: 0,
                perfil_comercial: 'VAREJO',
                cor: cor || undefined,
                acionamento: 'motorizado'
            }).then(resultado => {
                if (!cancelado) {
                    setConsulta({ chave, motores: resultado })
                }
            }).catch(erro => {
                if (!cancelado) {
                    setConsulta({
                        chave,
                        motores: [],
                        erro: erro instanceof Error
                            ? erro.message
                            : 'Falha na consulta tecnica.'
                    })
                }
            })
        }, 350)

        return () => {
            cancelado = true
            clearTimeout(timer)
        }
    }, [chave])

    if (!motorized) return null

    const atual = consulta?.chave === chave
        ? consulta
        : null

    const tecnicos = atual?.motores ?? []

    const ids = new Set(
        tecnicos.filter(m => m.kits.length === 1)
            .map(m => m.produto_id)
    )

    const motores = catalog.filter(p => ids.has(p.id))

    const fornecedores = [...new Set(
        motores.map(p => p.nome_fornecedor || 'Fornecedor não informado')
    )].sort()

    const motoresFiltrados = fornecedor
        ? motores.filter(p =>
            (p.nome_fornecedor || 'Fornecedor não informado') === fornecedor
        )
        : motores

    return (
        <>
            <label className="field">
                <span>Fornecedor do motor</span>
                <select
                    aria-label="Fornecedor do motor"
                    value={fornecedor}
                    onChange={event => {
                        setFornecedor(event.target.value)
                        onChange({
                            ...product,
                            motorProdutoId: undefined,
                            kitProdutoId: undefined,
                            rolo: undefined,
                            suggestedPrice: undefined,
                        })
                    }}
                >
                    <option value="">Todos os fornecedores</option>
                    {fornecedores.map(nome => (
                        <option key={nome} value={nome}>{nome}</option>
                    ))}
                </select>
            </label>

            <label className="field">
                <span>Modelo do motor</span>
                <select
                    aria-label={`Motor de ${product.product || 'Rolô'}`}
                    value={product.motorProdutoId ?? ''}
                    onChange={event => onChange({
                        ...product,
                        motorProdutoId: event.target.value
                            ? Number(event.target.value)
                            : undefined,
                        kitProdutoId: undefined,
                        rolo: undefined,
                        suggestedPrice: undefined,
                    })}
                >
                    <option value="">Selecione o motor</option>
                    {motoresFiltrados.map(p => (
                        <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                </select>
                {!atual && (
                    <small>Informe as medidas e aguarde a consulta tecnica.</small>
                )}
                {atual?.erro && (
                    <small role="alert">{atual.erro}</small>
                )}
                {atual && !atual.erro && !motoresFiltrados.length && (
                    <small>Nenhum motor compativel com esta configuracao.</small>
                )}
                {product.motorProdutoId != null && atual
                    && !ids.has(product.motorProdutoId) && (
                    <small role="alert">
                        Motor selecionado incompativel.
                        Selecione novamente.
                    </small>
                )}
                {tecnicos.some(m =>
                    m.produto_id === product.motorProdutoId
                    && m.carga_pendente === true
                ) && (
                    <small role="status">
                        Capacidade de carga pendente de confirmacao.
                    </small>
                )}
            </label>

            {product.motorProdutoId != null && (
                <label className="field">
                    <span>
                        <input
                            type="checkbox"
                            checked={product.incluirKitInstalacao ?? false}
                            onChange={event => onChange({
                                ...product,
                                incluirKitInstalacao: event.target.checked,
                                rolo: undefined,
                                suggestedPrice: undefined,
                            })}
                        />
                        {' '}Incluir conjunto de instalacao
                    </span>
                </label>
            )}
        </>
    )
}
