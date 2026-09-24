# Representação de dados

> **Objetivo:** converter números entre decimal, binário e hexadecimal, explicar complemento de dois, overflow, por que `0.1 + 0.2 != 0.3` e como um "ç" vira bytes em UTF-8.

## Por que isso importa

No módulo anterior vimos que a CPU só manipula bits. Mas o seu programa lida com idades, preços, nomes com acento, e alguém precisa decidir como cada coisa vira zeros e uns. Essas decisões vazam para o seu código o tempo todo.

É por isso que um contador em C# fica negativo de repente, que um sistema financeiro com `float` perde centavos e que aparece "AÃ§Ã£o" no lugar de "Ação" num CSV. Nada disso é mistério quando você sabe como os dados são representados.

## Conceitos

### Bits e bytes

Um **bit** é um dígito que vale 0 ou 1. Um **byte** é um grupo de 8 bits. Com n bits dá para formar 2ⁿ combinações diferentes, então um byte tem 2⁸ = 256 valores possíveis (de 0 a 255 se interpretados como inteiro sem sinal).

O ponto central: **bits não têm significado sozinhos**. O mesmo byte `01000001` pode ser o número 65 ou a letra "A". Quem decide é o tipo que o programa usa para interpretá-lo.

### Binário

No decimal, cada posição vale uma potência de 10. No binário, cada posição vale uma potência de 2. Para ler `1101`, some as posições que têm 1:

| Posição | 2³ | 2² | 2¹ | 2⁰ |
| --- | --- | --- | --- | --- |
| Valor da posição | 8 | 4 | 2 | 1 |
| Dígito | 1 | 1 | 0 | 1 |

8 + 4 + 0 + 1 = **13**.

Para ir de decimal para binário, divida por 2 repetidamente e anote os restos:

1. 13 ÷ 2 = 6, resto **1**
2. 6 ÷ 2 = 3, resto **0**
3. 3 ÷ 2 = 1, resto **1**
4. 1 ÷ 2 = 0, resto **1**

Lendo os restos de baixo para cima: `1101`. Confere.

### Hexadecimal

O hexadecimal (base 16) usa os dígitos 0–9 e as letras A–F (A=10 até F=15). A grande vantagem: **cada dígito hexa corresponde a exatamente 4 bits**, então um byte é sempre dois dígitos hexa.

Converter binário para hexa é agrupar de 4 em 4 a partir da direita. Pegue `00101010`:

1. Separe: `0010` `1010`
2. `0010` = 2 e `1010` = 8 + 2 = 10 = A
3. Resultado: `0x2A`

E de hexa para decimal: `0x2A` = 2 × 16 + 10 = **42**. Da mesma forma, `0xFF` = 15 × 16 + 15 = 255, o maior valor de um byte. O prefixo `0x` é só a convenção para dizer "isto está em hexa".

### Inteiros com sinal e complemento de dois

Como representar números negativos só com bits? A solução usada por praticamente todo processador é o **complemento de dois**. Para obter -5 em 8 bits:

1. Escreva 5 em binário: `00000101`
2. Inverta todos os bits: `11111010`
3. Some 1: `11111011`

Esse é o -5. O bit mais à esquerda funciona como indicador de sinal (1 = negativo), e a beleza do esquema é que a CPU usa o mesmo circuito de soma para positivos e negativos: `00000101 + 11111011` dá `00000000` (o "vai um" que sobra é descartado).

Com n bits, a faixa vai de -2ⁿ⁻¹ até 2ⁿ⁻¹ - 1. Para 8 bits, de -128 a 127. Para o `int` do C#, que tem 32 bits, de -2.147.483.648 a 2.147.483.647.

### Overflow

Se o tipo tem tamanho fixo, o que acontece ao passar do limite? Em complemento de dois, somar 1 ao maior positivo (`01111111` em 8 bits) dá `10000000`, que é o menor negativo. Isso é **overflow**: o valor "dá a volta".

Em Python isso não acontece com `int`, porque o interpretador aumenta automaticamente a quantidade de memória usada pelo número. Em C#, `int` tem 32 bits e ponto.

### Ponto flutuante (IEEE 754)

Para números com parte fracionária, `float` do Python e `double` do C# usam o padrão **IEEE 754 de 64 bits**: 1 bit de sinal, 11 de expoente e 52 de mantissa (os dígitos significativos). É notação científica em base 2: algo como 1,0110... × 2ᵉ.

O problema é que muitas frações simples em decimal são **dízimas periódicas em binário**. Assim como 1/3 vira 0,3333... em decimal, 0,1 vira `0,0001100110011...` em binário, repetindo para sempre. Como só cabem 52 bits, o valor é arredondado. O 0,1 guardado é, na verdade, um pouquinho maior que 0,1; o mesmo vale para 0,2. Somando os dois erros, o resultado fica a um passo de arredondamento do número mais próximo de 0,3, e a comparação falha.

Não é bug do Python nem do C#: acontece em qualquer linguagem que use IEEE 754.

### Decimal para dinheiro

Para valores monetários, use tipos decimais, que representam números em base 10 e guardam 0,1 exatamente. Em Python, `decimal.Decimal`; em C#, `decimal` (128 bits). São mais lentos, mas para dinheiro exatidão vale mais.

### Texto: ASCII, Unicode e UTF-8

**ASCII** é uma tabela antiga que associa 128 caracteres a números de 0 a 127: "A" é 65, "a" é 97, espaço é 32. Não tem "ç", "ã" nem nada fora do inglês.

**Unicode** resolve isso atribuindo um número único, o *code point*, a cada caractere de praticamente todos os sistemas de escrita. Escrevemos como `U+` seguido de hexa: "A" é U+0041, "ç" é U+00E7, "€" é U+20AC.

Mas code point é um número abstrato. Como gravá-lo em bytes? Isso é a **codificação**, e a dominante é o **UTF-8**, que usa uma quantidade variável de bytes:

| Faixa de code points | Bytes em UTF-8 | Exemplo |
| --- | --- | --- |
| U+0000 a U+007F | 1 | "a" vira `61` |
| U+0080 a U+07FF | 2 | "ç" vira `C3 A7` |
| U+0800 a U+FFFF | 3 | "€" vira `E2 82 AC` |
| U+10000 a U+10FFFF | 4 | emojis, por exemplo |

Os primeiros 128 code points ficam idênticos ao ASCII, o que torna o UTF-8 compatível com texto antigo.

## Na prática

O Python tem funções prontas para conferir as conversões que você fez à mão:

```python
print(bin(13))
print(hex(42))
print(int("1101", 2))
print(int("FF", 16))
print(ord("A"), chr(65))
```

```text
0b1101
0x2a
13
255
65 A
```

Agora o overflow em C#. O `int` tem tamanho fixo, e por padrão o C# não verifica se a conta passou do limite:

```csharp
int contador = int.MaxValue;
contador = contador + 1;
Console.WriteLine(contador);

try
{
    int verificado = checked(contador - 1);
    Console.WriteLine(verificado);
}
catch (OverflowException)
{
    Console.WriteLine("overflow detectado");
}
```

```text
-2147483648
overflow detectado
```

A primeira conta deu a volta silenciosamente. Na segunda, `checked` pede para o runtime verificar, e subtrair 1 do menor `int` lança `OverflowException`. Em Python, o equivalente simplesmente funciona: `2**31 + 1` dá `2147483649`, sem drama.

O clássico do ponto flutuante, e a solução com `Decimal`:

```python
from decimal import Decimal

print(0.1 + 0.2)
print(0.1 + 0.2 == 0.3)
print(Decimal("0.1") + Decimal("0.2") == Decimal("0.3"))
print(Decimal(0.1))
```

```text
0.30000000000000004
False
True
0.1000000000000000055511151231257827021181583404541015625
```

A última linha revela o valor real guardado no `float` 0.1. Repare que o `Decimal` foi criado a partir de **strings**; se você passar o `float`, herda o erro dele. Quando precisar comparar `float`, use `math.isclose(a, b)` em vez de `==`.

Em C# a ideia é a mesma, com o sufixo `m` indicando literal `decimal`:

```csharp
Console.WriteLine(0.1 + 0.2 == 0.3);
Console.WriteLine(0.1m + 0.2m == 0.3m);
```

```text
False
True
```

Por fim, texto virando bytes. Em Python, `str` é uma sequência de caracteres Unicode e `bytes` é uma sequência de bytes; `encode` e `decode` fazem a ponte:

```python
palavra = "ação"
dados = palavra.encode("utf-8")
print(len(palavra), len(dados))
print(dados)
print(dados.hex(" "))
print(dados.decode("latin-1"))
```

```text
4 6
b'a\xc3\xa7\xc3\xa3o'
61 c3 a7 c3 a3 6f
aÃ§Ã£o
```

Quatro caracteres, seis bytes: "ç" e "ã" ocupam dois bytes cada. A última linha mostra o famoso texto embaralhado (*mojibake*): os bytes eram UTF-8, mas foram decodificados como Latin-1, que trata cada byte como um caractere.

## Armadilhas comuns

- **Usar `float` ou `double` para dinheiro.** Os centavos somem aos poucos. Use `Decimal` ou `decimal`, ou guarde valores em centavos como inteiros.
- **Comparar ponto flutuante com `==`.** Compare com tolerância, usando `math.isclose`.
- **Criar `Decimal` a partir de `float`.** `Decimal(0.1)` herda o erro; use `Decimal("0.1")`.
- **Esquecer que `int` do C# tem limite.** Somas grandes, multiplicações e contadores de longa duração podem estourar sem aviso. Considere `long` ou `checked`.
- **Supor que um caractere é um byte.** Em UTF-8 isso só vale para ASCII. Cortar bytes no meio de um "ç" gera texto corrompido.
- **Abrir arquivo sem declarar a codificação.** No Windows, o padrão pode não ser UTF-8. Use `open(caminho, encoding="utf-8")`.

## Recuperação ativa

1. Converta 26 para binário e para hexadecimal, mostrando cada passo.
2. Como se representa -1 em complemento de dois com 8 bits? Explique o procedimento.
3. O que acontece com um `int` do C# que vale `int.MaxValue` quando você soma 1? E em Python?
4. Explique, sem usar a palavra "bug", por que `0.1 + 0.2 == 0.3` é falso.
5. Qual a diferença entre um code point Unicode e a sua codificação em UTF-8? Quantos bytes "ç" ocupa em UTF-8?
6. O que causa um texto aparecer como "aÃ§Ã£o"?

## Para ir além

- [Aritmética de ponto flutuante: problemas e limitações — documentação do Python](https://docs.python.org/pt-br/3/tutorial/floatingpoint.html)
- [Unicode HOWTO — documentação do Python](https://docs.python.org/3/howto/unicode.html)
- [Instruções checked e unchecked — Microsoft Learn](https://learn.microsoft.com/pt-br/dotnet/csharp/language-reference/statements/checked-and-unchecked)
- [Complemento para dois — Wikipédia](https://pt.wikipedia.org/wiki/Complemento_para_dois)
