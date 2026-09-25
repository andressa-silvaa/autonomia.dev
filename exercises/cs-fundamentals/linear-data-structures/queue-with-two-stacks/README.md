Implemente a classe `Queue` (fila, FIFO) usando **duas listas como pilhas**: só `append()` e `pop()` sem argumento.

- `enqueue(item)` coloca no fim da fila.
- `dequeue()` tira e devolve o primeiro da fila; fila vazia levanta `IndexError`.
- `len(queue)` diz quantos itens tem.

Cada operação deve custar O(1) em média.
