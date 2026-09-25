Escreva `build_request(manual, tools, question, now)`, que monta os argumentos de uma chamada de forma que o cache de prompt funcione entre chamadas.

A função recebe o texto do manual (estável), uma lista de definições de ferramenta (cada uma um dicionário com `name`), a pergunta do usuário (muda sempre) e um texto com a data e hora atuais (muda sempre). Deve devolver um dicionário com:

- `"tools"`: as ferramentas **ordenadas por `name`**, para que a ordem não varie entre chamadas
- `"system"`: uma lista de blocos. O primeiro bloco tem o manual e `{"type": "ephemeral"}` em `cache_control`. O segundo bloco tem o texto `f"Agora: {now}"` e **não** tem `cache_control`
- `"messages"`: uma lista com uma mensagem de usuário contendo a pergunta

Não chame a API; só monte a estrutura.
