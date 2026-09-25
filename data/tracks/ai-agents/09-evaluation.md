# Avaliação

> **Objetivo:** Construir um conjunto de avaliação que diga, com número, se uma mudança de prompt ou de modelo melhorou ou piorou o seu sistema.

## Por que isso importa

Você não aceitaria "rodei na mão e funcionou" como suíte de testes. Se um colega abrisse um pull request dizendo que testou o endpoint uma vez no Postman e a resposta pareceu certa, você pediria teste automatizado. Mas é exatamente assim que a maioria dos sistemas com LLM é validada: alguém muda o prompt, roda dois ou três exemplos no terminal, acha que ficou melhor e faz o deploy. Não é avaliação. É impressão.

O problema é pior com LLM do que com código comum, por dois motivos. A saída não é determinística: a mesma entrada pode gerar respostas diferentes entre chamadas, então uma execução isolada não prova nada nem sobre acerto nem sobre erro. E o erro do modelo é bem escrito — um código quebrado dá stack trace, um prompt ruim devolve um parágrafo fluente e plausível que você lê rápido demais e aprova. Avaliação é o instrumento que substitui a sua impressão por uma taxa comparável entre duas versões.

## Conceitos

### "Testei e pareceu bom" não é medição

Testar na mão tem dois defeitos estruturais. Você olha poucos casos, e olha justamente os casos que você tinha em mente quando escreveu o prompt: está avaliando contra a sua própria intenção, não contra a realidade do uso. E olha cada caso uma vez, sem repetir, então confunde sorte com competência. A analogia com testes automatizados é direta, com uma diferença importante: um teste unitário é binário e determinístico, passou ou não passou, sempre igual; uma avaliação de LLM é estatística — você roda N casos, conta quantos passaram e compara taxas. O resultado não é "verde ou vermelho", é "87% contra 82%". Você precisa aceitar isso para conseguir trabalhar.

### O conjunto de avaliação

Um conjunto de avaliação é uma lista de casos, e cada caso tem pelo menos duas coisas: a entrada que vai para o sistema e o critério do que se espera na saída. Pode ser um valor exato, um conjunto de campos obrigatórios, uma condição ("tem que citar a fonte", "não pode inventar número").

Vinte casos vindos de uso real valem mais que duzentos que você inventou sentada. Casos reais trazem a bagunça que você não imaginaria: entrada com erro de digitação, pergunta ambígua, campo vazio, texto colado do Word com caractere estranho. Casos inventados trazem a sua própria expectativa de volta, então o sistema passa e você não aprende nada. Se ainda não tem uso real, use registros de suporte, tickets, histórico de busca, qualquer texto que gente de verdade escreveu. E inclua casos difíceis de propósito: os que já falharam antes, os que estão na fronteira entre duas categorias, os que deveriam resultar em "não sei". Um conjunto onde tudo passa desde o primeiro dia não mede nada.

### Três formas de corrigir, da mais barata para a mais cara

**Verificação programática.** A saída é comparada com o esperado por código: igualdade, o JSON valida contra o schema, o número bate, a data está no formato certo, o id existe no banco. Custo zero, resultado determinístico, sem ambiguidade. Sempre que a tarefa permitir essa forma, use essa forma. Saída estruturada existe em boa parte para tornar isso possível.

**Heurística.** A saída contém certa palavra, não contém certa palavra, tem menos de N caracteres, começa com um cabeçalho, cita um dos documentos fornecidos. Também é barato e determinístico, mas é aproximado: "contém o nome do cliente" não garante que a frase está correta. Serve muito bem como rede de segurança negativa, do tipo "nunca pode aparecer um CPF na resposta".

**Modelo como juiz.** Um segundo modelo lê a saída e dá uma nota segundo uma rubrica que você escreveu. Serve para o que não é verificável por código: a resposta está fundamentada no documento, o tom está adequado, a explicação está correta. Funciona, mas custa dinheiro, é lento e — o ponto que quase todo mundo esquece — o juiz também erra. Ele é mais um sistema com LLM e precisa da mesma disciplina: pegue 30 ou 40 casos, corrija na mão, compare com a nota do juiz e meça a concordância. Se o juiz concorda com você em 60% dos casos, ele não está medindo qualidade, está gerando ruído com aparência de número.

Rubrica de juiz precisa ser explícita e discreta. "Dê uma nota de 0 a 10 para a qualidade" produz notas sem significado. "Responda `pass` se a resposta cita pelo menos um trecho do documento fornecido e não afirma nada que não esteja no documento; caso contrário `fail`, com o motivo" produz algo verificável.

### Variação entre execuções

A mesma entrada pode produzir saídas diferentes em chamadas diferentes. Isso não é defeito, é como a amostragem funciona, e a consequência prática é que uma execução do conjunto não é uma medição: é uma amostra. Rode o conjunto mais de uma vez — três é um mínimo razoável — e olhe a taxa de acerto e o espalhamento entre execuções. Se a versão A deu 84%, 86% e 85%, e a versão B deu 87%, 83% e 88%, você não tem evidência de que B é melhor: as faixas se sobrepõem. Um caso que passou uma vez e falhou duas é um caso instável, e instabilidade é um resultado em si, geralmente mais grave que uma falha consistente — a falha consistente você descobre, a instável chega em produção.

### Conjunto de desenvolvimento e conjunto de teste

Separe os casos em dois grupos desde o início. O conjunto de desenvolvimento é onde você mexe: olha os erros, entende o que falhou, ajusta o prompt, roda de novo. O conjunto de teste você só roda quando acha que terminou, e olha o número.

Se você ajustar o prompt olhando os erros do conjunto de teste, ele deixa de ser teste. Você não está mais melhorando o sistema, está decorando aquelas entradas. É o mesmo mecanismo do overfitting, e é exatamente a mesma falha lógica de escrever o teste depois, a partir do que o código já faz. O conjunto de teste tem valor justamente porque você não olhou para ele.

### Custo e latência são parte do resultado

Uma avaliação que só mede acerto está incompleta. Registre também tokens de entrada, tokens de saída, custo em dólar e tempo por caso. Os preços atuais por 1M de tokens (entrada/saída): Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5.

Com esses três números na mesma tabela você toma decisões que antes eram achismo. Um ganho de 2% de acerto que dobra o custo geralmente não vale. Sonnet 5 com um prompt melhor batendo Opus 5 com um prompt ruim é o resultado mais comum de todos, e você só descobre medindo os dois. `output_config={"effort": ...}` é outra alavanca: esforço baixo costuma custar bem menos, e em tarefas simples a queda de qualidade é zero.

### Regressão

Regressão é o que funcionava parar de funcionar. Em sistema com LLM ela é a norma, não a exceção: você adiciona uma instrução no prompt para consertar um caso e quebra três outros que ninguém estava olhando, porque a instrução nova compete com as antigas dentro do mesmo contexto. Por isso a avaliação roda a cada mudança de prompt, a cada troca de modelo, a cada alteração no que entra no contexto. O valor mais útil não é a taxa global, é a lista de casos que passavam antes e falham agora. Guarde o resultado por caso, não só o agregado, e faça o diff entre execuções.

## Na prática

Um avaliador mínimo não precisa de framework: uma lista de casos, uma função que roda o sistema, uma que corrige e um laço. Comece assim e só adicione estrutura quando a falta dela doer.

```python
import anthropic
from dataclasses import dataclass

client = anthropic.Anthropic()

MODEL = "claude-sonnet-5"
PRICE_PER_INPUT_TOKEN = 2.0 / 1_000_000
PRICE_PER_OUTPUT_TOKEN = 10.0 / 1_000_000

SYSTEM = (
    "Classifique o ticket de suporte em exatamente uma destas categorias: "
    "billing, bug, feature_request, other. "
    "Responda apenas com a categoria, sem pontuacao e sem explicacao."
)


@dataclass
class Case:
    input_text: str
    expected: str


CASES = [
    Case("minha fatura veio com valor errado esse mes", "billing"),
    Case("o botao de exportar nao faz nada no Firefox", "bug"),
    Case("seria otimo poder filtrar por data no relatorio", "feature_request"),
    Case("bom dia, so queria agradecer o atendimento", "other"),
    Case("fui cobrado duas vezes e o app trava ao abrir o recibo", "billing"),
]
```

O último caso é ambíguo de propósito: menciona cobrança e travamento. Casos assim revelam se o prompt tem critério de desempate ou se o modelo decide no chute. A execução e a correção vêm em seguida — aqui a correção é programática, comparação exata depois de normalizar.

```python
def run_case(case: Case) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=16,
        system=SYSTEM,
        messages=[{"role": "user", "content": case.input_text}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    cost = (
        response.usage.input_tokens * PRICE_PER_INPUT_TOKEN
        + response.usage.output_tokens * PRICE_PER_OUTPUT_TOKEN
    )
    return {"output": text.strip().lower(), "cost": cost}


def grade(case: Case, result: dict) -> bool:
    return result["output"] == case.expected
```

O laço roda cada caso várias vezes, porque uma execução é amostra e não medição, e guarda o resultado por caso para você comparar duas versões depois.

```python
def evaluate(cases: list[Case], runs: int = 3) -> dict:
    per_case = {case.input_text: [] for case in cases}
    total_cost = 0.0

    for _ in range(runs):
        for case in cases:
            result = run_case(case)
            per_case[case.input_text].append(grade(case, result))
            total_cost += result["cost"]

    total = sum(len(v) for v in per_case.values())
    passed = sum(sum(v) for v in per_case.values())
    unstable = [k for k, v in per_case.items() if 0 < sum(v) < len(v)]

    return {
        "pass_rate": passed / total,
        "unstable": unstable,
        "total_cost": total_cost,
        "per_case": per_case,
    }


report = evaluate(CASES)
print(f"taxa: {report['pass_rate']:.1%}  custo: ${report['total_cost']:.4f}")
for text in report["unstable"]:
    print(f"instavel: {text}")
```

`unstable` é a saída mais valiosa desse relatório: os casos que passaram em algumas execuções e falharam em outras, sintoma de prompt ambíguo e não de modelo ruim. Quando a correção não cabe em código, use um juiz com rubrica explícita e saída estruturada, para receber um veredito que você consegue contar em vez de um parágrafo que teria que ler.

```python
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

RUBRIC = (
    "Voce avalia respostas de um assistente que so pode usar o documento fornecido.\n"
    "Responda 'pass' somente se as duas condicoes valerem:\n"
    "1. toda afirmacao factual da resposta aparece no documento;\n"
    "2. a resposta nao inventa numero, data ou nome ausente do documento.\n"
    "Caso contrario responda 'fail' e cite em 'reason' o trecho problematico.\n"
    "Ausencia de informacao no documento com a resposta admitindo isso e 'pass'."
)


def judge(document: str, question: str, answer: str) -> dict:
    response = client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=512,
        system=RUBRIC,
        output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    f"<documento>{document}</documento>\n"
                    f"<pergunta>{question}</pergunta>\n"
                    f"<resposta>{answer}</resposta>"
                ),
            }
        ],
    )
    if response.stop_reason == "refusal":
        return {"verdict": "fail", "reason": response.stop_details.explanation}
    return response.parsed_output
```

Antes de confiar nesse juiz, corrija 30 casos na mão e compare com o veredito dele; se a concordância for baixa, o problema está na rubrica e não nos casos, porque condição vaga produz veredito vago. E use `client.messages.count_tokens(...)` para estimar o custo do conjunto antes de rodar tudo — conjunto grande com juiz caro é a forma mais fácil de gastar dinheiro sem perceber.

## Armadilhas comuns

- **Conjunto que só tem caso fácil.** Se a taxa é 100% desde a primeira execução, o conjunto não discrimina nada e vai continuar dando 100% mesmo quando você piorar o sistema.
- **Ajustar o prompt olhando o conjunto de teste.** Você passa a otimizar para aquelas entradas específicas e o número perde o poder de prever o comportamento em produção.
- **Uma execução só.** Com amostragem, uma passada pode acertar por sorte e a seguinte errar. Sem repetição você não distingue melhoria real de variação.
- **Juiz sem auditoria.** Um modelo-juiz não calibrado devolve números com aparência de rigor e conteúdo de chute. Meça a concordância dele com a sua correção manual antes de usar.
- **Medir só acerto.** Sem custo e latência na mesma tabela, você vai aprovar mudanças que melhoram 1% e triplicam a conta.
- **Guardar só o agregado.** Sem resultado por caso, você vê a taxa cair de 88% para 85% e não tem ideia do que quebrou.

## Recuperação ativa

1. Por que "testei alguns exemplos e pareceu melhor" não sustenta uma decisão de trocar de prompt, e o que substituiria isso?
2. Você tem uma tarefa que extrai CNPJ, valor e data de uma nota fiscal. Qual das três formas de correção você usaria para cada campo, e por quê?
3. Uma pessoa do time mostra que o modelo-juiz aprovou 95% das respostas. Que pergunta você faz antes de aceitar esse número?
4. Explique, para alguém que só conhece teste unitário, por que a avaliação precisa rodar o mesmo caso mais de uma vez.
5. Qual é a consequência concreta de ajustar o prompt olhando os erros do conjunto de teste? Descreva o que acontece depois, em produção.
6. Uma mudança sobe o acerto de 86% para 89% e o custo por caso de $0.004 para $0.011. Que informação adicional você precisa para decidir?
7. Você trocou de modelo e a taxa global ficou igual. Por que ainda assim vale olhar o resultado por caso?

## Para ir além

- Anthropic, "Create strong empirical evaluations" — https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
- Anthropic, "Reducing latency" e a documentação de `count_tokens` — https://platform.claude.com/docs/en/build-with-claude/token-counting
- Hamel Husain, "Your AI Product Needs Evals" — https://hamel.dev/blog/posts/evals/
- Eugene Yan, "Task-Specific LLM Evals that Do & Don't Work" — https://eugeneyan.com/writing/evals/
