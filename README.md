# autonomia.dev

Sistema pessoal de formação de desenvolvedores. Ele não mede só conteúdo concluído: mede competência e autonomia, para responder a pergunta **"eu consigo resolver problemas de programação e engenharia sem ajuda?"**.

Tudo roda local e de graça: Python, SQLite, Docker e Ollama. O comando do terminal e o pacote Python se chamam `hone` (afiar habilidades).

## Status

| Fase | Situação |
|---|---|
| 0 — Arquitetura mínima | ✅ entregue |
| 1 — Núcleo de estudos | ✅ entregue |
| 2 — Diagnóstico e mapa de conhecimento | próxima |

## Requisitos

- Python 3.12+
- Git
- Docker Desktop (só para os serviços das trilhas)
- Ollama (a partir da Fase 3/7; ainda não é necessário)

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env          # Linux/macOS: cp .env.example .env
```

Edite o `.env`: coloque seu nome em `HONE_USER_NAME` e troque as senhas dos containers.

## Banco de dados

```powershell
hone db init      # cria data/hone.db e aplica as migrações
hone db status    # versão do schema e linhas por tabela
```

`db init` pode ser rodado quantas vezes você quiser: ele só aplica o que estiver pendente. Rode de novo sempre que atualizar o código.

## Estudando

```powershell
hone content sync                 # carrega as trilhas de data/ no banco
hone checkin                      # "o que você vai estudar hoje?"
hone today                        # streak, check-in, sessão e o que estudar agora
hone tracks                       # progresso em cada trilha
hone track cs-fundamentals         # módulos, status e pré-requisitos
hone session start recursion       # cronometra uma sessão (e marca o módulo como "estudando")
hone read recursion                # abre o conteúdo no terminal
hone session stop -n "o que aprendi"
hone done recursion                # conclui o módulo e mostra o que destravou
```

Um módulo só abre quando todos os pré-requisitos estão concluídos. Os módulos podem ser chamados pelo nome curto (`recursion`) ou pelo nome completo (`cs-fundamentals/recursion`).

## Dashboard

```powershell
hone serve --open
```

O dashboard mostra o streak, o check-in, o tempo de estudo dos últimos 14 dias, o progresso nas trilhas e o conteúdo dos módulos. Ele é só para leitura: registrar sessões e concluir módulos continua no CLI. O tema segue o sistema operacional e pode ser trocado no botão do topo.

Funciona sem internet: o Chart.js está em `dashboard/vendor/`. Sem conexão, só as fontes do Google Fonts deixam de carregar, e o navegador usa as fontes locais de fallback.

## Conteúdo das trilhas

```
data/
  catalog.toml              áreas e competências
  tracks/<trilha>/
    track.toml              a trilha, seus módulos e pré-requisitos
    01-modulo.md            teoria em Markdown
```

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

- `requires` aceita módulos da mesma trilha (`"recursion"`) ou de outra (`"outra-trilha/modulo"`).
- `hone content sync` valida tudo antes de gravar: pré-requisitos inexistentes, ciclos, arquivos faltando, competências desconhecidas. Se algo estiver errado, ele lista todos os problemas e não grava nada.
- Remover um módulo do arquivo não apaga o seu progresso no banco. O sync só avisa que o módulo ficou órfão.

## API local

Com `hone serve` rodando, a documentação da API fica em http://127.0.0.1:8000/docs, e o endpoint `/health` diz se o banco está em dia.

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
  core/          banco, migrações, entidades do domínio
    migrations/  arquivos NNNN_descricao.sql, aplicados em ordem
    workspace.py abre banco + usuária para CLI e API
  engines/
    content.py   leitura, validação e sync de data/
    progress.py  status dos módulos e trava de pré-requisitos
    sessions.py  sessões de estudo
    checkins.py  check-in diário e streak
    overview.py  resumo do dia (base do dashboard)
  cli/           comandos do terminal (typer + rich)
  api/           API local (FastAPI) e tokens de tema
  voice.py       textos com a voz do sistema e erros como "Desafio"
  ui_palette.py  cores da marca, compartilhadas entre CLI e dashboard
data/            catálogo e trilhas (TOML + Markdown)
exercises/       exercícios executáveis
dashboard/       dashboard HTML + JS puro + Chart.js
docker/          compose dos serviços reais das trilhas
scripts/         scripts de agendamento (briefing, check-in)
docs/adr/        registro das decisões de arquitetura
tests/
```

## Regras de código

As regras estão na skill `.claude/skills/code-style/SKILL.md`:

- todo código é escrito em inglês; textos exibidos para a usuária ficam em português;
- comentários e docstrings são proibidos, e qualquer exceção precisa de autorização explícita;
- a justificativa de cada decisão fica em `docs/adr/`, não no código.

## Como criar uma migração

1. Crie `hone/core/migrations/0003_descricao.sql`, com o próximo número da sequência.
2. Não use `BEGIN`/`COMMIT`: o executor já roda o arquivo inteiro numa transação.
3. Nunca edite uma migração que já foi aplicada; crie uma nova.
4. Rode `hone db init`.

## Ainda não coberto (fases futuras)

- **Ollama**: instalação e modelos (`qwen2.5-coder`, `llama3.2`, `phi3`) serão documentados quando a correção por IA entrar.
- **Agendamento (Agendador de Tarefas do Windows)**: o lembrete de check-in e o briefing diário vão ficar em `scripts/`, com um script que registra as tarefas via `schtasks`. Entram junto com o hook de pre-push (Fase 3) e o Tech Knowledge Hub (Fase 10).
