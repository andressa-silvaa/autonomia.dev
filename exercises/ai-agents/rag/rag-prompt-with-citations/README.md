Implemente `build_rag_prompt(question, chunks)`, que monta a mensagem enviada ao modelo num sistema de RAG.

`chunks` é uma lista de tuplas `(source, text)`. A função devolve uma string com, nesta ordem:

1. A linha `Fontes:`
2. Uma linha por trecho, no formato `[N] source: text`, com N começando em 1
3. Uma linha em branco
4. A linha `Responda apenas com base nas fontes acima. Cite a fonte usada no formato [N]. Se as fontes não responderem, diga que não há informação suficiente.`
5. Uma linha em branco
6. A linha `Pergunta: {question}`

Quando `chunks` estiver vazia, devolva apenas `Não há fontes disponíveis para responder.` (sem mais nada).
