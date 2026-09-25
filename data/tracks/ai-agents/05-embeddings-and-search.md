# Embeddings e busca semântica

> **Objetivo:** Representar textos como vetores, medir proximidade de significado com similaridade de cosseno e construir uma busca que encontra o que a busca por palavra-chave não encontra.

## Por que isso importa

Você já implementou busca. Provavelmente com `LIKE '%termo%'`, com um índice invertido, ou com uma tabela hash quando precisava de lookup exato. Todas essas estruturas resolvem o mesmo problema: dado um identificador, achar o registro. Uma tabela hash faz isso em O(1) médio justamente porque só entende igualdade: `hash("carro")` e `hash("automóvel")` caem em baldes sem nenhuma relação, e isso é uma propriedade desejável da função de hash, não um defeito. Boa dispersão exige que entradas parecidas produzam saídas distantes.

Só que uma parte grande dos problemas reais não é de igualdade, é de proximidade. A usuária pergunta "como cancelo minha assinatura" e o documento diz "encerramento de plano". Nenhum caractere em comum nas palavras que importam. Embeddings resolvem exatamente essa lacuna: são vetores de números que representam significado, construídos de forma que textos com sentido parecido ficam geometricamente próximos. É a inversão deliberada da propriedade da função de hash. Entender isso muda como você projeta qualquer sistema de busca, recomendação, deduplicação ou classificação de texto, e é o pré-requisito técnico de RAG.

## Conceitos

### O que é um embedding

Um embedding é uma lista de números de ponto flutuante de tamanho fixo que representa um texto. O modelo `all-MiniLM-L6-v2`, por exemplo, produz vetores de 384 dimensões: qualquer texto, de uma palavra a um parágrafo, vira uma lista de 384 floats.

Esses números não são legíveis individualmente. Não existe "a dimensão 17 é o quanto o texto fala sobre gatos". O que importa é a posição relativa: textos com significado parecido produzem vetores próximos no espaço de 384 dimensões, e a proximidade é mensurável.

Isso vem do treino. O modelo viu bilhões de pares de textos e foi ajustado para aproximar os que aparecem em contextos similares e afastar os que não. "Carro" e "automóvel" aparecem nos mesmos contextos, então seus vetores convergiram.

### Por que a busca por palavra-chave falha

Busca por substring ou por token compara sequências de caracteres. Ela é exata, rápida e completamente cega a sinônimos, paráfrases, flexões incomuns e traduções. Um índice invertido melhora isso com stemming e lista de sinônimos, mas ambos são tabelas mantidas à mão: alguém precisa saber de antemão que "encerrar plano" e "cancelar assinatura" são a mesma coisa.

Hash não resolve isso e nem poderia. A função de hash é projetada para que uma mudança mínima na entrada mude drasticamente a saída (efeito avalanche). Isso é o oposto do que você quer aqui. Um embedding é uma função que faz o contrário: entradas semanticamente próximas produzem saídas próximas.

Guarde essa frase: **hash é igualdade exata; embedding é proximidade**. São ferramentas para perguntas diferentes.

### Similaridade de cosseno

Para medir proximidade entre dois vetores, a métrica padrão é o cosseno do ângulo entre eles:

```
cos(A, B) = (A · B) / (||A|| × ||B||)
```

onde `A · B` é o produto escalar (soma dos produtos elemento a elemento) e `||A||` é a norma euclidiana (raiz da soma dos quadrados).

A intuição geométrica: o cosseno mede **direção**, ignorando **magnitude**. Dois vetores apontando para o mesmo lado dão 1, independente do tamanho. Perpendiculares dão 0. Opostos dão -1. Na prática, com modelos de embedding de texto, os valores ficam quase sempre entre 0 e 1, porque os vetores ocupam uma região restrita do espaço.

Ignorar magnitude é o que você quer. Um parágrafo longo e uma frase curta sobre o mesmo assunto podem ter normas bem diferentes, mas apontam para a mesma direção. A distância euclidiana penalizaria a diferença de tamanho; o cosseno não.

Quando os vetores já estão normalizados (norma 1), o cosseno se reduz ao produto escalar puro, e o cálculo fica bem mais barato.

### Dimensionalidade

O número de dimensões é uma escolha do modelo e um trade-off. `all-MiniLM-L6-v2` usa 384; outros modelos usam 768, 1024 ou 1536.

Mais dimensões dão mais capacidade de distinguir nuances, mas ocupam mais memória e deixam cada comparação mais cara. Faça a conta: 384 floats de 32 bits são 1536 bytes por vetor. Cem mil trechos são cerca de 150 MB, o que cabe confortavelmente em memória. Dez milhões de trechos com 1536 dimensões seriam cerca de 61 GB, o que já não cabe.

Vetores de modelos diferentes não são comparáveis entre si. Nem em número de dimensões, nem em significado. Trocar de modelo de embedding significa reindexar tudo.

### Como guardar e o custo de buscar

Para poucos itens, uma lista de tuplas `(texto, vetor)` em memória basta. Buscar é percorrer tudo comparando: **O(n) por consulta**, com `n` o número de itens indexados, e cada comparação custando O(d) com `d` dimensões. Total: O(n·d).

Com 1.000 trechos de 384 dimensões, são 384 mil operações de ponto flutuante por consulta. Com numpy isso leva menos de um milissegundo. Com 10 milhões de trechos, são 3,84 bilhões, e a busca linear deixa de ser viável.

A partir daí entra um banco vetorial (FAISS, Qdrant, pgvector, Chroma). Eles usam índices aproximados, tipicamente HNSW, que constrói um grafo navegável em camadas e faz a busca em tempo aproximadamente logarítmico. O preço é a palavra "aproximado": o resultado pode não ser o vizinho mais próximo exato, só um muito bom. É o mesmo trade-off de um filtro de Bloom, que troca exatidão por espaço e velocidade.

A decisão de engenharia é direta: comece com a lista em memória. Migre quando medir que a busca linear virou gargalo, não antes.

### O que embeddings não fazem

Esta seção importa tanto quanto as anteriores.

Embeddings **não raciocinam**. Eles medem semelhança de significado, não relação lógica. "O pagamento foi aprovado" e "o pagamento foi recusado" são semanticamente muito parecidos (mesmo assunto, mesma estrutura, uma palavra diferente) e vão ter similaridade alta. Se a sua busca precisa distinguir afirmação de negação, cosseno sozinho não distingue.

Embeddings **não sabem se a informação é verdadeira**. Um trecho com um erro factual e um trecho correto sobre o mesmo tema têm vetores próximos. A busca vai devolver os dois com nota parecida.

Embeddings **não entendem números ou datas** de forma aritmética. "R$ 100" e "R$ 1.000" são próximos no espaço vetorial, porque são estruturalmente parecidos. Se sua consulta depende de comparação numérica, use SQL para isso.

Busca semântica é um filtro de relevância, não um mecanismo de verdade. Na prática, híbridos (cosseno combinado com busca por palavra-chave) costumam superar qualquer um dos dois sozinho, justamente porque cobrem falhas diferentes.

## Na prática

A Anthropic não tem API de embeddings própria. Você usa um provedor externo (como a Voyage AI) ou um modelo local. Para um sistema que roda na sua máquina, o modelo local é a escolha coerente: é gratuito, não vaza dados e não depende de rede.

```bash
pip install sentence-transformers numpy
```

Gerando os primeiros vetores:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = ["Meu carro quebrou na estrada", "O automóvel apresentou defeito"]
vectors = model.encode(texts)

print(vectors.shape)
print(vectors[0][:5])
```

Saída:

```
(2, 384)
[-0.0312  0.0871 -0.0455  0.0209  0.0634]
```

Duas frases, 384 dimensões cada. Os cinco primeiros números não significam nada isoladamente; é a posição no espaço que carrega o sentido.

Agora a similaridade de cosseno, implementada direto da fórmula com numpy:

```python
import numpy as np


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


print(cosine_similarity(vectors[0], vectors[1]))
```

Saída aproximada: `0.72`.

Nenhuma palavra relevante em comum entre as duas frases ("carro"/"automóvel", "quebrou"/"defeito"), e mesmo assim 0.72. Uma busca por substring daria zero resultados.

Comparando com algo não relacionado, para calibrar a escala:

```python
unrelated = model.encode(["Receita de bolo de fubá"])[0]
print(cosine_similarity(vectors[0], unrelated))
```

Saída aproximada: `0.03`.

Não existe um limiar universal de "similar o suficiente". Ele depende do modelo e do domínio, e você o descobre medindo em cima dos seus dados. Calibre com exemplos que você sabe que deveriam casar e exemplos que não deveriam.

Uma busca completa numa lista pequena:

```python
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

documents = [
    "Para cancelar sua assinatura, acesse Configurações e clique em Encerrar plano.",
    "O reembolso é processado em até 7 dias úteis após a solicitação.",
    "Aceitamos cartão de crédito, boleto e Pix como formas de pagamento.",
    "O suporte técnico atende de segunda a sexta, das 9h às 18h.",
]

index = model.encode(documents, normalize_embeddings=True)


def search(query, top_k=2):
    q = model.encode([query], normalize_embeddings=True)[0]
    scores = index @ q
    ranked = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), documents[i]) for i in ranked]


for score, doc in search("como faço para sair do serviço"):
    print(f"{score:.3f}  {doc}")
```

Saída aproximada:

```
0.548  Para cancelar sua assinatura, acesse Configurações e clique em Encerrar plano.
0.211  O reembolso é processado em até 7 dias úteis após a solicitação.
```

Dois detalhes de engenharia aqui. Primeiro, `normalize_embeddings=True` deixa todos os vetores com norma 1, então o cosseno vira produto escalar puro e o denominador da fórmula some. Segundo, `index @ q` é uma multiplicação matriz-vetor: numpy faz as `n` comparações de uma vez, em código compilado, em vez de um laço Python. A complexidade continua O(n·d), mas a constante é ordens de grandeza menor.

O caso que fecha o argumento. A consulta foi "como faço para sair do serviço". Compare com uma busca por substring:

```python
query = "como faço para sair do serviço"
matches = [d for d in documents if query.lower() in d.lower()]
print(matches)

terms = query.lower().split()
matches = [d for d in documents if any(t in d.lower() for t in terms)]
print(matches)
```

Saída:

```
[]
['Para cancelar sua assinatura, acesse Configurações e clique em Encerrar plano.', 'O reembolso é processado em até 7 dias úteis após a solicitação.', 'O suporte técnico atende de segunda a sexta, das 9h às 18h.']
```

A busca por frase inteira não acha nada. A busca por termos soltos acha três dos quatro documentos, sem nenhuma ordenação útil, porque casou em palavras vazias como "para" e "do". A busca semântica achou o documento certo em primeiro lugar, sem nenhuma lista de sinônimos escrita à mão.

## Armadilhas comuns

- **Esperar que o cosseno distingua afirmação de negação.** "Pagamento aprovado" e "pagamento recusado" têm similaridade alta. Se a distinção importa, embedding sozinho não resolve.
- **Misturar vetores de modelos diferentes no mesmo índice.** Dimensões diferentes quebram na hora; dimensões iguais de modelos diferentes silenciosamente produzem resultados sem sentido. Trocar de modelo obriga a reindexar tudo.
- **Procurar um limiar de similaridade universal.** Não existe "0.7 é similar". A escala depende do modelo e do domínio, e precisa ser calibrada com exemplos reais do seu conjunto de dados.
- **Recomputar o embedding dos documentos a cada consulta.** O índice é construído uma vez e reusado; só a consulta precisa ser codificada no momento da busca. Errar isso transforma uma operação de milissegundos em segundos.
- **Partir direto para um banco vetorial.** Com alguns milhares de trechos, numpy em memória é mais rápido, mais simples de depurar e não adiciona um serviço à sua topologia. Migre quando medir o gargalo.
- **Tratar similaridade alta como prova de que a informação é correta.** O vetor mede semelhança de assunto, não veracidade. Um documento desatualizado tem nota tão boa quanto o atualizado.

## Recuperação ativa

1. Por que uma boa função de hash é péssima para busca semântica? Explique usando a propriedade que torna a função de hash boa para uma tabela hash.
2. Escreva a fórmula da similaridade de cosseno e explique por que o denominador existe. O que aconteceria se você usasse só o produto escalar em vetores não normalizados?
3. Você tem 5 milhões de trechos de 768 dimensões em float32. Quantos GB isso ocupa e qual o custo por consulta na busca linear? Em que momento você migraria para um índice aproximado, e o que perderia?
4. Uma busca semântica retorna, para "o pagamento foi aprovado?", um trecho que diz "o pagamento foi recusado", com nota 0.91. O sistema está quebrado? Justifique.
5. Explique por que `normalize_embeddings=True` permite trocar a fórmula do cosseno por um produto escalar, e o que isso muda no custo da busca.
6. Um colega quer melhorar a busca trocando o modelo de embedding por um de 1024 dimensões, mantendo o índice atual no banco. O que vai acontecer e por quê?
7. Dê um caso concreto do seu trabalho em que busca semântica seria pior que `WHERE`, e explique o que exatamente ela não consegue fazer ali.

## Para ir além

- [Documentação do sentence-transformers](https://sbert.net/) — modelos disponíveis, uso do `encode`, normalização e comparação de desempenho entre modelos.
- [Embeddings](https://platform.claude.com/docs/en/build-with-claude/embeddings) — a página da Anthropic sobre embeddings, incluindo a recomendação de provedores externos como a Voyage AI.
- [Efficient and robust approximate nearest neighbor search using HNSW graphs](https://arxiv.org/abs/1603.09320) — o artigo original do HNSW, o algoritmo por trás de FAISS, Qdrant e pgvector.
- [Documentação do FAISS](https://faiss.ai/) — biblioteca da Meta para busca vetorial em escala, com os tipos de índice e seus trade-offs de exatidão contra velocidade.
