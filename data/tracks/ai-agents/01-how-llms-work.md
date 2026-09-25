# Como um LLM funciona

> **Objetivo:** explicar o que acontece entre a sua chamada de API e o texto que volta, para prever o comportamento do modelo em vez de se surpreender com ele.

## Por que isso importa

Você já estudou o suficiente de fundamentos para saber que "o computador executa o programa" é uma frase vazia até você abrir a caixa: existe uma stack com tamanho fixo, existe heap, existe custo por operação. Com LLM acontece a mesma coisa. Quem trata o modelo como uma caixa mágica que "entende" texto fica preso num ciclo de superstição: muda uma palavra do prompt, a resposta melhora por acaso, e essa palavra vira lenda no time. Quem entende o mecanismo consegue responder perguntas de engenharia de verdade: por que essa conversa está custando dez vezes mais que a outra, por que o mesmo input gera saídas diferentes, por que o modelo inventou um método que não existe na sua biblioteca.

Nada do que vem a seguir é sobre treinar modelos. É sobre o que você precisa saber para usar um como componente de sistema, do mesmo jeito que você usa um banco de dados sem saber escrever um B-tree do zero, mas sabendo o suficiente sobre índices para não escrever uma query idiota. O modelo tem um limite físico de memória por chamada, um custo proporcional à quantidade de dados que você manda, um comportamento não determinístico por design e uma forma específica de errar. Esses quatro fatos explicam quase tudo.

## Conceitos

### Token: a unidade real de processamento

O modelo não lê caracteres e não lê palavras. Ele lê **tokens**: pedaços de texto que um algoritmo de tokenização produziu a partir de estatísticas do corpus de treino. Um token pode ser uma palavra inteira comum, um pedaço de palavra, um espaço em branco, um sinal de pontuação.

"Palavra" é a abstração errada por dois motivos. Primeiro, porque a fronteira não coincide: `desenvolvedora` pode virar três ou quatro tokens, enquanto `the` é sempre um. Segundo, porque todo custo e todo limite do sistema são contados em tokens, não em palavras. Se você raciocina em palavras, erra o orçamento.

Isso tem consequência direta para você: **português custa mais tokens que inglês para dizer a mesma coisa**. Acentos, cedilha e palavras mais longas fazem o tokenizador quebrar mais. Em inglês, a regra de bolso histórica é 1 token para cada 3 a 4 caracteres; em português a proporção piora. Mais adiante você vai medir isso em vez de acreditar em mim.

### Previsão do próximo token

O modelo faz uma coisa só: dada a sequência de tokens até agora, produz uma distribuição de probabilidade sobre qual é o próximo token. Aí um token é escolhido, anexado à sequência, e o processo repete. Gerar 500 tokens de resposta são 500 passadas pelo modelo.

Pense na complexidade: cada passada custa em função do tamanho da sequência inteira. É por isso que conversas longas ficam lentas e caras de forma não linear, e é por isso que gerar (saída) custa mais caro por token do que ler (entrada) na tabela de preços.

Não existe uma etapa de "planejamento" separada onde o modelo decide a resposta inteira e depois escreve. A estrutura da resposta emerge token a token. Guarde isso: metade das técnicas de prompting derivam desse fato.

### Amostragem: por que a saída muda a cada chamada

Se o modelo devolve uma distribuição de probabilidade, alguém precisa escolher. Escolher sempre o token mais provável (chamado de *greedy*) produz texto repetitivo e sem graça. Por isso a escolha é uma **amostragem** da distribuição: tokens mais prováveis têm mais chance, mas não são certeza.

O parâmetro que historicamente controlava o achatamento dessa distribuição é a **temperatura**. Temperatura baixa concentra a probabilidade nos candidatos mais fortes; temperatura alta espalha. Nos modelos Claude atuais (Opus 5, Sonnet 5), os parâmetros de amostragem foram removidos da API: você não passa `temperature`. O controle que sobrou é o de esforço, que você vai ver no módulo de prompting.

O ponto de engenharia é este: **saída diferente para o mesmo input não é bug**. É a definição do componente. Se o seu sistema precisa de determinismo, o determinismo tem que vir do seu lado: schema validado, teste sobre a estrutura e não sobre o texto exato, e um conjunto de avaliação que meça taxa de acerto em vez de comparar strings. Escrever um teste que compara a resposta do modelo com uma string fixa é escrever um teste que vai falhar amanhã.

### Janela de contexto: um limite físico, não uma sugestão

Toda chamada tem um orçamento total de tokens: o que você manda mais o que o modelo gera. Esse orçamento é a **janela de contexto**. No Claude Opus 5 e no Sonnet 5 ela é de 1M tokens; no Haiku 4.5, 200K.

A analogia que serve para você é a stack. A stack tem tamanho fixo, definido antes de o programa rodar; você não "pede mais stack" no meio da execução, e estourar o limite não degrada o desempenho, aborta. A janela de contexto é igual: é um espaço fixo por chamada, e o que não cabe não entra. A diferença importante é que a stack cresce e encolhe conforme as chamadas retornam, enquanto a janela de contexto de uma conversa só cresce, porque cada turno é anexado ao histórico.

Dentro da janela, a informação não é hierarquizada como na sua cabeça. Está tudo lá, plano. O modelo não tem um índice que diga "isto aqui é a regra de negócio importante, isto é ruído". Gerenciar o que entra é trabalho seu, e é o assunto do módulo de context engineering.

### A API é sem estado

Esta é a parte que mais surpreende quem vem de software tradicional. O endpoint de mensagens **não guarda a sua conversa**. Não existe sessão no servidor. Quando você manda o quinto turno de um diálogo, você está mandando de novo, por inteiro, os quatro turnos anteriores mais o novo.

Some as consequências:

- Conversas longas crescem em custo de forma quadrática. Se cada turno adiciona N tokens, o turno k reenvia k×N tokens. Dez turnos de 2.000 tokens não custam 20.000 tokens de entrada; custam cerca de 110.000.
- Manter o histórico é responsabilidade do seu código. Uma lista `messages` em Python é o seu banco de dados de conversa.
- Cortar o histórico é uma decisão de arquitetura, não um detalhe. Cortar o começo apaga as instruções; cortar o meio quebra referências.

O cache de prompt existe justamente para mitigar isso: você marca um prefixo estável com `cache_control={"type": "ephemeral"}` e as chamadas seguintes leem esse prefixo do cache, muito mais barato. O detalhe crítico é que **o cache é por prefixo**: qualquer byte que mude no começo invalida tudo que vem depois. Colocar `datetime.now()` no início do prompt de sistema derruba 100% do cache e ninguém percebe, porque não dá erro, só chega uma fatura maior. A forma de verificar é ler `response.usage.cache_read_input_tokens`: se ele vem zero em chamadas que deveriam bater no cache, existe um invalidador silencioso.

### Alucinação é consequência do mecanismo

Um modelo que prevê o próximo token mais provável vai, diante de uma pergunta sobre algo que ele não sabe, produzir a continuação mais plausível. Plausível não é o mesmo que verdadeiro. O resultado é um nome de função que soa perfeito para aquela biblioteca, com assinatura coerente, que simplesmente não existe.

Repare que isso não é um defeito a ser corrigido com uma frase no prompt. Escrever "não invente informações" reduz a frequência em alguns casos, porque empurra a distribuição para respostas mais cautelosas, mas não muda a natureza do processo. **Não existe prompt que transforme previsão de token em verificação de fato.**

A conclusão de engenharia é arquitetural. Onde a correção importa, você não pede confiabilidade ao modelo; você constrói verificação em volta dele: schema validado, execução do código gerado, comparação com uma fonte de verdade, citação de trecho recuperado. É a mesma postura de quem nunca confia num input de usuário.

### Corte de conhecimento

O modelo foi treinado com dados até uma certa data, o **training cutoff**. Depois disso ele não sabe nada, e o mais perigoso é que ele não sabe que não sabe: sobre uma biblioteca lançada depois do corte, ele vai gerar a continuação plausível com base em bibliotecas parecidas.

Isso atinge você em cheio no trabalho diário, porque a coisa que mais muda rápido é exatamente API de framework. É por isso que RAG e ferramentas de busca existem: colocar a informação atual dentro da janela de contexto em vez de esperar que ela esteja nos pesos.

## Na prática

A instalação e o cliente. A biblioteca lê a chave da variável de ambiente `ANTHROPIC_API_KEY`, então o construtor não recebe argumento nenhum.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explique em duas frases o que é um token."}],
)
```

O erro mais comum de quem começa é escrever `response.content[0].text` e seguir a vida. `response.content` é uma **lista de blocos**, e cada bloco tem um `.type` que pode ser `text`, `thinking` ou `tool_use`. Com pensamento estendido ligado, o bloco zero é um `thinking` e o seu `.text` não existe: você toma um `AttributeError` em produção. Sempre filtre por tipo.

```python
for block in response.content:
    if block.type == "text":
        print(block.text)
```

Vale ler também os dois campos que informam o que aconteceu. `usage` traz o consumo real, que é o que a fatura vai cobrar, e `stop_reason` diz por que o modelo parou.

```python
print(response.usage.input_tokens, response.usage.output_tokens)
print(response.stop_reason)
```

`stop_reason` vale `end_turn` quando o modelo terminou naturalmente, `max_tokens` quando ele bateu no teto que você definiu e foi cortado no meio, `tool_use` quando ele quer chamar uma ferramenta e `refusal` quando ele recusou a tarefa. Tratar `max_tokens` como se fosse `end_turn` é como ignorar o retorno de um `read()`: você processa um texto truncado achando que está completo.

Agora a medição do custo em tokens. Nunca use `tiktoken` nem estimativa por caracteres para modelos Claude: cada família de modelo tem o seu tokenizador, e a única resposta certa vem do endpoint de contagem.

```python
def count(text: str) -> int:
    result = client.messages.count_tokens(
        model="claude-sonnet-5",
        messages=[{"role": "user", "content": text}],
    )
    return result.input_tokens


english = "The quick brown fox jumps over the lazy dog every single morning."
portuguese = "A rápida raposa marrom pula sobre o cão preguiçoso toda santa manhã."

for label, text in [("en", english), ("pt", portuguese)]:
    tokens = count(text)
    print(f"{label}: {len(text)} chars, {tokens} tokens, {len(text) / tokens:.2f} chars/token")
```

A saída tem a forma abaixo (os números exatos variam por modelo, a diferença entre os idiomas não):

```text
en: 66 chars, 22 tokens, 3.00 chars/token
pt: 68 chars, 30 tokens, 2.27 chars/token
```

Menos caracteres por token significa mais tokens para o mesmo conteúdo, e mais tokens significa mais dinheiro e mais espaço ocupado na janela. Com Sonnet 5 a $2 por 1M tokens de entrada, essa diferença é irrelevante numa chamada e relevante num prompt de sistema de 5.000 tokens que roda um milhão de vezes.

Por fim, o custo de uma conversa. Esta função deixa visível o crescimento quadrático que o estado do lado do cliente provoca.

```python
history = []


def send(user_text: str) -> str:
    history.append({"role": "user", "content": user_text})
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=history,
    )
    reply = "".join(b.text for b in response.content if b.type == "text")
    history.append({"role": "assistant", "content": reply})
    print(f"turno {len(history) // 2}: entrada={response.usage.input_tokens}")
    return reply
```

Rode três turnos e olhe a coluna de entrada. Ela não é constante, ela sobe a cada turno, porque a cada chamada o histórico inteiro sobe de novo pela rede.

## Armadilhas comuns

- **Ler `response.content[0].text` sem checar `.type`.** Com pensamento estendido o primeiro bloco é `thinking` e o código quebra com `AttributeError` só em produção, nunca no teste que você rodou sem thinking.
- **Ignorar `stop_reason`.** Um `max_tokens` devolve texto truncado sem erro nenhum. Se você joga esse texto num `json.loads()`, o erro aparece três camadas abaixo e você vai depurar o parser em vez do teto de tokens.
- **Estimar tokens por caracteres ou com `tiktoken`.** `tiktoken` é o tokenizador de outra família de modelos. A estimativa erra mais ainda em português. Use `count_tokens`.
- **Tratar variação de saída como bug.** Abrir chamado porque "a resposta mudou" é não ter entendido o componente. O que se testa é estrutura e taxa de acerto, nunca igualdade de string.
- **Achar que "não invente" resolve alucinação.** A instrução muda a distribuição, não o mecanismo. Correção vem de verificação no seu código, não de adjetivo no prompt.
- **Colocar conteúdo volátil no começo do prompt.** Timestamp, UUID ou um `json.dumps()` de dicionário sem ordenação no início invalidam o cache inteiro de forma silenciosa. Confira com `usage.cache_read_input_tokens`.

## Recuperação ativa

1. Uma conversa de 10 turnos, cada um com 2.000 tokens novos, tem quantos tokens de entrada cobrados no total? Explique por que não são 20.000.
2. Seu colega diz que o modelo "está com bug, porque rodou duas vezes e deu respostas diferentes". Responda a ele usando amostragem e distribuição de probabilidade.
3. Por que a janela de contexto se parece mais com a stack do que com o heap? Onde a analogia quebra?
4. O modelo gerou um método de biblioteca que não existe, com assinatura plausível. Explique por que isso acontece a partir do mecanismo, e diga que mudança de arquitetura reduz o dano (não que frase acrescentar ao prompt).
5. Você precisa saber se um contrato de 40 páginas cabe numa chamada para o Haiku 4.5. Descreva exatamente como medir, e por que a sua estimativa mental em palavras não serve.
6. Um prompt de sistema de 8.000 tokens é reenviado a cada turno. O cache está configurado, mas `cache_read_input_tokens` volta zero sempre. Liste três causas possíveis.
7. Por que rodar o mesmo produto com prompts em inglês pode sair mais barato, mesmo entregando a resposta final em português?

## Para ir além

- Documentação oficial da Messages API: <https://platform.claude.com/docs/en/api/messages>
- Contagem de tokens: <https://platform.claude.com/docs/en/docs/build-with-claude/token-counting>
- Cache de prompt, incluindo as regras de invalidação por prefixo: <https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching>
- Andrej Karpathy, "Let's build the GPT Tokenizer" — implementa um tokenizador BPE do zero e mostra por que idiomas fora do inglês custam mais tokens: <https://www.youtube.com/watch?v=zduSFxRajkE>
