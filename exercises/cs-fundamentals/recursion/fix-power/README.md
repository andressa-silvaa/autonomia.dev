Esta função deveria calcular `base` elevado a `exponent` (com `exponent` inteiro e não negativo), mas termina com `RecursionError`:

```python
def power(base, exponent):
    return base * power(base, exponent - 1)
```

Corrija mantendo a solução recursiva.
