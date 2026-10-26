-- Exemplos de manipulação de dados (DML) da Biblioteca Municipal de Cristópolis.
-- Rode depois de criar o esquema:  sqlite3 exemplo.db < app/schema.sql  e então  sqlite3 exemplo.db < docs/banco/exemplos_dml.sql
-- Os dados são fictícios. Os exemplos marcados como RESTRIÇÃO falham de propósito e estão comentados.
PRAGMA foreign_keys = ON;

-- INSERT: Cadastro de categorias, livros, usuários e empréstimos
INSERT INTO categoria (nome) VALUES ('Romance'), ('Infantil');

INSERT INTO livro
  (titulo, autor, isbn, ano_publicacao, id_categoria, quantidade_total) VALUES
  ('Dom Casmurro', 'Machado de Assis', '9788500000011', 1899, 1, 3),
  ('O Pequeno Príncipe', 'Antoine de Saint-Exupéry', '9788500000059', 1943, 2, 2),
  ('Vidas Secas', 'Graciliano Ramos', '9788500000042', 1938, 1, 1);

INSERT INTO usuario (nome, cpf, telefone, tipo_usuario) VALUES
  ('Maria Oliveira', '39184726393', '77998123456', 'aluno'),
  ('João Antônio Souza', '52998224725', '77991234567', 'comunidade'),
  ('Ana Paula Ribeiro', '11144477735', '77993456789', 'aluno');

INSERT INTO emprestimo
  (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) VALUES
  ('2026-10-01', '2026-10-31', 'ativo', 1, 1),
  ('2026-09-10', '2026-10-10', 'ativo', 2, 3);

INSERT INTO reserva (data_reserva, status, id_usuario, id_livro) VALUES
  ('2026-10-20', 'ativa', 3, 3);

-- SELECT: Livros com a quantidade disponível (total menos empréstimos ativos)
SELECT l.titulo,
       l.quantidade_total AS total,
       COUNT(e.id_emprestimo) AS emprestados,
       l.quantidade_total - COUNT(e.id_emprestimo) AS disponiveis
  FROM livro l
  LEFT JOIN emprestimo e ON e.id_livro = l.id_livro AND e.status = 'ativo'
 GROUP BY l.id_livro
 ORDER BY l.titulo;

-- SELECT: Empréstimos em atraso (data de referência: 25/10/2026)
SELECT u.nome AS usuario,
       l.titulo AS livro,
       e.data_devolucao_prevista AS prevista,
       CAST(julianday('2026-10-25') - julianday(e.data_devolucao_prevista) AS INTEGER)
         AS dias_de_atraso
  FROM emprestimo e
  JOIN usuario u ON u.id_usuario = e.id_usuario
  JOIN livro l ON l.id_livro = e.id_livro
 WHERE e.status = 'ativo'
   AND date(e.data_devolucao_prevista) < date('2026-10-25');

-- UPDATE: Devolução: o empréstimo é encerrado e o aviso da reserva é reiniciado, na mesma transação
BEGIN;
UPDATE emprestimo
   SET status = 'devolvido', data_devolucao_real = '2026-10-25'
 WHERE id_emprestimo = 2;
UPDATE reserva
   SET aviso_visto = 0
 WHERE id_livro = 3 AND status = 'ativa';
COMMIT;

-- SELECT: Reservas ativas cujo livro já tem exemplar disponível (prontas para retirada)
SELECT u.nome AS usuario, l.titulo AS livro, r.data_reserva
  FROM reserva r
  JOIN usuario u ON u.id_usuario = r.id_usuario
  JOIN livro l ON l.id_livro = r.id_livro
 WHERE r.status = 'ativa'
   AND l.quantidade_total - (SELECT COUNT(*) FROM emprestimo e
                              WHERE e.id_livro = l.id_livro AND e.status = 'ativo') > 0;

-- UPDATE: Inativação de um usuário que já tem histórico
UPDATE usuario SET ativo = 0 WHERE id_usuario = 2;

SELECT nome, ativo FROM usuario ORDER BY id_usuario;

-- DELETE: Remoção de um usuário sem empréstimos nem reservas
INSERT INTO usuario (nome, cpf, telefone)
  VALUES ('Cadastro feito por engano', '45317828791', '77990000001');

DELETE FROM usuario WHERE cpf = '45317828791';

SELECT COUNT(*) AS usuarios_restantes FROM usuario;

-- RESTRIÇÃO: Chave estrangeira: o banco recusa apagar um livro que tem empréstimos
-- DELETE FROM livro WHERE id_livro = 1;
-- Resultado esperado: Erro do banco: FOREIGN KEY constraint failed

-- RESTRIÇÃO: Unicidade: o banco recusa um segundo usuário com o mesmo CPF
-- INSERT INTO usuario (nome, cpf, telefone)
--   VALUES ('Outra pessoa', '39184726393', '77990000002');
-- Resultado esperado: Erro do banco: UNIQUE constraint failed: usuario.cpf

-- RESTRIÇÃO: CHECK: o banco recusa um status que não existe
-- UPDATE emprestimo SET status = 'perdido' WHERE id_emprestimo = 1;
-- Resultado esperado: Erro do banco: CHECK constraint failed: status IN ('ativo', 'devolvido')
