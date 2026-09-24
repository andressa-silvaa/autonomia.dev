# ADR 0001 — Arquitetura mínima (Fase 0)

- **Data:** 2026-09-23
- **Status:** aceita

## Contexto

A Fase 0 pede as entidades principais, o schema SQLite, um Docker Compose base, a estrutura do projeto Python e o Git configurado. O objetivo é que a própria criadora consiga ler e manter o código sozinha, com o mínimo de "mágica".

## Decisões

### 1. SQL puro com `sqlite3`, sem ORM

O schema fica em arquivos `.sql`, e o que está no arquivo é exatamente o que roda no banco. Um ORM esconderia o SQL, que é justamente um dos assuntos estudados. Os repositórios (a partir da Fase 1) vão usar consultas parametrizadas (`?`).

### 2. Migrações versionadas pelo `PRAGMA user_version`

O SQLite guarda um número inteiro no cabeçalho do arquivo do banco, e ele é usado como versão do schema. Cada arquivo `NNNN_nome.sql` roda dentro de `BEGIN … PRAGMA user_version = N; COMMIT`. Se algo falhar, nada daquele arquivo fica aplicado pela metade.

- A numeração precisa ser contínua. Um buraco quase sempre é erro de digitação, então o sistema falha cedo.
- Um banco numa versão maior que a do código é recusado, para não corromper dados.

### 3. Configuração da conexão

- `PRAGMA foreign_keys = ON`: o SQLite vem com as chaves estrangeiras desligadas por padrão.
- `PRAGMA journal_mode = WAL`: permite que a API leia enquanto o CLI escreve.
- `row_factory = sqlite3.Row`: acesso às colunas pelo nome.

### 4. Convenções do schema

- Datas e horas ficam em TEXT ISO-8601 UTC. Datas sem hora ficam em `AAAA-MM-DD`.
- Booleanos são INTEGER 0/1 com CHECK.
- Toda tabela de dados pessoais tem `user_id`, preparando a Fase 12 (multiusuário) sem reescrever tudo.
- Os estados de domínio têm CHECK no SQL e ficam espelhados no enum `Mastery`. Um teste garante que as duas listas batem.
- `exercises.kind` e `exercises.grading` não têm CHECK: novos formatos vão surgir, e o SQLite não permite alterar um CHECK sem recriar a tabela. A validação desses campos fica nos enums Python.
- `attempts.used_ai` e `attempts.hints_used` existem desde o início, porque a pergunta central do sistema é sobre autonomia.
- `reviews` já nasce com os campos do SM-2 (EF inicial 2.5).
- Um módulo exigir a si mesmo é barrado por CHECK. Ciclos maiores serão detectados com NetworkX na Fase 2.

### 5. Engines como módulos, não serviços

`hone/engines/` vai recebendo um módulo por fase (learning, knowledge, exercise…). Regra de dependência: `core` nunca importa engines, e CLI/API usam engines, nunca o contrário.

### 6. Docker Compose com profiles

Cada serviço (SQL Server, Oracle, MongoDB, Redis, RabbitMQ, Kafka) fica num profile próprio, então nada sobe por padrão e só roda o que o módulo atual precisa. As portas ficam presas em `127.0.0.1`. As senhas vêm do `.env`, e o compose recusa subir se alguma estiver faltando (`${VAR:?}`). As imagens de SDK (dotnet, node) entram na Fase 4.

### 7. Identidade visual centralizada

`hone/ui_palette.py` é a fonte única das cores: coral `#F0643C` como assinatura da marca, verde-azulado `#2A9D8F` como cor fria complementar, mostarda para alertas e um neutro para o que deve recuar. O CLI usa essas cores por nome de estilo; o dashboard vai reutilizar os mesmos valores como CSS variables. Os erros aparecem como "Desafio" + "Próximo passo", nunca como traceback cru.

### 8. Código em inglês e sem comentários

Esta decisão foi tomada pela criadora e substitui a regra 6 do documento de requisitos ("código comentado"). O código deve se explicar por nomes, funções pequenas e constantes nomeadas; a justificativa das decisões fica neste diretório. Os textos exibidos para a usuária continuam em português. Detalhes em `.claude/skills/code-style/SKILL.md`.

### 9. Agendamento pelo Agendador de Tarefas do Windows

O documento de requisitos cita cron (Linux), mas o sistema roda no Windows. As tarefas agendadas (briefing diário, lembrete de check-in) vão usar o Agendador de Tarefas, registradas via `schtasks` e chamando comandos `hone`. A lógica fica toda no CLI, então trocar de agendador no futuro não exige mudar código.

### 10. O documento de requisitos fica fora do Git

O PDF de requisitos é referência pessoal e não é versionado (`*.pdf` está no `.gitignore`).

## Consequências

- Mudar o schema exige uma nova migração. Isso é intencional e deixa o histórico explícito.
- Sem ORM, o mapeamento linha → dataclass é manual, mas fica visível.
- Este ADR é o lugar para entender o "porquê" do código.
