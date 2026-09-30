# FASE 8E.1A — DIAGNÓSTICO SOMENTE LEITURA: ROLÔ E DOUBLE VISION

---

## 1. TABELA ROLÔ

| Componente / Regra | Backend (motor_calculo_produtos.py) | Orçamentos (modulos/orcamentos.py) | Produtos/Receita (modulos/produtos.py) | Catálogo Técnico (app/technical/catalog.py) | React Frontend (types/budget.ts) |
|---|---|---|---|---|---|
| **Cálculo de área (tecido)** | `(largura - 0.03) × (altura + 0.15) × 1.05` (perda 5%) | Não calcula — delega ao motor | Não calcula — usa motor | `TECIDO_ROLO` (M²) | `usesArea()` retorna true; subtotal = área × qtd × preço |
| **Tubo (linear)** | `largura - 0.025` | `largura - 0.025` | `largura - 0.025` | `TUBO_ROLO_32MM` / `TUBO_ROLO_38MM` (M) | Não calcula — recebe do backend |
| **Fita tubo** | `largura - 0.025` | `largura - 0.025` | `largura - 0.025` | `FITA_TUBO_ROLO` (M) | — |
| **Base / Perfil** | `largura - 0.025` | `largura - 0.025` | `largura - 0.025` | `BASE_ROLO` (M) | — |
| **Fita base** | `largura - 0.03` | `largura - 0.025` | `largura - 0.03` | `FITA_BASE_ROLO` (M) | — |
| **Espaguete base** | `largura - 0.03` | `largura - 0.025` | `largura - 0.03` | `ESPAGUETE_BASE_ROLO` (M) | — |
| **Corrente** | `min(altura × 2, 3.0)` | `altura × 0.90 × 2` (Double Vision) / Rolô usa motor | `altura × 0.90 × 2` (Double Vision) | `CORRENTE_ROLO` (M) | — |
| **Emenda corrente** | `3 × qtd` | `3 × qtd` (Double Vision) | `3 × qtd` (Double Vision) | `EMENDA_CORRENTE_ROLO` (UN) | — |
| **Tampa base** | `2 × qtd` | `2 × qtd` (Double Vision) | `2 × qtd` (Double Vision) | `TAMPA_BASE_ROLO` (UN) | — |
| **Comando** | `1 × qtd` (kit compatível com tubo) | `Kit Comando Ação Premium 32/38mm` | `comando_32` / `comando_38` | `COMANDO_ROLO_32MM` / `COMANDO_ROLO_38MM` (KIT) | — |
| **Suporte** | Não entra (vem no kit/comando) | Não entra | Não entra (vem no kit) | — | — |
| **Ponteira** | Não mapeado | Não mapeado | Não mapeado | — | — |
| **Bandô** | Não aplicável | Não aplicável | Não aplicável | — | — |
| **Guias** | Não aplicável | Não aplicável | Não aplicável | — | — |
| **Mínimo faturável** | Não implementado | Não implementado | Não implementado | — | Não implementado |
| **Consumo tecido** | Área + 5% perda + sobra 15cm altura | — | — | — | — |

### Seleção de Tubo 32mm vs 38mm — CONFLITO CRÍTICO

| Origem | Arquivo / Linha | Regra |
|---|---|---|
| **Backend Motor (padrão)** | `motor_calculo_produtos.py:98` | Prioriza `tubo_32` se ambos fornecidos no catálogo (teste `test_motor_prioriza_tubo_32_quando_32_e_38_sao_fornecidos`) |
| **Orçamentos (escolher_tubo_rolo)** | `modulos/orcamentos.py:1654-1668` | **≤ 2,20m → 32mm**; **> 2,20m → 38mm** |
| **Produtos (chaves_rolo_manual_por_largura)** | `modulos/produtos.py:4083-4094` | **≤ 1,80m → 32mm**; **> 1,80m → 38mm** |
| **Teste caracterização** | `tests/test_rolo_caracterizacao_fase0.py:27` | Usa largura 2m → espera tubo_32 (compatível com 1,80 e 2,20) |
| **Prévia receita (produtos.py:3793)** | `modulos/produtos.py:3793` | `tubo: "38mm" if largura > 1.80 else "32mm"` |

### Componentes da Receita Base Rolô Manual (receita_rolo_manual_base_smarttec)

| Chave Técnica | Item Preferido | Obrigatório | Bloqueado |
|---|---|---|---|
| `tubo_32` | TUBO P/ ROLÔ 32MM NATURAL | TUBO, 32MM | 38MM, 41MM, ROMANA, PAINEL, HORIZONTAL, TRILHO |
| `tubo_38` | TUBO P/ ROLÔ 38MM NATURAL | TUBO, 38MM | 32MM, 41MM, ROMANA, PAINEL, HORIZONTAL, TRILHO |
| `fita_tubo` | FTF FITA DUPLA FACE 20MMX100MTS INCOLOR | FITA, DUPLA, FACE | FPH, PH, HORIZONTAL, BASE ROLO, COSTURA, ROMANA, GIRATORIO |
| `base` | BASE CONICA BRANCO AC133 / BASE CHATA 02 | BASE | CABECEIRA, ROMANA, GIRATORIO, HORIZONTAL, TAMPA, FITA, ESPAGUETE, TRILHO |
| `fita_base` | FITA DE PLASTICO ADESIVA IMPORTADA 15MM | FITA | GIRATORIO, HASTE, ROMANA, HORIZONTAL, DUPLA FACE, FTF, FPH |
| `espaguete_base` | ESP ESPAGUETE MACARRAO 3,00MM | ESPAGUETE | 2,50MM, 2,5MM, 3,50MM, 3,5MM, ROMANA, HORIZONTAL |
| `corrente` | CORRENTE BOLA 10 JUNTA BRANCO | CORRENTE, BOLA | TRACAO, TETO, TRILHO, MOLA, ONE TOUCH, COMANDO, ROMANA, HORIZONTAL |
| `emenda_corrente` | EMENDA DA CORRENTE CONECTOR BRANCO | EMENDA, CORRENTE | METAL, CSF, TRILHO, TETO, ROMANA, HORIZONTAL |
| `tampa_base` | TAMPA DA BASE CHATA 02 BRANCO | TAMPA, BASE | COM ABA, ABA, 5618 COM ABA, TRILHO, TUBO, ROMANA, HORIZONTAL |
| `comando_32` | COMANDO 32MM ACAO MAXI BRANCO | COMANDO, 32MM | PREMIUM, JP, 38MM, MOTOR, ROMANA, HORIZONTAL |
| `comando_38` | COMANDO 38MM ACAO MAXI BRANCO | COMANDO, 38MM | PREMIUM, JP, 32MM, MOTOR, ROMANA, HORIZONTAL |

### Classificação A/B/C/D — ROLÔ

| Item | Classificação | Justificativa |
|---|---|---|
| Cálculo tecido (motor) | **A** | Regra técnica consolidada no motor centralizado |
| Cálculo tubo/base (motor) | **A** | Regra técnica consolidada |
| Seleção tubo 32/38 (motor) | **C** | Motor prioriza 32mm se ambos no catálogo; não usa largura |
| Seleção tubo 32/38 (orçamentos) | **B** | Regra legada 2,20m centralizada em `escolher_tubo_rolo` |
| Seleção tubo 32/38 (produtos/receita) | **B** | Regra legada 1,80m em `chaves_rolo_manual_por_largura` |
| Corrente (motor: 2×altura máx 3m) | **A** | Regra técnica do motor |
| Corrente (orçamentos DV: 90%×2) | **B** | Regra legada Double Vision |
| Receita base (produtos.py) | **A** | Receita determinística validada (Warma) |
| Catálogo técnico | **A** | Formalizado, versionado, imutável |
| React frontend (cálculo) | **D** | Não calcula — só exibe; backend recalcula |
| Mínimo faturável | **D** | Não existe em nenhum layer |

---

## 2. TABELA DOUBLE VISION

| Componente / Regra | Orçamentos (montar_receita_double_vision) | Catálogo Técnico (app/technical/catalog.py) | Motor Genérico (motor_calculo_produtos.py) | React Frontend |
|---|---|---|---|---|
| **Cálculo tecido** | `(largura - 0.025) × (altura × 2 + 0.15)` | `TECIDO_DOUBLE_VISION` (M²) | `_calcular_generico` → área × 1.05 | `usesArea()` true |
| **Tubo manual** | `escolher_tubo_rolo(largura)` → 32/38mm (2,20m) | `TUBO_DOUBLE_VISION_32MM`, `_38MM`, `_41MM` (M) | Não tem regra específica | — |
| **Tubo motorizada** | 41mm padrão; 38mm se bateria | `TUBO_DOUBLE_VISION_41MM` (M) | Não tem regra específica | — |
| **Comando manual** | `Kit Comando Ação Premium {tubo}` | `COMANDO_DOUBLE_VISION` (KIT) | — | — |
| **Motor motorizada** | `Motor Double Vision` (1 UN) | `MOTOR_DOUBLE_VISION` (UN) | — | — |
| **Suporte motor** | `Suporte/Adaptador Motor Double Vision` (1 KIT) | `SUPORTE_ADAPTADOR_MOTOR_DOUBLE_VISION` (KIT) | — | — |
| **Controle** | 1 UN | `CONTROLE_MOTOR` (UN) | — | — |
| **Eixo base** | `largura - 0.028` | `EIXO_BASE_DOUBLE_VISION` (M) | — | — |
| **Base cunha** | `largura - 0.020` | `BASE_CUNHA_DOUBLE_VISION` (M) | — | — |
| **Tampa eixo** | 2 UN (par fixo) | `TAMPA_EIXO_DOUBLE_VISION` (UN) | — | — |
| **Tampa base** | 2 UN (par fixo) | `TAMPA_BASE_DOUBLE_VISION` (UN) | — | — |
| **Grapas** | ≤1m: 2; >1m: +1 a cada 50cm | `GRAPA_DOUBLE_VISION_40MM` (UN) | — | — |
| **Barra estabilizadora** | `largura` (sem bandô) | `BARRA_ESTABILIZADORA_DOUBLE_VISION` (M) | — | — |
| **Bandô** | `largura` (com bandô) | `BANDO_DOUBLE_VISION` (M) | — | — |
| **Tampa bandô** | 2 UN | `TAMPA_BANDO_DOUBLE_VISION` (UN) | — | — |
| **Espaguete** | `largura - 0.025` | `ESPAGUETE_DOUBLE_VISION_2_5MM` (M) | — | — |
| **Fita plástica** | `largura - 0.025` | `FITA_PLASTICA_DOUBLE_VISION_1_5MM` (M) | — | — |
| **Corrente** | `altura × 0.90 × 2` | `CORRENTE_BOLA10_DOUBLE_VISION` (M) | — | — |
| **Emenda corrente** | 3 UN | `EMENDA_CORRENTE_DOUBLE_VISION` (UN) | — | — |
| **Pêndulo** | 1 UN (manual) | Não catalogado | — | — |
| **Mínimo faturável** | Não implementado | — | — | — |
| **Consumo tecido duplo** | Altura × 2 + 15cm | Conceito no catálogo | — | — |

### Receita Própria vs Motor Genérico — DOUBLE VISION

| Aspecto | Receita Própria (`montar_receita_double_vision`) | Motor Genérico (`_calcular_generico`) |
|---|---|---|
| **Tecido** | Largura -2,5cm × Altura dupla +15cm | Área largura × altura × 1.05 |
| **Tubo** | Regra específica manual/motorizada | Metro linear pela maior medida |
| **Bandô/B.Estabilizadora** | Lógica condicional (com/sem bandô) | Não contempla |
| **Componentes base** | Eixo + cunha + tampas (2 cada) | Não contempla |
| **Grapas** | Regra por largura (≤1m: 2, +1/50cm) | Não contempla |
| **Corrente** | 90% altura × 2 | Não contempla |
| **Motor/Suporte/Controle** | Só motorizada | Não contempla |
| **Status catálogo** | `PROVISORIA` (contrato produtivo pendente) | — |

### Classificação A/B/C/D — DOUBLE VISION

| Item | Classificação | Justificativa |
|---|---|---|
| Receita própria (orçamentos.py) | **B** | Regra legada SmartTec completa, usada em produção |
| Catálogo técnico | **C** | Formalizado como `PROVISORIA`; contrato produtivo pendente |
| Motor genérico (fallback) | **D** | Não suporta Double Vision corretamente |
| Seleção tubo manual | **C** | Usa `escolher_tubo_rolo` (2,20m) — diverge de Rolô produtos (1,80m) |
| Seleção tubo motorizada | **B** | Regra clara: 41mm padrão, 38mm bateria |
| Bandô opcional | **B** | Regra legada implementada |
| Grapas por largura | **B** | Regra legada implementada |
| React frontend | **D** | Não calcula — delega 100% ao backend |

---

## 3. TABELA DE CONFLITOS COM ARQUIVO/LINHA

| # | Conflito | Arquivo / Linha (Origem A) | Arquivo / Linha (Origem B) | Detalhe |
|---|---|---|---|---|
| 1 | **Limite tubo 32/38: 1,80m vs 2,20m** | `modulos/produtos.py:4091` (`largura > 1.80`) | `modulos/orcamentos.py:1668` (`largura <= 2.20`) | Diferença de 40cm na transição; produtos usa 1,80m, orçamentos usa 2,20m |
| 2 | **Motor prioriza tubo_32 ignorando largura** | `motor_calculo_produtos.py:98` (`_pegar(catalogo, "tubo_32", "tubo_38", "tubo")`) | `tests/test_rolo_caracterizacao_fase0.py:51-56` | Teste confirma: se ambos no catálogo, motor escolhe 32mm mesmo acima de 2,20m |
| 3 | **Desconto largura tecido vs tubo/base** | `motor_calculo_produtos.py:87` (`desconto_tecido = 0.03`) | `motor_calculo_produtos.py:86` (`desconto_tubo_base = 0.025`) | Tecido -3cm; tubo/base -2,5cm; fita_base/espaguete usam -3cm |
| 4 | **Corrente: motor vs Double Vision** | `motor_calculo_produtos.py:96` (`min(altura × 2, 3.0)`) | `modulos/orcamentos.py:1953` (`altura × 0.90 × 2`) | Motor Rolô: 2×altura máx 3m; DV orçamentos: 180% altura |
| 5 | **Fita base / espaguete: desconto divergente** | `motor_calculo_produtos.py:105-106` (usam `desconto_tecido` = 0.03) | `modulos/orcamentos.py:1966-1967` (usam `largura_tecido` = largura - 0.025) | Motor: -3cm; DV orçamentos: -2,5cm |
| 6 | **React calcula subtotal próprio** | `frontend-erp/src/types/budget.ts:96` (`productLineSubtotal`) | `modulos/orcamentos.py:2251` (`base_calculo_subtotal = area_m2`) | React usa `parseDecimal(width)×parseDecimal(height)×qtd×price`; backend usa área já calculada |
| 7 | **React não tem regra de tubo** | `frontend-erp/src/types/budget.ts` — ausente | `modulos/orcamentos.py:1654` / `modulos/produtos.py:4091` | React não seleciona tubo; backend decide |
| 8 | **Catálogo técnico Double Vision = PROVISORIA** | `app/technical/catalog.py:87` (`status=TechnicalFunctionStatus.PROVISORIA`) | `modulos/orcamentos.py:1909` (receita completa em produção) | Catálogo marca como provisório; orçamentos usa receita completa |
| 9 | **Perfil comercial: React vs Backend** | `frontend-erp/src/types/budget.ts:92` (`commercialPercent`) | `modulos/orcamentos.py:1745-1747` (`padroes` com mesmas %) | Valores idênticos (Dec 50%, Var 100%, Cons 150%), mas React calcula local, backend recalcula |
| 10 | **Sem custo cadastrado: React vs Backend** | `frontend-erp/src/types/budget.ts:91` (`productCost` cai para `valor_venda` ou 0) | `modulos/orcamentos.py:1809-1829` (`calcular_valor_produto_por_tipo_venda`) | React: `custo_final || valor_custo || valor_venda || 0` → preço 0 se nada; Backend: prioriza custo+lucro, fallback valor_venda |

---

## 4. LACUNAS IDENTIFICADAS

| Lacuna | Descrição | Onde Afeta |
|---|---|---|
| **Mínimo faturável** | Não existe regra de área mínima faturável em nenhum layer (backend, orçamentos, produtos, React) | Orçamentos, Produção, Precificação |
| **Consumo tecido duplo (DV)** | Catálogo tem `TECIDO_DOUBLE_VISION` mas não define regra de consumo (altura × 2 + sobra) | Catálogo técnico, Motor |
| **Ponteira / Tampa lateral Rolô** | Não mapeado no catálogo técnico nem no motor | Rolô completo |
| **Guias laterais** | Não existe para Rolô; existe para Romana (`GUIA_CORDA_ROMANA`) e Persiana Externa (`GUIA`) | Rolô, Double Vision |
| **Suporte Rolô separado** | Documentado que "vem no kit/comando" mas não há validação técnica | Receita Rolô, Catálogo |
| **Bandô Double Vision opcional** | Regra existe em orçamentos mas não no catálogo técnico nem motor | Double Vision |
| **Motor Double Vision no catálogo** | Existe `MOTOR_DOUBLE_VISION` e `SUPORTE_ADAPTADOR` mas motor genérico não os usa | Motor, Catálogo |
| **Perfil comercial persistido** | React envia `perfil_comercial` no payload; backend recalcula; não há validação de consistência | Orçamento API, React |
| **Produto sem custo** | React mostra preço 0; backend usa valor_venda se houver; comportamento divergente | Precificação, Orçamento |
| **Validação largura/altura mínimas** | Não há regra de largura/altura mínima técnica para Rolô/DV | Motor, Orçamentos |
| **Desperdício/perda por modelo** | Motor usa 5% fixo; não diferencia Rolô vs DV vs Romana | Motor centralizado |

---

## 5. CLASSIFICAÇÃO A/B/C/D — RESUMO CONSOLIDADO

| Categoria | Item | Classificação |
|---|---|---|
| **Rolô — Motor Cálculo** | Tecido, Tubo, Base, Fitas, Espaguete, Corrente, Emenda, Tampa, Comando | **A** |
| **Rolô — Motor Cálculo** | Seleção tubo 32/38 (ignora largura, prioriza catálogo) | **C** |
| **Rolô — Orçamentos** | `escolher_tubo_rolo` (2,20m), `kit_por_tubo_rolo`, área comercial | **B** |
| **Rolô — Produtos/Receita** | Receita base determinística, `chaves_rolo_manual_por_largura` (1,80m) | **A** (receita) / **B** (limite 1,80m) |
| **Rolô — Catálogo Técnico** | Funções formalizadas, imutáveis, versionadas | **A** |
| **Rolô — React** | Cálculo local de subtotal, perfil comercial, sem regra técnica | **D** |
| **Double Vision — Receita Própria** | Completa em `montar_receita_double_vision` (orçamentos.py) | **B** |
| **Double Vision — Catálogo Técnico** | Formalizado mas `PROVISORIA` | **C** |
| **Double Vision — Motor Genérico** | Não suporta (fallback genérico) | **D** |
| **Double Vision — Seleção Tubo** | Manual: 2,20m (orçamentos) vs 1,80m (produtos); Motorizada: 41mm/38mm | **C** (manual) / **B** (motorizada) |
| **Double Vision — React** | Não calcula nada técnico | **D** |
| **Perfil Comercial** | Decorador 50%, Varejo 100%, Consumidor Final 150% | **A** (valores idênticos React/Backend) |
| **Sem Custo Cadastrado** | React: preço 0; Backend: fallback valor_venda | **C** (divergência) |
| **Mínimo Faturável** | Não existe | **D** (ausente) |

---

## OBSERVAÇÕES FINAIS

1. **Dois limites de tubo convivem**: 1,80m (produtos/receita) e 2,20m (orçamentos). O motor de cálculo **não usa largura** para escolher tubo — prioriza `tubo_32` se presente no catálogo.

2. **Double Vision tem receita própria completa** em `modulos/orcamentos.py:1909` mas o catálogo técnico marca tudo como `PROVISORIA` e o motor genérico não a suporta.

3. **React é puramente apresentacional** para cálculos técnicos: não seleciona tubo, não calcula receita, só calcula subtotal estimado localmente. O backend recalcula tudo ao salvar.

4. **Perfil comercial** está alinhado nos valores (50/100/150) mas React calcula preço estimado localmente; backend recalcula com regra de prioridade: custo+lucro > valor_venda > 0.

5. **Nenhum layer implementa mínimo faturável**, consumo tecido duplo formalizado, ponteira, guias laterais, ou validação de largura/altura mínimas técnicas.

---
*Diagnóstico gerado em 2026-09-09 — FASE 8E.1A — SOMENTE LEITURA*