Implemente `two_sum(numbers, target)`: devolva uma tupla `(i, j)` com `i < j` tal que `numbers[i] + numbers[j] == target`. Se houver mais de um par, devolva o que termina primeiro (o menor `j`). Se não houver, devolva `None`.

```python
two_sum([2, 7, 11, 15], 9)  # (0, 1)
two_sum([3, 2, 4], 6)  # (1, 2)
two_sum([1, 2], 10)  # None
```

A solução precisa ser O(n): os testes incluem uma lista grande.
