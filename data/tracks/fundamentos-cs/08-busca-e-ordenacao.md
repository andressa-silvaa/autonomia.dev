# Busca e ordenação

> **Objetivo:** implementar busca binária sem erros de limite, explicar por que merge sort é O(n log n) e decidir com segurança quando usar a ordenação da biblioteca e como ordenar por uma chave.

## Por que isso importa

Buscar e ordenar são o melhor laboratório para ver Big-O fazendo diferença. Num milhão de itens, a busca linear pode precisar de um milhão de comparações; a binária, de umas vinte. Uma ordenação O(n²) faz na ordem de um trilhão de operações; uma O(n log n), de vinte milhões. Você quase nunca vai escrever uma ordenação no trabalho, mas precisa saber o que a biblioteca garante e como ordenar pelo campo certo. E escrever busca binária sem bug treina precisão para qualquer laço.

## Conceitos

### Busca linear

Olhar item por item até achar. Funciona com qualquer lista e custa O(n) no pior caso. É o que o `in` faz numa lista.

### Busca binária

Se a lista está **ordenada**, dá para fazer muito melhor. Olhe o item do meio. Se ele é o que você procura, acabou. Se é maior, o alvo só pode estar na metade da esquerda; se é menor, só pode estar na da direita. A cada passo, metade dos candidatos é descartada. Partindo de n itens, depois de k passos sobram n / 2^k, e isso chega a 1 quando k = log₂ n. Por isso a busca binária é O(log n).

O pré-requisito é inegociável: numa lista desordenada, o algoritmo devolve respostas erradas sem avisar.

### Ordenação por seleção e por inserção

São os algoritmos que você inventaria sozinho, e os dois são O(n²).

- **Seleção:** ache o menor e coloque na posição 0; ache o menor do que sobrou e coloque na posição 1; e assim por diante. São cerca de n²/2 comparações, mesmo com a lista já ordenada.
- **Inserção:** como organizar cartas na mão: deslize cada item para a esquerda até o lugar certo. No pior caso (lista invertida) é O(n²), mas numa lista quase ordenada cada item anda pouco e o custo fica perto de O(n).

### Merge sort: dividir e conquistar

O merge sort usa a recursão do módulo anterior. O raciocínio é o salto de fé: divida a lista em duas metades, **confie** que a chamada recursiva ordena cada uma, e depois intercale (merge) as duas metades ordenadas numa só. O caso base é uma lista com zero ou um item, que já está ordenada.

Intercalar duas listas ordenadas é linear: compare a frente de cada uma, tire a menor, repita. Dividir ao meio até pedaços de tamanho 1 dá log n níveis, e em cada nível os merges passam pelos n itens uma vez: O(n log n), em qualquer caso. O preço é memória extra O(n) para as listas intercaladas.

### Quicksort, em linhas gerais

O quicksort escolhe um item como **pivô**, deixa os menores à esquerda e os maiores à direita, e repete recursivamente em cada lado. Em média é O(n log n) e muito rápido, porque trabalha dentro do próprio array. Mas se o pivô for sempre o pior possível (o primeiro item de uma lista já ordenada, por exemplo), as divisões ficam desequilibradas e ele degrada para O(n²).

### Estabilidade

Uma ordenação é **estável** quando itens com a mesma chave mantêm a ordem relativa que tinham antes. Ordene pedidos por data e depois, de forma estável, por cliente: os pedidos de cada cliente continuam em ordem de data. Merge sort e inserção são estáveis; seleção e quicksort, na forma clássica, não.

### O que as bibliotecas usam

| Ferramenta | Algoritmo | Estável? | Pior caso |
|---|---|---|---|
| `sorted()` e `list.sort()` do Python | Timsort (híbrido de merge sort e inserção) | Sim | O(n log n) |
| `Array.Sort` e `List<T>.Sort` do C# | Introsort (quicksort que troca para heapsort e inserção quando precisa) | Não | O(n log n) |
| `OrderBy` do LINQ | Ordenação estável própria | Sim | O(n log n) |

O Timsort aproveita trechos já ordenados, por isso é tão rápido em listas parcialmente ordenadas.

### Implementar ou usar o da biblioteca

Implemente para aprender. No código de verdade, use o da biblioteca: é testado e otimizado. Até a busca binária tem versão pronta em Python, o módulo `bisect`.

## Na prática

Começamos pela busca binária iterativa. Ela devolve o índice do alvo, ou -1 se não existir.

```python
def busca_binaria(itens, alvo):
    esquerda = 0
    direita = len(itens) - 1
    while esquerda <= direita:
        meio = (esquerda + direita) // 2
        if itens[meio] == alvo:
            return meio
        if itens[meio] < alvo:
            esquerda = meio + 1
        else:
            direita = meio - 1
    return -1


numeros = [3, 8, 15, 23, 42, 57, 91]
print(busca_binaria(numeros, 42))
print(busca_binaria(numeros, 10))
```

```text
4
-1
```

Cada detalhe evita um erro de limite, o famoso off-by-one. `direita` começa em `len - 1`, o último índice válido. A condição é `<=` porque, quando `esquerda == direita`, ainda sobra um candidato; com `<`, ele seria pulado. Os ajustes são `meio + 1` e `meio - 1` porque o meio já foi verificado; com `esquerda = meio`, o intervalo pode parar de encolher e o laço nunca termina. Rastreie a busca por 10: o meio é o índice 3 (valor 23), maior, então `direita = 2`; o meio passa a ser 1 (valor 8), menor, então `esquerda = 2`; o meio é 2 (valor 15), maior, `direita = 1`. Agora `esquerda > direita`, não sobrou candidato, e devolvemos -1.

Em C#, com índices enormes, `esquerda + direita` pode estourar o `int`; a forma segura é `esquerda + (direita - esquerda) / 2`. Em Python inteiros não estouram.

Agora o merge sort. A função principal é só a descrição do algoritmo; o trabalho fica no merge.

```python
def merge_sort(itens):
    if len(itens) <= 1:
        return itens
    meio = len(itens) // 2
    esquerda = merge_sort(itens[:meio])
    direita = merge_sort(itens[meio:])
    return intercalar(esquerda, direita)


def intercalar(a, b):
    resultado = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            resultado.append(a[i])
            i += 1
        else:
            resultado.append(b[j])
            j += 1
    resultado.extend(a[i:])
    resultado.extend(b[j:])
    return resultado


print(merge_sort([38, 27, 43, 3, 9, 82, 10]))
```

```text
[3, 9, 10, 27, 38, 43, 82]
```

O `<=` no `intercalar` torna a ordenação estável: no empate, sai primeiro o item da esquerda, que veio antes. Os `extend` copiam o que sobrou quando uma das listas acaba.

No dia a dia, o que você usa é ordenar por chave. O parâmetro `key` recebe uma função que extrai de cada item o valor comparado.

```python
pessoas = [
    {"nome": "Bia", "idade": 31},
    {"nome": "Caio", "idade": 25},
    {"nome": "Ana", "idade": 31},
]

por_idade = sorted(pessoas, key=lambda p: p["idade"])
print([p["nome"] for p in por_idade])

por_idade_e_nome = sorted(pessoas, key=lambda p: (p["idade"], p["nome"]))
print([p["nome"] for p in por_idade_e_nome])
```

```text
['Caio', 'Bia', 'Ana']
['Caio', 'Ana', 'Bia']
```

No primeiro caso, Bia e Ana empatam e, como o Timsort é estável, mantêm a ordem original. No segundo, a chave é uma tupla, comparada campo a campo: idade, depois nome. `reverse=True` inverte a ordem. `sorted()` devolve uma lista nova; `list.sort()` ordena no lugar e devolve `None`.

Em C#, o equivalente idiomático é o LINQ:

```csharp
var pessoas = new[]
{
    new { Nome = "Bia", Idade = 31 },
    new { Nome = "Caio", Idade = 25 },
    new { Nome = "Ana", Idade = 31 },
};

var ordenadas = pessoas.OrderBy(p => p.Idade).ThenBy(p => p.Nome);
Console.WriteLine(string.Join(", ", ordenadas.Select(p => p.Nome)));
```

```text
Caio, Ana, Bia
```

O `ThenBy` faz o papel do segundo campo da tupla. Diferente de `Array.Sort`, `OrderBy` não altera o original: produz uma nova sequência.

## Armadilhas comuns

- **Busca binária em dados desordenados.** Não dá erro, só devolve a resposta errada. Ordene antes ou use busca linear.
- **Off-by-one nos limites.** `<` no lugar de `<=`, ou `direita = len(itens)`, fazem a busca pular um candidato ou acessar índice inválido. Teste com lista vazia, com um item e com o alvo nas pontas.
- **Fazer `lista = lista.sort()`.** O `sort()` devolve `None`, e você perde a lista. Use `lista.sort()` sozinho ou `lista = sorted(lista)`.
- **Contar com estabilidade em `Array.Sort`.** No C#, itens empatados podem trocar de ordem. Se a ordem original importa, use `OrderBy`.
- **Ordenar para achar um único item.** Ordenar custa O(n log n); uma busca linear custa O(n). Ordenar só compensa se você vai buscar muitas vezes nos mesmos dados.

## Recuperação ativa

1. Por que a busca binária é O(log n)? Explique com o que acontece com o número de candidatos a cada passo.
2. Na busca binária iterativa, por que a condição do laço é `esquerda <= direita` e não `esquerda < direita`? E por que os ajustes são `meio + 1` e `meio - 1`?
3. Explique de onde vêm o "n" e o "log n" no custo O(n log n) do merge sort.
4. O que é uma ordenação estável? Dê um exemplo em que isso muda o resultado.
5. Por que a ordenação por inserção fica rápida em listas quase ordenadas, e qual algoritmo de biblioteca tira proveito disso?
6. Você precisa ordenar uma lista de produtos por categoria e, dentro de cada categoria, por preço decrescente. Como faria em Python e em C#?

## Para ir além

- [Guia de ordenação na documentação do Python](https://docs.python.org/pt-br/3/howto/sorting.html)
- [Módulo `bisect` na documentação do Python](https://docs.python.org/pt-br/3/library/bisect.html)
- [Método `Enumerable.OrderBy` na documentação da Microsoft](https://learn.microsoft.com/pt-br/dotnet/api/system.linq.enumerable.orderby)
- [Busca binária na Wikipedia](https://pt.wikipedia.org/wiki/Pesquisa_bin%C3%A1ria)
