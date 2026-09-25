# ADR 0002 — Núcleo de estudos (Fase 1)

- **Data:** 2026-09-23
- **Status:** aceita

## Decisões

### 1. Conteúdo em arquivos, sincronizado com o banco

Áreas, competências, trilhas e módulos ficam em `data/` (TOML + Markdown), e `hone content sync` importa tudo para o SQLite. Assim o conteúdo é versionado no Git, pode ser editado em qualquer editor e o banco guarda só o que é pessoal (progresso, sessões, check-ins). Decisão tomada pela criadora.

- O TOML é lido com `tomllib`, que vem na biblioteca padrão, sem dependência nova.
- O sync valida tudo antes de gravar e roda numa única transação. Um erro não deixa o banco pela metade.
- Os ciclos de pré-requisitos são detectados com `graphlib.TopologicalSorter` (biblioteca padrão). O NetworkX entra na Fase 2, quando o grafo passar a sugerir sequências.
- O sync nunca apaga módulos, para não perder progresso. Módulos que sumiram dos arquivos são reportados como órfãos.
- `content` precisa ficar dentro da pasta da trilha, o que impede ler arquivos fora de `data/`.

### 2. Status do módulo é calculado, não gravado

`module_progress` guarda só dois estados reais: `in_progress` e `completed`. Os estados "disponível" e "trancado" são calculados a cada leitura a partir dos pré-requisitos. Assim, mudar um pré-requisito no `track.toml` passa a valer no próximo sync, sem migração de dados.

A trava de progresso vale para abrir (`read`, `session start`) e para concluir (`done`) um módulo.

### 3. Check-in manual com intenção

`hone checkin` registra, uma vez por dia, uma frase sobre o que vai ser estudado. O streak conta os dias seguidos com check-in. Se hoje ainda não teve check-in, o streak de ontem continua vivo até a meia-noite. Decisão tomada pela criadora.

O dia do check-in usa a data local; os horários ficam em UTC (`hone/core/clock.py`).

### 4. Uma sessão aberta por vez

Garantido por índice único parcial no banco (`WHERE ended_at IS NULL`), além da checagem no código. O gráfico do dashboard soma os minutos no dia local em que cada sessão começou; uma sessão em andamento conta até agora.

### 5. `open_workspace` como porta de entrada

CLI e API abrem o banco pelo mesmo `open_workspace()`, que confere se o banco existe, se o schema está em dia e se há usuária cadastrada. Cada falha vira uma exceção de domínio, e `voice.challenge_for()` a traduz em "Desafio" + "Próximo passo", o mesmo texto no terminal e no dashboard.

### 6. Dashboard sem build step

HTML + JS puro + Chart.js, servidos pelo FastAPI. As rotas são por hash (`#/trilhas/...`), então não é preciso configurar nada no servidor.

- O Chart.js fica em `dashboard/vendor/` para o dashboard funcionar offline.
- As cores vêm de `/theme/tokens.css`, gerado a partir de `hone/ui_palette.py`. CLI e dashboard usam a mesma fonte de cores.
- O Markdown é renderizado no servidor com `markdown-it-py`, com HTML bruto desligado.
- Nesta fase o dashboard é só leitura. Ações ficam no CLI, que é a interface primária do MVP.

### 7. Tipografia

Bricolage Grotesque (títulos), Atkinson Hyperlegible (corpo) e JetBrains Mono (código), todas com fallback local. **Substituída pelo ADR 0005.**

## Consequências

- Adicionar uma trilha é criar uma pasta em `data/tracks/` e rodar o sync.
- Um banco da Fase 0 precisa de `hone db init` para receber a migração 0002. Os dados existentes são preservados.
