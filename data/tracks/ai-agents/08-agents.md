# Agentes

> **Objetivo:** Decidir com critério quando uma tarefa merece um agente, construir o laço com limites e observabilidade, e reconhecer os casos em que um workflow determinístico simplesmente ganha.

## Por que isso importa

"Agente" virou palavra de marketing, então vale fixar a definição técnica antes de qualquer coisa: um agente é um laço em que o **modelo** decide a próxima ação, repetidamente, até julgar que terminou. Num workflow, quem decide a sequência é o seu código — você chama o modelo três vezes, em ordem fixa, e cada resposta alimenta a próxima etapa. Mesmo SDK, mesmas ferramentas, arquitetura completamente diferente. A pergunta não é "como faço um agente", é "quem precisa decidir a sequência aqui, eu ou o modelo".

Essa escolha tem consequência direta em duas coisas que você já leva a sério: custo e depurabilidade. Um workflow tem número de chamadas conhecido, caminho previsível e stack trace útil. Um agente tem número de voltas desconhecido, histórico que cresce a cada volta e uma trajetória que você só entende se tiver instrumentado. A moda de resolver tudo com agente custa caro e, na maior parte dos casos, entrega resultado pior do que três chamadas encadeadas bem escritas. Saber quando não usar é a competência, não o contrário.

## Conceitos

### Workflow e agente: quem decide a sequência

No workflow, o controle de fluxo é seu. Você escreve algo como: extrair os campos do documento, depois classificar o tipo, depois gerar o resumo com o template daquele tipo. Se a classificação falhar, você sabe exatamente em qual das três chamadas. O modelo é um componente com entrada e saída dentro de uma função que você projetou.

No agente, você dá as ferramentas e o objetivo, e o modelo escolhe. Ele pode ler o documento primeiro, ou buscar contexto antes, ou decidir que precisa de mais uma consulta. O laço continua enquanto `stop_reason` for `tool_use`, sem número fixo de voltas. A capacidade que você ganha é lidar com tarefas cujo caminho não dá para escrever de antemão. O preço é que você não sabe mais o caminho.

### Os quatro critérios

Antes de escolher a arquitetura de agente, passe pelos quatro:

- **Complexidade da tarefa.** É realmente multi-etapa e difícil de especificar antes? "Transformar este design doc em um PR" é. "Extrair o CNPJ deste PDF" não é.
- **Valor do resultado.** O resultado justifica latência e custo maiores? Um agente pode custar dez a cinquenta vezes uma chamada única.
- **Viabilidade.** O modelo é bom nesse tipo de tarefa hoje? Se ele erra 40% das etapas individuais, vinte etapas encadeadas não produzem nada aproveitável.
- **Custo do erro.** O erro é detectável e reversível? Teste que falha, review, rollback são redes de segurança. Transferência bancária executada não é.

Se a resposta for "não" a qualquer um deles, fique no nível mais simples. E comece sempre pelo mais simples: chamada única, depois workflow, e só então agente. A ordem inversa gasta semanas para chegar num lugar pior.

### O laço de agente

Estruturalmente é o mesmo laço de tool calling do módulo anterior: chama, checa `stop_reason`, executa as ferramentas, devolve os `tool_result`, repete. A diferença é a ausência de um número fixo de voltas e a presença de um objetivo aberto no prompt inicial em vez de uma instrução pontual.

Isso significa que tudo que você aprendeu sobre validação de entrada, `is_error` e paralelismo continua valendo — e passa a valer mais, porque agora o modelo tem mais oportunidades de errar. Um erro de validação que você toleraria numa chamada é um erro que se repete vinte vezes num agente.

### Por que o custo explode

A API é **sem estado**. Cada volta do laço reenvia o histórico inteiro: prompt de sistema, definições de ferramentas, todas as mensagens anteriores, todos os `tool_result` acumulados. Numa conversa de uma volta isso é irrelevante. Num agente de vinte voltas, o crescimento dos tokens de entrada é aproximadamente quadrático em relação ao número de voltas, e domina a conta.

Some a isso que as voltas também geram pensamento (tokens de saída, os mais caros) e que resultados de ferramenta podem ser grandes — o conteúdo de um arquivo, uma resposta de API inteira. Um agente que lê cinco arquivos de 20 mil tokens carrega 100 mil tokens de entrada em **toda** volta subsequente. Em Opus 5, a $5 por 1M de tokens de entrada, dez voltas assim já são meio dólar só de reenvio.

Os controles que funcionam:

- **Limite de voltas no seu código.** Não é opcional. É a diferença entre um bug caro e um bug catastrófico.
- **Orçamento de tarefa** (beta): `output_config={"task_budget": {"type": "tokens", "total": N}}`, mínimo 20.000. É um teto **advisório** que o modelo enxerga e usa para se organizar — ele termina com elegância em vez de ser cortado. Diferente de `max_tokens`, que é um corte forçado que o modelo não vê chegando.
- **Esforço menor**: `output_config={"effort": "low"}` para subtarefas mecânicas.
- **Modelo mais barato para subtarefas.** Haiku 4.5 custa $1/$5 por 1M contra $5/$25 do Opus 5. Se a subtarefa é extrair campos de um texto, não precisa do modelo mais caro.

### O erro que se propaga

Este é o problema estrutural dos agentes e não tem solução completa. Numa chamada única, um erro é uma resposta ruim que você descarta. Num agente, uma decisão errada na volta 3 entra no histórico como fato e condiciona as voltas 4 a 15. O modelo lê o próprio passo errado como contexto confiável e constrói em cima dele.

Isso muda como você mede qualidade. Acurácia por chamada não diz quase nada: 95% de acerto por passo, em vinte passos, é 36% de chance de a trajetória inteira sair limpa. As mitigações práticas são reduzir o número de passos, tornar as ferramentas mais difíceis de usar errado (validação estrita, mensagens de erro que orientam), e colocar checkpoints — um ponto do laço em que o seu código, não o modelo, verifica se o estado ainda faz sentido.

### Observabilidade é requisito

Um agente sem instrumentação é uma caixa preta cara. Você precisa registrar, por volta: número da volta, `stop_reason`, quais ferramentas foram chamadas com quais argumentos, se deram erro, e `usage.input_tokens` / `usage.output_tokens`.

Isso não é luxo de produção, é o que torna o desenvolvimento possível. Sem esse log você não consegue responder "por que ele fez isso", "onde começou a dar errado" nem "por que a conta veio nesse valor". Com ele, a trajetória vira um artefato que você lê como lê um stack trace. Trate esse log como você trataria log estruturado de qualquer serviço: campos fixos, um registro por volta, agregável depois.

### Quando o workflow ganha

Se você consegue escrever a sequência de passos, escreva. O workflow ganha quando o caminho é conhecido, quando o custo previsível importa, quando você precisa reproduzir o comportamento, e quando latência é sensível. Ele também é mais fácil de avaliar: cada etapa tem entrada e saída definidas, então cada etapa tem teste.

A checagem honesta é esta: se você consegue desenhar o fluxograma da tarefa sem losangos que dependem de julgamento aberto, você não precisa de agente. Precisa de três funções.

## Na prática

Um agente mínimo, à mão, com as duas coisas que sempre faltam: teto de voltas e registro de custo.

```python
import json
import anthropic

client = anthropic.Anthropic()

PRICING = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

DOCS = {
    "guia-fiscal": "Notas fiscais vencem em 30 dias. Multa de 2% apos o vencimento.",
    "guia-rh": "Ferias sao solicitadas com 45 dias de antecedencia.",
}

SEARCH_DOCS = {
    "name": "search_docs",
    "description": (
        "Busca o conteudo de um documento interno pelo seu slug. "
        "Slugs validos: 'guia-fiscal', 'guia-rh'. Retorna erro se o slug nao existe."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"slug": {"type": "string", "description": "Slug do documento."}},
        "required": ["slug"],
        "additionalProperties": False,
    },
    "strict": True,
}


def search_docs(slug: str) -> str:
    if slug not in DOCS:
        raise ValueError(f"Documento {slug!r} nao existe. Validos: {sorted(DOCS)}.")
    return DOCS[slug]
```

O agente em si. O contador de voltas e o acumulador de custo são parte da função, não um `print` que você adiciona depois para debugar.

```python
def run_agent(goal: str, model: str = "claude-sonnet-5", max_turns: int = 8) -> dict:
    messages = [{"role": "user", "content": goal}]
    trace, cost_usd = [], 0.0
    price_in, price_out = PRICING[model]

    for turn in range(1, max_turns + 1):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            tools=[SEARCH_DOCS],
            messages=messages,
        )
        usage = response.usage
        cost_usd += (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000

        calls = [b for b in response.content if b.type == "tool_use"]
        trace.append(
            {
                "turn": turn,
                "stop_reason": response.stop_reason,
                "tools": [{"name": b.name, "input": b.input} for b in calls],
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": round(cost_usd, 6),
            }
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return {
                "status": "done",
                "answer": text,
                "turns": turn,
                "cost_usd": cost_usd,
                "trace": trace,
            }

        results = []
        for block in calls:
            try:
                content, is_error = search_docs(**block.input), False
            except Exception as exc:
                content, is_error = str(exc), True
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": results})

    return {"status": "turn_limit", "turns": max_turns, "cost_usd": cost_usd, "trace": trace}


result = run_agent("Em quantos dias vence uma nota fiscal e qual a multa por atraso?")
print(result["status"], result["turns"], f"${result['cost_usd']:.4f}")
print(json.dumps(result["trace"], indent=2, ensure_ascii=False))
```

Repare que `status` distingue `done` de `turn_limit`. Um agente que estourou o teto não é um agente que terminou, e o chamador precisa poder tratar isso diferente.

Agora o comparativo. A tarefa: classificar um chamado de suporte e gerar uma resposta no tom adequado àquela categoria. Como workflow, o seu código decide a sequência:

```python
def classify_then_reply(ticket: str) -> dict:
    classification = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=64,
        system="Classifique o chamado em exatamente uma palavra: cobranca, tecnico ou outro.",
        messages=[{"role": "user", "content": ticket}],
    )
    category = classification.content[0].text.strip().lower()
    if category not in {"cobranca", "tecnico", "outro"}:
        category = "outro"

    tone = {
        "cobranca": "Seja formal, cite prazos e nao prometa estorno.",
        "tecnico": "Peca logs e versao do sistema antes de sugerir solucao.",
        "outro": "Agradeca e encaminhe para triagem humana.",
    }[category]

    reply = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        system=f"Escreva uma resposta ao cliente. {tone}",
        messages=[{"role": "user", "content": ticket}],
    )
    return {"category": category, "reply": reply.content[0].text}
```

Duas chamadas, número fixo, modelo barato na etapa mecânica, fallback determinístico quando a classificação sai fora do conjunto esperado. O caminho é legível na função. Cada etapa é testável isoladamente: você consegue escrever um teste que passa um chamado de cobrança e verifica `category == "cobranca"` sem tocar na segunda chamada.

A mesma tarefa como agente seria `run_agent` com uma ferramenta `get_tone_guide(category)` e o objetivo "classifique este chamado e responda no tom certo". Funciona. E custa mais: o modelo gasta uma volta decidindo classificar, uma chamando a ferramenta, uma escrevendo — três requisições em vez de duas, cada uma reenviando o histórico acumulado, todas no modelo caro porque o laço usa um modelo só. Você também perde o fallback determinístico: se o modelo inventar uma categoria, não há `if` para corrigir. E perde o teste por etapa, porque não existem mais etapas fixas para testar.

O agente aqui não compra nada. A sequência era conhecida desde o começo — é exatamente o caso em que o workflow ganha.

## Armadilhas comuns

- **Começar pelo agente.** A ordem é chamada única, workflow, agente. Pular etapas leva semanas até você descobrir que duas chamadas encadeadas resolviam.
- **Laço sem teto de voltas.** Um modelo em ciclo gasta dinheiro real em silêncio. Teto no seu código, sempre, e status diferente quando ele é atingido.
- **Confundir `task_budget` com `max_tokens`.** O primeiro é advisório e o modelo enxerga, então ele se organiza para terminar. O segundo é corte forçado e invisível: a resposta simplesmente trunca no meio.
- **Ignorar que o histórico é reenviado.** Um `tool_result` gigante na volta 2 é pago de novo em todas as voltas seguintes. Trunque ou resuma resultados grandes antes de devolver.
- **Medir acurácia por chamada.** 95% por passo em vinte passos é 36% de trajetória limpa. O que importa é a taxa de sucesso da tarefa inteira.
- **Instrumentar depois.** Sem log por volta, "por que ele fez isso" é impossível de responder e você acaba reconstruindo o agente no escuro.
- **Um modelo caro para o laço inteiro.** Subtarefas mecânicas rodam em Haiku 4.5 ou com `effort: "low"` sem perda perceptível.

## Recuperação ativa

1. Explique a diferença entre workflow e agente para alguém que já programa, sem usar a palavra "autônomo". Qual é a única pergunta que decide entre os dois?
2. Percorra os quatro critérios para uma tarefa real do seu trabalho. Em qual deles ela falha, e o que você construiria no lugar?
3. Por que o custo de um agente cresce mais rápido que o número de voltas? Estime, em ordem de grandeza, o custo de vinte voltas com 30 mil tokens de contexto acumulado em Opus 5.
4. Um agente acerta 95% de cada passo individual. Ele executa quinze passos. Qual a chance de a trajetória inteira sair correta, e o que essa conta muda na sua arquitetura?
5. Diferencie `max_tokens`, `output_config.effort` e `task_budget`: o que cada um controla e qual deles o modelo enxerga durante a geração.
6. Desenhe os campos mínimos do log de uma volta de agente e explique qual pergunta de depuração cada campo responde.
7. Descreva uma tarefa em que o agente genuinamente ganha do workflow e diga exatamente qual propriedade da tarefa torna a sequência impossível de escrever antes.

## Para ir além

- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — os padrões de workflow (chaining, routing, orquestração) antes de recorrer ao agente.
- [Agent SDK e o laço de agente](https://platform.claude.com/docs/en/agents-and-tools/agent-sdk/overview) — como a Anthropic estrutura o laço quando ele já vem pronto.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — o que fazer quando o histórico reenviado vira o gargalo de custo.
- [Task budgets](https://platform.claude.com/docs/en/build-with-claude/task-budgets) — referência do teto advisório e de como ele difere de `max_tokens`.
