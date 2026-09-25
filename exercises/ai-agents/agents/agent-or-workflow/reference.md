**1. Nota fiscal: workflow.** A sequência é conhecida: extrair com saída estruturada, validar, gravar. Nada aqui depende de uma descoberta no meio do caminho. Um agente aqui só acrescenta custo, latência e imprevisibilidade, e fica mais difícil de testar.

**2. Traduzir 10 mil descrições: workflow, e nem isso.** São 10 mil chamadas independentes, sem laço nenhum. Vale usar o modelo mais barato que atenda e processar em lote. Um agente por descrição seria desperdício puro.

**3. Investigar o erro 500: agente é defensável.** Aqui a sequência não é conhecida: o que olhar depois depende do que o log mostrou. Talvez seja um deploy recente, talvez um banco lento, talvez uma dependência fora do ar. É o caso clássico de exploração aberta. Ainda assim, com limite de voltas, orçamento e registro de cada passo, porque o erro se propaga: uma hipótese errada no meio leva a dez voltas erradas depois.

**4. Perguntas de clientes: workflow (RAG).** Buscar trechos relevantes, montar o prompt, responder citando a fonte. A sequência é fixa. Só viraria agente se a resposta precisasse de várias buscas encadeadas, decididas a partir do que a primeira trouxe, e nesse caso comece medindo se o RAG simples já resolve.

**5. Revisar PR: fronteira, e depende do escopo.** Se é revisar o diff, é workflow: mande o diff e peça a revisão. Se é revisar entendendo o impacto (abrir os arquivos chamados, ver os testes existentes, checar se a mudança quebra outro módulo), vira exploração, e aí um agente com ferramentas de leitura de arquivo se justifica. Comece pelo workflow e só suba se a revisão estiver rasa por falta de contexto.

O critério que decide os cinco é o mesmo: **eu consigo escrever a sequência de passos agora, no código, sem saber qual é a entrada específica?** Se sim, workflow: mais barato, mais rápido, testável, e previsível. Se a sequência depende do que for descoberto no meio, aí o agente ganha o direito de existir, com limites explícitos.
