-- Rollback autossuficiente. Remove todos os dados da estrutura criada nesta fase.
-- Não usa CASCADE: dependências futuras externas impedirão remoção silenciosa.
-- Não toca em public.cores.
BEGIN;
DROP TABLE public.grades_variacoes_valores;
DROP TABLE public.grades_variacoes;
COMMIT;
