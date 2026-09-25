Escreva `run_agent(client, initial_messages, max_turns, token_budget)`, o laço de um agente com limites.

O `client` é um objeto com o método `send(messages)`, que devolve um objeto com:

- `.stop_reason`: `"tool_use"` ou `"end_turn"`
- `.tool_calls`: lista de chamadas (vazia quando não há)
- `.tokens`: quantos tokens aquela volta consumiu

Regras do laço:

1. Chame `client.send(messages)` e contabilize os tokens
2. Se `stop_reason` for `"end_turn"`, pare com o motivo `"done"`
3. Se os tokens acumulados atingirem ou passarem `token_budget`, pare com o motivo `"budget"`
4. Se o número de voltas atingir `max_turns`, pare com o motivo `"max_turns"`
5. Caso contrário, execute as ferramentas (chame `client.run_tools(response.tool_calls)`, que devolve a mensagem a acrescentar), acrescente ao histórico e continue

Devolva um dicionário: `{"reason": ..., "turns": ..., "tokens": ...}`.

A ordem das checagens importa: um agente que terminou na última volta permitida terminou, não estourou o limite.
