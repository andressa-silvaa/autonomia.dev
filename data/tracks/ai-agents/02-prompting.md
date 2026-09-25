# Prompting

> **Objetivo:** escrever instruções que produzem o resultado que você quer de forma repetível, e saber distinguir o que muda a resposta do que é apenas superstição herdada de modelos antigos.

## Por que isso importa

Prompting tem má fama entre pessoas que programam, e a fama é merecida quando o assunto vira coleção de truques mágicos. Mas o núcleo do trabalho é o mesmo de qualquer especificação técnica: dizer o que você quer, em que formato, com que restrições, e com exemplos quando a descrição por si só é ambígua. Você já faz isso ao escrever a docstring de uma função pública ou a descrição de uma issue que outra pessoa vai implementar. A diferença é que aqui o executor não faz perguntas de esclarecimento, então a ambiguidade não vira uma thread no Slack: vira uma saída errada com cara de certa.

Existe um segundo motivo, mais prático. A área acumulou técnicas que fizeram sentido em modelos de 2022 e 2023 e hoje são ruído puro: implorar "pense passo a passo", prometer gorjeta, dizer que a carreira de alguém depende da resposta, exigir que o modelo assuma a persona de um especialista. Essas coisas estão em milhares de posts e em prompts de produção que ninguém revisou. Reconhecer o que envelheceu vale mais do que decorar mais uma técnica, porque cada linha de prompt custa token em toda chamada e ocupa espaço na janela de contexto.

## Conceitos

### Prompt de sistema versus mensagem do usuário

São dois canais com papéis diferentes. O `system` carrega o que é estável: quem o modelo é naquele contexto, as regras que valem sempre, o formato de saída, o que nunca fazer. As mensagens em `messages` carregam a tarefa específica e os dados daquela chamada.

A separação não é estética, é operacional. Primeiro, porque o `system` é o prefixo natural da requisição, e prefixo estável é exatamente o que o cache de prompt precisa para funcionar. Segundo, porque misturar regra permanente com dado variável produz prompts que ninguém consegue manter: em três meses ninguém sabe qual parte daquela string é política do produto e qual parte é gambiarra de um caso específico.

Uma regra de segurança que vem de graça: instrução vem do `system`, dado vem do `messages`. Quando você cola texto de usuário dentro do prompt de sistema, você acaba de criar uma superfície de injeção de prompt.

### Ser específico sobre a tarefa

Instrução vaga produz saída vaga, e não porque o modelo seja preguiçoso: porque, diante de "resuma este texto", a continuação mais provável é um resumo genérico de tamanho arbitrário. Você não deu nenhum sinal que deslocasse a distribuição.

Ser específico significa responder antecipadamente às perguntas que um humano faria: para quem é, qual o tamanho, o que é obrigatório incluir, o que deve ficar de fora, o que fazer nos casos em que falta informação. Esse último ponto é o que mais economiza tempo depois. Se você não diz o que fazer quando o dado não está no texto, o modelo vai preencher com o mais plausível, e você descobre isso em produção.

### Ser específico sobre o formato

Formato é contrato. Se a saída vai para um olho humano, descreva a estrutura ("três parágrafos, sem lista"). Se a saída vai para o seu código, não descreva: **imponha**, com saída estruturada e JSON Schema, que é o assunto do próximo módulo.

O meio-termo é onde mora a dor: pedir JSON em prosa no meio do prompt e depois dar `json.loads()` no resultado. Funciona em 95% das chamadas e falha nas outras 5% com cercas de markdown, uma frase de introdução ou uma vírgula sobrando.

### Exemplos (few-shot) e quando eles ganham da explicação

Dar exemplos de entrada e saída desejada é a técnica que continua tendo o melhor retorno por token gasto. Ela é especialmente forte quando o que você quer é difícil de descrever mas fácil de mostrar: um tom de voz específico, uma convenção de nomenclatura da sua empresa, uma classificação com fronteiras sutis entre categorias.

O critério para escolher entre explicar e exemplificar é este: se você consegue escrever a regra em uma frase clara, explique, sai mais barato. Se você começa a escrever a regra e percebe que precisa de quatro exceções, mostre três exemplos. Escolha exemplos que cubram justamente os casos de fronteira, porque exemplos todos iguais e todos fáceis não ensinam nada, só gastam tokens.

Um detalhe de execução: a forma nativa de dar exemplos no Claude é alternar turnos `user` e `assistant` no array `messages`, não colar um bloco de texto com "Exemplo 1:". Assim os exemplos ficam no mesmo formato da tarefa real.

### Raciocínio: o que mudou

A técnica clássica era pedir ao modelo que raciocinasse em voz alta antes de responder, o famoso "pense passo a passo". Ela funcionava por um motivo mecânico, não motivacional: como o modelo gera token a token e cada token gerado entra no contexto dos seguintes, produzir raciocínio intermediário dá a ele mais computação e mais contexto antes de comprometer a resposta.

Nos modelos atuais isso virou parâmetro. Você liga o pensamento estendido com `thinking={"type": "adaptive"}` e o modelo decide sozinho quanto pensar de acordo com a dificuldade. O quanto ele se esforça no geral você controla com `output_config={"effort": ...}`, que aceita `low`, `medium`, `high`, `xhigh` e `max`.

Duas consequências práticas. A primeira: o parâmetro antigo `budget_tokens` foi **removido** nos modelos atuais e agora devolve erro 400, então prompt ou código copiado de tutorial de 2024 quebra. A segunda: pedir raciocínio dentro do texto do prompt hoje é redundante e às vezes contraproducente, porque você paga tokens para reproduzir no texto o que o parâmetro já faz melhor.

Escolha de esforço é decisão de custo. `low` para classificação e tarefas de alto volume, `high` quando a qualidade importa, `max` quando errar custa mais caro que a chamada. Medir antes de subir é o comportamento certo.

### Iterar sobre falhas reais, não sobre pressentimento

Este é o hábito que separa engenharia de superstição. O ciclo é: junte de 10 a 20 entradas reais, rode o prompt, olhe **as saídas erradas**, ache o que elas têm em comum, mude uma coisa só, rode de novo no mesmo conjunto.

Sem esse conjunto fixo, você está ajustando com amostra de tamanho 1 sobre um componente não determinístico. Vai parecer que melhorou, porque você olhou uma saída boa depois da mudança. É o mesmo erro de declarar que uma otimização funcionou depois de rodar o benchmark uma vez. Uma coisa por vez também importa: se você mexeu em três instruções e o resultado melhorou, não sabe qual delas pagou.

### Idioma e custo

Como você mediu no módulo anterior, português consome mais tokens que inglês para o mesmo conteúdo. Num prompt de sistema longo, reenviado em toda chamada de um serviço de volume, isso é dinheiro real.

O importante é que as duas pontas são independentes: você pode escrever as instruções em inglês e pedir explicitamente a resposta em português do Brasil. A qualidade em português não depende do idioma da instrução. Não vale a pena para um script pessoal; vale para um prompt de sistema de milhares de tokens em produção. Meça com `count_tokens` e decida com o número na mão.

### O que hoje é ruído

Vale listar, porque essas coisas aparecem em código legado:

- Implorar por raciocínio ("pense com muito cuidado, passo a passo, antes de responder"). Use `thinking` e `effort`.
- Prometer gorjeta, dinheiro ou consequências emocionais. Nunca teve efeito confiável e hoje só gasta tokens.
- Ameaçar ou apelar ("minha carreira depende disso").
- Persona decorativa ("você é um engenheiro sênior de classe mundial"). Papel que restringe o comportamento de forma concreta ajuda; adjetivo elogioso não faz nada.
- CAPS LOCK e pilhas de pontos de exclamação para enfatizar. Enfatize com estrutura: uma seção de restrições com itens curtos.

## Na prática

Um prompt ruim, do tipo que todo mundo já escreveu:

```python
bad_prompt = """Você é um engenheiro de software de classe mundial, extremamente
inteligente. Pense passo a passo com muito cuidado antes de responder, isso é muito
importante para minha carreira. Analise o log de erro abaixo e me diga o que fazer.

LOG:
{log}
"""
```

O que há de errado, item por item. O elogio não restringe nada. O pedido de raciocínio duplica o que `thinking` faz. O apelo emocional é token puro. E, o mais grave, ninguém disse o que é "me diga o que fazer": uma frase, uma investigação, um patch? Nem o que fazer se o log for insuficiente. A saída vai ter tamanho e formato aleatórios a cada chamada.

A versão reescrita separa o que é estável do que varia, e diz o que fazer quando falta informação.

```python
system_prompt = """Você analisa logs de erro de aplicações Python em produção.

Para cada log, responda exatamente nesta estrutura:
1. Causa provável: uma frase.
2. Evidência: as linhas específicas do log que sustentam a causa.
3. Próximo passo de investigação: uma ação concreta e verificável.

Restrições:
- Se o log não contiver evidência suficiente para uma causa, escreva
  "Evidência insuficiente" no item 1 e indique no item 3 qual log ou métrica
  adicional é necessário.
- Não sugira mudanças de código que exijam arquivos que você não viu.
- Máximo de 150 palavras.
"""

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    system=system_prompt,
    thinking={"type": "adaptive"},
    output_config={"effort": "medium"},
    messages=[{"role": "user", "content": log_text}],
)
```

O critério que mudou não foi "ficar mais educado com o modelo". Foi: estrutura de saída fixa, definição explícita do comportamento no caso ruim, teto de tamanho, e o raciocínio migrado de texto para parâmetro. Note também que `system_prompt` é uma constante, e por isso é um bom candidato a `cache_control`.

Agora few-shot. A tarefa é classificar mensagens de suporte, e a fronteira entre "bug" e "dúvida" é sutil o bastante para que descrever em prosa fique pior do que mostrar.

```python
examples = [
    ("O botão de exportar some depois que eu filtro por data.", "bug"),
    ("Como faço para exportar só os pedidos de um mês?", "duvida"),
    ("Exportei e o CSV veio com as colunas trocadas.", "bug"),
    ("Vocês têm exportação em XLSX?", "duvida"),
]

shots = []
for text, label in examples:
    shots.append({"role": "user", "content": text})
    shots.append({"role": "assistant", "content": label})

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=16,
    system="Classifique a mensagem de suporte como 'bug' ou 'duvida'. Responda apenas com o rótulo.",
    messages=shots
    + [{"role": "user", "content": "O total da nota fiscal está vindo com centavos a mais."}],
    output_config={"effort": "low"},
)
```

Três decisões aqui. Os exemplos vão como turnos alternados, no mesmo formato da pergunta real. `max_tokens=16` porque a saída é um rótulo, e isso protege de uma resposta longa acidental. E o modelo é o Haiku 4.5, com `effort` baixo: classificação simples e de alto volume não paga Opus, e a diferença de preço é de $1 por 1M de tokens de entrada contra $5.

Antes de subir um prompt de sistema longo para produção, meça o que ele custa por chamada.

```python
count = client.messages.count_tokens(
    model="claude-sonnet-5",
    system=system_prompt,
    messages=[{"role": "user", "content": ""}],
)
monthly_calls = 200_000
cost = count.input_tokens * monthly_calls / 1_000_000 * 2.00
print(f"{count.input_tokens} tokens por chamada, ${cost:.2f}/mês só de prompt de sistema")
```

Com um prompt de 1.200 tokens e 200 mil chamadas por mês em Sonnet 5, são $480 mensais só para reenviar as mesmas instruções. É esse número que decide se vale escrever as instruções em inglês e se vale configurar cache de prefixo.

## Armadilhas comuns

- **Carregar ruído de modelos antigos.** "Pense passo a passo", gorjeta, apelo emocional e elogio. Custam token em toda chamada e hoje não compram nada; o raciocínio virou `thinking` e `effort`.
- **Usar `budget_tokens`.** Removido nos modelos atuais: erro 400. Código velho copiado de tutorial quebra na primeira execução.
- **Ajustar o prompt olhando uma saída só.** Componente não determinístico exige conjunto fixo de casos e comparação antes e depois. Caso contrário você está reforçando crença, não medindo efeito.
- **Mudar várias coisas de uma vez.** Melhorou, mas você não sabe por quê, e não consegue remover o que não serve depois.
- **Não dizer o que fazer quando falta informação.** Sem essa instrução o modelo preenche com o plausível, e o dado inventado passa despercebido justamente porque parece certo.
- **Colar texto de usuário dentro do `system`.** Além de quebrar o cache de prefixo, é injeção de prompt servida em bandeja. Instrução no `system`, dado no `messages`.
- **Pedir JSON em prosa e confiar.** Funciona quase sempre, e é exatamente por isso que a falha aparece só em produção. Para isso existe saída estruturada.

## Recuperação ativa

1. Qual é a diferença funcional, e não apenas organizacional, entre pôr uma instrução no `system` e pô-la na mensagem do usuário? Cite um efeito de custo e um de segurança.
2. Por que "pense passo a passo" funcionava em modelos antigos? Explique pelo mecanismo de geração token a token, não por analogia com psicologia humana.
3. Você tem uma regra de classificação com quatro exceções. Explicar ou dar exemplos? Justifique com o critério, e diga como escolher quais exemplos usar.
4. Um prompt melhorou depois que você mudou três instruções ao mesmo tempo. Que problema isso cria, e como você descobre qual das três pagou?
5. Quando vale a pena escrever o prompt de sistema em inglês e pedir resposta em português? Descreva a conta que decide isso.
6. Você precisa classificar 500 mil mensagens por mês em duas categorias. Que modelo e que `effort` você escolhe, e o que você mede antes de subir esse default?
7. Reescreva mentalmente esta instrução: "Extraia os dados importantes do e-mail". Liste pelo menos quatro coisas que faltam nela.

## Para ir além

- Guia oficial de engenharia de prompt da Anthropic: <https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/overview>
- Pensamento estendido e esforço, com a migração de `budget_tokens`: <https://platform.claude.com/docs/en/docs/build-with-claude/extended-thinking>
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" — o artigo original da técnica, útil para entender por que ela funcionava e por que virou parâmetro: <https://arxiv.org/abs/2201.11903>
