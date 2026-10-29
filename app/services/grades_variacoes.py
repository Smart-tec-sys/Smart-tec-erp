from sqlalchemy import text


def empresa_id(tenant):
    value = getattr(tenant, "empresa_id", None)
    if value is None or int(value) <= 0:
        raise PermissionError("Empresa atual não identificada.")
    return int(value)


def obter_grade(db, tenant, grade_id):
    row = db.execute(text("SELECT * FROM grades_variacoes WHERE id=:id AND empresa_id=:empresa"),
                     {"id": grade_id, "empresa": empresa_id(tenant)}).mappings().first()
    if row is None:
        raise LookupError("Grade não encontrada.")
    return dict(row)


def listar_grades(db, tenant):
    return [dict(r) for r in db.execute(text(
        "SELECT g.*, (SELECT count(*) FROM grades_variacoes_valores v WHERE v.grade_id=g.id) AS quantidade_valores "
        "FROM grades_variacoes g WHERE empresa_id=:empresa ORDER BY ordem,nome,id"),
        {"empresa": empresa_id(tenant)}).mappings()]


def _duplicado(db, table, scope, scope_id, field, value, exclude=0):
    row = db.execute(text(f"SELECT id FROM {table} WHERE {scope}=:scope "
        f"AND lower(trim({field}))=lower(trim(:value)) AND id<>:exclude"),
        {"scope": scope_id, "value": value, "exclude": exclude}).first()
    if row:
        raise ValueError("Já existe uma grade com esse nome." if field == "nome"
                         else "Já existe esse valor na grade.")


def criar_grade(db, tenant, data):
    values = data.model_dump()
    values["empresa"] = empresa_id(tenant)
    _duplicado(db, "grades_variacoes", "empresa_id", values["empresa"], "nome", values["nome"])
    row = db.execute(text("INSERT INTO grades_variacoes (empresa_id,nome,descricao,ativo,ordem) "
        "VALUES (:empresa,:nome,:descricao,:ativo,:ordem) RETURNING *"), values).mappings().one()
    result = dict(row)
    db.commit()
    return result


def atualizar_grade(db, tenant, grade_id, data):
    current = obter_grade(db, tenant, grade_id)
    values = data.model_dump(exclude_unset=True)
    if "nome" in values:
        _duplicado(db, "grades_variacoes", "empresa_id", current["empresa_id"], "nome", values["nome"], grade_id)
    if not values:
        return current
    assignments = ", ".join(f"{k}=:{k}" for k in values)
    values.update(id=grade_id, empresa=current["empresa_id"])
    row = db.execute(text(f"UPDATE grades_variacoes SET {assignments} WHERE id=:id AND empresa_id=:empresa RETURNING *"), values).mappings().one()
    result = dict(row)
    db.commit()
    return result


def excluir_grade(db, tenant, grade_id):
    current = obter_grade(db, tenant, grade_id)
    if db.execute(text("SELECT id FROM grades_variacoes_valores WHERE grade_id=:id LIMIT 1"), {"id":grade_id}).first():
        raise ValueError("A grade possui valores. Desative-a ou remova os valores antes de excluir.")
    db.execute(text("DELETE FROM grades_variacoes WHERE id=:id AND empresa_id=:empresa"),
               {"id":grade_id, "empresa":current["empresa_id"]})
    db.commit()


def listar_valores(db, tenant, grade_id):
    obter_grade(db, tenant, grade_id)
    return [dict(r) for r in db.execute(text(
        "SELECT * FROM grades_variacoes_valores WHERE grade_id=:grade ORDER BY ordem,valor,id"),
        {"grade":grade_id}).mappings()]


def obter_valor(db, tenant, grade_id, valor_id):
    obter_grade(db, tenant, grade_id)
    row = db.execute(text("SELECT * FROM grades_variacoes_valores WHERE id=:id AND grade_id=:grade"),
        {"id":valor_id,"grade":grade_id}).mappings().first()
    if row is None:
        raise LookupError("Valor não encontrado nesta grade.")
    return dict(row)


def criar_valor(db, tenant, grade_id, data):
    obter_grade(db, tenant, grade_id)
    values = data.model_dump()
    values["grade"] = grade_id
    _duplicado(db,"grades_variacoes_valores","grade_id",grade_id,"valor",values["valor"])
    row = db.execute(text("INSERT INTO grades_variacoes_valores (grade_id,valor,ativo,ordem) "
        "VALUES (:grade,:valor,:ativo,:ordem) RETURNING *"),values).mappings().one()
    result = dict(row)
    db.commit()
    return result


def atualizar_valor(db, tenant, grade_id, valor_id, data):
    current = obter_valor(db, tenant, grade_id, valor_id)
    values = data.model_dump(exclude_unset=True)
    if "valor" in values:
        _duplicado(db,"grades_variacoes_valores","grade_id",grade_id,"valor",values["valor"],valor_id)
    if not values:
        return current
    assignments = ", ".join(f"{k}=:{k}" for k in values)
    values.update(id=valor_id, grade=grade_id)
    row = db.execute(text(f"UPDATE grades_variacoes_valores SET {assignments} WHERE id=:id AND grade_id=:grade RETURNING *"),values).mappings().one()
    result = dict(row)
    db.commit()
    return result


def excluir_valor(db, tenant, grade_id, valor_id):
    obter_valor(db, tenant, grade_id, valor_id)
    db.execute(text("DELETE FROM grades_variacoes_valores WHERE id=:id AND grade_id=:grade"),
               {"id":valor_id,"grade":grade_id})
    db.commit()
