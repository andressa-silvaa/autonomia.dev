A saída estruturada garantiu que o JSON tem a forma certa. Agora escreva `validate_invoice(invoice, today)`, que confere o que o schema **não** consegue garantir.

A função recebe um dicionário já validado pelo schema (com `number`, `issued_on`, `total`, `currency` e os itens em `items`) e a data de hoje (`datetime.date`). Devolve uma **lista de mensagens de problema**, vazia quando está tudo certo.

Regras a verificar, nesta ordem:

1. `"data no futuro"` — se `issued_on` for posterior a `today`
2. `"nota sem itens"` — se `items` estiver vazia
3. `"total não bate com os itens"` — se `total` diferir da soma de `quantity * unit_price` dos itens em mais de um centavo
4. `"quantidade inválida no item N"` — para cada item (N é o índice, começando em 0) com `quantity` menor ou igual a zero

Junte todos os problemas encontrados; não pare no primeiro.
