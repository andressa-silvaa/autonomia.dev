Qual é a complexidade de tempo desta função?

```python
def count_halvings(n):
    steps = 0
    while n > 1:
        n //= 2
        steps += 1
    return steps
```
