const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { createRequire, registerHooks } = require('node:module')
const { pathToFileURL } = require('node:url')

const root = path.resolve(__dirname, '..')
const libraryRoot = process.env.SMARTTEC_TEST_VITE_ROOT || root
const dependencyRequire = createRequire(path.join(libraryRoot, 'package.json'))
const compiled = new Map()
registerHooks({
  resolve(spec, context, next) {
    if (spec.endsWith('.css') && context.parentURL) return { url: new URL(spec, context.parentURL).href, shortCircuit: true }
    try { return next(spec, context) } catch (error) {
      if (!spec.startsWith('.') && !spec.startsWith('file:') && !spec.startsWith('node:')) return { url: pathToFileURL(dependencyRequire.resolve(spec)).href, shortCircuit: true }
      throw error
    }
  },
  load(url, context, next) {
    if (url.endsWith('.css')) return { format: 'module', source: '', shortCircuit: true }
    if (compiled.has(url)) return { format: 'module', source: compiled.get(url), shortCircuit: true }
    return next(url, context)
  },
})

;(async () => {
  const { transformWithOxc } = await import(pathToFileURL(path.join(libraryRoot, 'node_modules/vite/dist/node/index.js')))
  let cells = [], index = 0, effects = []
  global.__clientPickerHooks = {
    useState(initial) { const n = index++; if (!(n in cells)) cells[n] = initial; return [cells[n], value => { cells[n] = typeof value === 'function' ? value(cells[n]) : value }] },
    useRef(initial) { const n = index++; return cells[n] ?? (cells[n] = { current: initial }) },
    useMemo: fn => fn(), useId: () => 'client-test',
    useEffect(fn, deps) { const n = index++; if (!cells[n] || deps.some((value, i) => value !== cells[n][i])) { cells[n] = deps; effects.push(fn) } },
  }
  const filename = path.join(root, 'src/components/BudgetClientPicker.tsx')
  const source = fs.readFileSync(filename, 'utf8').replace("import { useEffect, useId, useMemo, useRef, useState } from 'react'", 'const {useEffect,useId,useMemo,useRef,useState}=globalThis.__clientPickerHooks')
  const url = pathToFileURL(filename).href
  compiled.set(url, (await transformWithOxc(source, filename, { jsx: { runtime: 'automatic' } })).code)
  const { BudgetClientPicker } = await import(url)
  const clients = [
    { id: 12, nome: 'José Ávila', documento: '123.456.789-01' },
    { id: 34, nome: 'Decor São Paulo', documento: '12.345.678/0001-90' },
    { id: 56, nome: 'Cliente sem documento', documento: null },
  ]
  const before = JSON.stringify(clients)
  const changed = []
  let created = 0, props, tree
  const nodes = element => element == null || typeof element !== 'object' ? [] : Array.isArray(element) ? element.flatMap(nodes) : [element, ...nodes(element.props?.children)]
  const text = element => element == null ? '' : typeof element === 'string' || typeof element === 'number' ? String(element) : Array.isArray(element) ? element.map(text).join('') : text(element.props?.children)
  function render() { index = 0; tree = BudgetClientPicker(props); return tree }
  function settle() { render(); for (let n = 0; effects.length && n < 4; n++) { effects.splice(0).forEach(fn => fn()); render() } return tree }
  function mount(value = 0, records = clients) {
    cells = []; effects = []
    props = { clients: records, value, onChange(id) { changed.push(id); props = { ...props, value: id } }, onCreate() { created++ } }
    settle()
  }
  const input = () => nodes(tree).find(node => node.props?.role === 'combobox')
  const options = () => nodes(tree).filter(node => node.props?.role === 'option')
  function search(value) { input().props.onChange({ target: { value } }); settle() }
  function key(key) { const event = { key, prevented: false, preventDefault() { this.prevented = true }, stopPropagation() {} }; input().props.onKeyDown(event); settle(); return event }

  mount(34, [])
  assert.equal(input().props.value, 'Cliente #34', 'ID salvo não é perdido enquanto cadastros carregam')
  props = { ...props, clients }; settle()
  assert.equal(input().props.value, 'Decor São Paulo', 'reabre cliente pelo ID real após carga')
  input().props.onFocus(); settle()
  search('jose avila')
  assert.equal(props.value, 0, 'editar nome selecionado invalida o ID anterior antes de salvar')
  assert.equal(input().props.value, 'jose avila', 'a busca digitada não é apagada ao limpar o vínculo antigo')
  assert.equal(options().filter(option => text(option).includes('José Ávila')).length, 1)
  assert.ok(!options().some(option => text(option).includes('Decor São Paulo')))
  key('Enter')
  assert.equal(props.value, 12)
  assert.equal(input().props.value, 'José Ávila')
  assert.equal(input().props['aria-expanded'], false)
  assert.equal(changed.at(-1), 12)

  nodes(tree).find(node => node.props?.['aria-label'] === 'Limpar cliente').props.onClick(); settle()
  assert.equal(props.value, 0); assert.equal(input().props.value, '')
  search('12345678000190')
  assert.ok(options().some(option => text(option).includes('Decor São Paulo')), 'CNPJ sem máscara localiza cadastro mascarado')
  key('Enter'); assert.equal(props.value, 34)
  search('123.456.789-01'); key('Enter'); assert.equal(props.value, 12, 'CPF com máscara seleciona ID correto')
  search('12345678901'); key('Enter'); assert.equal(props.value, 12, 'CPF sem máscara seleciona ID correto')

  search('não existe')
  assert.ok(nodes(tree).some(node => node.props?.role === 'status' && text(node).includes('Nenhum cliente')))
  assert.equal(props.value, 0)
  key('Enter'); assert.equal(created, 1, 'preserva ação explícita do cadastro existente')
  assert.equal(props.value, 0, 'cadastro não inventa ID')
  input().props.onFocus(); settle(); key('Escape')
  assert.equal(input().props['aria-expanded'], false)
  const wrapper = tree
  input().props.onFocus(); settle()
  wrapper.props.onBlur({ currentTarget: { contains: () => false }, relatedTarget: null }); settle()
  assert.equal(input().props['aria-expanded'], false, 'sair do controle fecha sugestões')

  mount()
  const down = key('ArrowDown')
  assert.equal(down.prevented, true)
  assert.equal(input().props['aria-activedescendant'], 'client-test-0')
  key('ArrowDown'); key('Enter')
  assert.equal(props.value, 34, 'seleção por teclado conserva ID real')
  props = { ...props, value: 56 }; settle()
  assert.equal(input().props.value, 'Cliente sem documento', 'mudança externa de cliente restaura nome correto')
  props = { ...props, value: 0 }; settle()
  assert.equal(input().props.value, '')
  props = { ...props, disabled: true }; settle()
  assert.equal(input().props.disabled, true)
  assert.equal(input().props['aria-expanded'], false)
  assert.equal(JSON.stringify(clients), before, 'cadastros não são alterados')
  delete global.__clientPickerHooks
  console.log('Cliente pesquisável: restauração por ID, nome sem acento, CPF/CNPJ com/sem máscara, seleção, troca, limpeza, teclado e cadastro existente preservados; sem rede/banco.')
})().catch(error => { console.error(error); process.exitCode = 1 })
