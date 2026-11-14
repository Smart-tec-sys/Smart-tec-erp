# Smart-tec Fiscal V1 — laboratório XML NF-e 4.00

**Estado:** protótipo sintético, não assinado, não autorizado e **não habilitado para notas de clientes**.

O módulo \`app/services/fiscal_nfe_xml_homologacao.py\` produz bytes XML \`NFe/infNFe\` com identificação, emitente, destinatário, um item, impostos de **exemplo**, total, transporte, pagamento e informações complementares. Ele é determinístico e usa somente dados **fictícios codificados no módulo**. Não recebe ID de empresa, vendedor, pedido, CNPJ ou lista de produtos reais; não lê o banco nem tem acesso a certificados. A chave inserida no atributo \`Id\` é um **identificador de demonstração** calculado com dígito módulo 11, não uma chave de nota emitida ou reservada.

## Referências e limites

- Portal Nacional da NF-e: Pacote de Schemas XML 010g v1.03 (publicado em 26/10/2026) e Nota Técnica 2025.002 v1.53 (30/10/2026) com alterações da RTC (IBS/CBS).
- Estrutura NF-e 4.00: \`NFe/infNFe/ide,emit,dest,det,total,transp,pag,infAdic\`. O schema da raiz \`NFe\` também exige \`ds:Signature\`, **ausente neste protótipo**.
- Utilizados os XSDs do repositório público Java_NFe 4.3.0 apenas como **referência estrutural**, não como prova de conformidade da versão oficial vigente.
- Os exemplos tributários codificados no laboratório NÃO representam tributação correta de persianas, cortinas ou outros produtos reais. Grupos IBS/CBS não estão calculados. Não há cálculo de CST/CSOSN, PIS, COFINS, IPI, IS, descontos, fretes, e nem validação efetiva contra a versão oficial atual dos XSDs.

## Uso seguro para desenvolvimento

\`\`\`python
from app.services.fiscal_nfe_xml_homologacao import gerar_xml_ficticio_nao_assinado
print(gerar_xml_ficticio_nao_assinado().decode("utf-8"))
\`\`\`

A função \`validar_xsd_documento_assinado(xml, caminho_schema)\` recusa explicitamente o protótipo sem assinatura e exige arquivo \`nfe_v4.00.xsd\` local. **O protótipo não passa nem declara ter passado na validação XSD da NF-e**. Não existe endpoint público de download/geração, gravação de XML ou envio SEFAZ.

## Aceite da fase seguinte

1. Obter pacotes XSD e notas técnicas **oficiais** com verificação de origem/versão e testes reproduzíveis sem rede.
2. Implementar composição tributária por UF/operação e validação contábil/legislativa antes de montar campos fiscais.
3. Implementar preenchimento de produtos e destinatários reais com acesso autenticado por tenant, proteção de PII e separação de custos/comissão internos.
4. Criar fluxo de numeração, idempotência, persistência e eventos de NF-e antes de assinatura A1 segura.
5. Assinar e validar XML no ambiente de homologação, testar rejeições e só depois avaliar transmissão SEFAZ, autorização, protocolo, cancelamento e DANFE.

**Não ativar emissão em produção, alterar Render ou mesclar automaticamente este PR.**


## Validação estrutural com XSD de referência (não oficial)

O workflow \`.github/workflows/fiscal-prevalidacao-v1.yml\` baixa em CI uma cópia **pública e versionada** do pacote de schemas do projeto \`Samuel-Oliveira/Java_NFe\`, tag \`4.3.0\`. Antes de executar testes, confirma:
- Commit Git \`272f7b75437f234d9c963aacd8502eeb8a941e4e\`
- Git blob SHA do \`schemas/nfe_v4.00.xsd\`: \`5b2eb0810b9c77bf33b1d46d448364dfc6f64f28\`
- Git blob SHA do \`schemas/leiauteNFe_v4.00.xsd\`: \`4f1ad97fa39840afff140286415f105ca8d3145d\`

Estes hashes confirmam apenas que os arquivos da **referência** são estáveis; **não autenticam o pacote PL_010g v1.03 do Portal Nacional da NF-e**. O download do ZIP oficial diretamente da fonte primária não estava acessível nesta sessão. Não armazenar, distribuir ou identificar a cópia do GitHub como oficial.

Os testes em \`tests/test_fiscal_nfe_xsd_referencia.py\` usam \`lxml.etree.XMLSchema\` offline para exigir:
1. Rejeição de XML sem \`ds:Signature\` no schema de NF-e completo.
2. Ausência de outras incompatibilidades estruturais no XML fictício (além da assinatura).
3. Rejeição de campos desconhecidos propositalmente inseridos.
4. Ausência de assinatura no gerador de laboratório.

Uma rejeição por assinatura **não comprova nem substitui assinatura válida**. Ainda é obrigatório testar integridade, X509, digest, referência do \`infNFe/@Id\`, canonicalização, regras da SEFAZ e o XSD **oficial verificado** com a versão correta. Nenhuma emissão ou integração com banco real foi habilitada.

## Laboratório XMLDSig e PFX fictício (14/11/2026)

- `app/services/fiscal_nfe_assinatura_laboratorio.py` implementa assinatura `ds:Signature` enveloped em `NFe/infNFe`, `Reference URI="#NFe..."`, C14N e algoritmo RSA-SHA1/SHA1 especificado no padrão de NF-e consultado. SHA-1 é legado e seu uso fica restrito ao laboratório, **não constitui recomendação para outras assinaturas**.
- A função de assinatura recebe bytes de PFX e senha exclusivamente em memória e **só aceita certificado RSA autossinado e identificado com CN fixo de laboratório**, com key usage de assinatura, validade e correspondência chave pública/privada. Não importa certificado de empresas e não persiste arquivo nem senha.
- `verificar_xml_assinado_laboratorio` verifica o hash do `infNFe`, assinatura `SignedInfo`, algoritmos, referência interna única e validade do certificado fictício; rejeita alteração de valores/ID, senha incorreta, expiração, certificado diferente, algoritmos inesperados e XML externo.
- Testes geram certificados PFX com chaves efêmeras e senhas fictícias. Nenhum certificado real, credencial SEFAZ, banco ou cliente é utilizado.
- O exemplo **assinado artificialmente** passa no XSD estrutural espelhado e versionado do projeto Java_NFe 4.3.0, verificado por hash; **isso NÃO comprova a conformidade com schemas oficiais PL_010g v1.03**, verificação ICP-Brasil, cálculos tributários, regras SEFAZ ou autorização fiscal.
- Nenhuma API pública, integração de emissão, assinatura de venda real, armazenamento/rotação de certificados ou transmissão foi criada. O estágio para usar A1 real necessita cofre de segredos por CNPJ, política de acesso, auditoria, validade/revogação ICP-Brasil, idempotência, numeração, revalidação de NTs vigentes e homologação SEFAZ.

**Status:** ensaio criptográfico local exclusivamente fictício; emissão permanece bloqueada.
