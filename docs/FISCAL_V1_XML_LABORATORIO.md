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
