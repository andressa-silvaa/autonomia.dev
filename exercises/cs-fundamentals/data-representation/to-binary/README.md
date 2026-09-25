Implemente `to_binary(number)`, que recebe um inteiro **não negativo** e devolve a representação binária dele como texto.

```python
to_binary(0)  # "0"
to_binary(5)  # "101"
to_binary(10)  # "1010"
```

Regras:

- Não vale usar `bin()`, `format()` nem f-string com `:b`. A ideia é entender a conversão, não chamar quem já sabe.
- Número negativo deve levantar `ValueError`.
