**De onde vêm os casos.** Do histórico real de mensagens de suporte, não da minha imaginação. Pegaria umas 100 mensagens já classificadas por gente do time, garantindo que as quatro categorias apareçam, inclusive as raras. Vinte casos reais valem mais que duzentos inventados, porque mensagens reais são bagunçadas: vêm com erro de digitação, dois assuntos na mesma mensagem, e gente reclamando de cobrança enquanto relata um bug.

Incluiria de propósito casos limite: mensagem ambígua que serve para duas categorias, mensagem vazia ou só com "oi", mensagem fora do escopo (alguém pedindo emprego), e mensagem em outro idioma. São eles que quebram o sistema em produção.

**Como se corrige.** Verificação programática: a saída é uma de quatro categorias, então basta comparar com a categoria esperada. É determinístico, instantâneo e custa zero. Modelo-juiz aqui seria desperdício: juiz é para saída sem resposta única, como um resumo ou uma explicação.

**Como evito me enganar.** Separo os 100 casos em dois conjuntos: uns 30 para desenvolvimento, que eu olho enquanto ajusto o prompt, e uns 70 para teste, que eu só rodo depois de decidir a mudança. Se eu ajustar o prompt olhando os mesmos casos que uso para medir, eu acabo otimizando para aquele gabarito específico, o número sobe, e a qualidade real não muda. É o mesmo raciocínio de treino e teste.

**Variação entre execuções.** Como existe amostragem, a mesma mensagem pode ser classificada diferente em duas chamadas. Rodaria cada caso três vezes e olharia a taxa de acerto, não o resultado de uma execução. Os casos que às vezes acertam e às vezes erram merecem atenção separada: eles indicam ambiguidade real, seja na mensagem, seja na definição da categoria.

**O que mais medir.** Custo por mensagem e latência. Se uma mudança de prompt sobe o acerto de 88% para 90% mas dobra o custo, para um volume alto de mensagens isso pode não valer. Mediria também a matriz de confusão, e não só o acerto total: errar `cobranca` como `duvida` é bem menos grave do que classificar tudo como `outro` e ninguém ser atendido.

**Quando rodar.** A cada mudança de prompt e a cada troca de modelo, antes de subir. Sem isso, uma regressão silenciosa só aparece pela reclamação do cliente.
