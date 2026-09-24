# Tabelas hash (dicionários e conjuntos)

> **Objetivo:** explicar como um dicionário encontra uma chave sem percorrer tudo, reconhecer quando trocar uma lista por um `set` ou `dict` e evitar os erros de chave que quebram essa mágica.

## Por que isso importa

No módulo anterior você viu que buscar um valor numa lista é O(n): não tem jeito, é olhar um por um. Mas o array tem um superpoder, o acesso O(1) por índice. A tabela hash é a ideia de transformar a própria chave num índice. Se "maria@email.com" virasse o número 7, bastaria olhar a casa 7 do array. É isso que `dict` e `set` fazem, e é por isso que eles aparecem em quase toda otimização séria de código: contar ocorrências, remover duplicados, cruzar duas listas, fazer cache. Entender como funciona por dentro também explica aqueles erros estranhos, como `TypeError: unhashable type: 'list'`.

## Conceitos

### Função hash

Uma função hash recebe um valor e devolve um número inteiro. Ela precisa ser **determinística**: o mesmo valor sempre gera o mesmo número. Idealmente, valores diferentes geram números bem espalhados. Em Python você vê isso com `hash()`:

```python
print(hash(42))
print(hash("abc") == hash("abc"))
```

```text
42
True
```

O número de uma string muda entre execuções do Python (é uma proteção de segurança), mas dentro da mesma execução é estável, e só isso importa para a tabela.

### Buckets: do hash ao índice

A tabela é um array de **buckets** (baldes). Para guardar uma chave, calculamos `hash(chave) % tamanho_do_array` e isso dá a posição. Com 8 buckets, uma chave cujo hash é 42 vai para o bucket 42 % 8 = 2. Para buscar, repetimos a mesma conta e olhamos direto no bucket 2. Nenhuma varredura.

### Colisões

Com infinitas chaves possíveis e poucos buckets, duas chaves diferentes vão cair no mesmo lugar. Hash 42 e hash 50 dão, os dois, bucket 2 numa tabela de 8. Isso é uma **colisão**, e ela é inevitável. Existem duas famílias de solução:

- **Encadeamento:** cada bucket guarda uma pequena lista de pares chave-valor. Na colisão, o novo par entra nessa lista. Na busca, vamos ao bucket e comparamos as chaves da lista uma por uma.
- **Endereçamento aberto:** cada bucket guarda no máximo um par. Se o lugar está ocupado, a tabela tenta outro bucket seguindo uma regra fixa (o próximo, ou um salto calculado) até achar vaga. A busca segue a mesma sequência de tentativas. O `dict` do CPython usa uma variação disso.

Repare num detalhe importante: como chaves diferentes podem ter o mesmo hash, a tabela sempre confirma com uma comparação de igualdade. O hash só diz onde procurar; a igualdade diz se achou.

### Fator de carga e redimensionamento

O **fator de carga** é a razão entre itens guardados e número de buckets. Com 6 itens em 8 buckets, ele é 0,75. Quanto mais cheia a tabela, mais colisões e mais comparações por busca. Por isso, ao passar de um limite, a tabela aloca um array maior e reinsere todos os itens, recalculando `hash % novo_tamanho`. É a mesma lógica do array dinâmico: uma operação O(n) de vez em quando, que dá O(1) amortizado por inserção.

### Por que O(1) em média e O(n) no pior caso

Com uma boa função hash e fator de carga controlado, cada bucket tem poucos itens, em média uma quantidade constante. Buscar, inserir e remover custam O(1) em média. Mas se todas as chaves colidirem no mesmo bucket (função hash ruim, ou dados escolhidos por alguém mal-intencionado), a tabela degenera numa lista e a busca vira O(n). Na prática, com os tipos padrão, o caso médio é o que você vai ver.

### Dicionários e conjuntos

Um **dicionário** guarda pares chave-valor: `dict` em Python, `Dictionary<TKey, TValue>` em C#. Um **conjunto** guarda só chaves, sem valor, e serve para responder "isso está aqui?" e para eliminar duplicados: `set` em Python, `HashSet<T>` em C#. Por baixo, os dois são tabelas hash.

### Chaves precisam de hash estável

Se você coloca uma chave na tabela e depois ela muda, o hash muda também. A tabela vai procurar no bucket novo, mas a chave está guardada no antigo. Ela fica perdida lá dentro. Por isso o Python só aceita como chave objetos **hashable**, na prática os imutáveis: `int`, `str`, `tuple` de imutáveis, `frozenset`. Uma `list` não pode ser chave.

Em C# a regra é um contrato: se você sobrescreve `Equals`, precisa sobrescrever `GetHashCode` de forma coerente. Dois objetos iguais segundo `Equals` **têm** que retornar o mesmo `GetHashCode`. O contrário não é exigido: hashes iguais podem ser de objetos diferentes (é a colisão). Em Python o par equivalente é `__eq__` e `__hash__`.

## Na prática

Um caso que aparece o tempo todo: você tem uma lista de pedidos e uma lista de clientes bloqueados, e quer saber quais pedidos são de clientes bloqueados.

```python
pedidos = ["ana", "bruno", "carla", "ana", "davi"]
bloqueados = ["carla", "davi"]

suspeitos = [p for p in pedidos if p in bloqueados]
print(suspeitos)
```

```text
['carla', 'davi']
```

O código está certo, mas `p in bloqueados` numa lista é uma busca linear. Para cada um dos n pedidos, percorremos até m bloqueados: O(n·m), que vira O(n²) quando as listas têm tamanhos parecidos. Com 100 mil de cada, são 10 bilhões de comparações. A mudança é uma linha:

```python
pedidos = ["ana", "bruno", "carla", "ana", "davi"]
bloqueados = set(["carla", "davi"])

suspeitos = [p for p in pedidos if p in bloqueados]
print(suspeitos)
```

```text
['carla', 'davi']
```

Montar o `set` custa O(m), e cada `in` agora é O(1) em média. O total cai para O(n + m). Mesmo resultado, ordem de grandeza completamente diferente.

Outro padrão essencial é a contagem de frequência. Queremos saber quantas vezes cada palavra aparece num texto.

```python
texto = "o rato roeu a roupa do rei o rato fugiu"

contagem = {}
for palavra in texto.split():
    contagem[palavra] = contagem.get(palavra, 0) + 1

print(contagem["rato"])
print(contagem["rei"])
```

```text
2
1
```

O `get(palavra, 0)` devolve a contagem atual ou zero se a palavra ainda não apareceu. Cada palavra gera uma busca e uma escrita, as duas O(1) em média, então o texto inteiro é processado em O(n). A biblioteca padrão tem uma ferramenta pronta para isso, `collections.Counter`, que faz a mesma coisa e ainda oferece `most_common()`:

```python
from collections import Counter

contagem = Counter("o rato roeu a roupa do rei o rato fugiu".split())
print(contagem.most_common(2))
```

```text
[('o', 2), ('rato', 2)]
```

Em C#, a contagem fica assim. `TryGetValue` faz a busca uma vez só, em vez de perguntar `ContainsKey` e depois ler:

```csharp
var texto = "o rato roeu a roupa do rei o rato fugiu";
var contagem = new Dictionary<string, int>();

foreach (var palavra in texto.Split(' '))
{
    contagem.TryGetValue(palavra, out var atual);
    contagem[palavra] = atual + 1;
}

Console.WriteLine(contagem["rato"]);
```

```text
2
```

Quando `TryGetValue` não acha a chave, `atual` fica com o valor padrão de `int`, que é zero, e a lógica funciona igual à versão em Python.

## Armadilhas comuns

- **Usar lista como chave.** `{[1, 2]: "x"}` gera `TypeError: unhashable type: 'list'`. Converta para `tuple` se a sequência não vai mudar.
- **Sobrescrever `Equals` sem `GetHashCode` em C#.** O compilador avisa, e o `Dictionary` passa a não achar objetos que você jura que estão lá. Para tipos de dados simples, um `record` já gera os dois de forma coerente.
- **Mudar um objeto que já é chave.** Se o hash depende de um campo mutável e o campo muda, a chave some da tabela. Chave deve ser imutável na prática.
- **Acessar chave inexistente com colchetes.** `d["x"]` levanta `KeyError` em Python e `KeyNotFoundException` em C#. Use `get` ou `TryGetValue` quando a ausência é esperada.
- **Converter para `set` e esperar ordem.** `set` não preserva a ordem de inserção. O `dict` do Python preserva desde a versão 3.7, mas isso é garantia da linguagem, não propriedade de tabelas hash em geral, e `Dictionary` do C# não promete ordem.

## Recuperação ativa

1. Descreva o caminho que uma chave percorre desde a chamada `d["ana"] = 5` até ser guardada num bucket.
2. O que é uma colisão e por que a tabela precisa comparar chaves com igualdade mesmo depois de achar o bucket?
3. Explique o que é fator de carga e o que acontece quando ele passa do limite. Por que isso não estraga o custo médio da inserção?
4. Em que situação uma busca numa tabela hash vira O(n)?
5. Por que uma `list` não pode ser chave de `dict`, mas uma `tuple` de inteiros pode? Qual é a regra equivalente em C#?
6. Você tem duas listas de 50 mil e-mails e precisa encontrar os que aparecem nas duas. Como faria e qual o custo?

## Para ir além

- [Dicionários no tutorial oficial do Python](https://docs.python.org/pt-br/3/tutorial/datastructures.html#dictionaries)
- [Método `Object.GetHashCode` na documentação da Microsoft](https://learn.microsoft.com/pt-br/dotnet/api/system.object.gethashcode)
- [Tabela de dispersão na Wikipedia](https://pt.wikipedia.org/wiki/Tabela_de_dispers%C3%A3o)
