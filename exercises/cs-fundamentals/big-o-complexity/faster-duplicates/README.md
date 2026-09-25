A função abaixo funciona, mas compara todo mundo com todo mundo: é O(n²).

```python
def has_duplicates(items):
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                return True
    return False
```

Reescreva `has_duplicates` para que ela seja **O(n)** e continue dando as mesmas respostas. Os testes incluem uma lista grande: a versão O(n²) não passa a tempo.
