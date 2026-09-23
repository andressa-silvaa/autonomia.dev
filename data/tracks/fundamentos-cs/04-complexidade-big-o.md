# Complexidade de algoritmos (Big-O)

> **Objetivo:** estimar como o tempo e a memória de um trecho de código crescem com o tamanho da entrada, classificá-lo em notação Big-O e identificar loops escondidos que tornam um programa lento.

## Por que isso importa

Você testa uma função com 100 itens e ela responde na hora. Em produção, com 1 milhão de itens, trava por meia hora. O código não mudou; a entrada, sim. Big-O é a ferramenta que permite prever isso **antes** de acontecer, olhando só para o código.

Também é a linguagem comum para discutir soluções: "isso é quadrático, dá para fazer linear" comunica muito em poucas palavras, numa revisão de código ou numa entrevista.

## Conceitos

### Medir crescimento, não segundos

Cronometrar diz quanto um programa demorou **naquela máquina, com aqueles dados, naquele momento**. Mude o processador ou a versão do Python, e o número muda. Até a mesma operação custa tempos diferentes dependendo de onde o dado está, como vimos no primeiro módulo.

Big-O faz outra pergunta: **se a entrada dobrar, o que acontece com o trabalho?** Se o trabalho dobra, o crescimento é linear. Se quadruplica, é quadrático. Essa resposta não depende da máquina.

### Contar operações

O método é contar quantas vezes as operações básicas (uma comparação, uma soma, um acesso a posição) são executadas em função de **n**, o tamanho da entrada. Pense nesta função que soma uma lista:

```python
def somar(numeros):
    total = 0
    for x in numeros:
        total += x
    return total
```

Uma atribuição antes do loop, uma soma para cada um dos n elementos, um retorno no final: cerca de n + 2 operações. O que importa é que o trabalho cresce na mesma proporção que n.

### As regras de simplificação

Big-O descreve o comportamento para n grande, então duas regras simplificam a contagem:

1. **Descarte constantes multiplicativas.** 3n e n são ambos O(n). A constante depende de detalhes de implementação; o formato da curva, não.
2. **Descarte termos de menor ordem.** Em n² + 5n + 100, com n = 1 milhão, o n² vale 10¹² e o resto é ruído. Fica O(n²).

Então n + 2 vira O(n).

### As classes mais comuns

- **O(1), constante:** o trabalho não depende de n. Acessar `lista[i]` ou ler `len(lista)`.
- **O(log n), logarítmica:** a cada passo, o problema é cortado pela metade. Dobrar n acrescenta só um passo. Busca binária é o exemplo clássico.
- **O(n), linear:** percorre cada elemento uma vez (ou um número fixo de vezes). Somar, achar o máximo, `x in lista`.
- **O(n log n):** típico dos bons algoritmos de ordenação, incluindo o `sorted` do Python.
- **O(n²), quadrática:** para cada elemento, percorre todos os outros. Dois loops aninhados sobre a mesma entrada.
- **O(2ⁿ), exponencial:** cada elemento a mais dobra o trabalho. Aparece ao testar todas as combinações possíveis.

### Pior, médio e melhor caso

O mesmo algoritmo pode fazer quantidades diferentes de trabalho para entradas do mesmo tamanho. Procurar um valor numa lista:

- **Melhor caso:** está na primeira posição. Uma comparação.
- **Pior caso:** não está na lista. n comparações.
- **Caso médio:** supondo posições igualmente prováveis, cerca de n/2, que ainda é O(n).

Quando alguém diz só "é O(n)", quase sempre está falando do **pior caso**, porque é a garantia que importa: o sistema precisa aguentar a entrada ruim.

### Complexidade de espaço

A mesma análise vale para memória: quanto espaço **extra** o algoritmo usa em função de n? `somar` usa O(1) de espaço extra: só `total`, não importa o tamanho da lista. Já uma função que monta uma lista nova com o dobro de cada elemento usa O(n). Muitas vezes dá para trocar um pelo outro: gastar memória para economizar tempo, como veremos na armadilha do final.

## Na prática

**O(log n): busca binária.** Numa lista ordenada, olhe o meio. Se o alvo é maior, descarte a metade esquerda; se é menor, a direita. Repita.

```python
def busca_binaria(ordenada, alvo):
    inicio, fim = 0, len(ordenada) - 1
    while inicio <= fim:
        meio = (inicio + fim) // 2
        if ordenada[meio] == alvo:
            return meio
        if ordenada[meio] < alvo:
            inicio = meio + 1
        else:
            fim = meio - 1
    return -1


print(busca_binaria([2, 5, 8, 12, 16, 23, 38], 23))
```

```text
5
```

Com 1 milhão de elementos, quantas vezes dá para cortar pela metade até sobrar um? Cerca de 20, porque 2²⁰ é aproximadamente 1 milhão. Vinte comparações em vez de um milhão.

**O(n²): procurar duplicatas comparando todos com todos.**

```python
def tem_duplicata(itens):
    for i in range(len(itens)):
        for j in range(i + 1, len(itens)):
            if itens[i] == itens[j]:
                return True
    return False


print(tem_duplicata([3, 1, 4, 1, 5]))
```

```text
True
```

O loop externo roda n vezes; o interno, em média, n/2. Dá cerca de n²/2 comparações no pior caso. Descartando a constante: O(n²).

**O(n log n): ordenar primeiro.** Depois de ordenar, duplicatas ficam vizinhas, e uma passada linear resolve:

```python
def tem_duplicata_ordenando(itens):
    ordenados = sorted(itens)
    for i in range(len(ordenados) - 1):
        if ordenados[i] == ordenados[i + 1]:
            return True
    return False
```

Ordenar custa O(n log n) e a passada custa O(n). Pela regra dos termos menores, o total é O(n log n). Repare no custo de espaço: `sorted` cria uma lista nova, então usamos O(n) de memória extra.

**O(2ⁿ): Fibonacci ingênuo.**

```python
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


print(fib(20))
```

```text
6765
```

Cada chamada dispara outras duas, que disparam outras duas, e muitos valores são recalculados várias vezes. O número de chamadas cresce exponencialmente (a base exata é cerca de 1,6, mas a classificação usual é O(2ⁿ)). `fib(30)` já demora perceptivelmente; `fib(50)` você não vai querer esperar.

### Tabela comparativa

Operações aproximadas por classe:

| Classe | n = 10 | n = 1.000 | n = 1.000.000 |
| --- | --- | --- | --- |
| O(1) | 1 | 1 | 1 |
| O(log n) | ~3 | ~10 | ~20 |
| O(n) | 10 | 1.000 | 1.000.000 |
| O(n log n) | ~33 | ~10.000 | ~20.000.000 |
| O(n²) | 100 | 1.000.000 | 1.000.000.000.000 |
| O(2ⁿ) | 1.024 | ~10³⁰¹ | um número com ~301 mil dígitos |

Para ter noção: a 1 bilhão de operações simples por segundo, O(n²) com n = 1 milhão leva cerca de 17 minutos. O(n log n), uns 20 milissegundos. E O(2ⁿ) com n = 1.000 não terminaria antes do fim do universo.

### A armadilha: `x in lista` dentro de um loop

Este código parece linear, com um `for` só:

```python
def em_comum(a, b):
    resultado = []
    for x in a:
        if x in b:
            resultado.append(x)
    return resultado
```

O loop está escondido. Em uma lista, `x in b` percorre `b` elemento por elemento até achar, ou até o fim. Com `a` de tamanho n e `b` de tamanho m, o total é O(n × m); se forem do mesmo tamanho, O(n²).

A correção é converter `b` para `set`. Um conjunto é organizado internamente (por *hashing*, assunto do módulo sobre tabelas hash) de forma que a verificação de pertinência custa O(1) em média. Rode o código abaixo no mesmo arquivo em que definiu `em_comum`, para comparar as duas versões:

```python
import time


def em_comum_rapido(a, b):
    conjunto_b = set(b)
    return [x for x in a if x in conjunto_b]


a = list(range(10_000))
b = list(range(10_000, 20_000))

inicio = time.perf_counter()
em_comum(a, b)
print(f"lista: {time.perf_counter() - inicio:.3f} s")

inicio = time.perf_counter()
em_comum_rapido(a, b)
print(f"set:   {time.perf_counter() - inicio:.3f} s")
```

Os números variam com a máquina, mas a diferença é algo nesta ordem:

```text
lista: 1.400 s
set:   0.001 s
```

Como as listas não têm elementos em comum, a versão com lista cai sempre no pior caso: 10 mil × 10 mil = 100 milhões de comparações. A versão com `set` gasta O(m) para montar o conjunto e O(n) para verificar, O(n + m) no total, em troca de O(m) de memória extra. Com 100 mil itens em cada lista, a primeira levaria minutos; a segunda, milissegundos.

## Armadilhas comuns

- **Contar loops visíveis e ignorar os escondidos.** `x in lista`, `lista.index(x)`, `lista.remove(x)` e `lista.insert(0, x)` são O(n) cada. Dentro de um loop, viram O(n²).
- **Achar que O(1) significa "instantâneo".** Significa que não cresce com n. Uma operação O(1) lenta pode perder de uma O(n) rápida para n pequeno.
- **Otimizar sem medir.** Big-O diz como cresce; para n pequeno, a constante pode dominar. Escolha a classe certa e depois meça com dados reais.
- **Esquecer do espaço.** Converter para `set` ou criar listas intermediárias custa memória. Com dados enormes, isso pode ser o gargalo.
- **Somar loops aninhados em vez de multiplicar.** Dois loops em sequência dão O(n + n) = O(n). Um dentro do outro dá O(n × n) = O(n²).

## Recuperação ativa

1. Por que Big-O mede crescimento em vez de tempo em segundos?
2. Simplifique para notação Big-O: 4n² + 10n + 7. Quais regras você aplicou?
3. Por que a busca binária precisa de uma lista ordenada, e por que ela é O(log n)?
4. Dê um exemplo de melhor e pior caso ao procurar um elemento numa lista não ordenada.
5. Um código tem um único `for` sobre uma lista e, dentro dele, `if x in outra_lista`. Qual a complexidade, e como reduzi-la?
6. O que significa dizer que uma função usa O(1) de espaço extra?

## Para ir além

- [Time Complexity — Python Wiki](https://wiki.python.org/moin/TimeComplexity)
- [Grande-O — Wikipédia](https://pt.wikipedia.org/wiki/Grande-O)
- [Big O notation — Wikipedia](https://en.wikipedia.org/wiki/Big_O_notation)
- [Algoritmo de busca binária — Wikipédia](https://pt.wikipedia.org/wiki/Pesquisa_bin%C3%A1ria)
