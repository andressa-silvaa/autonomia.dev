# RAG

> **Objetivo:** Construir um pipeline que responde perguntas sobre os seus documentos recuperando só os trechos relevantes, citando a fonte e admitindo quando a resposta não está ali.

## Por que isso importa

O modelo não conhece os seus documentos. Ele não viu o manual interno da sua empresa, o runbook do seu time nem o contrato que você assinou ontem. Se você perguntar, ele vai responder mesmo assim, com a mesma fluência de sempre, inventando o que falta. A saída mais perigosa de um LLM não é o erro óbvio: é o erro plausível, bem escrito e sem nenhum sinal de incerteza.

A solução ingênua é enfiar tudo na janela de contexto. Você já sabe por que isso falha: contexto irrelevante compete com o relevante e piora a resposta, além de custar proporcionalmente. Um manual de 500 mil tokens consultado 200 vezes por dia no Sonnet 5 custa $200 por dia em entrada, para responder perguntas que dependem de 2 mil tokens cada. RAG (retrieval-augmented generation, ou geração aumentada por recuperação) é a alternativa de engenharia: em vez de carregar o banco inteiro na memória, você indexa, busca o que interessa e passa só isso adiante. É a mesma lógica de um índice de banco de dados, aplicada a texto. Este módulo junta as duas peças anteriores: busca semântica seleciona o contexto, context engineering decide como ele é montado.

## Conceitos

### O problema que RAG resolve

Três limitações do modelo sozinho:

- **Conhecimento.** Ele não viu seus dados privados, nem nada posterior ao corte de treino.
- **Custo.** Reenviar um corpus inteiro a cada pergunta é desperdício em escala quadrática de gasto.
- **Verificabilidade.** Uma resposta gerada de memória não tem fonte. Você não consegue auditar.

RAG endereça os três de uma vez: busca o relevante, envia pouco, e a fonte vem junto porque você sabe exatamente de onde veio cada trecho.

### O pipeline completo

Cinco etapas, em duas fases.

**Fase de indexação (uma vez, ou a cada atualização dos documentos):**

1. **Dividir em trechos.** Quebrar cada documento em pedaços de tamanho gerenciável.
2. **Indexar.** Gerar o embedding de cada trecho e guardar junto com o texto e a referência de origem.

**Fase de consulta (a cada pergunta):**

3. **Buscar.** Gerar o embedding da pergunta e recuperar os `k` trechos mais similares.
4. **Montar o prompt.** Colocar os trechos recuperados no contexto, com instruções claras.
5. **Responder citando.** O modelo redige a resposta com base nos trechos, indicando a fonte.

Separar as duas fases importa: a indexação é cara e rara, a consulta é barata e frequente. Nunca reindexe dentro do caminho da requisição.

### Tamanho do trecho é uma decisão de engenharia

Esta é a variável que mais afeta a qualidade e a que mais gente ignora.

**Trecho grande** (2000+ caracteres) carrega bastante contexto ao redor da informação, então o modelo entende melhor o que está lendo. Em compensação, o embedding representa um vetor médio de vários assuntos, o que dilui a busca: um trecho que fala de cinco coisas não é fortemente próximo de nenhuma delas. E ele traz ruído para a janela.

**Trecho pequeno** (200 caracteres) produz embeddings precisos, porque cada vetor representa uma ideia só. Mas ele perde contexto: "o prazo é de 30 dias" não diz prazo de quê, e sozinho é inútil tanto para a busca quanto para o modelo.

Na prática, algo entre 500 e 1500 caracteres funciona como ponto de partida para prosa. Isso não é uma constante universal: código, tabelas e transcrições pedem estratégias diferentes. Quando a estrutura do documento é clara (seções, parágrafos), dividir respeitando essa estrutura bate qualquer corte por contagem de caracteres.

Trate isso como parâmetro a ser medido, não como valor mágico copiado de um tutorial.

### Sobreposição entre trechos

Cortar por tamanho fixo eventualmente parte uma frase ou um raciocínio no meio. A informação fica dividida entre o fim de um trecho e o começo do seguinte, e nenhum dos dois responde a pergunta.

A solução é sobreposição: cada trecho repete os últimos `N` caracteres do anterior. Com trechos de 800 e sobreposição de 150, o começo de cada trecho repete o fim do anterior, e uma informação que cai na fronteira aparece inteira em pelo menos um deles.

O custo é redundância no índice. Com 150 de sobreposição em trechos de 800, você armazena cerca de 23% a mais de vetores e texto. É um trade-off de espaço por recall, exatamente o mesmo formato de decisão de um índice de banco.

### Montar o prompt e instruir o modelo

Recuperar bem não basta. Se você entrega os trechos e pergunta, o modelo vai misturar o que leu com o que ele acha que sabe, sem avisar. A instrução precisa ser explícita e restritiva:

- Responda **apenas** com base nos trechos fornecidos.
- Se a resposta não estiver nos trechos, diga que não sabe. Não complete com conhecimento geral.
- Cite a fonte de cada afirmação.

O terceiro ponto não é decoração. A citação é o que permite auditar: ela transforma uma resposta em algo verificável por quem lê. Sem citação, você trocou uma alucinação sem fonte por uma alucinação com aparência de pesquisa, o que é pior. Numerar os trechos no prompt e pedir referência ao número é a forma mais simples de conseguir isso.

Ordem de montagem (você viu isso em context engineering): as instruções estáveis vêm primeiro, no `system`, onde podem ser cacheadas. Os trechos recuperados e a pergunta mudam a cada consulta e vão em `messages`, por último.

### Onde RAG falha

Três modos de falha que você precisa reconhecer antes de propor RAG para um problema.

**Perguntas agregadas.** "Quantos clientes existem no total?", "Qual o maior valor mencionado?", "Liste todas as exceções do contrato." Essas perguntas exigem varrer o documento inteiro, e RAG por construção olha só `k` trechos. Ele vai responder com base nos 5 trechos que recuperou e dar um número errado com toda a confiança do mundo. Para agregação, use SQL, não busca vetorial.

**Recuperação errada.** Se a busca traz o trecho errado, a resposta está condenada antes de o modelo começar. Um modelo bom não conserta recuperação ruim, e nenhum ajuste de prompt compensa isso.

**Perguntas que exigem juntar informação espalhada.** "Compare a política de 2023 com a de 2025" precisa de dois trechos específicos recuperados juntos. Uma busca por similaridade com a pergunta inteira pode trazer cinco trechos sobre 2023 e nenhum sobre 2025.

### Avaliar a recuperação separada da resposta

Quando o sistema erra, existem duas causas possíveis e elas se consertam de formas completamente diferentes. Meça separado.

**Avaliação da recuperação.** Monte um conjunto de perguntas para as quais você sabe qual trecho contém a resposta. Meça: o trecho correto apareceu nos `k` recuperados? Isso é *recall@k*. É uma métrica objetiva, barata de calcular, que não envolve o modelo e não custa nenhum token. Se o recall@5 está em 60%, nenhum trabalho de prompt vai salvar os 40% restantes.

**Avaliação da resposta.** Dado que os trechos certos foram recuperados, a resposta está correta? Citou a fonte certa? Disse "não sei" quando devia?

Depurar as duas juntas é o que faz alguém passar uma semana ajustando o prompt quando o problema era o tamanho do trecho.

## Na prática

Um RAG completo e funcional. Indexação, busca, montagem do prompt e resposta com citação.

```bash
pip install sentence-transformers numpy anthropic
```

```python
import numpy as np
import anthropic
from sentence_transformers import SentenceTransformer

encoder = SentenceTransformer("all-MiniLM-L6-v2")
client = anthropic.Anthropic()

SYSTEM = """Você responde perguntas usando apenas os trechos fornecidos.
Regras:
- Use somente a informação dos trechos. Não use conhecimento geral.
- Cite a fonte de cada afirmação no formato [n], onde n é o número do trecho.
- Se os trechos não contiverem a resposta, diga exatamente: "Não encontrei essa informação nos documentos."
"""


def split(text, size=800, overlap=150):
    step = size - overlap
    return [text[i : i + size] for i in range(0, len(text), step) if text[i : i + size].strip()]


def build_index(documents):
    chunks = []
    for name, text in documents.items():
        for position, chunk in enumerate(split(text)):
            chunks.append({"source": name, "position": position, "text": chunk})
    vectors = encoder.encode([c["text"] for c in chunks], normalize_embeddings=True)
    return chunks, vectors


def retrieve(question, chunks, vectors, k=3):
    q = encoder.encode([question], normalize_embeddings=True)[0]
    scores = vectors @ q
    return [chunks[i] for i in np.argsort(scores)[::-1][:k]]


def answer(question, chunks, vectors):
    found = retrieve(question, chunks, vectors)
    context = "\n\n".join(
        f"[{n}] (fonte: {c['source']}, trecho {c['position']})\n{c['text']}"
        for n, c in enumerate(found, start=1)
    )
    prompt = f"Trechos:\n\n{context}\n\nPergunta: {question}"
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return text, prompt, response.usage
```

São as cinco etapas do pipeline, uma função cada. Três pontos merecem atenção.

O `SYSTEM` é idêntico em toda consulta, então vai em `system` com `cache_control`, onde é cacheado. Os trechos e a pergunta mudam a cada chamada e vão em `messages`, depois do ponto de cache. Essa é a ordem de context engineering aplicada.

O `retrieve` usa `vectors @ q` porque os embeddings foram normalizados: o cosseno vira produto escalar, e numpy faz as `n` comparações de uma vez. É O(n·d), o suficiente até alguns milhares de trechos.

A leitura de `response.content` percorre os blocos filtrando por `.type == "text"`. `content` é uma lista de blocos, nunca uma string.

Rodando:

```python
docs = {
    "politica-reembolso.md": (
        "Solicitações de reembolso devem ser feitas em até 30 dias após a compra. "
        "O valor é estornado no mesmo meio de pagamento em até 7 dias úteis. "
        "Compras com desconto promocional não são reembolsáveis."
    ),
    "suporte.md": (
        "O suporte técnico atende de segunda a sexta, das 9h às 18h, horário de Brasília. "
        "Chamados críticos têm resposta em até 4 horas."
    ),
}

chunks, vectors = build_index(docs)
text, prompt, usage = answer("Tenho quanto tempo para pedir dinheiro de volta?", chunks, vectors)
print(text)
```

Saída:

```
Solicitações de reembolso devem ser feitas em até 30 dias após a compra [1]. O estorno é feito no mesmo meio de pagamento em até 7 dias úteis [1].
```

A pergunta não contém "reembolso" nem "30 dias". Busca por palavra-chave não acharia. A busca semântica trouxe o trecho certo e a citação `[1]` aponta para a fonte.

O prompt montado, que é o que realmente chega ao modelo:

```python
print(prompt)
```

```
Trechos:

[1] (fonte: politica-reembolso.md, trecho 0)
Solicitações de reembolso devem ser feitas em até 30 dias após a compra. O valor é estornado no mesmo meio de pagamento em até 7 dias úteis. Compras com desconto promocional não são reembolsáveis.

[2] (fonte: suporte.md, trecho 0)
O suporte técnico atende de segunda a sexta, das 9h às 18h, horário de Brasília. Chamados críticos têm resposta em até 4 horas.

Pergunta: Tenho quanto tempo para pedir dinheiro de volta?
```

Sempre imprima o prompt montado quando um RAG der resposta estranha. Na maioria das vezes o problema está visível ali, antes de o modelo entrar na história.

Testando o comportamento com pergunta fora do escopo:

```python
text, _, _ = answer("Qual o CNPJ da empresa?", chunks, vectors)
print(text)
```

```
Não encontrei essa informação nos documentos.
```

Esse é o teste mais importante do sistema. Sem a instrução explícita no `SYSTEM`, o modelo teria inventado um CNPJ com formato válido. Inclua sempre pelo menos um caso desses na sua suíte de testes.

E o modo de falha por agregação:

```python
text, _, _ = answer("Quantas regras existem ao todo nos documentos?", chunks, vectors)
print(text)
```

A resposta vai contar as regras dos 3 trechos recuperados, não de todos. Com `k=3` e um corpus de 200 trechos, o número está errado e a resposta soa segura. Esse tipo de pergunta não é para RAG.

Avaliando a recuperação sozinha, sem gastar um token:

```python
cases = [
    ("Tenho quanto tempo para pedir dinheiro de volta?", "politica-reembolso.md"),
    ("Até que horas vocês atendem?", "suporte.md"),
]

hits = sum(
    1
    for question, expected in cases
    if expected in {c["source"] for c in retrieve(question, chunks, vectors, k=3)}
)
print(f"recall@3: {hits}/{len(cases)}")
```

```
recall@3: 2/2
```

Rode isso primeiro, sempre. Se o recall estiver baixo, o problema é recuperação (tamanho do trecho, sobreposição, modelo de embedding, valor de `k`) e mexer no prompt não vai resolver nada.

## Armadilhas comuns

- **Ajustar o prompt quando o problema é a recuperação.** Se o trecho certo não foi recuperado, nenhuma instrução salva a resposta. Meça recall@k antes de tocar no prompt.
- **Usar RAG para perguntas agregadas.** "Quantos", "qual o total", "liste todos" exigem varrer o corpus inteiro. RAG olha `k` trechos e responde errado com confiança. Use SQL.
- **Esquecer de instruir o "não sei".** Sem instrução explícita, o modelo preenche a lacuna com conhecimento geral e você não tem como perceber. Teste esse caso sempre.
- **Cortar por tamanho fixo ignorando a estrutura do documento.** Partir uma tabela ou uma seção no meio produz trechos que não fazem sentido sozinhos. Quando há estrutura, respeite-a.
- **Reindexar dentro da requisição.** Gerar embeddings de todos os documentos a cada pergunta transforma uma operação de milissegundos em segundos e desperdiça computação. Indexe uma vez, consulte muitas.
- **Tratar a citação como enfeite.** Sem fonte verificável, a resposta é indistinguível de uma alucinação bem escrita, e ninguém consegue auditar quando dá errado.

## Recuperação ativa

1. Explique, com números, por que RAG é mais barato que colocar um corpus de 300 mil tokens no contexto de toda pergunta. Use os preços do Sonnet 5.
2. Seu RAG responde errado. Descreva a ordem em que você investiga e qual métrica calcula primeiro. Por quê essa e não outra?
3. Trechos de 200 caracteres e trechos de 3000 caracteres degradam o sistema de formas diferentes. Descreva cada uma.
4. Por que a sobreposição entre trechos existe? Qual o custo dela, e como você calcularia esse custo para trechos de 1000 com sobreposição de 200?
5. Um usuário pergunta "quantas exceções o contrato tem no total?" e o sistema responde "três". Explique por que essa resposta é suspeita mesmo se estiver certa por acaso.
6. Qual a função exata da citação de fonte? O que exatamente você perde ao removê-la, mantendo a resposta igual?
7. Você precisa comparar duas versões de uma política que estão em documentos diferentes. Por que a busca por similaridade simples provavelmente falha aqui, e o que você faria?

## Para ir além

- [Retrieval augmented generation](https://platform.claude.com/docs/en/build-with-claude/search-and-retrieval) — a página da Anthropic sobre padrões de recuperação e montagem de contexto.
- [Citations](https://platform.claude.com/docs/en/build-with-claude/citations) — recurso nativo da API que faz o modelo citar trechos exatos de documentos, com localização por caractere ou página.
- [Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) — técnica que adiciona contexto a cada trecho antes de indexar, reduzindo a taxa de falha na recuperação.
- [Documentação do pgvector](https://github.com/pgvector/pgvector) — extensão do PostgreSQL para busca vetorial, quando a lista em memória deixar de ser suficiente.
