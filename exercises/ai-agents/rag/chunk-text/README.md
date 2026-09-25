Implemente `chunk_text(text, size, overlap)`, que divide um texto em trechos de no máximo `size` caracteres, com `overlap` caracteres de sobreposição entre trechos vizinhos.

```python
chunk_text("abcdefghij", 4, 1)  # ["abcd", "defg", "ghij", "j"]
chunk_text("abc", 10, 0)  # ["abc"]
chunk_text("", 4, 1)  # []
```

Regras:

- `size` menor ou igual a zero levanta `ValueError`
- `overlap` negativo ou maior ou igual a `size` levanta `ValueError` (senão o avanço seria zero e o laço nunca terminaria)
- Texto vazio devolve lista vazia
