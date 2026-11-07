const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { registerHooks } = require('node:module')
const { test } = require('node:test')

const file = path.join(__dirname, '../src/components/ClienteImportPanel.tsx')
let compiled
registerHooks({
  resolve(spec, context, next) {
    try { return next(spec, context) } catch (error) {
      if (spec.startsWith('.') && !path.extname(spec)) return next(spec + '.ts', context)
      throw error
    }
  },
  load(url, context, next) {
    if (url === pathToFileURL(file).href) {
      return { format: 'module', source: compiled, shortCircuit: true }
    }
    return next(url, context)
  },
})

const nodes = tree => !tree || typeof tree !== 'object' ? [] :
  Array.isArray(tree) ? tree.flatMap(nodes) : [tree, ...nodes(tree.props?.children)]
const text = tree => tree == null ? '' : Array.isArray(tree) ? tree.map(text).join('') :
  typeof tree === 'object' ? text(tree.props?.children) : String(tree)

test('seletor CSV envia TAB real e invalida a prévia ao mudar o separador', async () => {
  const { transformWithOxc } = await import('vite')
  const state = []
  let slot = 0
  globalThis.clientImportHooks = {
    useState(initial) {
      const index = slot++
      if (!(index in state)) state[index] = initial
      return [state[index], value => { state[index] = value }]
    },
    useRef: initial => ({ current: initial }),
  }
  try {
    const source = fs.readFileSync(file, 'utf8')
      .replace("import { useRef, useState } from 'react'",
        'const {useRef,useState}=globalThis.clientImportHooks')
      .replace(/import \{\r?\n[\s\S]*?\} from '\.\.\/services\/clienteImport'/,
        'const inspectClientImport=()=>{throw new Error("API inesperada")};const previewClientImport=inspectClientImport;const confirmClientImport=inspectClientImport')
      .replace("import { getEmpresaId } from '../services/auth'", 'const getEmpresaId=()=>1')
      .replace("import './clienteImport.css'", '')
    compiled = (await transformWithOxc(source, file, { jsx: { runtime: 'automatic' } })).code
    const { ClienteImportPanel } = await import(pathToFileURL(file))
    let tree = ClienteImportPanel({ onComplete: async () => {}, onClose() {} })
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Importação manual CSV/XLSX').props.onClick()
    slot = 0
    tree = ClienteImportPanel({ onComplete: async () => {}, onClose() {} })
    const label = nodes(tree).find(node => node.type === 'label' && text(node).startsWith('Separador CSV'))
    const select = nodes(label).find(node => node.type === 'select')
    const option = nodes(select).find(node => node.type === 'option' && text(node) === 'Tabulação')
    assert.equal(option.props.value, '\t')
    assert.deepEqual([...option.props.value].map(char => char.charCodeAt(0)), [9])
    select.props.onChange({ target: { value: option.props.value } })
    assert.equal(state[1].separador, '\t')
    assert.deepEqual(state[1].mapeamento, {})
    assert.equal(state[2], null)
    assert.equal(state[3], null)
    assert.equal(state[5], false)
  } finally {
    delete globalThis.clientImportHooks
  }
})
