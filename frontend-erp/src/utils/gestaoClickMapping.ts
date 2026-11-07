import type { ImportConfig, ImportSourceConfig, ImportTable } from '../services/clienteImport'

const expected = {
  clientes: { total: 16, columns: { 0: 'Codigo', 1: 'Tipo de pessoa', 2: 'Nome', 3: 'CPF', 8: 'CNPJ', 12: 'Telefone', 13: 'Celular', 14: 'E-mail' } },
  enderecos: { total: 9, columns: { 1: 'Tipo', 2: 'CEP', 3: 'Logradouro', 5: 'Complemento', 6: 'Bairro', 7: 'Cidade', 8: 'UF' } },
  contatos: { total: 6, columns: { 1: 'Tipo de contato', 2: 'Nome', 3: 'Contato', 4: 'Cargo' } },
}

export function gestaoClickMapping(
  config: ImportConfig, clientes: ImportTable,
  enderecos: ImportTable, contatos: ImportTable,
): ImportConfig {
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
  for (const [name, table] of Object.entries({ clientes, enderecos, contatos })) {
    const signature = expected[name as keyof typeof expected]
    if (table.colunas.length !== signature.total ||
        Object.entries(signature.columns).some(([index, label]) => normalize(table.colunas[Number(index)]) !== normalize(label))) {
      throw new Error(`Colunas de ${name} diferentes do backup GestãoClick analisado. Use o mapeamento manual e confira a amostra.`)
    }
  }
  const source = (table: ImportTable, mapeamento: Record<string, number>, options = config): ImportSourceConfig => {
    if (!/^c[o\uFFFD]digo$/.test(normalize(table.colunas[0]))) {
      throw new Error('Coluna de código do cliente não reconhecida. Confira o mapeamento manual.')
    }
    const separators: ImportSourceConfig['separador'][] = ['auto', ';', ',', '\t', '|']
    const separator = table.separador == null ? 'auto' : separators.find(value => value === table.separador)
    if (!separator) throw new Error('Separador não reconhecido. Confira as opções de leitura.')
    return {
      codigo_cliente: 0, mapeamento, linha_cabecalho: options.linha_cabecalho, aba: table.aba,
      separador: separator, encoding: options.encoding,
    }
  }
  return {
    ...config, ...source(clientes, { tipo: 1, nome: 2, cpf: 3, cnpj: 8, telefone_comercial: 12, telefone_celular: 13, email: 14 }),
    enderecos: source(enderecos, { tipo_endereco: 1, cep: 2, logradouro: 3, numero: 4, complemento: 5, bairro: 6, cidade: 7, estado: 8 }, { ...config, ...config.enderecos }),
    contatos: source(contatos, { tipo_contato: 1, nome_contato: 2, contato: 3, cargo: 4, observacao_contato: 5 }, { ...config, ...config.contatos }),
  }
}
