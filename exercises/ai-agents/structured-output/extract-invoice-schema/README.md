Você vai extrair dados de notas fiscais com saída estruturada. Escreva a função `invoice_schema()` que devolve o JSON Schema (como dicionário Python) com estas regras:

- `number`: texto, obrigatório
- `issued_on`: texto no formato `AAAA-MM-DD`, obrigatório (use `"pattern"` com uma expressão regular)
- `total`: número, obrigatório, não pode ser negativo
- `currency`: texto, obrigatório, só aceita `"BRL"`, `"USD"` ou `"EUR"`
- `notes`: texto, opcional
- Nenhum campo além desses é aceito

Não chame a API neste exercício: só monte o schema.
