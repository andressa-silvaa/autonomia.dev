Na ida, cada chamada empilha um frame novo, com o seu próprio `n`:

1. `fatorial(3)` precisa de `fatorial(2)` e espera.
2. `fatorial(2)` precisa de `fatorial(1)` e espera.
3. `fatorial(1)` precisa de `fatorial(0)` e espera.
4. `fatorial(0)` é o caso base: devolve 1 sem chamar ninguém.

Nesse ponto a pilha tem quatro frames e para de crescer. Na volta, cada frame recebe o resultado, faz a sua multiplicação e é desempilhado: `fatorial(1)` devolve 1 × 1 = 1, `fatorial(2)` devolve 2 × 1 = 2, e `fatorial(3)` devolve 3 × 2 = 6.
