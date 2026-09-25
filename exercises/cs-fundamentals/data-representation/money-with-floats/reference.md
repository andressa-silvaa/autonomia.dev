Um `float` guarda o número em binário, e muitos decimais simples não têm representação exata em binário, do mesmo jeito que 1/3 não tem em decimal. O 0.1 vira algo como 0.1000000000000000055. Por isso `0.1 + 0.2 == 0.3` dá `False`: a soma dá 0.30000000000000004.

Num preço isolado isso é invisível, mas somando milhares de vendas os pequenos erros se acumulam, e os arredondamentos no relatório deixam de bater com os do banco.

Para dinheiro, use `Decimal` (criado a partir de texto, `Decimal("0.10")`) ou guarde tudo em centavos como inteiros (`1990` para R$ 19,90) e só formate na hora de mostrar.
