# Como o computador executa um programa

> **Objetivo:** explicar, passo a passo, o que acontece entre você digitar `python app.py` ou `dotnet run` e o processador de fato executar o seu código.

## Por que isso importa

Muita gente programa anos tratando o computador como uma caixa preta: escreve o código, aperta "rodar" e torce. Funciona até o dia em que algo fica lento sem motivo aparente, um erro só acontece em produção ou alguém pergunta numa entrevista "qual a diferença entre compilado e interpretado?".

Entender o caminho do seu código até o processador não é curiosidade acadêmica. É o que te permite raciocinar sobre desempenho, ler mensagens de erro com calma e entender por que o C# precisa de um passo de build e o Python não. E, mais importante, é a base de tudo o que vem depois nesta trilha.

## Conceitos

### A CPU e o ciclo buscar-decodificar-executar

A CPU (unidade central de processamento) é, no fundo, uma máquina bem simples que repete o mesmo ciclo bilhões de vezes por segundo:

1. **Buscar:** lê da memória a próxima instrução, no endereço guardado num registrador especial chamado *contador de programa* (em x86 ele se chama *instruction pointer*).
2. **Decodificar:** interpreta os bits dessa instrução para descobrir o que fazer ("somar", "copiar", "pular para outro endereço") e com quais dados.
3. **Executar:** faz a operação e guarda o resultado. Depois avança o contador para a próxima instrução, ou pula para outro lugar se a instrução era um desvio (é assim que `if` e loops existem no nível mais baixo).

Processadores modernos fazem truques para acelerar isso (executam várias instruções em paralelo, tentam adivinhar desvios), mas o modelo mental continua valendo.

### Registradores

Registradores são pequenas áreas de armazenamento dentro da própria CPU. São pouquíssimos (dezenas) e cada um guarda tipicamente 64 bits. Toda conta acontece neles: a CPU traz dados da memória para um registrador, opera e, se precisar, devolve o resultado para a memória.

### Memória RAM vs disco

A RAM é onde ficam o programa e os dados **enquanto ele roda**. É rápida, mas volátil: desligou, perdeu. O disco (SSD ou HD) guarda arquivos de forma permanente, mas é muito mais lento. Em ordem de grandeza aproximada:

| Onde está o dado | Tempo de acesso aproximado |
| --- | --- |
| Registrador | menos de 1 nanossegundo |
| Cache L1 da CPU | cerca de 1 ns |
| RAM | cerca de 100 ns |
| SSD NVMe | dezenas de microssegundos (dezenas de milhares de ns) |

Por isso, antes de rodar, o programa precisa ser **carregado** do disco para a RAM. E por isso ler arquivo dentro de um loop apertado costuma ser uma péssima ideia.

### Instruções de máquina

A CPU não entende Python nem C#. Ela entende apenas *instruções de máquina*: sequências de bits com significado definido pelo fabricante (x86-64 na maioria dos PCs, ARM na maioria dos celulares e Macs recentes). Escrito de forma legível, em *assembly*, um `c = a + b` poderia virar algo assim:

```text
mov eax, [a]
add eax, [b]
mov [c], eax
```

Copia `a` da memória para o registrador `eax`, soma `b` a ele e grava o resultado em `c`. Toda linguagem, por mais alto nível que seja, termina virando algo desse tipo.

### Compilação, interpretação e JIT

Existem três grandes estratégias para ir do código-fonte até as instruções de máquina:

- **Compilação antecipada (AOT):** um compilador traduz o programa inteiro para código de máquina antes de rodar. C, C++, Rust e Go funcionam assim. O resultado é um executável específico para um processador e sistema operacional.
- **Interpretação:** um programa chamado interpretador lê o código e vai executando as operações ele mesmo. O CPython (o Python "oficial") faz isso, mas com um passo intermediário: primeiro traduz o código-fonte para **bytecode**, instruções simples para uma máquina virtual, e depois um loop dentro do interpretador executa esse bytecode uma instrução por vez.
- **JIT (just-in-time):** compila para código de máquina **durante** a execução. O .NET usa essa abordagem: o compilador do C# gera **IL** (*Intermediate Language*), que fica dentro de um arquivo `.dll`. Quando um método é chamado pela primeira vez, o JIT do runtime (o CLR) traduz aquele IL para instruções nativas do seu processador, e as próximas chamadas usam o código já traduzido.

Repare que "linguagem compilada" e "linguagem interpretada" é uma simplificação: a estratégia é da *implementação*, não da linguagem. O PyPy, por exemplo, é um Python com JIT, e o .NET também oferece Native AOT.

### Processo e thread

Quando você executa um programa, o sistema operacional cria um **processo**: uma instância em execução, com seu próprio espaço de memória isolado, identificador (PID) e recursos como arquivos abertos. Dois processos não enxergam a memória um do outro.

Dentro de um processo existem uma ou mais **threads**: linhas de execução independentes que compartilham a mesma memória do processo. Cada thread tem seu próprio contador de programa, então pode estar executando um trecho diferente do código. Compartilhar memória é o que torna threads leves e úteis, e também o que as torna perigosas. Vamos aprofundar isso num módulo futuro sobre concorrência.

## Na prática

O módulo `dis` da biblioteca padrão mostra o bytecode que o CPython gera para uma função. É a forma mais direta de ver a "tradução intermediária" com seus próprios olhos.

```python
import dis


def soma(a, b):
    return a + b


dis.dis(soma)
```

No Python 3.12 a saída é parecida com esta (os detalhes mudam entre versões):

```text
  4           0 RESUME                   0

  5           2 LOAD_FAST                0 (a)
              4 LOAD_FAST                1 (b)
              6 BINARY_OP                0 (+)
             10 RETURN_VALUE
```

Leia de cima para baixo: carrega `a`, carrega `b`, aplica a operação binária `+`, devolve o resultado. Cada linha dessas é uma volta no loop do interpretador, e cada volta executa dezenas de instruções de máquina. Esse "custo por instrução de bytecode" é um dos motivos pelos quais Python puro é mais lento que C#.

Agora veja processo e thread na prática. O programa abaixo cria três threads e cada uma imprime o PID do processo em que está rodando:

```python
import os
import threading


def trabalhar(nome):
    print(f"{nome} rodando no processo {os.getpid()}")


threads = [threading.Thread(target=trabalhar, args=(f"thread-{i}",)) for i in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

```text
thread-0 rodando no processo 18432
thread-1 rodando no processo 18432
thread-2 rodando no processo 18432
```

O número muda a cada execução, mas é o mesmo nas três linhas: são três threads dentro de um único processo. O `join` faz o programa principal esperar cada thread terminar.

### O que acontece quando você roda `python app.py`

1. O shell pede ao sistema operacional para criar um processo e carregar nele o executável do interpretador (`python`).
2. O interpretador lê `app.py` do disco para a memória.
3. Ele analisa o texto e o compila para bytecode. Para módulos importados, esse bytecode é salvo em `__pycache__` como arquivos `.pyc`, e reaproveitado se o código-fonte não mudou. O script principal é compilado de novo a cada execução.
4. O loop da máquina virtual executa o bytecode, instrução por instrução.
5. Quando o programa termina, o processo é encerrado e o sistema operacional recupera a memória.

### O que acontece quando você roda `dotnet run`

1. O `dotnet` dispara um build: o compilador do C# (Roslyn) transforma seus arquivos `.cs` em IL, empacotado numa `.dll` dentro de `bin/`.
2. O host do .NET cria o processo e carrega o runtime (CLR).
3. O CLR carrega a `.dll` e começa pelo ponto de entrada (`Main` ou as instruções de nível superior).
4. Cada método, na primeira chamada, passa pelo JIT e vira código de máquina. O runtime pode recompilar métodos muito usados com mais otimizações depois (*tiered compilation*).
5. A CPU executa esse código nativo diretamente.

A diferença-chave: no .NET, a tradução para código de máquina acontece de verdade; no CPython, o que roda na CPU é o interpretador, que por sua vez "encena" o seu bytecode.

## Armadilhas comuns

- **Achar que Python não compila nada.** Ele compila, só que para bytecode, não para código de máquina.
- **Achar que `dotnet run` é igual a rodar um executável pronto.** Ele compila antes; em produção você normalmente usa `dotnet publish` e roda o resultado.
- **Confundir processo com thread.** Processos são isolados; threads do mesmo processo compartilham memória. Mudar uma variável global numa thread afeta as outras.
- **Esquecer da hierarquia de memória.** Acessar disco ou rede é milhares de vezes mais lento que acessar RAM. Na hora de otimizar, é ali que costuma estar o gargalo.
- **Tratar "compilado vs interpretado" como propriedade da linguagem.** É da implementação. Existe Python com JIT e C# compilado antecipadamente.

## Recuperação ativa

1. Descreva, com suas palavras, as três etapas do ciclo que a CPU repete e o papel do contador de programa.
2. Por que um programa precisa ser carregado do disco para a RAM antes de executar?
3. Qual a diferença entre bytecode do Python e IL do .NET em relação ao que acontece com eles durante a execução?
4. Liste o que acontece, em ordem, desde `dotnet run` até a CPU executar seu método `Main`.
5. Duas threads do mesmo processo alteram a mesma lista. Por que isso é possível, e por que não seria entre dois processos?

## Para ir além

- [Módulo `dis` — documentação do Python](https://docs.python.org/3/library/dis.html)
- [Processo de execução gerenciada — Microsoft Learn](https://learn.microsoft.com/pt-br/dotnet/standard/managed-execution-process)
- [Unidade central de processamento — Wikipédia](https://pt.wikipedia.org/wiki/Unidade_central_de_processamento)
- [Compilação just-in-time — Wikipédia](https://pt.wikipedia.org/wiki/Compila%C3%A7%C3%A3o_just-in-time)
