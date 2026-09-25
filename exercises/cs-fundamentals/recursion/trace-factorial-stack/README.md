Considere:

```python
def fatorial(n):
    if n == 0:
        return 1
    return n * fatorial(n - 1)
```

Descreva, passo a passo, o que acontece na pilha de chamadas durante `fatorial(3)`: o que é empilhado na ida, quando a pilha para de crescer e o que cada chamada devolve na volta.

Esta é corrigida por autoavaliação: no envio, você compara com uma resposta de referência e marca cada critério.
