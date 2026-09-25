Prompt reescrito:

```
Você revisa funções Python de um sistema de cobrança. Para a função enviada, aponte problemas em quatro categorias, nesta ordem: correção (bugs e casos limite não tratados), segurança (entrada não validada, injeção, dado sensível em log), precisão numérica (uso de float para dinheiro, arredondamento) e manutenibilidade (nomes, tamanho, duplicação).

Para cada problema, escreva uma linha no formato:
[categoria] linha X: problema — consequência concreta

Ordene do mais grave para o menos grave. Se não houver problema numa categoria, escreva "[categoria] nenhum problema encontrado". Se o trecho enviado não for suficiente para avaliar alguma categoria (por exemplo, a função chama outra que não foi enviada), diga explicitamente o que falta em vez de supor.
```

O que mudou:

- **Tarefa específica.** "Está bom" não quer dizer nada: bom em quê? O prompt agora nomeia as quatro categorias, e elas vêm do domínio (cobrança, onde precisão numérica importa de verdade).
- **Formato fixo.** Como a saída alimenta um relatório automático, o formato de cada linha é definido. Sem isso, cada resposta vem com uma estrutura diferente e nada dá para parsear.
- **Instrução para a ausência.** Sem dizer o que fazer quando não há problema, o modelo tende a inventar um para ser útil. "Nenhum problema encontrado" dá a ele uma saída honesta.
- **Instrução para informação faltando.** Isso reduz a chance de o modelo assumir o que a função chamada faz e revisar em cima de uma suposição.
- **Ordenação.** Quem lê o relatório precisa ver primeiro o que quebra em produção.
