# ADR 0005 — Interface em formato de aplicação

- **Data:** 2026-09-25
- **Status:** aceita
- **Substitui:** a decisão 7 do ADR 0002 (tipografia) e a decisão 9 do ADR 0004 (parte visual)

## Contexto

A criadora rejeitou a primeira interface: disse que estava "ridícula, cara de IA", que o conteúdo não aproveitava o espaço lateral da tela, que o modo claro deveria ser o padrão e que o botão de tema estava feio.

O documento de requisitos já pedia para evitar "clichês de feito por IA". A primeira versão caiu neles de outro jeito: coluna central estreita (820 px), saudação grande ("Oi, Andressa."), número gigante de streak, rótulos de seção em maiúsculas espaçadas, *chips* arredondados por toda parte e símbolos unicode (✔ ▶ ○ ·) no lugar de ícones.

## Decisões

### 1. Layout de aplicação, não de página

Barra lateral fixa com a navegação, e área principal que ocupa o resto da tela (sem largura máxima, com margem proporcional). O conteúdo se organiza em grades de duas colunas:

- **Hoje:** o que estudar e as trilhas à esquerda; check-in, sessão e gráfico à direita.
- **Módulo:** teoria à esquerda; exercícios, sessão e conclusão numa coluna lateral que acompanha a rolagem.
- **Exercício:** enunciado, dicas e histórico à esquerda; editor e resultado à direita, lado a lado.
- **Mapa:** competências e grafo à esquerda; diagnóstico, objetivo e lacunas à direita.

Abaixo de 1100 px as grades viram uma coluna; abaixo de 760 px a barra lateral vira uma faixa horizontal no topo.

### 2. Modo claro é o padrão

O tema deixa de seguir o sistema por padrão. São três opções explícitas num seletor segmentado discreto no pé da barra lateral: Claro (padrão), Escuro e Sistema. A escolha fica no `localStorage`.

### 3. Paleta mais sóbria

O coral da marca ficou mais escuro (`#C4461E` no claro), para dar contraste suficiente sobre branco e para ser usado como acento pontual, não como enfeite. Os neutros ficaram levemente quentes, sem chegar a bege forte: fundo `#F6F5F2`, cartões brancos, barra lateral um tom acima do fundo.

### 4. Tipografia com contraste entre título e texto

Source Serif 4 nos títulos (serifada, com ar de documento técnico), IBM Plex Sans no corpo e IBM Plex Mono no código. A fonte base caiu para 15 px, tamanho de ferramenta, não de página de leitura.

### 5. Ícones desenhados, não símbolos de texto

Um `<svg>` com `<symbol>` no HTML guarda os ícones (navegação, status de módulo e exercício, dica, iniciar e encerrar sessão), usados por referência. Substituem os ✔ ▶ ○ · e mantêm alinhamento e peso consistentes.

### 6. Hierarquia por cartão, sem elemento decorativo

Cada bloco é um cartão branco com borda de 1 px, sem sombra. Os números de destaque (streak, XP) ficam numa faixa compacta no cabeçalho da página, em vez de ocupar meia tela. Os rótulos de seção voltaram a ser títulos normais, sem maiúsculas espaçadas.

## Consequências

- `hone/ui_palette.py` continua sendo a fonte única das cores, agora sem os estilos de terminal (removidos no ADR 0004).
- Nenhuma mudança na API nem nos engines: a reformulação foi só de HTML, CSS e da camada de renderização do JavaScript.
