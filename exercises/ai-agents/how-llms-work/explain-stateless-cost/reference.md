A API é **sem estado**: ela não guarda a sua conversa. Cada chamada precisa levar o histórico inteiro, então no turno 50 você está enviando as 49 mensagens anteriores mais a nova. Os tokens de entrada do turno 50 são muito maiores que os do turno 1, e é por isso que a mesma pergunta custa mais no fim.

Olhando o total acumulado, fica pior. Se cada turno acrescenta mais ou menos a mesma quantidade de texto, o turno 1 envia 1 bloco, o turno 2 envia 2, o turno 3 envia 3, e assim por diante. Somando, 1 + 2 + 3 + ... + n, o que dá n(n+1)/2: **quadrático** no número de turnos. Dobrar o tamanho da conversa não dobra o custo, quadruplica.

O que dá para fazer:

- **Cache de prompt**: se a parte inicial do prompt é estável (instruções, documentos), marque com `cache_control`. A leitura do cache custa cerca de 10% do preço de entrada.
- **Resumir o histórico antigo**: trocar 30 turnos antigos por um resumo curto.
- **Descartar o que não importa**: resultados grandes de ferramenta raramente precisam ficar na conversa para sempre.

Vale separar: isso tudo é custo de **entrada**. A saída é cobrada mais caro por token, mas não acumula do mesmo jeito, porque cada resposta é gerada uma vez só.
