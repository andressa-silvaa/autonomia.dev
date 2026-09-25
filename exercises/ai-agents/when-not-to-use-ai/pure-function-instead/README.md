Alguém propôs usar um LLM para calcular o total de um pedido, porque "a regra é complicada". Não é: é uma função pura, e uma função pura é mais barata, instantânea, testável e sempre certa.

Implemente `order_total(items, discount_percent, tax_percent)`:

- `items` é uma lista de dicionários com `quantity` (int) e `unit_price_cents` (int)
- O subtotal é a soma de `quantity * unit_price_cents`
- O desconto é aplicado sobre o subtotal, **antes** do imposto
- O imposto é aplicado sobre o valor já com desconto
- Devolva o total em **centavos**, como inteiro, arredondando para o centavo mais próximo (meio centavo arredonda para cima)
- Percentual negativo, ou desconto acima de 100, levanta `ValueError`
- Quantidade ou preço negativo levanta `ValueError`

Trabalhe em centavos com inteiros. Nada de float para dinheiro.
