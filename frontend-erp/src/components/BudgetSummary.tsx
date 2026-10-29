import { ZeroNumberInput } from './ZeroNumberInput'
import { selectZeroOnFocus } from '../utils/selectZeroOnFocus'
import {
  ArrowLeft,
  Check,
  ChevronRight,
} from 'lucide-react'

import { formatCurrency } from '../types/budget'

type Props = {
  products:number
  services:number
  freight:number
  showFreight?:boolean

  discount:number
  onDiscount:(value:number)=>void

  includeBankFee:boolean
  onIncludeBankFee:(value:boolean)=>void

  bankFeePercent:number
  onBankFeePercent:(value:number)=>void

  internalValue:number
  partnerValue:number
  rtValue:number
  bankFeeValue:number
  clientTotal:number

  onCancel:()=>void
  onSave:()=>void

  saveLabel?:string
  saving?:boolean
  isCollapsed?:boolean
  onToggle?:()=>void
}

export function BudgetSummary({
  products,
  services,
  freight,
  showFreight = true,

  discount,
  onDiscount,

  includeBankFee,
  onIncludeBankFee,

  bankFeePercent,
  onBankFeePercent,

  internalValue,
  partnerValue,
  rtValue,
  bankFeeValue,
  clientTotal,

  onCancel,
  onSave,

  saveLabel = 'Salvar orçamento',
  saving,
  isCollapsed,
  onToggle,
}:Props){

  const subtotal=
    products+
    services+
    freight

  const discountPercent=
    subtotal>0
      ? discount/subtotal*100
      : 0

  const changeDiscountPercent=(value:number)=>{
    const percent=Math.max(
      0,
      Math.min(
        100,
        Number(value)||0
      )
    )

    onDiscount(
      subtotal*percent/100
    )
  }

  return (
    <aside onFocusCapture={selectZeroOnFocus}
      className={
        `budget-summary panel ${
          isCollapsed
            ? 'collapsed'
            : ''
        }`
      }
    >
      <div className="summary-heading">
        <div>
          <span className="eyebrow">
            RESUMO COMERCIAL
          </span>

          <h2>Conferência</h2>
        </div>

        <button
          type="button"
          className="summary-toggle"
          onClick={onToggle}
          aria-label={
            isCollapsed
              ? 'Mostrar resumo'
              : 'Recolher resumo'
          }
        >
          <ChevronRight size={16}/>
        </button>
      </div>

      {!isCollapsed && (
        <div>

          <div className="summary-lines">

            <div>
              <span>Produtos</span>
              <strong>
                {formatCurrency(products)}
              </strong>
            </div>

            <div>
              <span>Serviços</span>
              <strong>
                {formatCurrency(services)}
              </strong>
            </div>

            {showFreight && <div>
              <span>Frete</span>
              <strong>
                {formatCurrency(freight)}
              </strong>
            </div>}

            <div>
              <span>Subtotal</span>
              <strong>
                {formatCurrency(subtotal)}
              </strong>
            </div>

          </div>

          <div
            style={{
              display:'grid',
              gridTemplateColumns:'1fr 1fr',
              gap:8,
              marginTop:14,
            }}
          >

            <label className="field">
              <span>Desconto R$</span>

              <ZeroNumberInput
                min="0"
                step="0.01"
                value={discount === 0 ? '' : discount}
                onValueChange={value =>
                  onDiscount(
                    Math.max(
                      0,
                      value||0
                    )
                  )
                }
              />
            </label>

            <label className="field">
              <span>Desconto %</span>

              <ZeroNumberInput
                min="0"
                max="100"
                step="0.01"
                value={
                  Number(
                    discountPercent.toFixed(2)
                  ) === 0
                    ? ''
                    : Number(
                        discountPercent.toFixed(2)
                      )
                }
                onValueChange={value =>
                  changeDiscountPercent(
                    value
                  )
                }
              />
            </label>

          </div>

          <div
            style={{
              marginTop:14,
              paddingTop:14,
              borderTop:'1px solid rgba(148,163,184,.18)',
            }}
          >

            <label className="field">
              <span>Taxa bancária</span>

              <select
                value={
                  includeBankFee
                    ? 'SIM'
                    : 'NAO'
                }
                onChange={e=>{
                  const ativo=
                    e.target.value==='SIM'

                  onIncludeBankFee(ativo)

                  if(!ativo){
                    onBankFeePercent(0)
                  }
                }}
              >
                <option value="NAO">
                  Não incluir
                </option>

                <option value="SIM">
                  Incluir
                </option>
              </select>
            </label>

            {includeBankFee && (
              <label
                className="field"
                style={{marginTop:8}}
              >
                <span>Taxa %</span>

                <ZeroNumberInput
                  min="0"
                  max="99.99"
                  step="0.01"
                  value={bankFeePercent === 0 ? '' : bankFeePercent}
                  placeholder="Ex: 7,2"
                  onValueChange={value =>
                    onBankFeePercent(
                      value
                    )
                  }
                />
              </label>
            )}

          </div>

          <div
            className="summary-lines"
            style={{marginTop:16}}
          >

            <div>
              <span>Valor interno</span>
              <strong>
                {formatCurrency(internalValue)}
              </strong>
            </div>

            {partnerValue>0 && (
              <div>
                <span>Valor da revenda</span>
                <strong>
                  {formatCurrency(partnerValue)}
                </strong>
              </div>
            )}

            {rtValue>0 && (
              <div>
                <span>RT</span>
                <strong>
                  {formatCurrency(rtValue)}
                </strong>
              </div>
            )}

            {includeBankFee && bankFeeValue>0 && (
              <div>
                <span>Taxa banco</span>
                <strong>
                  {formatCurrency(bankFeeValue)}
                </strong>
              </div>
            )}

          </div>

          <div className="summary-total">
            <span>Total cliente</span>

            <strong>
              {formatCurrency(clientTotal)}
            </strong>
          </div>

          <button
            type="button"
            className="primary-button summary-action"
            onClick={onSave}
            disabled={saving}
          >
            <Check size={17}/>

            {saving
              ? 'Salvando...'
              : saveLabel}
          </button>

          <button
            type="button"
            className="back-button"
            onClick={onCancel}
          >
            <ArrowLeft size={15}/>
            Cancelar e voltar
          </button>

        </div>
      )}
    </aside>
  )
}