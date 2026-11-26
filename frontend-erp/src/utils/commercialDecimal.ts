import Decimal from 'decimal.js'

const D = Decimal.clone({
  precision: 28,
  rounding: Decimal.ROUND_HALF_UP
})

const money = (value: Decimal) =>
  value.toDecimalPlaces(2, D.ROUND_HALF_UP)

export function decimalSum(values: number[]): number {
  return money(values.reduce(
    (sum, value) => sum.plus(value), new D(0)
  )).toNumber()
}

export function commercialPercentage(
  base: number, percent: number
): number {
  return money(
    new D(base).times(percent).div(100)
  ).toNumber()
}

export function commercialNet(
  total: number, discount: number
): number {
  return money(
    D.max(0, new D(total).minus(discount))
  ).toNumber()
}

export function commercialBankTotal(
  base: number, rate: number
): number {
  if (rate <= 0 || rate >= 100) return base

  return money(
    new D(base).div(
      new D(1).minus(new D(rate).div(100))
    )
  ).toNumber()
}

export function commercialDifference(
  total: number, base: number
): number {
  return money(
    new D(total).minus(base)
  ).toNumber()
}


export function moneyToCents(value: number | string): number {
  const result = new D(value)
    .times(100)
    .toDecimalPlaces(0, D.ROUND_HALF_UP)
    .toNumber()

  if (!Number.isSafeInteger(result)) {
    throw new Error('Valor monetario fora da faixa segura.')
  }

  return result
}
