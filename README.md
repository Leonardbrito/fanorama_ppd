# Fanorona via RMI/RPC — Documentação

Projeto de Programação Paralela e Distribuída (IFCE) — implementação do
jogo de tabuleiro **Fanorona** para dois jogadores, cada um com o seu
tabuleiro (podendo estar em máquinas diferentes), comunicando-se
**somente por RMI/RPC** (XML-RPC, biblioteca padrão `xmlrpc` do Python).
Interface gráfica em Tkinter.

## Índice

1. [Visão geral](#1-visão-geral)
2. [Como executar](#2-como-executar)
3. [Estrutura do código](#3-estrutura-do-código)
4. [Como o tabuleiro é representado](#4-como-o-tabuleiro-é-representado)
5. [Regras de movimento e captura implementadas](#5-regras-de-movimento-e-captura-implementadas)
6. [Comunicação via RMI/RPC](#6-comunicação-via-rmirpc)
7. [O caminho de uma jogada, do clique à outra tela](#7-o-caminho-de-uma-jogada-do-clique-à-outra-tela)
8. [Concorrência (threads)](#8-concorrência-threads)
9. [Mapa das funcionalidades pedidas](#9-mapa-das-funcionalidades-pedidas)
10. [Glossário](#10-glossário)
11. [Limitações conhecidas](#11-limitações-conhecidas)

---

## 1. Visão geral

### O que é RMI/RPC

- **RPC** (*Remote Procedure Call*) permite chamar uma função que roda em
  **outra máquina** como se fosse uma função local. Quem chama escreve
  `adversario.move(...)`; a biblioteca serializa os argumentos, manda pela
  rede, executa lá e devolve o resultado.
- **RMI** (*Remote Method Invocation*) é a mesma ideia orientada a objetos
  (nome vindo do Java): chama-se um método de um **objeto remoto** através
  de um representante local, o *proxy* (ou *stub*).

Neste projeto isso é feito com o **XML-RPC** do Python. Ele é simples de
entender porque só tem duas peças:

| Peça | Classe do Python | Papel |
|---|---|---|
| Servidor | `xmlrpc.server.SimpleXMLRPCServer` | Registra um objeto e deixa **o outro lado** chamar os métodos dele. |
| Proxy | `xmlrpc.client.ServerProxy` | Representa o servidor **do outro lado**. Chamar um método do proxy executa o método lá. |

### A ideia central do projeto

Cada tabuleiro é **servidor e cliente ao mesmo tempo**:

```
        Máquina A                                 Máquina B
 ┌──────────────────────┐                  ┌──────────────────────┐
 │ servidor RPC         │ <--------------  │ proxy de A           │
 │  move, chat, ...     │   B chama A      │                      │
 │                      │                  │                      │
 │ proxy de B           │  -------------->  │ servidor RPC         │
 │                      │   A chama B      │  move, chat, ...     │
 └──────────────────────┘                  └──────────────────────┘
```

Quando eu jogo, **chamo `move` no servidor do adversário**. Quando ele joga,
**ele chama `move` no meu servidor**. Não existe um servidor central, e não
existe nenhum protocolo de texto escrito à mão: só chamadas de método.

### Por que só coordenadas, e não o estado do tabuleiro?

Os dois lados rodam **o mesmo `GameEngine`**, que é determinístico (mesma
posição + mesma jogada = mesmo resultado). Então basta enviar *"o que foi
decidido"* — `move(1, 2, 2, 3, "APPROACH")` — e o outro lado refaz a jogada
no próprio tabuleiro. Os dois tabuleiros ficam sempre iguais sem precisar
transmitir o estado inteiro a cada jogada.

---

## 2. Como executar

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
instalada — o projeto usa só a biblioteca padrão do Python (`tkinter`,
`xmlrpc`, `threading`, `queue`).

### Jogando uma partida (dois jogadores, duas máquinas)
1. Uma pessoa fica na aba **"Hospedar partida"**, informa seu nome e
   uma porta (ex.: 5000), e clica em **Conectar**. Quem hospeda sempre
   joga com as peças escuras e começa a partida.
2. A outra pessoa clica na aba **"Entrar em partida"**, informa seu
   nome, o IP de quem hospedou e a mesma porta, e clica em **Conectar**.
   Essa pessoa joga com as peças douradas.

> **Firewall:** quem entra também sobe um servidor RPC, numa porta livre
> escolhida pelo sistema, para o host conseguir chamá-lo de volta. Se houver
> firewall, ele precisa permitir conexões de entrada do Python (e o host
> precisa liberar a porta escolhida).

### Testando sozinho, na mesma máquina
Abra dois terminais e rode `python3 main.py` em cada um. Em um deles
deixe na aba "Hospedar partida"; no outro, use a aba "Entrar em
partida" com IP `localhost` (valor padrão do campo) e a mesma porta.

---

## 3. Estrutura do código

```
main.py                        -> ponto de entrada
fanorona/
 ├── model/                    -> regras do jogo (não depende de GUI nem de rede)
 │    ├── color.py             -> Color: WHITE/BLACK
 │    ├── point.py             -> Point: um ponto (linha, coluna) do tabuleiro
 │    ├── direction.py         -> Direction: uma das 8 direções de movimento
 │    ├── board.py             -> Board: tabuleiro 5x9, posição inicial, topologia
 │    ├── capture_option.py    -> CaptureOption: uma opção de captura (tipo + peças capturadas)
 │    └── game_engine.py       -> GameEngine: turnos, movimentos, capturas, sequência, vitória
 ├── net/                      -> comunicação via RMI/RPC
 │    ├── game_connection.py   -> servidor RPC (métodos chamados pelo adversário) + proxy para o adversário
 │    └── network_setup.py     -> hospedar (subir servidor e esperar register) / entrar (chamar register no host)
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

- **model**: só sabe as regras do Fanorona. Não conhece Tkinter nem rede.
- **net**: só sabe chamar/receber métodos remotos (RPC). Não conhece as
  regras do jogo — apenas repassa coordenadas e tipos de captura.
- **gui**: a "cola" entre as duas coisas — interpreta cliques do mouse,
  chama o `GameEngine`, e manda o resultado pela rede.

Isso significa que, para entender a parte de **RMI/RPC**, só é preciso ler
os dois arquivos de `net/` (cerca de 400 linhas, bem comentadas).

---

## 4. Como o tabuleiro é representado

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

---

## 5. Regras de movimento e captura implementadas

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

---

## 6. Comunicação via RMI/RPC

Todo o código desta seção está em `fanorona/net/`.

### 6.1 Métodos remotos

São os métodos da classe `_GameService` (`game_connection.py`), expostos
pelo servidor RPC de cada tabuleiro. **É o adversário quem os chama; a
execução acontece na minha máquina.**

| Método | Quando é chamado | O que faz no lado que recebe |
|---|---|---|
| `register(porta, nome)` | Uma vez, quando alguém **entra** na partida | Guarda o nome, cria o proxy de volta (usando o IP de quem chamou + a porta informada) e devolve o nome do host. |
| `move(fr, fc, tr, tc, tipo)` | A cada jogada | Vira o evento `("move", ...)`. `tipo` é `NONE`, `APPROACH` ou `WITHDRAWAL` — já resolvido por quem jogou. |
| `end_turn()` | Jogador encerra a sequência de capturas | Vira o evento `("endturn",)`. |
| `resign()` | Jogador desiste | Vira o evento `("resign",)`. |
| `rematch()` | Jogador pede revanche | Vira o evento `("rematch",)`. |
| `chat(mensagem)` | Mensagem de chat | Vira o evento `("chat", mensagem)`. |
| `ping()` | A cada 3s sem nada a enviar | Só devolve `True`: serve para saber se o outro lado continua no ar. |
| `bye()` | Jogador sai da partida | Vira o evento `("disconnected", ...)`. |

Só métodos **públicos** são expostos pelo `xmlrpc`; tudo que começa com
`_` fica privado. Por isso `_GameService` é uma classe separada: ela
expõe só o que o adversário pode chamar, e esconde `send_move`, `close`
etc., que são de uso interno.

### 6.2 Como a conexão é estabelecida

```
        HOST (NetworkSetup.host)                    QUEM ENTRA (NetworkSetup.join)
 1. sobe o servidor RPC na porta 5000
 2. espera alguém chamar register()  ...
                                                    3. sobe o PRÓPRIO servidor RPC (porta livre, ex.: 41873)
                                                    4. cria o proxy  http://IP_DO_HOST:5000
                                                    5. chama  host.register(41873, "Beto")  ─────────┐
 6. register() roda no host:                                                                          │
      - guarda o nome "Beto"                        <─────────────────────────────────────────────────┘
      - cria o proxy de volta: http://IP_DE_QUEM_CHAMOU:41873
      - devolve o nome do host ("Ana")  ───────────> 7. recebe "Ana" como resposta da chamada
 8. wait_for_peer() acorda                           8. connect_to() retorna
 9. as duas telas de jogo abrem — os dois lados já conseguem chamar um ao outro
```

Detalhe interessante: o host descobre o **IP** de quem chamou olhando de
onde veio a requisição HTTP (`_ThreadedXMLRPCServer.finish_request`), então
quem entra só precisa informar a **porta** do próprio servidor.

### 6.3 Enviando uma chamada: fila + thread de escrita

Os métodos `send_move`, `send_chat`, `send_resign` etc. **não chamam o
adversário diretamente**. Eles só colocam a chamada numa fila:

```python
def send_move(self, frm, to, choice):
    self._enqueue(("move", frm.row, frm.col, to.row, to.col, choice_name))
```

Uma thread própria (`_write_loop`) tira da fila e faz a chamada remota:

```python
call = self._outgoing.get(timeout=PING_INTERVAL_S)
method, *args = call
getattr(self._peer, method)(*args)     # equivale a  self._peer.move(1, 2, 2, 3, "NONE")
```

`self._peer` é o `ServerProxy` do adversário. Esse `getattr` é só uma forma
de escolher o método pelo nome (`"move"`, `"chat"`...); o efeito é o mesmo de
escrever `self._peer.move(...)`.

Por que a fila? Porque uma chamada remota **bloqueia** até a resposta chegar.
Se ela rodasse direto no clique do mouse, a janela congelaria em rede lenta.
E, como existe **uma só** thread de escrita fazendo **uma chamada por vez**,
as jogadas chegam ao adversário **na ordem em que foram feitas**.

### 6.4 Recebendo uma chamada: evento na fila de entrada

Quando o adversário chama `move` no meu servidor, o método
`_GameService.move` roda numa thread do servidor e só faz:

```python
self._conn._emit(("move", Point(fr, fc), Point(tr, tc), CaptureType[choice]))
return True
```

`_emit` coloca a tupla na `queue.Queue` de entrada. **Nunca mexe na tela
direto**: o Tkinter só pode ser usado pela thread principal. Quem consome
a fila é o `MainApp` (ver seção 7). Se algum evento chegar antes da
partida começar (`start()` ainda não foi chamado), ele fica guardado e é
entregue no `start()`.

Eventos que a fila de entrada carrega:

```
("move", from_point, to_point, capture_type)     ("endturn",)
("resign",)      ("rematch",)      ("chat", mensagem)      ("disconnected", motivo)
```

### 6.5 Detectando que o adversário caiu

RPC **não mantém conexão aberta** (cada chamada é uma requisição HTTP
independente), então não há um "socket fechado" para avisar a queda. Por isso:

- se a fila de saída ficar parada por 3s, a thread de escrita chama `ping()`;
- se **qualquer** chamada falhar (timeout de 10s, conexão recusada...), vira o
  evento `("disconnected", ...)` e a interface volta para a tela inicial;
- ao sair da partida normalmente, `close()` chama `bye()` antes de encerrar,
  então o outro lado percebe na hora, sem esperar o `ping`.

Ao encerrar, o servidor RPC é desligado e a **porta é liberada**, para dar
para hospedar de novo.

---

## 7. O caminho de uma jogada, do clique à outra tela

Exemplo: o host (peças escuras) move a peça de (1,3) para (2,4).

```
 MÁQUINA DO HOST                                         MÁQUINA DO ADVERSÁRIO
 ───────────────                                         ─────────────────────
 1. clique no tabuleiro
    BoardCanvas converte pixel -> Point
 2. GameScreen._handle_point_clicked
    (é minha vez? a peça é minha?)
 3. GameEngine.try_move(frm, to, escolha)
    valida e aplica no tabuleiro LOCAL
 4. GameConnection.send_move(...)
    só enfileira ("move", 1, 3, 2, 4, "NONE")
 5. thread de escrita: peer.move(1,3,2,4,"NONE")  ───►  6. servidor RPC: _GameService.move(...)
    (chamada RPC, via HTTP/XML)                            coloca ("move", ...) na fila de entrada
                                                        7. MainApp._poll_events (a cada 50 ms,
                                                           na thread principal) tira da fila
                                                        8. GameScreen.apply_remote_move
                                                           roda o MESMO GameEngine.try_move
                                                        9. redesenha o tabuleiro
```

Os mesmos passos valem para `chat`, `resign`, `end_turn` e `rematch`. Só
muda o método remoto chamado e o que a tela do outro lado faz com o evento.

Arquivos envolvidos, na ordem: `board_canvas.py` → `game_screen.py` →
`game_engine.py` → `game_connection.py` (envio) ⇒ rede ⇒
`game_connection.py` (recepção) → `main_app.py` → `game_screen.py`.

---

## 8. Concorrência (threads)

Por que existem threads: tudo que espera a rede (esperar adversário,
chamar método remoto) **bloqueia**, e a interface gráfica não pode
bloquear. Cada tarefa lenta roda numa thread própria:

| Thread | Criada em | Faz |
|---|---|---|
| principal | `main.py` | Só ela mexe no Tkinter. `MainApp._poll_events` roda nela a cada 50 ms. |
| `fanorona-rpc-server` | `GameConnection.listen` | `serve_forever`: aceita as chamadas que o adversário faz em mim. |
| uma por chamada recebida | `ThreadingMixIn` | Executa o método remoto (ex.: `_GameService.move`) e coloca o evento na fila. |
| `fanorona-rpc-writer` | `GameConnection.start` | Tira chamadas da fila de saída e as executa no adversário (inclui o `ping`). |
| `fanorona-host-thread` / `fanorona-join-thread` | `NetworkSetup` | Esperar o adversário / chamar `register` sem travar a janela. |

As threads **nunca** conversam direto com a interface. A ponte é sempre uma
`queue.Queue` (segura entre threads):

```
 clique ──► send_move() ──► [fila de SAÍDA] ──► thread de escrita ──► RPC ──► adversário
 adversário ──► RPC ──► thread do servidor ──► [fila de ENTRADA] ──► thread principal ──► tela
```

Por isso **envio e recepção são paralelos**: enviar nunca fica esperando
receber, e vice-versa.

---

## 9. Mapa das funcionalidades pedidas

| Requisito do enunciado | Onde está |
|---|---|
| Comunicação somente por RMI/RPC | `net/game_connection.py`, `net/network_setup.py` |
| Controle de turno, com definição de quem inicia | `GameEngine.current_turn`; quem hospeda joga com as escuras e começa (`ConnectScreen`). |
| Movimentação das peças nos tabuleiros | `GameScreen` + `GameEngine.try_move`; replicada no outro lado via `move()` → `apply_remote_move`. |
| Desistência | Botão "Desistir" → `send_resign()` → método remoto `resign()` → `apply_remote_resign`. |
| Chat durante toda a partida | `ChatPanel` → `send_chat()` → método remoto `chat()` → `apply_remote_chat`. |
| Indicação de vencedor | `GameEngine` (`game_over`, `winner`) → `GameOverScreen`. |
| Tabuleiros em máquinas diferentes | Host informa porta; quem entra informa IP + porta (seção 6.2). |

---

## 10. Glossário

- **RPC / RMI**: chamar um método que executa em outra máquina como se fosse local.
- **Servidor RPC**: processo que registra um objeto e fica esperando chamadas (`SimpleXMLRPCServer`).
- **Proxy / stub**: objeto local que representa o servidor remoto (`ServerProxy`); chamar um método dele dispara a chamada de rede.
- **XML-RPC**: variante de RPC em que a chamada e a resposta viajam como XML sobre HTTP.
- **Serialização (marshalling)**: converter os argumentos em XML para enviar (e de volta ao receber). O XML-RPC só aceita tipos simples — por isso `move` recebe 4 inteiros e uma string.
- **`register`**: método de apresentação inicial; é como o host descobre como chamar quem entrou.
- **Fila (`queue.Queue`)**: estrutura segura entre threads, usada para passar chamadas a enviar e eventos recebidos.
- **Evento**: tupla colocada na fila de entrada (`("move", ...)`, `("chat", ...)`) para a interface tratar.
- **Determinístico**: mesma posição + mesma jogada = mesmo resultado. É o que permite enviar só coordenadas.

---

## 11. Limitações conhecidas

- Não há reconexão automática caso a conexão caia no meio da partida
  (o jogo apenas avisa que a conexão foi perdida).
- Não há suíte de testes automatizados; a validação foi feita jogando
  com duas instâncias do jogo.
- Não há opção de configurar quem começa jogando além da convenção
  "quem hospeda começa".
- Não há placar de partidas anteriores nem replay de jogadas.
- Qualquer máquina que alcance as portas consegue chamar os métodos
  remotos (não há autenticação) — adequado para um trabalho acadêmico em
  rede local.
