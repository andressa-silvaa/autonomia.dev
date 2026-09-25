Implemente `cosine_similarity(a, b)`, que recebe dois vetores (listas de números) e devolve a similaridade de cosseno entre eles.

```python
cosine_similarity([1, 0], [1, 0])  # 1.0
cosine_similarity([1, 0], [0, 1])  # 0.0
cosine_similarity([1, 0], [-1, 0])  # -1.0
```

Regras:

- Vetores de tamanhos diferentes levantam `ValueError`
- Se qualquer um dos vetores for todo zero, devolva `0.0` (vetor sem direção não tem ângulo)
- Não use numpy nem scipy: a ideia é entender a conta
