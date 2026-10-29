"""Validação de papéis comerciais sem alterar preços ou vínculos de representante."""
CLIENTE_FINAL_CAMPOS = (
    "cliente_final_nome", "cliente_final_documento", "cliente_final_telefone",
    "cliente_final_email", "cliente_final_endereco",
)


def validar_origem_comercial(cliente_id, parceiro_id, cliente_final):
    if cliente_id is not None and parceiro_id is not None:
        raise ValueError("Cliente direto e parceiro não podem ser informados ao mesmo tempo.")
    if cliente_id is None and parceiro_id is None:
        raise ValueError("Venda direta exige cliente.")
    if parceiro_id is None and any(value is not None and str(value).strip() for value in cliente_final.values()):
        raise ValueError("Cliente final da revenda só pode ser informado em venda por parceiro.")
