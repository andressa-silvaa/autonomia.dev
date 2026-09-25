# ADR 0004 — Engine de exercícios e interface no navegador (Fase 3)

- **Data:** 2026-09-25
- **Status:** aceita
- **Substitui:** a decisão 6 do ADR 0002 ("dashboard só leitura; ações no CLI")

## Contexto

O documento de requisitos pedia um CLI como interface primária do MVP e um dashboard só para leitura. Nas Fases 1 e 2 isso virou uma coleção de comandos (`hone checkin`, `hone session start`, `hone diagnostic start`…). No meio da Fase 3, a criadora disse que não queria rodar tantos comandos: queria **um comando só** que abrisse o sistema no navegador, e fazer tudo por lá. As decisões abaixo foram tomadas com ela.

## Decisões

### 1. Um comando, tudo no navegador

- `hone` (ou o atalho `scripts/open-hone.cmd`) aplica migrações, garante a usuária, recarrega `data/` e `exercises/`, sobe o servidor e abre o navegador. Se o sistema já estiver aberto, só abre o navegador.
- Todos os subcomandos foram **removidos**, não escondidos. Menos código para manter. O agendamento pelo Agendador de Tarefas (ADR 0001, decisão 9), quando vier, vai chamar a API local em vez de comandos.
- Conteúdo inválido impede a abertura e aparece no terminal com o mesmo "Desafio / Próximo passo" de sempre; nada é gravado pela metade.
- Os textos de "próximo passo" deixaram de citar comandos e passaram a apontar para telas ("encerre a sessão na tela Hoje").

### 2. Segurança da API local

A API agora grava dados e **executa código Python**. Sem proteção, qualquer site aberto no navegador poderia enviar uma requisição para `127.0.0.1:8000` e rodar código na máquina.

- `TrustedHostMiddleware` só aceita `127.0.0.1` e `localhost` no cabeçalho `Host`, o que bloqueia DNS rebinding.
- Toda requisição que muda dados (`POST`, `PUT`, `DELETE` em `/api/`) exige o cabeçalho `X-Hone-Client: dashboard`. Um site de outra origem não consegue enviar um cabeçalho próprio sem autorização de CORS, e a API não habilita CORS.
- O servidor continua preso a `127.0.0.1`.

### 3. Exercícios em arquivos, como o resto do conteúdo

`exercises/<trilha>/<módulo>/<exercício>/` com `exercise.toml`, `README.md` (enunciado) e, conforme o formato, `starter.py` + `test_solution.py` ou `reference.md`. O `hone` sincroniza tudo na abertura, com a mesma validação em bloco do conteúdo.

- O formato da resposta sai do que existe na pasta: `options` + `answer` (escolha), `accept` (digitada), `test_solution.py` (código) ou `rubric` (texto). Exatamente um.
- Escolha e digitada usam `grading = "auto"`; texto usa `"ollama"` ou `"self"`.
- O slug é o nome da pasta e é único no repositório inteiro.
- Exercício que some dos arquivos fica com `retired = 1` e deixa de ser obrigatório; as tentativas antigas ficam.
- O XP base vem da dificuldade (5, 10, 20, 35, 50), não é escrito à mão.

### 4. Código roda local, em subprocesso, com timeout

A solução é salva em `workspace/` (fora do Git) e rodada com `pytest` num diretório temporário, junto com o `test_solution.py` original, com timeout (`HONE_EXERCISE_TIMEOUT`, 10 s). Os testes ficam fora da pasta de trabalho, para não serem editados sem querer. O resultado vem do relatório JUnit do pytest.

- É o próprio código da criadora, na máquina dela; isolamento em Docker, C#/xUnit e SQL real ficam para a Fase 4, como o documento ordena.
- Exercícios de complexidade medem tempo com folga grande (0,15 a 0,3 s contra segundos de uma solução quadrática ou linear), para barrar a solução lenta sem ficar instável.

### 5. Ollama opcional, com autoavaliação como rede de segurança

Respostas de texto com `grading = "ollama"` são corrigidas pelo modelo local (`HONE_OLLAMA_MODEL`, padrão `qwen2.5-coder:7b`) com saída JSON estruturada e temperatura 0. O modelo julga cada critério da rubrica; a nota é calculada pelo sistema, não pelo modelo.

- Se o Ollama não responde, se o modelo não está instalado ou se a resposta vem fora do formato, a tela oferece autoavaliação guiada pela mesma rubrica, com a resposta de referência. Nada é gravado até a autoavaliação ser enviada.
- Aprovação por rubrica: pelo menos dois terços dos critérios.
- O cliente usa só `urllib` da biblioteca padrão.

### 6. XP que não dá para "farmar"

- **XP de competência** só na primeira aprovação de cada exercício. Escolha e digitada valem metade; autoavaliação vale metade; cada dica tira 25% (mínimo de 25%).
- **XP de atividade**: 2 por tentativa, só nas três primeiras de cada exercício.
- Resposta errada em quiz não revela o gabarito, senão bastaria errar e reenviar.
- Os dois tipos ficam em `xp_events`, separados, como pede o documento.

### 7. Exercício aprovado vira evidência de domínio

Aprovar promove as competências do módulo, **só para cima**:

| Aprovação | Evidência |
|---|---|
| código (testes) | consegue aplicar |
| escolha ou digitada | reconhece |
| texto corrigido pelo Ollama | consegue explicar (só se já estiver em "consegue aplicar"; senão, reconhece) |
| texto por autoavaliação | reconhece |

Esquecimento e queda de domínio ficam para a repetição espaçada (Fase 7).

### 8. Exercícios obrigatórios travam a conclusão do módulo

Cada módulo tem um exercício obrigatório. Concluir o módulo exige passar nele; os opcionais dão XP e evidência. Módulos sem exercício continuam como antes.

### 9. Editor no navegador

Uma `textarea` com fonte monoespaçada, Tab inserindo quatro espaços e Ctrl+Enter para enviar, sem biblioteca de editor. O rascunho é salvo sozinho (com atraso de ~1 s) em `workspace/` e também antes de qualquer ação que recarregue a página, como pedir uma dica.

### 10. Tentativa registra o que importa para autonomia

Cada tentativa guarda duração desde que o exercício foi aberto, dicas usadas, sessão de estudo ativa e a marcação honesta "usei IA nesta tentativa". São a base do índice de autonomia da Fase 6.

## Consequências

- Os testes de interface passaram a ser testes da API (`TestClient`), que é exatamente o que a tela chama.
- O frontend deixou de ser só leitura e cresceu; continua sem build step e sem framework, como no ADR 0002.
- Um banco da Fase 2 é atualizado sozinho na próxima abertura do `hone` (migração 0004).
