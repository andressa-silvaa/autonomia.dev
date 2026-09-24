# Recursão

> **Objetivo:** escrever e rastrear à mão funções recursivas, explicando o que acontece na pilha de chamadas e quando vale mais a pena usar um laço.

## Por que isso importa

Algumas estruturas são recursivas por natureza. Uma pasta contém arquivos e outras pastas, que contêm arquivos e outras pastas. Uma lista pode conter listas. Um JSON pode ter objetos dentro de objetos. Tentar percorrer isso com laços simples vira uma bagunça de índices e contadores; com recursão, o código fica quase igual à descrição do problema. Além disso, os melhores algoritmos de ordenação do próximo módulo são recursivos. E, como você já estudou a pilha de memória, está no ponto certo para entender recursão de verdade, e não como mágica.

## Conceitos

### Caso base e caso recursivo

Uma função recursiva é uma função que chama a si mesma. Para isso não virar um laço infinito, ela precisa de duas partes:

- **Caso base:** a situação simples o bastante para responder direto, sem chamar a si mesma.
- **Caso recursivo:** a situação em que a função resolve um pedaço e delega o resto para uma chamada a si mesma com um problema **menor**, que se aproxima do caso base.

O fatorial mostra as duas coisas. Por definição, 0! = 1, e n! = n × (n − 1)!. A primeira linha é o caso base; a segunda é o caso recursivo.

### A pilha de chamadas

Lembre do módulo sobre memória: cada vez que uma função é chamada, o programa empilha um **stack frame** com os parâmetros, as variáveis locais e o ponto para onde voltar. Quando a função termina, o frame é desempilhado.

Na recursão isso não muda nada. Cada chamada de `fatorial` é uma chamada normal, com seu próprio frame e seu próprio `n`. O `n` de uma chamada não se mistura com o `n` da outra, porque vivem em frames diferentes. A pilha cresce enquanto as chamadas descem até o caso base, e vai encolhendo à medida que cada uma devolve seu resultado para quem chamou.

### Recursão vs iteração

Tudo que se faz com recursão dá para fazer com laço, e o contrário também. A diferença está em clareza e custo. Cada chamada recursiva ocupa um frame, então uma recursão com profundidade n usa O(n) de memória de pilha, enquanto um laço usa O(1). Chamar função também é mais lento que repetir um laço. Regra prática: se o problema é uma sequência simples (somar uma lista, contar de 1 a n), use laço. Se o problema tem forma de árvore (pastas, estruturas aninhadas, dividir e conquistar), recursão costuma ser mais clara e a profundidade costuma ser pequena.

### Limites de profundidade

A pilha tem tamanho finito. O Python protege você com um limite de profundidade, por padrão 1000 chamadas; ao passar dele, levanta `RecursionError`. Você pode consultar com `sys.getrecursionlimit()`. Dá para aumentar com `sys.setrecursionlimit`, mas isso geralmente só adia o problema e pode derrubar o interpretador de verdade.

No C# não existe esse limite artificial: a recursão cresce até esgotar a pilha da thread (tipicamente 1 MB) e o processo morre com `StackOverflowException`. Esse erro não pode ser capturado com `try/catch`; o programa simplesmente termina. É mais um motivo para garantir que o caso base sempre será alcançado.

### Como pensar recursivamente

O jeito que funciona é o que muita gente chama de "salto de fé": **confie que a chamada menor já funciona**. Para escrever `soma(lista)`, você não tenta imaginar todas as chamadas. Você pensa: "se eu soubesse somar o resto da lista, a soma total seria o primeiro item mais a soma do resto". Depois pergunta: qual é a menor entrada possível e qual a resposta dela? Uma lista vazia soma zero. Pronto, são essas duas frases, e o código sai delas.

## Na prática

Comece pelo fatorial:

```python
def fatorial(n):
    if n == 0:
        return 1
    return n * fatorial(n - 1)


print(fatorial(4))
```

```text
24
```

Rastreie à mão `fatorial(4)`. A chamada com n = 4 não é caso base, então precisa de `fatorial(3)` e fica esperando. O mesmo acontece com 3, 2 e 1. Aí a pilha tem cinco frames, e o do topo é `fatorial(0)`, que devolve 1 sem chamar ninguém. Agora a pilha desfaz: `fatorial(1)` recebe 1 e devolve 1 × 1 = 1; `fatorial(2)` devolve 2 × 1 = 2; `fatorial(3)` devolve 3 × 2 = 6; `fatorial(4)` devolve 4 × 6 = 24. Descer é empilhar perguntas; subir é desempilhar respostas.

```text
fatorial(4) = 4 * fatorial(3)
              fatorial(3) = 3 * fatorial(2)
                            fatorial(2) = 2 * fatorial(1)
                                          fatorial(1) = 1 * fatorial(0)
                                                        fatorial(0) = 1
```

Agora a sequência de Fibonacci, em que cada termo é a soma dos dois anteriores: fib(0) = 0, fib(1) = 1, fib(n) = fib(n − 1) + fib(n − 2).

```python
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


print(fib(10))
```

```text
55
```

O código é idêntico à definição, mas tem um problema sério. Rastreie `fib(4)`: ela chama `fib(3)` e `fib(2)`. A `fib(3)` chama `fib(2)` e `fib(1)`. Repare que `fib(2)` já foi calculada duas vezes, e isso piora a cada nível. Cada chamada gera duas, formando uma árvore que dobra de tamanho quase a cada nível, então o custo é O(2^n). `fib(40)` faz centenas de milhões de chamadas e leva segundos; `fib(60)` não termina num tempo razoável.

A saída é **memoização**: guardar o resultado de cada `n` já calculado e reaproveitar. Você acabou de estudar a estrutura ideal para isso, o dicionário.

```python
def fib_memo(n, cache=None):
    if cache is None:
        cache = {}
    if n < 2:
        return n
    if n not in cache:
        cache[n] = fib_memo(n - 1, cache) + fib_memo(n - 2, cache)
    return cache[n]


print(fib_memo(80))
```

```text
23416728348467685
```

Agora cada valor de 0 a n é calculado uma vez só, e o custo cai para O(n). O `cache=None` com criação dentro da função evita a armadilha do argumento padrão mutável, que veremos abaixo. A biblioteca padrão oferece o mesmo recurso pronto com o decorador `functools.cache`.

Por fim, um uso onde a recursão brilha: somar todos os números de uma lista que pode ter listas dentro, em qualquer profundidade.

```python
def soma_aninhada(itens):
    total = 0
    for item in itens:
        if isinstance(item, list):
            total += soma_aninhada(item)
        else:
            total += item
    return total


print(soma_aninhada([1, [2, 3], [4, [5, [6]]]]))
```

```text
21
```

Aplique o salto de fé: para cada item, se é um número, soma; se é uma lista, confie que `soma_aninhada` sabe somá-la. O caso base aqui está implícito: uma lista só com números não faz nenhuma chamada recursiva. Percorrer pastas segue exatamente o mesmo formato, trocando "é lista?" por "é diretório?":

```python
from pathlib import Path


def tamanho_total(pasta):
    total = 0
    for caminho in pasta.iterdir():
        if caminho.is_dir():
            total += tamanho_total(caminho)
        else:
            total += caminho.stat().st_size
    return total


print(tamanho_total(Path(".")))
```

Em C#, a recursão se escreve igual. A diferença é o que acontece se o caso base falhar:

```csharp
static long Fatorial(int n)
{
    if (n == 0)
        return 1;
    return n * Fatorial(n - 1);
}

Console.WriteLine(Fatorial(20));
```

```text
2432902008176640000
```

Chame `Fatorial(-1)` e o `n` nunca chega a zero: o processo termina com `StackOverflowException`, sem chance de tratamento.

## Armadilhas comuns

- **Esquecer o caso base ou não se aproximar dele.** `fatorial(-1)` na versão acima nunca chega em zero. Proteja com `if n <= 0` ou valide a entrada.
- **Recalcular os mesmos subproblemas.** Se a árvore de chamadas repete argumentos, como no Fibonacci, use memoização.
- **Usar recursão para sequências longas.** Percorrer uma lista de 10 mil itens recursivamente estoura o limite do Python. Laço resolve.
- **Argumento padrão mutável.** `def f(n, cache={})` cria o dicionário uma vez só, na definição da função, e ele é compartilhado entre todas as chamadas externas. Às vezes parece útil, mas costuma gerar bugs difíceis de achar.
- **Esquecer o `return` do resultado recursivo.** Chamar `soma(resto)` sem usar o valor faz a função devolver `None` e o erro aparecer longe dali.

## Recuperação ativa

1. Quais são as duas partes obrigatórias de uma função recursiva e o que acontece se faltar cada uma delas?
2. Desenhe a pilha de chamadas de `fatorial(3)` no momento em que ela está mais alta. Quantos frames existem e qual o valor de `n` em cada um?
3. Por que o Fibonacci ingênuo é O(2^n) e como a memoização reduz isso para O(n)?
4. Qual a diferença entre `RecursionError` no Python e `StackOverflowException` no C#, do ponto de vista de quem escreve o programa?
5. Explique o "salto de fé" usando como exemplo uma função que conta quantos arquivos existem numa pasta e em todas as subpastas.

## Para ir além

- [`sys.getrecursionlimit` na documentação do Python](https://docs.python.org/pt-br/3/library/sys.html#sys.getrecursionlimit)
- [`functools.cache` na documentação do Python](https://docs.python.org/pt-br/3/library/functools.html#functools.cache)
- [Classe `StackOverflowException` na documentação da Microsoft](https://learn.microsoft.com/pt-br/dotnet/api/system.stackoverflowexception)
- [Recursividade (ciência da computação) na Wikipedia](https://pt.wikipedia.org/wiki/Recursividade_(ci%C3%AAncia_da_computa%C3%A7%C3%A3o))
