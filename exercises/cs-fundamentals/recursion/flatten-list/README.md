Implemente `flatten(nested)`, que recebe uma lista que pode ter listas dentro de listas, em qualquer profundidade, e devolve uma lista simples com todos os valores na mesma ordem.

```python
flatten([1, [2, [3, [4]], 5]])  # [1, 2, 3, 4, 5]
flatten([[], [[]]])  # []
```

A lista original não deve ser modificada.
