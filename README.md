# Fanorona via Sockets — Documentação

Projeto de Programação Paralela e Distribuída (IFCE) — implementação do
jogo de tabuleiro **Fanorona** com comunicação entre dois tabuleiros via
**Sockets TCP**, em Python (Tkinter).

## 1. Como executar

### Pré-requisitos
- Python 3.10 ou mais recente.
- Tkinter (biblioteca gráfica **padrão** do Python — não precisa de
  `pip install`, mas em algumas distros Linux é empacotada à parte do
  Python):
  ```
  sudo apt-get install -y python3-tk
  ```
  No Windows e no macOS o Tkinter normalmente já vem junto com o
  instalador oficial do Python.

Para conferir se já está tudo certo:
```
python3 -c "import tkinter; print('tkinter OK')"
```

### Rodando o jogo
Na raiz do projeto:
```
python3 main.py
```
Isso abre a tela de conexão. Nenhuma outra dependência precisa ser
instalada (`pip install` não é necessário) — o projeto usa só a
biblioteca padrão do Python (`tkinter`, `socket`, `threading`, `queue`).

### Jogando uma partida (dois jogadores, duas máquinas)
1. Uma pessoa fica na aba **"Hospedar partida"**, informa seu nome e
   uma porta (ex.: 5000), e clica em **Conectar**. Quem hospeda sempre
   joga com as peças escuras e começa a partida.
2. A outra pessoa clica na aba **"Entrar em partida"**, informa seu
   nome, o IP de quem hospedou e a mesma porta, e clica em **Conectar**.
   Essa pessoa joga com as peças douradas.

### Testando sozinho, na mesma máquina
Abra dois terminais e rode `python3 main.py` em cada um. Em um deles
deixe na aba "Hospedar partida"; no outro, use a aba "Entrar em
partida" com IP `localhost` (valor padrão do campo) e a mesma porta.

## 2. Estrutura do código

```
main.py                        -> ponto de entrada
test_game_engine.py            -> bateria de testes manuais do motor (ver seção 5)
fanorona/
 ├── model/                    -> regras do jogo (não depende de GUI nem de rede)
 │    ├── color.py             -> Color: WHITE/BLACK
 │    ├── point.py             -> Point: um ponto (linha, coluna) do tabuleiro
 │    ├── direction.py         -> Direction: uma das 8 direções de movimento
 │    ├── board.py             -> Board: tabuleiro 5x9, posição inicial, topologia
 │    ├── capture_option.py    -> CaptureOption: uma opção de captura (tipo + peças capturadas)
 │    └── game_engine.py       -> GameEngine: turnos, movimentos, capturas, sequência, vitória
 ├── net/                      -> comunicação via sockets
 │    ├── game_connection.py   -> protocolo de texto sobre socket (envia/recebe)
 │    └── network_setup.py     -> hospedar (socket servidor) / conectar (socket cliente)
 └── gui/                      -> interface gráfica (Tkinter)
      ├── theme.py             -> cores, fontes e botões/cartões reutilizáveis
      ├── dialogs.py           -> diálogos modais (confirmar desistência, captura ambígua)
      ├── connect_screen.py    -> tela inicial (hospedar/entrar)
      ├── game_screen.py       -> tela da partida (liga tabuleiro + rede + chat)
      ├── board_canvas.py      -> desenha o tabuleiro e captura cliques
      ├── history_panel.py     -> histórico de jogadas
      ├── chat_panel.py        -> chat da partida
      ├── game_over_screen.py  -> tela de fim de jogo
      ├── game_over_info.py    -> dados exibidos na tela de fim de jogo
      └── main_app.py          -> janela principal, troca de tela, fila de eventos de rede
```

A separação em três pacotes foi intencional:
- **model**: só sabe as regras do Fanorona. Não conhece Tkinter nem socket.
  Isso permite testar a lógica isoladamente (veja `test_game_engine.py`).
- **net**: só sabe enviar/receber texto por um socket. Não conhece as
  regras do jogo — apenas repassa coordenadas e tipos de captura.
- **gui**: a "cola" entre as duas coisas — interpreta cliques do mouse,
  chama o `GameEngine`, e manda o resultado pela rede.

## 3. Como o tabuleiro é representado

O tabuleiro tem 5 linhas x 9 colunas (45 intersecções). Casas vizinhas na
horizontal e na vertical são sempre ligadas por uma linha. As ligações
diagonais existem apenas em metade das "células" do tabuleiro, alternando
em padrão de tabuleiro de xadrez — é isso que forma o desenho
característico de "X" alternados do Fanorona real. Essa regra está em
`Board.is_connected(point, direction)`.

A posição inicial (`Board._setup_initial_position`) segue o padrão
clássico: as duas linhas mais próximas de cada jogador ficam completas
(18 peças), e a linha central se divide: 4 peças de cada lado e a casa
central vazia — totalizando 22 peças por jogador.

## 4. Regras de movimento e captura implementadas

Tudo isso está em `game_engine.py`:

- **Movimento simples**: mover uma peça para uma casa vazia vizinha
  ligada por uma linha. Só é permitido como único movimento do turno
  (se não captura nada).
- **Captura por aproximação**: ao mover a peça, se na mesma direção do
  movimento houver peça(s) adversária(s) em sequência, elas são capturadas.
- **Captura por afastamento**: se peça(s) adversária(s) estavam coladas
  à casa de origem, na direção **oposta** ao movimento, elas também podem
  ser capturadas.
- **Ambiguidade**: quando os dois tipos de captura são possíveis ao mesmo
  tempo, o jogo pergunta ao jogador qual ele quer usar (`NEEDS_CHOICE`
  em `GameEngine`, tratado com um diálogo em `game_screen.py`).
- **Sequência de capturas (chain)**: depois de capturar, a mesma peça
  pode continuar se movendo e capturando, desde que:
  - o novo movimento também resulte em captura;
  - a peça não passe duas vezes pela mesma casa no mesmo turno;
  - a peça não repita a mesma direção do passo imediatamente anterior
    (regra clássica do Fanorona para evitar capturas "ida e volta").
  O jogador pode escolher parar a sequência a qualquer momento clicando
  em "Terminar jogada".
- **Fim de jogo**: um jogador vence quando o adversário perde todas as
  peças, quando o adversário não tem nenhum movimento legal, ou quando o
  adversário desiste (botão "Desistir"). Depois do fim de jogo, dá para
  pedir revanche (reinicia a partida usando a mesma conexão).

Toda essa lógica foi testada isoladamente antes de integrar com a
interface gráfica (veja a seção 5).

## 5. Testes da lógica (`test_game_engine.py`)

O arquivo `test_game_engine.py` é um pequeno programa de console (sem
GUI, não depende de Tkinter) que monta cenários customizados de
tabuleiro e verifica, passo a passo, que o motor de regras se comporta
como esperado: contagem de peças, existência das linhas diagonais
alternadas, captura por aproximação, captura por afastamento,
ambiguidade de escolha, e uma sequência real de duas capturas em
direções diferentes.

Para executar:
```
python3 test_game_engine.py
```
Todos os testes imprimem `[OK]` quando passam.

## 6. Protocolo de rede

A comunicação usa **sockets TCP** com um protocolo simples de texto, uma
mensagem por linha (implementado em `game_connection.py`):

| Mensagem                                   | Significado                                  |
|---------------------------------------------|-----------------------------------------------|
| `HELLO nome`                                | Identificação inicial (troca de nomes), antes da partida começar. |
| `MOVE fromRow fromCol toRow toCol TIPO`     | Uma jogada. `TIPO` é `NONE`, `APPROACH` ou `WITHDRAWAL` — já resolvido por quem jogou, para o outro lado só precisar repetir a mesma jogada. |
| `ENDTURN`                                   | O jogador encerrou voluntariamente uma sequência de capturas. |
| `RESIGN`                                    | O jogador desistiu da partida.                |
| `REMATCH`                                   | Pedido de revanche (reinicia a partida dos dois lados). |
| `CHAT texto`                                | Mensagem de chat (resto da linha).            |

**Por que enviar apenas coordenadas, e não todo o estado do tabuleiro?**
Como os dois lados executam exatamente o mesmo `GameEngine` com o mesmo
algoritmo determinístico, basta que cada lado replique a jogada recebida
da mesma forma que quem jogou localmente. Isso mantém o protocolo simples
e o tabuleiro sempre sincronizado, sem precisar transmitir o estado
inteiro a cada jogada.

Quem hospeda a partida (`NetworkSetup.host`) abre um socket servidor e
aguarda uma conexão; quem entra (`NetworkSetup.join`) conecta diretamente
pelo IP e porta informados. Depois de estabelecida a conexão, os dois
lados usam a mesma classe `GameConnection` para trocar mensagens.

### Concorrência: threads de envio e recepção

Cada `GameConnection` usa **duas threads próprias**, uma para cada
sentido da comunicação (ver `game_connection.py`, método `start`):

- **Thread de leitura** (`_read_loop`): fica bloqueada em `readline()`
  esperando dados chegarem do socket. Cada mensagem recebida é
  transformada num evento e colocada numa `queue.Queue` de entrada —
  ela nunca mexe na interface diretamente.
- **Thread de escrita** (`_write_loop`): os métodos `send_move`,
  `send_chat` etc. não escrevem no socket na hora — eles só colocam a
  linha numa fila de saída e retornam imediatamente. É essa thread,
  rodando em paralelo com a de leitura, que retira as linhas da fila e
  efetivamente as envia pelo socket.

Isso significa que enviar uma mensagem nunca fica esperando a leitura
(nem vice-versa): as duas operações realmente acontecem em paralelo,
em threads diferentes, comunicando-se com o resto do programa através
de filas (`queue.Queue`), que são seguras para uso entre threads.

Quem finalmente aplica os eventos recebidos na tela é a janela
principal (`main_app.py`), que esvazia a fila de entrada periodicamente
via `root.after(...)`, sempre na thread principal — o Tkinter, como a
maioria das bibliotecas gráficas, só pode ser manipulado com segurança
por uma única thread, então a leitura de rede nunca atualiza a
interface diretamente.

`NetworkSetup.host`/`NetworkSetup.join` também rodam em suas próprias
threads (`fanorona-host-thread`/`fanorona-join-thread`), já que abrir
o socket servidor e aceitar/conectar (`accept()`/`connect()`) também
são chamadas bloqueantes — sem isso, a janela travaria enquanto
esperasse o outro jogador conectar.

## 7. Limitações conhecidas / possíveis melhorias

- Não há reconexão automática caso a conexão caia no meio da partida
  (o jogo apenas avisa que a conexão foi perdida).
- Não há opção de configurar quem começa jogando além da convenção
  "quem hospeda começa".
- Não há placar de partidas anteriores nem replay de jogadas.

Essas melhorias não fazem parte dos requisitos do projeto, mas poderiam
ser adicionadas facilmente por cima da arquitetura atual, já que a
separação entre regras (`model`), rede (`net`) e interface (`gui`) deixa
cada parte independente das outras.
