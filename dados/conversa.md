# Registro da conversa — Projeto Fanorona via Sockets

Este documento resume, em ordem cronológica, toda a conversa de desenvolvimento
do projeto Fanorona (jogo de tabuleiro com comunicação via sockets TCP),
incluindo decisões tomadas, bugs encontrados/corrigidos e explicações dadas
ao longo do processo.

---

## 1. Execução inicial do projeto (versão Java)

O projeto começou como uma implementação em **Java (Swing)**, localizada em
`src/Main.java` e pacotes `fanorona.model` / `fanorona.net` / `fanorona.gui`.

- O ambiente não tinha JDK instalado (`java`/`javac` não encontrados).
- Foi instalado o **OpenJDK 21** via `apt` (com autorização do usuário).
- O projeto foi compilado (`javac -d out ...`) e executado (`java -cp out fanorona.Main`)
  com sucesso, abrindo a janela do jogo.
- Notou-se que a estrutura de pastas (`src/gui`, `src/model`, `src/net`) não
  seguia exatamente os pacotes declarados (`fanorona.gui`, etc.), mas isso não
  impediu a compilação por não usar `-sourcepath` implícito problemático.

## 2. Redesenho da interface (Java) com base em um protótipo visual

O usuário forneceu um PDF de protótipo ("Telas para prototipar.pdf") com 4 telas:

1. **Conectar** — título "FANORONA", abas Hospedar/Entrar, campos de nome/IP/porta.
2. **Tabuleiro & Chat** — cabeçalho com turno, tabuleiro, histórico de jogadas, chat.
3. **Confirmar desistência** — modal de confirmação.
4. **Fim de jogo** — vencedor, motivo, estatísticas, botões Sair/Jogar novamente.

Foi feita uma reescrita completa da GUI Java para bater com esse protótipo:

- Criado um "design system" reutilizável: `Theme.java`, `RoundedPanel.java`,
  `RoundButton.java`, `ModalOverlay.java`.
- Reescritos: `ConnectPanel`, `BoardPanel`, `ChatPanel`, `GamePanel`.
- Criados: `HistoryPanel` (histórico de jogadas no formato `#n Nome C2 → C3 (captura xN)`),
  `GameOverPanel`, `GameOverInfo`.
- Protocolo de rede estendido: troca de nomes de jogador (`HELLO`) e revanche (`REMATCH`).
- `MainFrame` reescrito para navegar entre as 3 telas e atuar como listener de
  rede persistente (repassando eventos para o `GamePanel` ativo).

### Bugs encontrados e corrigidos nessa fase

- **Texto cortado em botões** (abas "Hospedar partida"/"Entrar em partida",
  botão "Jogar novamente"): a margem interna do botão era maior que o espaço
  disponível, fazendo o Swing desenhar "..." em vez do texto. Corrigido
  reduzindo a margem.
- **Ícone de medalha (emoji 🏅) não renderizava**: ambiente sem fonte de emoji
  colorido. Substituído por um círculo desenhado com uma estrela "★" (fonte
  padrão, sem depender de emoji).
- **Bug de quebra de linha em `JLabel` com HTML** (`<body style='width:Npx'>`):
  o auto-reflow do Swing calculava mal a altura/posição das linhas dentro de
  um `BoxLayout`, cortando texto no meio da palavra. Corrigido com um helper
  `Theme.wrapHtml(...)` que quebra o texto manualmente com `<br>` explícitos,
  usando `FontMetrics` para medir a largura real.
- **Campos cortados na tela de conectar** (relatado pelo usuário com print de
  tela): o card tinha uma altura fixa "chutada" (`setPreferredSize`), que era
  insuficiente para as métricas de fonte reais do sistema do usuário. Corrigido
  fazendo o card calcular a altura sob demanda (`RoundedPanel.setFixedWidth` +
  `getPreferredSize()` sobrescrito), em vez de travar um valor medido cedo demais.
- **IP padrão da tela de conectar** vinha preenchido com o IP de exemplo do
  mockup (`192.168.0.12`), impedindo testar localmente (duas instâncias na
  mesma máquina). Trocado o padrão para `localhost`.

### Indicativo de jogador

A pedido do usuário, foi adicionado um rótulo "Você é `<nome>`" abaixo do
logotipo "FANORONA" no cabeçalho da tela de jogo, para deixar claro de quem é
aquela tela (distinto do indicador "Vez de `<nome>`", que mostra de quem é a
vez atual).

## 3. Port completo para Python (Tkinter)

O usuário pediu para portar todo o projeto Java para Python, alegando que
Python seria mais fácil de explicar (ex.: para o professor da disciplina).

- Escolhida a biblioteca **Tkinter** (padrão do Python, não precisa de
  `pip install`) em vez de Pygame — justificativa: o app é majoritariamente
  formulários/widgets (campos, botões, listas, chat), não um jogo de ação em
  tempo real; só o tabuleiro precisa de desenho, e o `Canvas` do próprio
  Tkinter resolve isso.
- Estrutura de módulos espelhando os pacotes Java (para facilitar comparação):
  - `fanorona/model/`: `color.py`, `point.py` (era `Pt`), `direction.py` (era
    `Dir`, renomeado para não conflitar com a função embutida `dir()`),
    `capture_option.py`, `board.py`, `game_engine.py`.
  - `fanorona/net/`: `game_connection.py`, `network_setup.py`.
  - `fanorona/gui/`: `theme.py`, `dialogs.py`, `connect_screen.py`,
    `board_canvas.py`, `history_panel.py`, `chat_panel.py`, `game_screen.py`,
    `game_over_screen.py`, `game_over_info.py`, `main_app.py`.
  - `main.py` (ponto de entrada) e `test_game_engine.py` (bateria de testes
    do motor, porta do antigo `TestHarness.java`).
- Diferenças de design relevantes:
  - Diálogos modais (confirmar desistência, escolha de captura ambígua) viraram
    `tk.Toplevel` com `grab_set()` — mais idiomático no Tkinter do que a
    sobreposição customizada usada no Java.
  - O tabuleiro é desenhado num `tk.Canvas` (`create_line`/`create_oval`).
  - O chat usa um único `tk.Text` com "tags" para simular balões de mensagem
    (cor de fundo e alinhamento por mensagem).
  - A comunicação entre a thread de rede e a interface usa uma `queue.Queue`
    de eventos, esvaziada periodicamente pela janela principal via
    `root.after(...)` — o equivalente Python ao `SwingUtilities.invokeLater`
    do Java (Tkinter também não é thread-safe).
- Validação sem precisar de GUI: `test_game_engine.py` (17 checagens, todas
  `[OK]`, idêntico à versão Java) e um teste manual de rede (host + entrar +
  troca de nomes + jogada), ambos rodados com sucesso antes mesmo do `tkinter`
  estar instalado no sistema do usuário.
- O `tkinter` não vinha instalado por padrão no sistema (`ModuleNotFoundError`);
  orientado a instalar via `sudo apt-get install -y python3-tk`.

### Remoção do Java do projeto

A pedido do usuário, todo o material Java foi removido do repositório:
`src/`, `out/` (classes compiladas) e `Fanorona/` (outra pasta com `.class`
antigos). A pasta `python/` (onde a porta havia sido criada) foi promovida
para a raiz do projeto (arquivos `main.py`, `fanorona/`, `test_game_engine.py`
diretamente na raiz), e o `README.md` foi reescrito do zero para descrever
apenas a versão Python.

## 4. Pergunta do professor sobre threads e correção de arquitetura

O professor da disciplina comentou: *"Vcs vão precisar de threads para
paralelizar envio e recepção nos sockets. estamos fazendo assim?"*

Ao revisar o código, constatou-se que:
- A **recepção** já rodava em thread própria (loop bloqueante de `readline()`).
- O **envio**, porém, acontecia diretamente na thread chamadora (geralmente a
  da interface), sem thread dedicada — não totalmente "paralelizado".

Correção aplicada em `game_connection.py`:
- Cada `GameConnection` passou a ter **duas threads**: uma de leitura
  (`_read_loop`) e uma de escrita (`_write_loop`).
- Os métodos `send_move`/`send_chat`/etc. agora só colocam a mensagem numa
  fila de saída (`_outgoing`, uma `queue.Queue`) e retornam na hora; é a
  thread de escrita que efetivamente manda pelo socket, em paralelo com a
  thread de leitura.
- Durante os testes dessa mudança, foi encontrado e corrigido um **bug real**:
  ao fechar a conexão (`close()`), a thread de leitura não terminava, porque
  `sock.makefile()` mantém referências ao socket que atrasam o fechamento
  real do descritor. Corrigido chamando `sock.shutdown(socket.SHUT_RDWR)`
  antes de `sock.close()`, o que interrompe imediatamente qualquer leitura
  bloqueada, mesmo em outra thread.
- Testes confirmaram: 4 threads ativas por par de conexão (2 leitoras + 2
  escritoras), todas encerrando corretamente ao fechar.
- O `README.md` ganhou uma seção **"Concorrência: threads de envio e
  recepção"** explicando essa arquitetura, para apresentar ao professor.

## 5. Remoção de referências ao Java/port do código

Como o código seria apresentado ao professor, o usuário pediu para remover
qualquer menção a "Java", "Swing" ou "porta/equivalente a X.java" dos
comentários e docstrings — o código deveria se explicar por si mesmo, sem
expor que veio de uma versão anterior em outra linguagem. Foi feita uma
varredura completa (`grep`) em todos os arquivos `.py` e no `README.md`,
reescrevendo cada docstring/comentário para descrever o código como ele é.

## 6. Perguntas explicativas ao longo da conversa

Diversas perguntas conceituais foram respondidas durante o desenvolvimento,
sempre referenciando o código real do projeto:

- **"O que seria o Tkinter, por que não usar o Pygame?"** — Tkinter é a
  biblioteca gráfica padrão do Python, baseada em widgets prontos (botão,
  campo de texto, lista) e orientada a eventos. Pygame é uma biblioteca de
  jogos em tempo real (game loop, desenho quadro a quadro), sem widgets
  prontos. Como o Fanorona é um jogo por turnos com bastante formulário/lista/
  chat e pouca animação, o Tkinter economiza muito mais código.
- **"Como funciona o gatilho do popup de captura ambígua?"** — explicado o
  fluxo: `GameEngine.try_move` calcula as duas linhas de captura (aproximação
  e afastamento); se ambas tiverem peças capturáveis, devolve `NEEDS_CHOICE`
  sem alterar o tabuleiro; a tela (`GameScreen._attempt_move`) reage a esse
  resultado abrindo o diálogo modal (`dialogs.ask_capture_choice`), que
  bloqueia até o usuário escolher, e então chama `try_move` de novo, agora
  com a escolha, aplicando a jogada de verdade.
- **"Estamos utilizando sockets?"** — Confirmado: sockets TCP puros do módulo
  `socket` da biblioteca padrão (`socket.socket(AF_INET, SOCK_STREAM)` para
  hospedar, `socket.create_connection` para entrar), sem nenhuma biblioteca de
  rede de alto nível por cima.
- **"Pode explicar o pipeline do projeto?"** — Explicado o fluxo completo:
  início (`main.py` → `MainApp` → `ConnectScreen`) → conexão (`NetworkSetup`
  → `GameConnection.exchange_names`) → início da partida (`connection.start`
  cria as threads de rede, `MainApp` começa a esvaziar a fila de eventos) →
  jogada local (clique → `GameEngine.try_move` → `connection.send_move`) →
  jogada remota (thread de leitura → fila de eventos → `MainApp._poll_events`
  → `GameScreen.apply_remote_move` → mesmo `try_move`, determinístico) → fim
  de jogo e revanche (mesma conexão, novo `GameEngine`).

## 7. Bug do chat (campo de digitar invisível)

O usuário reportou "o chat não está funcionando": ao clicar na área do chat,
digitar e apertar Enter, nada acontecia.

### Investigação

Testes automatizados extensivos (rede isolada, `GameScreen` completo, fluxo
real via `MainApp` com duas janelas e `mainloop()` de verdade, mensagens com
acentuação, envio nos dois sentidos) passaram em **todos os cenários** — o
que indicava que a lógica de envio/recepção estava correta.

O usuário então enviou uma **captura de tela real**, que revelou o problema:
só aparecia a caixa de histórico do chat — **o campo de digitar mensagem e o
botão de enviar não apareciam na tela**. O usuário estava sem querer clicando
na caixa de histórico (somente leitura), por isso nada acontecia ao digitar.

### Causa raiz

Bug de **ordem de empacotamento no Tkinter** (`chat_panel.py`): a área de
histórico (`text_frame`, empacotada com `expand=True` para ocupar o espaço
disponível) era empacotada *antes* da barra de digitar (campo + botão). Como
no Tkinter quem é empacotado primeiro reserva espaço primeiro, o histórico
tomava toda a altura disponível, e a barra de digitar ficava com **altura
zero** — existia no código (confirmado via `winfo_ismapped() == 0`, altura
medida em 1 pixel), mas era invisível na tela.

### Correção

Invertida a ordem de empacotamento: a barra de digitar agora é empacotada
primeiro, com `side="bottom"` (reservando seu espaço no rodapé do painel), e
só depois o histórico é empacotado para ocupar o espaço restante. Confirmado
com uma captura de tela real do app rodando: agora aparecem histórico **e**
campo de digitar + botão "→" corretamente.

Testes re-executados após a correção: 17/17 testes do motor, rede (host +
entrar + jogada + chat + fechamento de 4 threads), análise estática
(`pyflakes`) e fluxo completo bidirecional de chat — todos passando.

## 8. Documentação (`README.md`)

O `README.md` foi mantido atualizado ao longo de todo o processo, cobrindo:
pré-requisitos e como executar (incluindo teste local com duas instâncias),
estrutura do código, representação do tabuleiro, regras de movimento/captura,
testes do motor, protocolo de rede (tabela de mensagens) e a seção de
concorrência (threads de envio/recepção) pensada especificamente para a
apresentação ao professor.

---

*Este arquivo foi gerado automaticamente a partir do histórico da conversa
de desenvolvimento, a pedido do usuário.*
