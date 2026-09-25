# Context engineering

> **Objetivo:** Montar o contexto de uma chamada de LLM decidindo o que entra, em que ordem e o que fica de fora, medindo tokens e cache em vez de chutar.

## Por que isso importa

Você já sabe o que acontece quando um programa trata memória como se fosse infinita: ele funciona no seu notebook com dez registros e cai em produção com dez milhões. A janela de contexto de um LLM é o mesmo tipo de recurso. Ela tem um teto rígido (1M tokens no Opus 5 e no Sonnet 5, 200K no Haiku 4.5), tem um preço por token e, diferente da RAM, ela também degrada a qualidade quando você a enche até a borda. Não existe swap. Existe só uma resposta pior e uma fatura maior.

A parte que surpreende quem vem de backend é que a API é sem estado. Cada chamada reenvia a conversa inteira: não existe sessão do lado do servidor guardando o histórico para você. Isso transforma "manter uma conversa longa" num problema de engenharia com custo mensurável, não numa conveniência. Context engineering é o trabalho de decidir o que ocupa esse espaço caro, em que ordem, e como reaproveitar o que já foi enviado. É a mesma disciplina de quem escolhe o que vai para o cache, o que vai para o disco e o que é recalculado. Só que aqui o cache tem regra de prefixo e você paga por byte desperdiçado.

## Conceitos

### A janela de contexto é um recurso escasso

Um token é aproximadamente um pedaço de palavra. Todo o contexto que você envia (instruções do sistema, definições de ferramentas, histórico, documentos, a pergunta) é convertido em tokens e cobrado como entrada; a saída é cobrada à parte e mais caro. Preços por 1M de tokens (entrada/saída): Opus 5 custa $5/$25, Sonnet 5 custa $2/$10, Haiku 4.5 custa $1/$5.

Pense na janela como um buffer de tamanho fixo que você aloca por chamada. Enchê-lo custa proporcionalmente mais, aumenta a latência e reduz a precisão. Esse terceiro ponto é o que engana.

### "Cabe" não é o mesmo que "deve entrar"

Com 1M de tokens, é tentador jogar o repositório inteiro na janela e deixar o modelo se virar. Não faça isso. Informação irrelevante compete com a informação relevante pela atenção do modelo. Um contexto com 200 mil tokens de documentação, dos quais 500 respondem a pergunta, produz uma resposta pior do que um contexto com só aqueles 500 tokens, e custa 400 vezes mais.

A pergunta certa não é "cabe?" e sim "isso aumenta a chance de uma resposta correta?". Se um trecho não aumenta, ele é ruído pago.

### O que colocar e em que ordem

A ordem de montagem de uma requisição é sempre a mesma: primeiro `tools`, depois `system`, depois `messages`. Dentro dessa estrutura, organize do mais estável para o mais volátil:

1. Definições de ferramentas, em ordem determinística.
2. Instruções de sistema que não mudam entre chamadas (papel, formato de saída, regras).
3. Conhecimento de fundo grande e estável (um manual, um esquema de banco).
4. Histórico da conversa.
5. A pergunta do usuário e qualquer coisa que muda a cada requisição.

Essa ordem não é estética. Ela é o que torna o cache de prompt utilizável.

### Cache de prompt: a regra do prefixo

O cache de prompt guarda o resultado do processamento de um prefixo do seu contexto, para reaproveitar na chamada seguinte. Você marca onde o prefixo termina com `cache_control={"type": "ephemeral"}`, seja de forma automática no topo da chamada, seja em blocos específicos de `system`.

A regra central: **o cache é por prefixo, e a comparação é byte a byte**. O sistema pega o conteúdo renderizado na ordem `tools` -> `system` -> `messages` e procura o maior prefixo idêntico ao que já está em cache. Um único byte diferente na posição 10 invalida tudo a partir dali, mesmo que os 200 mil tokens seguintes sejam idênticos.

A consequência prática é a regra de ordenação da seção anterior. Conteúdo estável vai primeiro porque ele é o que pode ser cacheado; conteúdo volátil vai por último porque ele é o que muda.

Economia: ler do cache custa cerca de 10% do preço normal de entrada. Escrever no cache custa cerca de 25% a mais que a entrada normal. Ou seja, o cache se paga a partir da segunda leitura. O TTL padrão é de 5 minutos, renovado a cada acesso; para janelas maiores, peça uma hora com `cache_control={"type": "ephemeral", "ttl": "1h"}`.

### Invalidadores silenciosos

Esta é a parte que consome tarde de debug. O cache falha em silêncio: você não recebe erro, só recebe uma fatura maior. Os culpados mais comuns:

- **Timestamp no system prompt.** Um `datetime.now()` interpolado em "Hoje é {data}" muda a cada segundo. Todo o prefixo depois dele morre.
- **JSON sem ordenação.** `json.dumps(d)` não garante ordem estável de chaves entre execuções de processos diferentes. Use `json.dumps(d, sort_keys=True)`.
- **Lista de ferramentas em ordem variável.** Se você monta `tools` a partir de um `set` ou de um dicionário construído dinamicamente, a ordem pode mudar. `tools` é o primeiro bloco renderizado, então isso invalida absolutamente tudo.
- **UUID de requisição, contador de sessão, número de tentativa** injetados no system.

O diagnóstico é sempre o mesmo: olhe `response.usage.cache_read_input_tokens`. Se ele é zero em chamadas repetidas que deveriam compartilhar prefixo, tem um invalidador ali.

### Conversa longa e o custo quadrático

Como a API é sem estado, cada turno reenvia o histórico inteiro. Isso tem uma assinatura de complexidade que você reconhece.

Seja `t` o tamanho médio em tokens de um turno. No turno 1 você envia `t`. No turno 2 envia `2t`. No turno `n`, envia `n·t`. O total acumulado ao longo de `n` turnos é `t·(1+2+...+n) = t·n·(n+1)/2`, que é **O(n²)**.

Uma conversa de 10 turnos custa 55 unidades de `t`. Uma de 100 turnos custa 5050, ou seja, 91 vezes mais para apenas 10 vezes mais interação. O cache amortiza bastante isso (as leituras saem a 10%), mas não muda a classe de complexidade. Conversas longas precisam de estratégia.

### Estratégias para conversa longa

Três abordagens, com trade-offs diferentes:

- **Resumir.** Você mesmo substitui os N turnos mais antigos por um resumo gerado por uma chamada auxiliar. Reduz tokens, mas perde detalhe e invalida o cache do trecho reescrito.
- **Descartar.** Manter apenas os últimos K turnos, em janela deslizante. Barato e previsível, mas o modelo simplesmente esquece o começo.
- **Deixar a API cuidar.** Existem dois recursos em beta, e eles são coisas **diferentes**: a *edição de contexto* limpa resultados antigos de ferramentas do histórico (apaga); a *compactação* resume automaticamente a conversa antiga (resume). Uma joga fora, a outra condensa.

Escolher entre elas é a mesma decisão de sempre: o que dá para perder.

## Na prática

Comece medindo. Nunca use `tiktoken` para modelos Claude: o tokenizador é outro e a contagem sai errada. A API tem um endpoint próprio.

```python
import anthropic

client = anthropic.Anthropic()

system_prompt = "Você é uma revisora de código Python. Aponte bugs, não estilo."
question = "Essa função usa recursão sem caso base. O que acontece?"

count = client.messages.count_tokens(
    model="claude-sonnet-5",
    system=system_prompt,
    messages=[{"role": "user", "content": question}],
)

print(count.input_tokens)
```

Saída aproximada: `47`. Com esse número você calcula o custo antes de gastar. A 1M tokens por $2 no Sonnet 5, 47 tokens de entrada custam $0.000094.

Agora um prompt montado com cache correto. O documento grande e as instruções são estáveis e vêm primeiro; a pergunta é volátil e vem por último, em `messages`.

```python
import anthropic

client = anthropic.Anthropic()

MANUAL = open("manual.md", encoding="utf-8").read()


def ask(question: str):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[
            {"type": "text", "text": "Responda apenas com base no manual abaixo."},
            {
                "type": "text",
                "text": MANUAL,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": question}],
    )


first = ask("Como configuro o timeout?")
second = ask("E o número de tentativas?")

print(first.usage.cache_creation_input_tokens, first.usage.cache_read_input_tokens)
print(second.usage.cache_creation_input_tokens, second.usage.cache_read_input_tokens)
```

Saída esperada, para um manual de cerca de 8 mil tokens:

```
8213 0
0 8213
```

A primeira chamada escreve no cache (pagando 25% a mais por aqueles tokens). A segunda lê (pagando 10%). O marcador `cache_control` fica no último bloco estável: tudo antes dele é o prefixo cacheado.

Note que `response.content` é uma **lista de blocos**, não uma string. Cada bloco tem `.type`. Sempre cheque antes de ler `.text`, porque um bloco pode ser de outro tipo:

```python
for block in first.content:
    if block.type == "text":
        print(block.text)
```

Agora o erro. Um `datetime.now()` no system prompt, algo que parece inofensivo:

```python
import anthropic
from datetime import datetime

client = anthropic.Anthropic()

MANUAL = open("manual.md", encoding="utf-8").read()


def ask_broken(question: str):
    return client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[
            {"type": "text", "text": f"Hoje é {datetime.now().isoformat()}."},
            {"type": "text", "text": "Responda apenas com base no manual abaixo."},
            {
                "type": "text",
                "text": MANUAL,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": question}],
    )


a = ask_broken("Como configuro o timeout?")
b = ask_broken("E o número de tentativas?")

print(a.usage.cache_read_input_tokens, b.usage.cache_read_input_tokens)
```

Saída:

```
0 0
```

O timestamp está no **primeiro** bloco, antes do manual. Como o prefixo mudou, o cache do manual inteiro é descartado, e você paga 25% a mais em todas as chamadas em vez de 10%. O conteúdo da resposta continua correto, e é por isso que esse bug sobrevive tanto tempo: ele só aparece na fatura.

A correção é mover o volátil para o fim, para depois do ponto de cache:

```python
messages = [{"role": "user", "content": f"Hoje é {datetime.now().date()}.\n\n{question}"}]
```

Uma verificação que vale automatizar: rode a mesma chamada duas vezes seguidas e afirme que a segunda tem `cache_read_input_tokens > 0`. Isso vira um teste de regressão de custo.

## Armadilhas comuns

- **Confundir "cabe na janela" com "deve ir para a janela".** Contexto irrelevante piora a resposta e multiplica o custo. Encher 1M de tokens porque você pode é o equivalente a alocar um array de um milhão de posições para guardar três valores.
- **Usar `tiktoken` para contar tokens do Claude.** O tokenizador é diferente. A contagem sai errada e você planeja custo em cima de um número falso. Use `client.messages.count_tokens`.
- **Colocar conteúdo volátil antes do estável.** Timestamp, UUID ou id de requisição no começo do `system` invalidam todo o prefixo. O cache morre em silêncio e nada no código indica isso.
- **Assumir que a API guarda a conversa.** Ela é sem estado. Se você não reenviar o histórico, o modelo não tem histórico. E se reenviar sem estratégia, o custo acumulado cresce O(n²).
- **Não olhar `usage` nunca.** `cache_read_input_tokens` e `cache_creation_input_tokens` são a única evidência de que o cache funciona. Sem logar isso, você está otimizando no escuro.
- **Achar que compactação e edição de contexto são a mesma coisa.** Edição de contexto apaga resultados antigos de ferramentas; compactação resume a conversa. Escolher a errada faz você perder informação que precisava, ou manter ruído que queria descartar.

## Recuperação ativa

1. Por que um contexto de 200 mil tokens pode produzir uma resposta pior que um de 2 mil, mesmo quando a informação necessária está nos dois?
2. Você adicionou um campo novo ao final do seu system prompt e a taxa de acerto do cache caiu a zero. Explique por que a posição do campo importa e como você confirmaria a causa com uma única métrica.
3. Deduza, sem olhar o texto, o custo acumulado em tokens de uma conversa de `n` turnos com turnos de tamanho `t`. Qual a classe de complexidade e por que o cache não a altera?
4. Um colega diz que vai ordenar a lista de `tools` alfabeticamente "para ficar organizado", mas ela era gerada a partir de um dicionário. Isso melhora ou piora o cache? Por quê?
5. Quando vale a pena pagar os 25% a mais de escrita no cache? Monte o raciocínio em número de chamadas.
6. Explique para alguém de backend a diferença entre compactação e edição de contexto, e dê um caso em que escolher a errada causa perda de informação.
7. Você tem um assistente que responde sobre um manual de 50 mil tokens, chamado por 30 usuários diferentes por minuto. Como você organiza a requisição para maximizar o reaproveitamento de cache entre usuários?

## Para ir além

- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — documentação oficial, com os limites mínimos de prefixo cacheável e a hierarquia de invalidação.
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) — o endpoint `count_tokens` e por que não usar tokenizadores de outros provedores.
- [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) — como a janela é consumida por sistema, ferramentas, histórico e saída.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — ensaio de engenharia da Anthropic sobre curadoria de contexto em agentes de longa duração.
