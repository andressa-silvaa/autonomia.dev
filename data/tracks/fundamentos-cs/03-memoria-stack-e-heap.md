# Memória: stack e heap

> **Objetivo:** explicar onde os dados do seu programa vivem, qual a diferença entre tipos por valor e por referência, e reconhecer (e evitar) bugs de aliasing e stack overflow.

## Por que isso importa

No primeiro módulo vimos que um processo tem seu próprio espaço de memória na RAM. Mas esse espaço não é um bloco sem forma: ele é organizado em regiões com regras diferentes, e duas delas afetam diretamente o código que você escreve todo dia, a **stack** (pilha) e a **heap** (monte).

Você altera uma lista dentro de uma função e a lista "original" também muda. Copia um objeto em C#, mexe na cópia e descobre que mexeu no original. Escreve uma recursão e o programa morre com erro de pilha. É tudo a mesma história, vista de ângulos diferentes.

## Conceitos

### A stack e os stack frames

Cada thread tem uma região de memória chamada **stack**. Ela funciona como uma pilha de pratos: você só coloca e tira do topo.

Toda vez que uma função é chamada, o runtime empilha um **stack frame** (quadro de pilha) com o que aquela chamada precisa: os parâmetros, as variáveis locais e o endereço para onde voltar quando ela terminar. Quando a função retorna, o frame é desempilhado e aquele espaço fica livre na hora.

Se `principal()` chama `calcular()`, que chama `somar()`, enquanto `somar` roda há três frames, com `somar` no topo. Cada retorno desempilha um. Um traceback mostra justamente essa sequência de frames empilhados.

A stack é rápida, mas é **pequena** (tipicamente 1 MB por thread no Windows e 8 MB no Linux) e os dados nela **morrem quando a função retorna**.

### A heap e a alocação dinâmica

E um dado que precisa sobreviver à função que o criou, ou cujo tamanho só se sabe durante a execução? Para isso existe a **heap**: uma região grande onde o programa pede blocos de memória sob demanda. Isso se chama **alocação dinâmica**.

A heap é flexível, mas tem custo: é preciso encontrar espaço livre, e alguém precisa devolver esse espaço quando ele não for mais necessário. Em C, você faz isso à mão. Em Python e C#, quem cuida é o coletor de lixo, que veremos adiante.

A ligação entre as duas regiões é a **referência**: uma variável local na stack guarda o endereço de um objeto que mora na heap.

### Tipos por valor e por referência em C#

O C# deixa essa distinção explícita.

- **Tipos por valor** (`int`, `double`, `bool`, `decimal` e qualquer `struct`): a variável **contém o próprio dado**. Atribuir uma variável a outra copia o valor inteiro.
- **Tipos por referência** (`class`, `string`, arrays, `List<T>`): a variável contém uma **referência** para um objeto na heap. Atribuir copia só a referência, e as duas variáveis passam a apontar para o mesmo objeto.

Uma precisão importante: é comum ouvir "struct fica na stack". Isso é verdade para uma variável local do tipo struct, mas uma struct que é campo de uma classe mora dentro daquele objeto, na heap. O que define um tipo por valor é o comportamento de **cópia**, não o endereço.

### Em Python, tudo é objeto (e toda variável é referência)

Python não tem essa divisão. Todo valor, inclusive `int`, é um objeto que vive na heap, e toda variável é apenas um **nome** que referencia um objeto. A atribuição `b = a` nunca copia o objeto: faz `b` apontar para o mesmo lugar que `a`.

Então por que `x = 10; y = x; y += 1` não altera `x`? Porque `int` é **imutável**. O `y += 1` não modifica o objeto 10; cria um novo objeto 11 e faz `y` apontar para ele. Com tipos mutáveis, como `list`, `dict` e `set`, a história muda.

### Aliasing

Quando dois nomes apontam para o mesmo objeto mutável, dizemos que existe **aliasing** (um é "apelido" do outro). Qualquer modificação feita por um nome é vista pelo outro. Isso não é defeito (é o que torna barato passar uma lista grande para uma função); o perigo é esquecer que está acontecendo.

### Garbage collector

Se objetos na heap não são liberados manualmente, quem libera? O **garbage collector** (GC, coletor de lixo). A ideia geral: um objeto que nenhuma parte do programa consegue mais alcançar, por nenhuma cadeia de referências, é lixo e pode ter a memória recuperada.

- **CPython** usa principalmente **contagem de referências**: cada objeto sabe quantas referências apontam para ele e é liberado quando o contador chega a zero. Um coletor extra roda de tempos em tempos para achar ciclos (A aponta para B, B aponta para A, ninguém aponta para eles).
- **.NET** usa um GC **geracional**: periodicamente, ele parte das referências "vivas" (variáveis nas stacks, campos estáticos), marca tudo o que é alcançável e recupera o resto. Objetos novos são verificados com mais frequência, porque a maioria morre jovem.

O GC te livra de liberar memória à mão, mas não de vazamentos: se você guarda objetos numa lista global e nunca remove, eles continuam alcançáveis e nunca são coletados.

### Stack overflow

Como a stack é pequena, empilhar frames demais a esgota. A causa clássica é recursão sem caso base, ou profunda demais. Em C#, isso gera `StackOverflowException`, que **não pode ser capturada** e derruba o processo. Em Python, o interpretador impõe um limite de profundidade antes de chegar lá e lança `RecursionError`.

## Na prática

Comece pelo contraste em C#. Duas estruturas idênticas, uma `struct` e uma `class`:

```csharp
PontoValor v1 = new PontoValor { X = 1 };
PontoValor v2 = v1;
v2.X = 99;
Console.WriteLine(v1.X);

PontoRef r1 = new PontoRef { X = 1 };
PontoRef r2 = r1;
r2.X = 99;
Console.WriteLine(r1.X);

struct PontoValor { public int X; }
class PontoRef { public int X; }
```

```text
1
99
```

Com a struct, `v2 = v1` copiou o dado, e alterar `v2` não tocou em `v1`. Com a classe, `r2 = r1` copiou só a referência, então alterar por `r2` é alterar o único objeto que existe.

Em Python, o mesmo efeito da classe acontece com qualquer objeto mutável. O operador `is` diz se dois nomes apontam para o mesmo objeto:

```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)
print(a is b)

c = list(a)
c.append(5)
print(a)
print(a is c)
```

```text
[1, 2, 3, 4]
True
[1, 2, 3, 4]
False
```

`b` é um apelido de `a`. Já `list(a)` cria uma lista nova com os mesmos elementos, e aí as duas seguem vidas separadas. Atenção: é uma cópia **rasa**. Se os elementos forem, eles mesmos, listas, as internas continuam compartilhadas. Para copiar tudo recursivamente existe `copy.deepcopy`.

Agora o bug clássico. O valor padrão de um parâmetro é criado **uma vez**, quando a função é definida, e não a cada chamada:

```python
def adicionar(item, lista=[]):
    lista.append(item)
    return lista


print(adicionar(1))
print(adicionar(2))
```

```text
[1]
[1, 2]
```

A segunda chamada "lembrou" do 1, porque as duas usaram a mesma lista padrão. A correção idiomática é usar `None` como sentinela e criar a lista dentro da função:

```python
def adicionar(item, lista=None):
    if lista is None:
        lista = []
    lista.append(item)
    return lista


print(adicionar(1))
print(adicionar(2))
```

```text
[1]
[2]
```

Outro primo do mesmo bug é `[[0] * 3] * 3`: parece uma matriz 3×3, mas são três referências para a **mesma** linha. Alterar `matriz[0][0]` muda a primeira coluna inteira. Use `[[0] * 3 for _ in range(3)]`, que cria uma linha nova a cada volta.

Por fim, veja o limite da stack em Python. Esta função chama a si mesma para sempre:

```python
import sys


def descer(n):
    return descer(n + 1)


print(sys.getrecursionlimit())
try:
    descer(0)
except RecursionError as erro:
    print(erro)
```

```text
1000
maximum recursion depth exceeded
```

Cada chamada empilha um frame novo e nenhuma retorna, até o Python interromper perto dos mil frames. Aumentar esse limite com `sys.setrecursionlimit` raramente é a resposta certa; normalmente a solução é reescrever com um loop.

## Armadilhas comuns

- **Achar que `b = a` copia uma lista.** Não copia; cria um apelido. Use `list(a)`, `a.copy()` ou `copy.deepcopy(a)`.
- **Usar objeto mutável como valor padrão de parâmetro.** Use `None` e crie o objeto dentro da função.
- **Repetir "struct vive na stack, class vive na heap" como regra absoluta.** O que importa é a semântica de cópia.
- **Criar structs grandes e mutáveis em C#.** Cada atribuição copia tudo, e alterações feitas numa cópia se perdem silenciosamente. Structs funcionam melhor pequenas e imutáveis.
- **Confiar que o GC evita todo vazamento.** Referências esquecidas em caches e listas globais mantêm objetos vivos.

## Recuperação ativa

1. O que um stack frame guarda, e o que acontece com ele quando a função retorna?
2. Por que dados que precisam sobreviver à função que os criou vão para a heap?
3. Em C#, o que acontece com o original quando você atribui uma `struct` a outra variável e altera a cópia? E com uma `class`?
4. Em Python, por que `y += 1` não altera `x` depois de `y = x` com inteiros, mas `b.append(4)` altera `a` depois de `b = a` com listas?
5. Explique por que `def f(lista=[])` é perigoso e como corrigir.
6. Qual a causa típica de um stack overflow, e como Python e C# reagem a ele?

## Para ir além

- [Tipos de valor — Microsoft Learn](https://learn.microsoft.com/pt-br/dotnet/csharp/language-reference/builtin-types/value-types)
- [Fundamentos da coleta de lixo — Microsoft Learn](https://learn.microsoft.com/pt-br/dotnet/standard/garbage-collection/fundamentals)
- [Por que valores padrão são compartilhados entre objetos? — FAQ de programação do Python](https://docs.python.org/3/faq/programming.html#why-are-default-values-shared-between-objects)
- [Modelo de dados: objetos, valores e tipos — documentação do Python](https://docs.python.org/3/reference/datamodel.html)
