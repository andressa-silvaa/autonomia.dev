# Formação em TI

Sistema pessoal de formação de desenvolvedores. Ele não mede só conteúdo concluído: mede competência e autonomia, para responder a pergunta **"eu consigo resolver problemas de programação e engenharia sem ajuda?"**.

Tudo roda local e de graça: Python, SQLite, Docker e Ollama.

## Status

| Fase | Situação |
|---|---|
| 0 — Arquitetura mínima | ✅ entregue |
| 1 — Núcleo de estudos | próxima |

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

Edite o `.env`: coloque seu nome em `FORMACAO_USER_NAME` e troque as senhas dos containers.

## Banco de dados

```powershell
formacao db init      # cria data/formacao.db e aplica as migrações
formacao db status    # versão do schema e linhas por tabela
```

`db init` pode ser rodado quantas vezes você quiser: ele só aplica o que estiver pendente.

## API local

```powershell
formacao serve
```

Abra http://127.0.0.1:8000/docs. O endpoint `/health` diz se o banco está em dia.

## Containers das trilhas

Nenhum serviço sobe sozinho. Cada um fica num *profile* e só sobe quando você pede. Rode a partir da raiz do projeto:

```powershell
docker compose --env-file .env -f docker/compose.yaml --profile redis up -d
docker compose --env-file .env -f docker/compose.yaml --profile redis down
```

Profiles disponíveis: `sqlserver`, `oracle`, `mongo`, `redis`, `rabbitmq`, `kafka`.

As portas só aceitam conexões de `127.0.0.1`, então nada fica exposto na rede. Os dados ficam em volumes nomeados; para apagar os dados de um serviço, use `docker volume rm formacao_<serviço>-data`.

## Testes e qualidade

```powershell
pytest
ruff check .
ruff format .
```

## Estrutura

```
formacao/
  core/          banco, migrações, entidades do domínio
    migrations/  arquivos NNNN_descricao.sql, aplicados em ordem
  engines/       engines da arquitetura (criados fase a fase)
  cli/           comandos do terminal (typer + rich)
  api/           API local (FastAPI)
  ui_palette.py  cores da marca, compartilhadas entre CLI e dashboard
data/tracks/     conteúdo das trilhas (Markdown)
exercises/       exercícios executáveis
dashboard/       dashboard HTML (Fase 1)
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

1. Crie `formacao/core/migrations/0002_descricao.sql`, com o próximo número da sequência.
2. Não use `BEGIN`/`COMMIT`: o executor já roda o arquivo inteiro numa transação.
3. Nunca edite uma migração que já foi aplicada; crie uma nova.
4. Rode `formacao db init`.

## Ainda não coberto (fases futuras)

- **Ollama**: instalação e modelos (`qwen2.5-coder`, `llama3.2`, `phi3`) serão documentados quando a correção por IA entrar.
- **Agendamento (Agendador de Tarefas do Windows)**: o briefing diário e o lembrete de check-in chegam com as Fases 1 e 10. Ficarão em `scripts/`, com um script que registra as tarefas via `schtasks`.
