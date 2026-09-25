# autonomia.dev

Sistema pessoal de formação de desenvolvedores. Ele não mede só conteúdo concluído: mede competência e autonomia, para responder a pergunta **"eu consigo resolver problemas de programação e engenharia sem ajuda?"**.

Tudo roda local e de graça: Python, SQLite, Docker e Ollama. O comando e o pacote Python se chamam `hone` (afiar habilidades).

## Status

| Fase | Situação |
|---|---|
| 0 — Arquitetura mínima | ✅ entregue |
| 1 — Núcleo de estudos | ✅ entregue |
| 2 — Diagnóstico e mapa de conhecimento | ✅ entregue |
| 3 — Engine de exercícios (e interface no navegador) | ✅ entregue |
| Trilha de IA e Agentes | ✅ entregue |
| 4 — Execução de código em Docker | próxima |

## Trilhas disponíveis

| Trilha | Módulos | Exercícios | Sobre |
|---|---|---|---|
| Fundamentos de CS | 8 | 18 | Execução de programas, memória, complexidade, estruturas de dados, recursão, busca e ordenação |
| IA e Agentes | 10 | 19 | Como um LLM funciona, prompting, saída estruturada, context engineering, embeddings, RAG, tool calling, agentes, avaliação e quando não usar IA |

## Requisitos

- Python 3.12+
- Git
- Ollama (opcional: corrige as respostas dissertativas; sem ele, elas vão de autoavaliação)
- Docker Desktop (só para os serviços das trilhas)

## Instalação (uma vez só)

```powershell
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env          # Linux/macOS: cp .env.example .env
```

Edite o `.env`: coloque seu nome em `HONE_USER_NAME` e troque as senhas dos containers.

## Abrindo o sistema

```powershell
hone
```

Pronto. O `hone` cria ou atualiza o banco, carrega as trilhas, as perguntas e os exercícios, e abre o sistema no navegador (http://127.0.0.1:8000). Deixe a janela do terminal aberta enquanto estuda; para sair, feche-a ou aperte Ctrl+C. Se você rodar `hone` com o sistema já aberto, ele só abre o navegador.

Sem terminal nenhum: dê dois cliques em `scripts/open-hone.cmd`. Dá para criar um atalho dele na área de trabalho (botão direito → Enviar para → Área de trabalho).

Se algum arquivo de conteúdo estiver com problema, o `hone` não abre e mostra no terminal o que corrigir. Nada fica gravado pela metade.

## O que dá para fazer no navegador

- **Hoje**: check-in do dia, cronômetro de sessão de estudo (livre ou num módulo), streak, XP, o que estudar agora e os minutos dos últimos 14 dias.
- **Trilhas**: módulos com pré-requisitos, conteúdo, exercícios e o botão de concluir. Um módulo só abre quando os pré-requisitos estão concluídos, e só pode ser concluído depois do exercício obrigatório.
- **Exercícios**: enunciado, editor de código com "Rodar testes" (Tab indenta, Ctrl+Enter envia), respostas dissertativas, dicas (cada uma custa um pouco de XP) e histórico de tentativas. Marque "Usei IA nesta tentativa" quando for o caso: isso vira métrica de autonomia.
- **Mapa**: diagnóstico (pode parar no meio), domínio por competência, objetivo, caminho até ele, lacunas e módulos por nível de pré-requisito.
- **Métricas**: XP de competência e de atividade, e prática por competência (aprovados, de primeira, tentativas, dicas, uso de IA).

O tema abre no modo claro e pode ser trocado (claro, escuro ou seguir o sistema) no canto de baixo da barra lateral. Funciona sem internet: só as fontes do Google Fonts deixam de carregar.

## Como os exercícios são corrigidos

| Tipo | Correção |
|---|---|
| Escolha ou resposta curta | gabarito (espaços e maiúsculas não importam) |
| Código Python | os testes do exercício rodam de verdade, com limite de tempo |
| Dissertativa | Ollama julga cada critério da rubrica; sem Ollama, autoavaliação com resposta de referência |

- Passa em dissertativa quem cumpre pelo menos dois terços dos critérios.
- **XP de competência** vem só da primeira aprovação de cada exercício; quiz e autoavaliação valem metade, e cada dica tira 25%. **XP de atividade** vem de tentar (2 por tentativa, nas três primeiras).
- Aprovar sobe o domínio das competências do módulo: código → "consegue aplicar"; quiz e autoavaliação → "reconhece"; dissertativa corrigida pelo Ollama → "consegue explicar" (se você já aplica).

As regras completas e o porquê de cada uma estão em `docs/adr/0004-exercise-engine-and-browser-interface.md`.

## Ollama (correção por IA local)

1. Baixe e instale em https://ollama.com/download (gratuito, sem conta).
2. Num terminal, baixe o modelo usado na correção (uns 4,7 GB):

   ```powershell
   ollama pull qwen2.5-coder:7b
   ```

3. Pronto: com o Ollama aberto, as dissertativas passam a ser corrigidas por ele. Nada sai da sua máquina.

Para trocar o modelo ou o endereço, use `HONE_OLLAMA_MODEL` e `HONE_OLLAMA_URL` no `.env`.

## Conteúdo das trilhas

```
data/
  catalog.toml              áreas e competências
  tracks/<trilha>/
    track.toml              a trilha, seus módulos e pré-requisitos
    01-modulo.md            teoria em Markdown
  diagnostics/<nome>.toml   perguntas do diagnóstico, por competência
exercises/<trilha>/<módulo>/<exercício>/
  exercise.toml             tipo, correção, dificuldade, dicas
  README.md                 enunciado
  starter.py                código inicial (exercícios de código)
  test_solution.py          testes (exercícios de código)
  reference.md              resposta de referência (dissertativas)
```

Tudo é validado a cada abertura do `hone`: pré-requisitos inexistentes, ciclos, arquivos faltando, competências desconhecidas, exercício sem formato de resposta. Se algo estiver errado, ele lista todos os problemas e não grava nada. Remover um módulo, pergunta ou exercício dos arquivos não apaga o seu histórico.

Exemplo de módulo no `track.toml`:

```toml
[[modules]]
slug = "recursion"
title = "Recursão"
summary = "Caso base, pilha de chamadas e memoização."
content = "07-recursion.md"
requires = ["stack-and-heap-memory"]
competencies = ["recursion"]
```

Exemplo de pergunta do diagnóstico:

```toml
[[questions]]
slug = "lifo-structure"
competency = "linear-data-structures"
kind = "concept"                 # concept, code_reading, debugging ou complete_code
prompt = "Qual estrutura segue a regra \"o último a entrar é o primeiro a sair\"?"
options = ["Pilha", "Fila", "Tabela hash"]
answer = 1                       # número da alternativa certa
explanation = "Pilha é LIFO; fila é FIFO."
```

Exemplo de `exercise.toml` de código (a pasta tem também `README.md`, `starter.py` e `test_solution.py`, que importa de `solution`):

```toml
title = "Achatar listas aninhadas"
kind = "code"
grading = "auto"
difficulty = 3                   # 1 a 5; define o XP (5, 10, 20, 35, 50)
required = true                  # trava a conclusão do módulo
hints = ["Primeira dica.", "Segunda dica."]
```

Exemplo de dissertativa (com `README.md` e, se quiser, `reference.md`):

```toml
title = "Por que não guardar dinheiro em float?"
kind = "explanation"
grading = "ollama"               # ou "self" para sempre autoavaliar
difficulty = 2
rubric = ["Explica que 0.1 não tem representação exata em binário", "Propõe Decimal ou centavos"]
```

Quiz de escolha usa `options` + `answer`; resposta curta usa `accept = ["..."]`.

## API local

Com o sistema aberto, a documentação da API fica em http://127.0.0.1:8000/docs, e `/health` diz se o banco está em dia. A API só aceita conexões de `127.0.0.1`, e toda ação que grava dados exige um cabeçalho que só o próprio dashboard envia, para que nenhum outro site aberto no navegador consiga usá-la.

## Containers das trilhas

Nenhum serviço sobe sozinho. Cada um fica num *profile* e só sobe quando você pede. Rode a partir da raiz do projeto:

```powershell
docker compose --env-file .env -f docker/compose.yaml --profile redis up -d
docker compose --env-file .env -f docker/compose.yaml --profile redis down
```

Profiles disponíveis: `sqlserver`, `oracle`, `mongo`, `redis`, `rabbitmq`, `kafka`.

As portas só aceitam conexões de `127.0.0.1`, então nada fica exposto na rede. Os dados ficam em volumes nomeados; para apagar os dados de um serviço, use `docker volume rm hone_<serviço>-data`.

## Testes e qualidade

```powershell
pytest
ruff check .
ruff format .
```

## Estrutura

```
hone/
  cli.py         o comando hone: prepara tudo e abre o navegador
  startup.py     migrações, usuária e sync do conteúdo na abertura
  core/          banco, migrações, entidades do domínio
    migrations/  arquivos NNNN_descricao.sql, aplicados em ordem
  engines/
    content.py        leitura, validação e sync de data/ e exercises/
    toml_tables.py    leitura e validação de campos dos arquivos TOML
    question_bank.py  perguntas do diagnóstico
    exercise_bank.py  exercícios (exercise.toml e arquivos da pasta)
    diagnostic.py     rodadas, correção e regras de domínio
    exercises.py      pasta de trabalho, dicas, tentativas, promoção de domínio
    submissions.py    envio: gabarito, testes, Ollama ou autoavaliação
    grading.py        executor de testes e correção por rubrica
    ollama.py         cliente do Ollama (só biblioteca padrão)
    xp.py             regras de XP
    metrics.py        prática por competência
    mastery.py        domínio atual e histórico por competência
    knowledge.py      grafo (NetworkX), caminho, lacunas e objetivo
    progress.py       status dos módulos e travas
    sessions.py       sessões de estudo
    checkins.py       check-in diário e streak
    overview.py       resumo do dia
  api/           API local (FastAPI), rotas por área e tokens de tema
  voice.py       textos com a voz do sistema e erros como "Desafio"
  ui_palette.py  cores da marca
data/            catálogo, trilhas e diagnóstico (TOML + Markdown)
exercises/       exercícios executáveis
workspace/       suas soluções e rascunhos (fora do Git)
dashboard/       interface HTML + JS puro + Chart.js
docker/          compose dos serviços reais das trilhas
scripts/         open-hone.cmd (abrir com dois cliques)
docs/adr/        registro das decisões de arquitetura
tests/
```

## Regras de código

As regras estão na skill `.claude/skills/code-style/SKILL.md`:

- todo código é escrito em inglês; textos exibidos para a usuária ficam em português;
- comentários e docstrings são proibidos, e qualquer exceção precisa de autorização explícita;
- a justificativa de cada decisão fica em `docs/adr/`, não no código.

## Como criar uma migração

1. Crie `hone/core/migrations/0005_descricao.sql`, com o próximo número da sequência.
2. Não use `BEGIN`/`COMMIT`: o executor já roda o arquivo inteiro numa transação.
3. Nunca edite uma migração que já foi aplicada; crie uma nova.
4. Abra o `hone`: ele aplica o que estiver pendente.

## Ainda não coberto (fases futuras)

- **Execução isolada em Docker**, C#/xUnit, SQL real e frontend com renderização: Fase 4.
- **Lembretes e briefing diário** pelo Agendador de Tarefas do Windows, e o **hook de pre-push** que bloqueia push sem check-in: vão chamar a API local, sem comandos novos.
