# Saída estruturada

> **Objetivo:** obter do modelo dados que o seu código consegue consumir com segurança, usando JSON Schema como contrato e validação própria como rede de proteção.

## Por que isso importa

Um LLM produz texto, e texto livre não integra com código. Se a saída do modelo vai alimentar um `if`, um `INSERT` ou uma chamada de API, alguém vai ter que transformar prosa em estrutura, e essa pessoa é você. A tentação é resolver com regex e `split()`, e isso funciona até o dia em que o modelo decide escrever "R$ 1.250,00" em vez de "1250.00", ou embrulhar o JSON numa cerca de markdown, ou começar com "Claro! Aqui está o JSON que você pediu:".

Você conhece esse problema de outro contexto. É a diferença entre parsear um formato serializado com contrato definido e adivinhar a estrutura de uma string. Ninguém no seu time aceitaria receber a resposta de um serviço interno como texto corrido para extrair o valor com `indexOf`; exigiria um JSON com schema. A saída estruturada é exatamente isso aplicado ao modelo: você declara o formato em JSON Schema, a API restringe a geração a respeitá-lo, e do outro lado você recebe algo com forma garantida. O que continua sendo seu é garantir que o conteúdo faça sentido, porque schema garante forma, nunca verdade.

## Conceitos

### Por que texto livre não integra

Parsear texto livre falha por um motivo estrutural: o espaço de saídas possíveis é infinito e não determinístico. Cada regra que você escreve cobre as saídas que você viu, e a variação do modelo garante que existem saídas que você não viu.

Pior: a falha é silenciosa. Um regex que não casa devolve `None`, e `None` vira um campo vazio no banco em vez de uma exceção. Você descobre em um relatório, três semanas depois.

### JSON Schema como contrato

JSON Schema descreve a forma de um objeto: quais campos existem, de que tipo, quais são obrigatórios, que valores um enum aceita. É o mesmo papel de uma classe com tipos em C# ou de um `TypedDict` em Python, só que num formato que a API entende.

Três propriedades fazem a diferença entre um schema decorativo e um contrato de verdade:

- `required`: lista os campos que precisam existir. Sem isso, um objeto vazio é válido.
- `additionalProperties: false`: impede campos inventados. Sem isso, o modelo pode acrescentar chaves que o seu código ignora, escondendo desentendimentos.
- `enum`: fecha o conjunto de valores aceitos. É o que transforma "categoria" de string livre em algo que você pode usar num `match`.

### `output_config` com `format`

Na API atual, você passa o schema em `output_config={"format": {...}}`. O parâmetro antigo `output_format`, que aparece em código de 2024, está descontinuado.

A diferença em relação a pedir JSON no prompt é de natureza, não de grau. No prompt, o JSON é a continuação mais provável, e "muito provável" não é "garantido". Com `output_config`, a restrição atua sobre a geração: tokens que quebrariam o schema não são candidatos válidos. Você deixa de tratar o formato como sorte.

### `client.messages.parse()`

O SDK oferece um atalho que faz a chamada e já valida a resposta contra o schema, devolvendo o objeto pronto. É o caminho padrão para extração: menos código de plumbing, e a falha de formato vira exceção no lugar certo em vez de um dicionário meio preenchido circulando pelo sistema.

### Validar sempre do seu lado

Aqui está a parte que quase todo mundo pula. **Schema válido não significa conteúdo correto.** O schema diz que `total` é um número; não diz que é o total certo. Diz que `cnpj` é uma string de 14 dígitos; não diz que o dígito verificador fecha. Diz que `data_vencimento` casa com um padrão; não diz que ela é posterior à data de emissão.

Um modelo que não encontra o valor no documento vai preencher o campo obrigatório com algo plausível, porque é isso que ele faz. O schema obriga a preencher; ele não obriga a acertar. Por isso a arquitetura correta tem duas camadas: a API garante a forma, e o seu código garante as invariantes de negócio, exatamente como você faria com qualquer payload vindo de fora.

Um recurso de schema que ajuda muito: permitir `null` nos campos que podem faltar e instruir explicitamente que ausência se representa com `null`. Dar ao modelo uma saída honesta reduz a pressão que gera invenção.

### Quando o modelo devolve algo inesperado

Mesmo com saída estruturada, três coisas podem dar errado, e cada uma tem um tratamento diferente:

- **`stop_reason == "max_tokens"`.** A geração foi cortada no meio e o JSON está incompleto. Não é caso de retry cego; é caso de aumentar `max_tokens`.
- **`stop_reason == "refusal"`.** O modelo recusou. Nenhum retry resolve, e você deve tratar como caminho de erro explícito, não como falha de parsing.
- **Validação de negócio reprovada.** A forma está certa, o conteúdo não. Aqui o retry pode fazer sentido, desde que você devolva ao modelo **qual** regra falhou. Retry com o mesmo input e a mesma mensagem é apostar na amostragem.

Em todos os casos, logue o input e a saída bruta. Sem isso você não consegue reproduzir o erro, porque o input que falhou é o dado, não o código.

### `strict: true` em ferramentas

Quando você dá ferramentas ao modelo (assunto do módulo de tool calling), cada ferramenta tem um `input_schema`. Marcar a ferramenta com `strict: true` garante que os argumentos que chegam validam exatamente contra esse schema. A exigência é a mesma do formato de saída: `additionalProperties: false` e `required` declarados.

Vale a pena porque o custo de um argumento errado é mais alto ali. Uma extração malformada você descarta; uma chamada de ferramenta malformada pode executar uma ação no mundo com o parâmetro trocado.

E mesmo com `strict`, uma regra não muda: sempre parseie a entrada da ferramenta com `json.loads()`, nunca com comparação de string sobre o JSON serializado. O escape pode variar sem que o valor mude.

### Por que "pedir JSON no prompt" é frágil

Vale nomear com precisão. Pedir JSON em prosa e dar `json.loads()` no texto falha de quatro jeitos distintos: cercas de markdown em volta, frase de introdução antes, campo faltando porque o modelo julgou irrelevante, e tipo trocado (`"1250"` em vez de `1250`). Os três primeiros quebram o parse, o que pelo menos é barulhento. O quarto passa, e é o que faz um total virar concatenação de string lá na frente.

## Na prática

O caminho ruim, para você reconhecer quando encontrar em código existente:

```python
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": f"Extraia o valor e o vencimento. Responda em JSON.\n\n{text}"}
    ],
)
raw = response.content[0].text
data = json.loads(raw)
amount = float(data["amount"])
```

Conte as suposições nessa fatia de código: que o bloco zero é texto, que não existe cerca de markdown, que `amount` existe, que ele é convertível para float, que `stop_reason` foi `end_turn`. São cinco pontos de falha sem nenhuma mensagem de erro útil.

O caminho bom começa pelo schema. Repare em `additionalProperties: false`, nos campos que aceitam `null` e no `enum` fechado.

```python
INVOICE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "supplier_name": {"type": "string"},
            "document_number": {"type": ["string", "null"]},
            "amount_cents": {"type": "integer"},
            "issue_date": {"type": "string", "description": "Formato ISO 8601: AAAA-MM-DD"},
            "due_date": {"type": "string", "description": "Formato ISO 8601: AAAA-MM-DD"},
            "currency": {"type": "string", "enum": ["BRL", "USD", "EUR"]},
        },
        "required": [
            "supplier_name",
            "document_number",
            "amount_cents",
            "issue_date",
            "due_date",
            "currency",
        ],
        "additionalProperties": False,
    },
}
```

`amount_cents` é inteiro de propósito. Valor monetário em float carrega o problema de representação binária que você já viu em fundamentos: `0.1 + 0.2` não dá `0.3`. Pedir centavos inteiros elimina a classe inteira de erro na fronteira.

O prompt de sistema diz explicitamente o que fazer quando o dado não está no documento. Essa frase é o que separa `null` honesto de número inventado.

```python
SYSTEM = """Você extrai dados estruturados de notas fiscais brasileiras.
Use apenas informação presente no documento. Se um campo não aparecer no
documento, retorne null para ele. Nunca infira, calcule ou complete valores
que não estejam escritos. Valores monetários vão em centavos, como inteiro."""
```

Agora a camada que é só sua. O schema já garantiu tipos e presença; o que falta é tudo que depende de conhecer o negócio.

```python
from datetime import date


def validate_invoice(payload: dict) -> list[str]:
    errors = []

    if payload["amount_cents"] <= 0:
        errors.append("amount_cents deve ser positivo")

    try:
        issue = date.fromisoformat(payload["issue_date"])
        due = date.fromisoformat(payload["due_date"])
    except ValueError:
        errors.append("datas fora do formato ISO 8601")
        return errors

    if due < issue:
        errors.append("due_date anterior a issue_date")
    if issue > date.today():
        errors.append("issue_date no futuro")

    doc = payload["document_number"]
    if doc is not None and not doc.isdigit():
        errors.append("document_number deve conter apenas dígitos")

    return errors
```

Nenhuma dessas quatro regras é expressável em JSON Schema, e as quatro pegam erros reais. Uma data de vencimento anterior à de emissão é o sintoma clássico de o modelo ter trocado dois campos que estavam próximos no documento: forma perfeita, conteúdo invertido.

Juntando tudo: a chamada com `output_config`, a checagem de `stop_reason` antes de qualquer parse, e um retry que informa ao modelo o que falhou. Esse retry é diferente de repetir a mesma chamada torcendo por outra amostragem.

```python
def extract_invoice(invoice_text: str, max_attempts: int = 2) -> dict:
    messages = [{"role": "user", "content": invoice_text}]

    for attempt in range(max_attempts):
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=2048,
            system=SYSTEM,
            messages=messages,
            output_config={"format": INVOICE_SCHEMA},
        )
        if response.stop_reason != "end_turn":
            raise RuntimeError(f"Parada inesperada: {response.stop_reason}")

        text = next(b.text for b in response.content if b.type == "text")
        payload = json.loads(text)
        errors = validate_invoice(payload)
        if not errors:
            return payload

        messages.append({"role": "assistant", "content": text})
        messages.append(
            {
                "role": "user",
                "content": "A extração falhou nestas validações: "
                + "; ".join(errors)
                + ". Corrija usando apenas o documento original.",
            }
        )

    raise ValueError(f"Extração inválida após {max_attempts} tentativas: {errors}")
```

Duas observações de custo. Cada tentativa reenvia o histórico inteiro, então um retry não custa o mesmo que a chamada original; custa mais. E o limite de tentativas precisa existir, porque um documento genuinamente ilegível não melhora na quinta chamada, só fica caro.

Quando você quer só o objeto validado e não precisa desse controle todo, `client.messages.parse()` faz a chamada e a validação contra o schema num passo só:

```python
result = client.messages.parse(
    model="claude-sonnet-5",
    max_tokens=2048,
    system=SYSTEM,
    messages=[{"role": "user", "content": invoice_text}],
    output_config={"format": INVOICE_SCHEMA},
)
```

Ele resolve a camada de forma. A camada de negócio continua sendo `validate_invoice`.

## Armadilhas comuns

- **Confiar que schema válido significa conteúdo correto.** O schema garante que `total` é número, nunca que é o número certo. Data de vencimento antes da emissão passa em qualquer schema.
- **Não permitir `null` em campos opcionais.** Se o campo é obrigatório e o dado não existe no documento, o modelo preenche com o plausível. Você forçou a invenção com o seu próprio schema.
- **Esquecer `additionalProperties: false` e `required`.** Sem os dois, o schema aceita objeto vazio e aceita campos inventados. Vira decoração.
- **Usar `output_format`.** Descontinuado. O parâmetro atual é `output_config={"format": ...}`.
- **Usar float para dinheiro.** Ponto flutuante binário não representa `0.10` exatamente. Peça centavos como inteiro e converta na borda de exibição.
- **Retry cego.** Repetir a mesma chamada sem dizer o que falhou é apostar na amostragem, e ainda reenvia o histórico inteiro. Devolva o erro de validação junto e limite as tentativas.
- **Não checar `stop_reason` antes de parsear.** Um `max_tokens` devolve JSON truncado, e o `JSONDecodeError` resultante manda você depurar o parser em vez do teto de tokens.

## Recuperação ativa

1. Sua extração devolveu um JSON perfeitamente válido pelo schema, mas com o CNPJ do cliente no campo do fornecedor. Explique por que o schema não pegou isso e onde essa verificação deveria estar.
2. Quais são as quatro maneiras distintas de "pedir JSON no prompt e dar `json.loads()`" falhar? Qual delas é a mais perigosa, e por quê?
3. Por que um campo obrigatório sem permissão de `null` aumenta a chance de invenção? Descreva a mudança de schema e de instrução que reduz isso.
4. O que exatamente `additionalProperties: false` impede, e que tipo de bug ele evita meses depois, quando alguém mudar o prompt?
5. Dê três regras de validação do seu domínio que não podem ser expressas em JSON Schema, e explique o que cada uma protege.
6. Um retry por falha de validação custa mais que a chamada original. Por quê? Como você decide o número máximo de tentativas?
7. Por que `strict: true` numa ferramenta é mais importante do que schema numa extração de texto? Pense no que acontece depois de cada uma.

## Para ir além

- Saída estruturada na documentação oficial, com as regras de JSON Schema aceitas: <https://platform.claude.com/docs/en/docs/build-with-claude/structured-outputs>
- Especificação do JSON Schema, seção de validação: <https://json-schema.org/understanding-json-schema/reference>
- Pydantic, para levar a camada de validação de negócio para modelos declarativos: <https://docs.pydantic.dev/latest/concepts/validators/>
- "What Every Computer Scientist Should Know About Floating-Point Arithmetic", de David Goldberg — a referência sobre por que dinheiro não vai em float: <https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html>
