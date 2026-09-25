Esta função deveria criar uma lista nova quando ninguém passa uma:

```python
def add_item(item, items=[]):
    items.append(item)
    return items
```

Mas olha o que acontece:

```python
add_item("a")  # ["a"]
add_item("b")  # ["a", "b"]  ← de onde veio o "a"?
```

Descubra o que está acontecendo na memória e corrija `add_item`. Quando alguém passar uma lista, a função deve continuar adicionando nela e devolvendo a mesma lista.
