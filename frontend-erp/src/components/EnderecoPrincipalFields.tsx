import type { EnderecoPrincipal } from '../services/cadastroConsultas'

export type CampoEndereco = keyof EnderecoPrincipal
type Props = {
  valores: Record<CampoEndereco, string>
  disabled?: boolean
  onChange: (campo: CampoEndereco, valor: string) => void
}

export function EnderecoPrincipalFields({ valores, disabled = false, onChange }: Props) {
  const fields: { campo: CampoEndereco; label: string; maxLength: number }[] = [
    { campo: 'cep', label: 'CEP', maxLength: 9 },
    { campo: 'logradouro', label: 'Logradouro', maxLength: 255 },
    { campo: 'numero', label: 'Número', maxLength: 30 },
    { campo: 'complemento', label: 'Complemento', maxLength: 255 },
    { campo: 'bairro', label: 'Bairro', maxLength: 100 },
    { campo: 'cidade', label: 'Cidade', maxLength: 150 },
    { campo: 'estado', label: 'UF', maxLength: 2 },
  ]
  return <div className="revenda-fields">
    {fields.map(({ campo, label, maxLength }) => <label className="cad-field" key={campo}>
      <span>{label}</span>
      <input name={campo} value={valores[campo]} disabled={disabled} maxLength={maxLength}
        inputMode={campo === 'cep' ? 'numeric' : undefined}
        onChange={event => onChange(campo, campo === 'estado' ? event.target.value.toUpperCase() : event.target.value)} />
    </label>)}
  </div>
}
