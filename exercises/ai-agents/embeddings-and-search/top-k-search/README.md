Você tem uma lista de documentos já convertidos em vetores. Implemente `top_k(query_vector, document_vectors, k)`, que devolve os `k` documentos mais parecidos com a consulta.

Devolva uma lista de tuplas `(índice, similaridade)`, da maior similaridade para a menor. Em caso de empate, o índice menor vem primeiro. Se `k` for maior que a quantidade de documentos, devolva todos.

Use a similaridade de cosseno. Você pode escrevê-la de novo ou copiar a sua do exercício anterior.
