const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { stripTypeScriptTypes } = require('node:module')
class Input {
  constructor(type, value, label = '', stepper = false) { Object.assign(this, { type, value, label, stepper, selected: false }) }
  closest(selector) {
    if (selector === '.stepper') return this.stepper ? {} : null
    return { querySelector: () => ({ textContent: this.label }) }
  }
  select() { this.selected = true }
}
const source = fs.readFileSync(path.join(__dirname, '../src/utils/selectZeroOnFocus.ts'), 'utf8')
const compiled = stripTypeScriptTypes(source).replace('export function selectZeroOnFocus', 'function selectZeroOnFocus') + '\nexports.selectZeroOnFocus = selectZeroOnFocus'
const context = { exports: {}, HTMLInputElement: Input }
vm.runInNewContext(compiled, context)
const cases = [
  [new Input('number', '0'), true],
  [new Input('text', '0,00', 'Largura'), true],
  [new Input('text', '0.00', 'Altura'), true],
  [new Input('text', '0', 'Quant.', true), true],
  [new Input('number', '123.45'), false],
  [new Input('text', '1', 'Quant.', true), false],
  [new Input('text', '000', 'Documento'), false],
  [new Input('number', ''), false],
  [Object.assign(new Input('number', '0'), {readOnly:true}), false],
  [Object.assign(new Input('number', '0'), {disabled:true}), false],
  [Object.assign(new Input('text', '0,00'), {inputMode:'decimal'}), true],
]
for (const [input, expected] of cases) {
  const original = input.value
  context.exports.selectZeroOnFocus({ target: input })
  assert.equal(input.selected, expected)
  assert.equal(input.value, original)
}
console.log('11 testes de foco numérico aprovados; valores preservados.')
