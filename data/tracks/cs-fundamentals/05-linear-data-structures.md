# Estruturas lineares: arrays, listas, pilhas e filas

> **Objetivo:** escolher entre array, array dinâmico, lista ligada, pilha e fila sabendo explicar o custo de cada operação e por que ele é esse.

## Por que isso importa

Quase todo programa guarda coisas em sequência: linhas de um arquivo, pedidos de um cliente, ações para desfazer. A forma como essa sequência fica na memória decide se uma operação leva um instante ou se trava o sistema quando os dados crescem. Você já viu Big-O e já sabe que a memória é uma fileira de endereços. Agora vamos juntar as duas coisas: cada estrutura linear é só uma maneira diferente de organizar itens nessa fileira, e o custo das operações sai direto dessa organização. Quem entende isso não precisa decorar tabela nenhuma, consegue deduzir.

## Conceitos

### Array: um bloco contíguo

Imagine 5 inteiros de 4 bytes cada, guardados lado a lado a partir do endereço 1000. O primeiro está em 1000, o segundo em 1004, o terceiro em 1008. Para achar o item de índice `i`, o computador faz uma conta: `endereço_base + i * tamanho_do_item`. Não importa se o array tem 5 ou 5 milhões de itens, é uma multiplicação e uma soma. Por isso acesso por índice é O(1).

O preço dessa contiguidade aparece quando você quer inserir no meio. Para abrir espaço na posição 2, todos os itens depois dela precisam andar uma casa para a direita. No pior caso isso move n itens: O(n). Remover do meio tem o mesmo problema, só que ao contrário.

Em C#, `int[]` é um array de tamanho fixo. Você decide o tamanho na criação e ele não muda.

### Array dinâmico: o array que cresce

A `list` do Python e a `List<T>` do C# são arrays dinâmicos. Por baixo existe um array comum com uma capacidade maior do que a quantidade de itens em uso. Quando você faz `append`, o item vai para a próxima casa livre: O(1).

Quando a capacidade acaba, a estrutura aloca um array novo, maior (a `List<T>` dobra; a `list` do CPython cresce por um fator menor, perto de 1,125, mas a ideia é a mesma), copia tudo e descarta o antigo. Essa cópia custa O(n). Então por que dizemos que `append` é O(1)?

Faça as contas com dobra: para chegar a 16 itens, as cópias foram de 1, 2, 4 e 8 itens, total 15. Ou seja, menos de uma cópia por item inserido, em média. Isso se chama custo **amortizado**: uma operação cara de vez em quando, diluída entre muitas baratas, dá O(1) por operação na média ao longo da sequência.

### Lista ligada: nós e ponteiros

Numa lista ligada cada item vive num **nó** separado, em qualquer lugar do heap, e cada nó guarda o valor e uma referência para o próximo. A lista em si só conhece o primeiro nó (a cabeça).

Isso inverte os custos. Inserir ou remover no começo é O(1): cria um nó e aponta ele para a antiga cabeça. Inserir depois de um nó que você já tem em mãos também é O(1), basta trocar dois ponteiros. Mas acessar o item de índice 500 exige andar 500 nós: O(n). Não existe a conta de endereço, porque os nós não estão lado a lado.

Na prática, listas ligadas perdem mais do que parecem. Cada nó carrega o custo extra do ponteiro, e nós espalhados pela memória aproveitam mal o cache do processador, enquanto um array é lido em blocos. Em geral, prefira array dinâmico e use lista ligada quando precisar de muitas inserções e remoções em pontos que você já referencia (o C# tem `LinkedList<T>` para isso).

### Pilha: último a entrar, primeiro a sair

Uma pilha (stack) só permite mexer no topo: `push` coloca, `pop` tira. É o comportamento LIFO (last in, first out), como uma pilha de pratos. O botão desfazer do editor e a própria pilha de chamadas que você estudou funcionam assim. Uma `list` do Python já é uma boa pilha: `append` e `pop()` no final são O(1).

### Fila: primeiro a entrar, primeiro a sair

Uma fila (queue) insere num lado e remove do outro: FIFO (first in, first out), como a fila do banco. Serve para processar tarefas na ordem de chegada. Aqui mora uma armadilha clássica que veremos na prática.

### Tabela de complexidades

| Operação | Array / array dinâmico | Lista ligada | `deque` |
|---|---|---|---|
| Acesso por índice | O(1) | O(n) | O(n) no meio, O(1) nas pontas |
| Inserir no final | O(1) amortizado | O(1) com ponteiro para a cauda | O(1) |
| Inserir no começo | O(n) | O(1) | O(1) |
| Inserir no meio | O(n) | O(1) se já tem o nó, O(n) para achar | O(n) |
| Remover do final | O(1) | O(1) na duplamente ligada | O(1) |
| Remover do começo | O(n) | O(1) | O(1) |
| Buscar um valor | O(n) | O(n) | O(n) |

## Na prática

Vamos usar uma pilha para resolver um problema real: verificar se os parênteses, colchetes e chaves de um texto estão balanceados. A ideia é que todo símbolo de abertura fica esperando o seu fechamento, e o último que abriu tem que ser o primeiro a fechar. Isso é exatamente LIFO.

```python
PARES = {")": "(", "]": "[", "}": "{"}


def balanceado(texto):
    pilha = []
    for char in texto:
        if char in "([{":
            pilha.append(char)
        elif char in PARES:
            if not pilha or pilha.pop() != PARES[char]:
                return False
    return not pilha


print(balanceado("(a[b]{c})"))
print(balanceado("(a[b)]"))
print(balanceado("(("))
```

```text
True
False
False
```

Acompanhe o segundo caso à mão. Lemos `(` e empilhamos. Lemos `[` e empilhamos; a pilha é `["(", "["]`. Chega `)`: tiramos o topo, que é `[`, mas `)` pede `(`. Deu errado, retorna `False`. No terceiro caso nenhum fechamento aparece, então a pilha termina com dois itens, e o `return not pilha` pega isso. Cada caractere é empilhado e desempilhado no máximo uma vez, então o algoritmo é O(n).

Agora a fila. O jeito ingênuo em Python é usar `list` e tirar do começo com `pop(0)`. Funciona, mas lembre do array: remover o primeiro item obriga todos os outros a andar uma casa para a esquerda. Isso é O(n) a cada remoção, e processar uma fila de n itens vira O(n²). O módulo `collections` tem o `deque` (lê-se "deck"), que foi feito para inserir e remover nas duas pontas em O(1).

```python
from collections import deque

fila = deque()
fila.append("pedido 1")
fila.append("pedido 2")
fila.append("pedido 3")

while fila:
    atual = fila.popleft()
    print("processando", atual)
```

```text
processando pedido 1
processando pedido 2
processando pedido 3
```

Em C# a separação já vem pronta nos tipos: `Stack<T>` e `Queue<T>`, ambos com operações principais em O(1).

```csharp
var pilha = new Stack<int>();
pilha.Push(1);
pilha.Push(2);
Console.WriteLine(pilha.Pop());

var fila = new Queue<string>();
fila.Enqueue("a");
fila.Enqueue("b");
Console.WriteLine(fila.Dequeue());
```

```text
2
a
```

Repare que o nome da estrutura já comunica a intenção. Quem lê `Queue<T>` sabe que a ordem de chegada importa, sem precisar investigar o código.

## Armadilhas comuns

- **Usar `list.pop(0)` ou `list.insert(0, x)` como fila.** Em listas pequenas ninguém percebe; com centenas de milhares de itens o programa fica lento sem motivo aparente. Use `deque`.
- **Achar que lista ligada é sempre melhor para inserir.** A inserção é O(1) só se você já tem o nó; encontrar a posição continua O(n). E o cache costuma favorecer o array.
- **Confundir O(1) amortizado com O(1) sempre.** Um `append` específico pode demorar porque disparou uma realocação. Para quase todo código isso é irrelevante, mas em sistemas com requisito de latência importa. Se você sabe o tamanho final, `new List<T>(capacidade)` evita as realocações.
- **Chamar `pop()` numa pilha vazia.** Em Python isso levanta `IndexError`; em C#, `InvalidOperationException`. Sempre verifique antes, como fizemos com `if not pilha`.
- **Modificar uma lista enquanto percorre ela com `for`.** Remover itens durante a iteração faz o laço pular elementos. Construa uma lista nova ou percorra uma cópia.

## Recuperação ativa

1. Por que acessar o item de índice `i` num array é O(1), mas numa lista ligada é O(n)? Explique usando endereços de memória.
2. O que significa dizer que `append` num array dinâmico é O(1) amortizado? Mostre com um exemplo numérico por que a média fica constante.
3. Descreva, passo a passo, o que a pilha contém ao verificar a string `{[()]}`.
4. Por que `list.pop(0)` é O(n) e qual estrutura você usaria no lugar? Qual seria o custo total de processar uma fila de n itens em cada caso?
5. Cite uma situação em que uma lista ligada é uma escolha melhor que um array dinâmico, e um motivo pelo qual ela costuma perder na prática.

## Para ir além

- [Documentação do `collections.deque`](https://docs.python.org/pt-br/3/library/collections.html#collections.deque)
- [TimeComplexity, wiki oficial do Python](https://wiki.python.org/moin/TimeComplexity)
- [Classe `List<T>` na documentação da Microsoft](https://learn.microsoft.com/pt-br/dotnet/api/system.collections.generic.list-1)
- [Array dinâmico na Wikipedia](https://en.wikipedia.org/wiki/Dynamic_array)
