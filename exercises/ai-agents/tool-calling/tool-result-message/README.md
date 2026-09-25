No laço de tool calling, depois de executar as ferramentas você precisa devolver os resultados ao modelo.

Implemente `build_tool_results(calls, outcomes)`:

- `calls` é a lista de blocos `tool_use` da resposta, cada um um dicionário com `id` e `name`
- `outcomes` é um dicionário que mapeia o `id` da chamada para o resultado: ou `{"ok": valor}`, ou `{"error": mensagem}`
- Devolva **uma única** mensagem de usuário: `{"role": "user", "content": [...]}`
- Cada item de `content` é `{"type": "tool_result", "tool_use_id": id, "content": texto}`, na mesma ordem de `calls`
- Quando o resultado for erro, acrescente `"is_error": True` ao bloco e use a mensagem de erro como conteúdo
- O conteúdo sempre vai como texto (use `str()` no valor)
- Se algum `id` de `calls` não estiver em `outcomes`, levante `KeyError`
