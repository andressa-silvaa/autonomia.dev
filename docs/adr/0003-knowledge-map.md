# ADR 0003 — Diagnóstico e mapa de conhecimento (Fase 2)

- **Data:** 2026-09-24
- **Status:** aceita

## Contexto

A Fase 2 pede diagnóstico inicial, estados de domínio, grafo de pré-requisitos com NetworkX, geração de lacunas e recomendação de sequência. As decisões abaixo foram aprovadas pela criadora antes da implementação.

## Decisões

### 1. Perguntas em arquivos, como o resto do conteúdo

As perguntas ficam em `data/diagnostics/*.toml` e entram no banco pelo mesmo `hone content sync`, com a mesma validação e a mesma transação única. Uma pergunta é de escolha (`options` + `answer`, com o número da alternativa certa) ou digitada (`accept`, com as respostas aceitas).

- Na hora de gravar, a alternativa certa vira texto. Assim a correção é uma só para os dois formatos: comparar a resposta com a lista de respostas aceitas.
- Respostas digitadas são comparadas sem espaços e sem diferença de maiúsculas (`n-1` vale o mesmo que `N - 1`).
- `options` e `accepted_answers` ficam em JSON dentro de colunas TEXT. São listas pequenas, sempre lidas inteiras, e não justificam uma tabela.
- Uma pergunta que some dos arquivos não é apagada, porque isso levaria junto as respostas antigas. Ela fica com `retired = 1` e sai dos próximos diagnósticos.
- `kind` não tem CHECK no SQL, pelo mesmo motivo de `exercises.kind` (ADR 0001): a validação fica no enum `QuestionKind`.

### 2. Tabelas próprias, separadas de `exercises` e `attempts`

`exercises` pertence a um módulo; uma pergunta de diagnóstico pertence a uma competência. Misturar as duas coisas complicaria a Fase 3. Por isso existem `diagnostic_questions`, `diagnostic_runs` e `diagnostic_answers`.

- Um índice único parcial garante no máximo um diagnóstico aberto por pessoa, como nas sessões de estudo.
- Cada resposta é gravada na hora. Parar no meio (digitando "pausar" ou com Ctrl+C) não perde nada, e `hone diagnostic start` continua de onde parou.

### 3. Confiança faz parte da resposta

Depois de cada resposta, o sistema pergunta se foi certeza ou chute. "Não sei" é uma resposta válida e não pede confiança. Um acerto no chute conta menos, porque a pergunta central do sistema é sobre autonomia, e acertar sem saber não é autonomia.

### 4. Regras simples para transformar respostas em domínio

Para cada competência, a partir das respostas daquela rodada:

| Resultado | Regra |
|---|---|
| consegue aplicar | pelo menos metade das respostas certas com certeza **e** todas as perguntas de código certas com certeza |
| reconhece | pelo menos metade das respostas certas com certeza |
| começando | pelo menos um acerto, mesmo no chute |
| desconhecido | nenhum acerto |

Perguntas de leitura de código, debugging e completar código contam como aplicação; perguntas de conceito, só como reconhecimento.

O diagnóstico nunca dá "consegue explicar" ou acima: isso exige explicar ou ensinar, e só será medido com o Modo Professor (Fase 7). Pelo mesmo motivo, se uma competência já estiver acima de "consegue aplicar", o diagnóstico não mexe nela.

### 5. Histórico de domínio em `mastery_events`

Toda mudança de domínio grava de onde veio, para onde foi, a origem (`diagnostic`) e o id da origem. `user_competencies` guarda só o estado atual. O histórico alimenta o relatório do diagnóstico agora e as métricas de retenção e evolução nas próximas fases. `source` não tem CHECK, porque novas origens (exercícios, revisões) vão surgir.

### 6. O diagnóstico informa, não destrava

Um resultado "consegue aplicar" não marca o módulo como concluído. O caminho mostra "o diagnóstico diz que você já aplica isto", e a criadora decide se roda `hone done`. A trava de progresso continua exigindo módulos concluídos. Pular conteúdo automaticamente com evidência suficiente é assunto do currículo adaptativo (Fase 7).

### 7. NetworkX para o caminho, `graphlib` para validar

O grafo é montado em memória a cada consulta, a partir de `module_prerequisites`, que já é a "snapshot em tabelas SQLite" pedida no documento de requisitos.

- `nx.ancestors` encontra todos os pré-requisitos, diretos e indiretos, do objetivo.
- `nx.lexicographical_topological_sort` ordena o caminho respeitando os pré-requisitos e, em caso de empate, a ordem do módulo na trilha.
- `nx.topological_generations` agrupa os módulos por nível para o dashboard.
- A detecção de ciclos no `content sync` continua com `graphlib`, que já funcionava, tem testes e não precisa de dependência.

### 8. Um objetivo por vez

`user_goals` guarda um único módulo-objetivo. Com objetivo, "continue daqui" (no terminal e no dashboard) passa a sugerir os módulos abertos do caminho, em vez da ordem das trilhas.

### 9. O que conta como lacuna

- **Com objetivo:** toda competência abaixo de "consegue aplicar" nos módulos do caminho. Em módulos já concluídos, só entra se o diagnóstico tiver avaliado a competência e ela estiver fraca. Concluir um módulo ainda não gera evidência de domínio; isso começa com os exercícios da Fase 3.
- **Sem objetivo:** só as competências que o diagnóstico avaliou e que ficaram abaixo de "consegue aplicar". Competências nunca estudadas não aparecem, para não encher a tela de coisas que simplesmente ainda não chegaram.

### 10. Perguntas abertas ficam para a Fase 3

Implementar do zero, testes, arquitetura e projeto prático precisam de correção por Ollama ou execução de código, que chegam nas Fases 3 e 4. Nesta fase, o diagnóstico cobre só o que o sistema corrige sozinho, e só a trilha de Fundamentos de CS, a única com conteúdo.

## Consequências

- Adicionar perguntas é editar `data/diagnostics/` e rodar `hone content sync`.
- Um novo diagnóstico sempre passa por todas as perguntas ativas. Rediagnosticar uma competência só fica para quando houver revisões (Fase 7).
- Um banco da Fase 1 precisa de `hone db init` para receber a migração 0003. Os dados existentes são preservados.
