import sqlite3

import pytest


def _connection():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE empresas (id INTEGER PRIMARY KEY);
        INSERT INTO empresas VALUES (1), (2);

        CREATE TABLE funcionarios (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            UNIQUE (empresa_id, id)
        );
        CREATE TABLE parceiros_comerciais (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            vendedor_responsavel_id INTEGER,
            FOREIGN KEY (empresa_id, vendedor_responsavel_id)
                REFERENCES funcionarios(empresa_id, id)
        );

        CREATE TABLE orcamentos (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            UNIQUE (id, empresa_id)
        );
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            UNIQUE (id, empresa_id)
        );
        CREATE TABLE servicos (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            UNIQUE (id, empresa_id)
        );
        CREATE TABLE orcamentos_itens (
            id INTEGER PRIMARY KEY,
            orcamento_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            servico_id INTEGER,
            descricao TEXT NOT NULL,
            preco_unitario NUMERIC NOT NULL,
            quantidade NUMERIC NOT NULL,
            FOREIGN KEY (orcamento_id, empresa_id)
                REFERENCES orcamentos(id, empresa_id) ON DELETE CASCADE,
            FOREIGN KEY (servico_id, empresa_id)
                REFERENCES servicos(id, empresa_id),
            FOREIGN KEY (servico_id)
                REFERENCES servicos(id) ON DELETE SET NULL
        );
        CREATE TABLE pedidos_itens (
            id INTEGER PRIMARY KEY,
            pedido_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            servico_id INTEGER,
            descricao TEXT NOT NULL,
            preco_unitario NUMERIC NOT NULL,
            quantidade NUMERIC NOT NULL,
            FOREIGN KEY (pedido_id, empresa_id)
                REFERENCES pedidos(id, empresa_id) ON DELETE CASCADE,
            FOREIGN KEY (servico_id, empresa_id)
                REFERENCES servicos(id, empresa_id),
            FOREIGN KEY (servico_id)
                REFERENCES servicos(id) ON DELETE SET NULL
        );

        INSERT INTO funcionarios VALUES (11, 1), (22, 2);
        INSERT INTO parceiros_comerciais VALUES (101, 1, 11), (202, 2, NULL);
        INSERT INTO orcamentos VALUES (301, 1), (302, 2);
        INSERT INTO pedidos VALUES (401, 1), (402, 2);
        INSERT INTO servicos VALUES (501, 1), (502, 2);
        """
    )
    return connection


def test_composite_vendor_reference_is_optional_but_tenant_scoped():
    connection = _connection()
    try:
        connection.execute(
            "INSERT INTO parceiros_comerciais VALUES (203, 2, 22)"
        )
        connection.execute(
            "INSERT INTO parceiros_comerciais VALUES (204, 2, NULL)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO parceiros_comerciais VALUES (205, 1, 22)"
            )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "table,parent_column,parent_id,service_id,company_id",
    [
        ("orcamentos_itens", "orcamento_id", 301, 501, 1),
        ("pedidos_itens", "pedido_id", 401, 501, 1),
    ],
)
def test_document_service_links_and_free_items_are_tenant_scoped(
    table, parent_column, parent_id, service_id, company_id
):
    connection = _connection()
    try:
        connection.execute(
            f"""
            INSERT INTO {table}
                (id, {parent_column}, empresa_id, servico_id, descricao, preco_unitario, quantidade)
            VALUES (1, ?, ?, ?, 'Snapshot original', 42.50, 2)
            """,
            (parent_id, company_id, service_id),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                f"""
                INSERT INTO {table}
                    (id, {parent_column}, empresa_id, servico_id, descricao, preco_unitario, quantidade)
                VALUES (2, ?, ?, ?, 'Não vincular', 10, 1)
                """,
                (parent_id, company_id, 502),
            )

        connection.execute(
            f"""
            INSERT INTO {table}
                (id, {parent_column}, empresa_id, servico_id, descricao, preco_unitario, quantidade)
            VALUES (3, ?, ?, NULL, 'Serviço livre legado', 12.25, 3)
            """,
            (parent_id, company_id),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                f"""
                INSERT INTO {table}
                    (id, {parent_column}, empresa_id, servico_id, descricao, preco_unitario, quantidade)
                VALUES (4, ?, 2, NULL, 'Empresa divergente', 1, 1)
                """,
                (parent_id,),
            )

        connection.execute("DELETE FROM servicos WHERE id = 501 AND empresa_id = 1")
        snapshot = connection.execute(
            f"SELECT servico_id, descricao, preco_unitario, quantidade, empresa_id FROM {table} WHERE id=1"
        ).fetchone()
        assert snapshot == (None, "Snapshot original", 42.5, 2, company_id)
    finally:
        connection.close()
