# Fanorona via RMI/RPC — roteiro de apresentação

Projeto de PPD (Programação Paralela e Distribuída, IFCE). Dois processos, um
por jogador (em máquinas diferentes da mesma rede), conversando **somente por
RPC** — `xmlrpc` da biblioteca padrão do Python: tabuleiros sincronizados,
controle de turno, desistência, revanche e chat em tempo real. Interface em
Tkinter.

O foco deste documento é o que o professor vai perguntar: **o caminho de uma
jogada, do clique de um jogador até o desenho na tela do outro**, com o nome de
cada função no meio do caminho.

---

## Sumário

1. [Resumo de 30 segundos](#1-resumo-de-30-segundos)
2. [RPC, RMI e o que este projeto usa](#2-rpc-rmi-e-o-que-este-projeto-usa)
3. [As camadas: quem fala com quem](#3-as-camadas-quem-fala-com-quem)
4. [Os métodos remotos](#4-os-métodos-remotos)
5. [Estabelecendo a conexão (`register`)](#5-estabelecendo-a-conexão-register)
6. [Fluxo completo de uma jogada](#6-fluxo-completo-de-uma-jogada)
7. [As threads de cada processo](#7-as-threads-de-cada-processo)
8. [O que vai de fato no fio (XML real)](#8-o-que-vai-de-fato-no-fio-xml-real)
9. [Por que os dois tabuleiros ficam iguais](#9-por-que-os-dois-tabuleiros-ficam-iguais)
10. [Ordem, perda e queda de conexão](#10-ordem-perda-e-queda-de-conexão)
11. [Os outros métodos: chat, desistência, fim de sequência, revanche](#11-os-outros-métodos-chat-desistência-fim-de-sequência-revanche)
12. [Perguntas prováveis, respostas prontas](#12-perguntas-prováveis-respostas-prontas)
13. [Roteiro de demonstração](#13-roteiro-de-demonstração)
14. [Cola rápida: funções por etapa](#14-cola-rápida-funções-por-etapa)
15. [Como executar](#15-como-executar)
16. [Regras do Fanorona implementadas](#16-regras-do-fanorona-implementadas)
17. [Limitações conhecidas](#17-limitações-conhecidas)

---

## 1. Resumo de 30 segundos

- Dois processos iguais (o mesmo `main.py`). Um escolhe **Hospedar** e abre uma
  porta; o outro escolhe **Entrar** e informa IP + porta do host.
- **Os dois são servidor e cliente ao mesmo tempo.** Cada processo sobe um
  servidor RPC (os métodos que o adversário pode chamar em mim) e guarda um
  *proxy* (o representante local do servidor do adversário).
- Quando eu jogo, **chamo `move(...)` no servidor do adversário**. Quando ele
  joga, ele chama `move(...)` no meu. Não existe servidor central.
- Os processos trocam **jogadas**, não tabuleiros. Os dois rodam o mesmo
  `GameEngine`, que é determinístico: mesma posição + mesma jogada = mesmo
  resultado.

A frase que amarra tudo:

> **Não há servidor do jogo. Há dois pares simétricos que se chamam
> mutuamente; a "verdade" é a regra do jogo, rodando igual dos dois lados.**

Números:

| | |
| --- | --- |
| processos | 2, simétricos (host e quem entra) |
| servidores RPC | 2 (um em cada processo) |
| métodos remotos | 8: `register`, `move`, `end_turn`, `resign`, `rematch`, `chat`, `ping`, `bye` |
| biblioteca | `xmlrpc.server.SimpleXMLRPCServer` + `xmlrpc.client.ServerProxy` (sem `pip install`) |
| transporte | XML sobre HTTP sobre TCP |
| threads de rede por processo | servidor + uma por chamada recebida + uma de escrita |
| tipos de evento na fila de entrada | 6: `move`, `endturn`, `resign`, `rematch`, `chat`, `disconnected` |

---

## 2. RPC, RMI e o que este projeto usa

- **RPC** (*Remote Procedure Call*): chamar uma função que roda em **outra
  máquina** como se fosse local. A biblioteca serializa os argumentos, manda
  pela rede, executa lá, devolve o resultado.
- **RMI** (*Remote Method Invocation*): a mesma ideia orientada a objetos (nome
  vindo do Java): chama-se um método de um **objeto remoto** por meio de um
  representante local, o *stub* (ou *proxy*).

Neste projeto, as duas peças do XML-RPC fazem esses papéis:

| Peça | Classe | Papel | No código |
| --- | --- | --- | --- |
| Servidor (*skeleton*) | `SimpleXMLRPCServer` + `register_instance` | recebe a chamada e executa o método no objeto registrado | [`_ThreadedXMLRPCServer`](fanorona/net/game_connection.py#L95) e [`_GameService`](fanorona/net/game_connection.py#L107) |
| Proxy (*stub*) | `ServerProxy` | representa o servidor **do outro lado**; chamar um método dele dispara a chamada de rede | [`GameConnection._make_proxy`](fanorona/net/game_connection.py#L206) |

Escrever `self._peer.move(1, 3, 2, 4, "NONE")` parece uma chamada local, mas faz:
monta o XML → HTTP POST → o adversário executa `_GameService.move` → devolve a
resposta.

**Se perguntarem "isso é RMI de verdade?"** Resposta honesta: é RPC (XML-RPC),
com o papel de stub/skeleton do RMI. Faltam duas coisas do RMI do Java: um
*registry* (aqui o "registro" é o IP + porta digitado pelo usuário) e passagem
de **referências a objetos** (aqui só trafegam tipos simples: inteiros e
strings). Por isso `move` recebe `fr, fc, tr, tc` e não um objeto `Point`.

---

## 3. As camadas: quem fala com quem

```
model  <----  gui  ---->  net
(regras)    (cola)      (RPC)
```

| pacote | papel | sabe do jogo? | sabe da rede? |
| --- | --- | --- | --- |
| `fanorona/model/` | regras: tabuleiro, jogadas, capturas, vitória (`GameEngine`) | sim | **não** |
| `fanorona/net/` | transporte RPC: servidor, proxy, fila de saída, detecção de queda | **não** (só repassa coordenadas) | sim |
| `fanorona/gui/` | cola: interpreta cliques, chama o engine, manda o resultado pela rede, aplica o que chegou | sim | só pela fila |

```
main.py
fanorona/
 ├── model/   color, point, direction, board, capture_option, game_engine
 ├── net/
 │    ├── game_connection.py  -> _GameService (servidor) + GameConnection (proxy, filas, threads)
 │    └── network_setup.py    -> NetworkSetup.host / .join / .cancel_hosting
 └── gui/     main_app, connect_screen, game_screen, board_canvas, chat_panel, ...
```

Duas fronteiras para dizer em voz alta:

1. **`net/` nunca aprende o jogo.** Ele carrega inteiros e strings. Quando algo
   de rede precisa aparecer na tela (queda), ele cria um *evento* na fila
   (`("disconnected", ...)`) e a GUI decide o que mostrar.
2. **A GUI nunca chama o adversário diretamente.** Ela chama `send_move`,
   `send_chat` etc. na `GameConnection`, que só enfileira. Para entender todo o
   RPC basta ler os dois arquivos de `net/` (~400 linhas, comentados).

---

## 4. Os métodos remotos

São os métodos públicos de [`_GameService`](fanorona/net/game_connection.py#L107).
**É o adversário quem chama; a execução acontece na minha máquina.**

| método | linha | quem chama / quando | o que faz no lado que recebe | evento gerado |
| --- | --- | --- | --- | --- |
| `register(porta, nome)` | [117](fanorona/net/game_connection.py#L117) | quem entra, **uma vez**, no `join` | guarda o nome, cria o proxy de volta, acorda o host, devolve o nome do host | — |
| `move(fr, fc, tr, tc, escolha)` | [122](fanorona/net/game_connection.py#L122) | a cada jogada | enfileira o evento e retorna `True` | `("move", Point, Point, CaptureType)` |
| `end_turn()` | [126](fanorona/net/game_connection.py#L126) | jogador encerra a sequência de capturas | idem | `("endturn",)` |
| `resign()` | [130](fanorona/net/game_connection.py#L130) | jogador desiste | idem | `("resign",)` |
| `rematch()` | [134](fanorona/net/game_connection.py#L134) | jogador pede revanche | idem | `("rematch",)` |
| `chat(mensagem)` | [138](fanorona/net/game_connection.py#L138) | mensagem de chat | idem | `("chat", texto)` |
| `ping()` | [142](fanorona/net/game_connection.py#L142) | a cada 3 s sem nada a enviar | só devolve `True` | — |
| `bye()` | [145](fanorona/net/game_connection.py#L145) | jogador sai da partida | marca que o adversário saiu | `("disconnected", ...)` |

`escolha` é `"NONE"`, `"APPROACH"` ou `"WITHDRAWAL"` (captura por aproximação
ou afastamento), **já resolvida por quem jogou** — o outro lado não tem como
perguntar ao jogador.

Por que `_GameService` é uma classe separada de `GameConnection`: o
`xmlrpc` expõe **todos os métodos públicos** do objeto registrado. Se
registrássemos a `GameConnection`, o adversário poderia chamar `send_move`,
`close`, `cancel`... Com `_GameService`, só existe na porta o que foi feito
para ser chamado. (Nomes começando com `_` nunca são expostos, e
`allow_dotted_names` fica desligado.)

Correspondência com um protocolo de texto, para quem já viu sockets:

| texto | RPC |
| --- | --- |
| `HELLO nome` | `register(porta, nome)` |
| `MOVE fr fc tr tc escolha` | `move(fr, fc, tr, tc, escolha)` |
| `ENDTURN` / `RESIGN` / `REMATCH` | `end_turn()` / `resign()` / `rematch()` |
| `CHAT texto` | `chat(texto)` |
| (não existia) | `ping()` e `bye()` |

Não há mais *parsing* de linha, delimitador nem tratamento de mensagem
cortada: o nome do método e os tipos dos argumentos **são** o protocolo.

---

## 5. Estabelecendo a conexão (`register`)

Problema: o RPC é pedido-resposta, e os dois lados precisam se chamar. Quem
entra conhece o IP e a porta do host (o usuário digitou), mas **o host não
conhece o endereço de quem entra**. A solução é o método `register`:

```
        HOST (NetworkSetup.host)                    QUEM ENTRA (NetworkSetup.join)
 1. listen(5000): sobe o servidor RPC
 2. wait_for_peer(): bloqueia ...
                                                    3. listen(0): sobe o PRÓPRIO servidor RPC
                                                       (porta livre escolhida pelo SO, ex.: 41873)
                                                    4. connect_to(): cria o proxy http://IP_DO_HOST:5000
                                                    5. proxy.register(41873, "Beto")  ──────────┐
 6. _on_register() roda no host:                                                                  │
      - cria o proxy de volta:                      <─────────────────────────────────────────────┘
        http://IP_DE_QUEM_CHAMOU:41873
      - guarda "Beto" e acorda wait_for_peer()
      - devolve o nome do host ("Ana") ──────────>  7. recebe "Ana" como retorno da chamada
 8. NetworkSetup.host chama on_connected          8. NetworkSetup.join chama on_connected
 9. as duas telas de jogo abrem; agora os dois lados já conseguem chamar um ao outro
```

Funções, em ordem:

- **Host:** `ConnectScreen._do_connect` ([connect_screen.py:84](fanorona/gui/connect_screen.py#L84))
  → `NetworkSetup.host` ([network_setup.py:35](fanorona/net/network_setup.py#L35))
  → `GameConnection.listen` ([game_connection.py:174](fanorona/net/game_connection.py#L174))
  → `wait_for_peer` ([:185](fanorona/net/game_connection.py#L185)).
- **Quem entra:** `NetworkSetup.join` ([network_setup.py:62](fanorona/net/network_setup.py#L62))
  → `listen(0)` → `connect_to` ([game_connection.py:191](fanorona/net/game_connection.py#L191))
  → `proxy.register(...)` (a chamada RPC).
- **No host, dentro do `register`:** `_GameService.register`
  → `GameConnection._on_register` ([game_connection.py:211](fanorona/net/game_connection.py#L211)).

**Como o host descobre o IP de quem chamou?** Pela própria requisição HTTP:
`_ThreadedXMLRPCServer.finish_request` ([:100](fanorona/net/game_connection.py#L100))
guarda `client_address[0]` numa `threading.local` (`_request_ctx`) — roda na
thread da requisição, então cada chamada vê o seu IP. Quem entra só informa a
**porta**.

**Terceiro jogador:** se um terceiro chamar `register`, `_on_register` levanta
`RuntimeError`; o `xmlrpc` transforma isso num `Fault` e o terceiro vê
*"Não foi possível conectar ... Esta partida já tem dois jogadores"*. (Testado:
a exceção atravessa a rede e chega ao chamador.) Isso só é possível porque o
servidor do host continua no ar durante toda a partida.

**Quem é quem:** o host joga com `Color.WHITE` (desenhada como peça **escura**) e
começa; quem entra joga com `Color.BLACK` (desenhada **dourada**) —
[connect_screen.py:100](fanorona/gui/connect_screen.py#L100) e
[:114](fanorona/gui/connect_screen.py#L114). O controle de turno é
`GameEngine.current_turn`; quem começa é decidido por convenção, sem troca de
mensagem.

### Roteiro de fala da seção 5 (2 a 3 minutos)

**Colinha: onde ir no código** (`Ctrl+G` + número).

| Passo | O que mostrar | Arquivo | Linha |
| --- | --- | --- | --- |
| 1 | host sobe o servidor e espera | `network_setup.py` | [41](fanorona/net/network_setup.py#L41), [43](fanorona/net/network_setup.py#L43) |
| 2 | quem entra sobe o próprio servidor (porta 0) | `network_setup.py` | [68](fanorona/net/network_setup.py#L68) |
| 3 | a chamada `register(minha_porta, meu_nome)` | `game_connection.py` | [196](fanorona/net/game_connection.py#L196) |
| 4 | o host lê o IP de quem chamou | `game_connection.py` | [103](fanorona/net/game_connection.py#L103) |
| 5 | o host cria o proxy de volta | `game_connection.py` | [215](fanorona/net/game_connection.py#L215) |
| 6 | acorda o host e devolve o nome | `game_connection.py` | [216-218](fanorona/net/game_connection.py#L216-L218) |

**Gancho (15 s)**

> "Eu mostrei que cada tabuleiro é servidor e cliente ao mesmo tempo. Isso cria
> um problema: **para eu ligar para você, preciso saber o seu número**. Quando a
> partida começa, o host não sabe quem é o adversário nem onde ele está. O
> `register` resolve isso."

**O problema (30 s)** *(mostrar o diagrama desta seção)*

> "Quem entra sabe o IP e a porta do host, porque o usuário digitou. O host não
> sabe nada de quem entra. Só que o RPC é pedido e resposta: o host só consegue
> falar com o adversário se **ele** também tiver um proxy. E para criar o proxy
> precisa de IP e porta."

**O pipeline (1 min 30 s)**

1. *(linhas 41 e 43)* "O host sobe o servidor na porta escolhida e bloqueia
   esperando alguém."
2. *(linha 68)* "Quem entra sobe o **próprio** servidor, numa porta livre que o
   sistema escolhe. É o 'ramal' onde o host vai poder me ligar de volta."
3. *(linha 196)* "Aí eu chamo `register` no host, passando a minha porta e o meu
   nome. É a única chamada em que a ordem importa, e é a primeira RPC da
   partida."
4. *(linha 103)* "Pense num telefone com identificador de chamadas: a porta eu
   informo no argumento, mas o IP o host já enxerga na própria requisição HTTP.
   Ele fica numa `threading.local`, porque cada chamada roda numa thread
   diferente e cada uma precisa ver o seu."
5. *(linha 215)* "Com IP e porta, o host cria o proxy de volta. **Nesse instante
   o host passa a ser cliente também.**"
6. *(linhas 216-218)* "Por fim, o `register` acorda o host e devolve o nome dele
   como resposta. Os dois abrem a tela de jogo, e dali em diante o caminho de
   envio e o de recepção são idênticos nos dois lados."

**Fechamento (15 s)**

> "O `register` é a chamada em que quem entra se apresenta como cliente e, de
> quebra, entrega ao host o endereço para ele virar cliente também. Depois
> disso não existe mais 'caminho do host' ou 'caminho de quem entrou'."

**Se perguntarem**

- *"E se um terceiro jogador tentar entrar?"* "O `_on_register` levanta um erro
  ([213-214](fanorona/net/game_connection.py#L213-L214)). O XML-RPC transforma
  isso num `Fault` e o terceiro vê 'esta partida já tem dois jogadores'. A
  exceção atravessa a rede."
- *"Funciona entre redes diferentes?"* "Na mesma rede, sim. Entre redes, o host
  precisa chamar de volta o IP de quem entrou, então um firewall ou NAT dele
  pode impedir. Com sockets isso não acontecia, porque só o host precisava de
  porta aberta."

---

## 6. Fluxo completo de uma jogada

Como os dois lados são simétricos, **um fluxo só** descreve os dois sentidos.
Exemplo: o host move a peça de (1,3) para (2,4), sem captura.

### Visão geral

```
JOGADOR QUE JOGA                                                 ADVERSÁRIO
────────────────                                                 ──────────
MainThread (Tk)
 1. clique → BoardCanvas → GameScreen._handle_point_clicked
 2. _attempt_move → GameEngine.try_move(frm, to, None)    valida e aplica no tabuleiro LOCAL
 3. _apply_local_result → connection.send_move(...)
        └─ _enqueue: só põe ("move",1,3,2,4,"NONE") na fila de SAÍDA   (retorna na hora)
 4. redesenha: quem jogou já vê o lance

thread de escrita (_write_loop)
 5. tira da fila de saída
 6. getattr(self._peer, "move")(1,3,2,4,"NONE")  ══ HTTP POST / XML ══>  thread do servidor
                                                                         7. _GameService.move
                                                                              └─ _emit(("move", Point, Point, CaptureType))
 8. recebe True e volta ao get()       <═══════════ True ══════════════     (cai na fila de ENTRADA)

                                                                         MainThread (Tk)
                                                                          9. _poll_events (a cada 50 ms) → get_nowait
                                                                         10. _handle_event → apply_remote_move
                                                                         11. GameEngine.try_move(frm, to, escolha)  ← o MESMO engine
                                                                         12. redesenha: o adversário vê o lance
```

### Passo a passo, com código

**1–2. O clique vira uma jogada validada.** `BoardCanvas` converte pixel em
`Point` e chama `GameScreen._handle_point_clicked`
([game_screen.py:121](fanorona/gui/game_screen.py#L121)), que filtra: jogo
acabou? é minha vez (`engine.current_turn is self.my_color`)? a peça é minha?
Escolhido o destino, `_attempt_move` ([:157](fanorona/gui/game_screen.py#L157))
chama `GameEngine.try_move` ([game_engine.py:96](fanorona/model/game_engine.py#L96)),
que valida e **já aplica** no tabuleiro local. Se houver captura ambígua
(aproximação *e* afastamento), o engine devolve `NEEDS_CHOICE` e a GUI abre um
diálogo (`dialogs.ask_capture_choice`) **antes de qualquer coisa ir para a rede**.

**3. Manda.** `_apply_local_result` ([:171](fanorona/gui/game_screen.py#L171))
só envia se o resultado for válido:

```python
if result.type == ResultType.SIMPLE_MOVE_TURN_ENDED:
    self.connection.send_move(frm, to, CaptureType.NONE)
```

`send_move` ([game_connection.py:286](fanorona/net/game_connection.py#L286))
**não usa a rede**; só achata os argumentos e enfileira:

```python
def send_move(self, frm, to, choice):
    choice_name = "NONE" if choice is None else choice.name
    self._enqueue(("move", frm.row, frm.col, to.row, to.col, choice_name))
```

**4.** Quem jogou já vê o lance no mesmo instante: o `GameEngine` local já foi
alterado no passo 2 e `board_canvas.redraw()` desenha o engine. Não espera
resposta da rede — não precisa, porque o outro lado vai aplicar a mesma regra
(seção 9).

**5–6. A thread de escrita faz a chamada RPC**
([`_write_loop`](fanorona/net/game_connection.py#L253)):

```python
call = self._outgoing.get(timeout=PING_INTERVAL_S)    # espera algo na fila (ou 3 s)
method, *args = call
getattr(self._peer, method)(*args)                    # ← RPC: self._peer.move(1,3,2,4,"NONE")
```

`self._peer` é o `ServerProxy`. O `getattr` só escolhe o método pelo nome
(`"move"`, `"chat"`...); o efeito é idêntico a escrever `self._peer.move(...)`.
É aqui que o `xmlrpc.client` serializa os argumentos em XML e faz o **HTTP POST**
para `http://<ip-do-adversário>:<porta>/`.

**7. O adversário recebe.** O `ThreadingMixIn` criou uma thread só para esta
chamada; ela executa `_GameService.move`
([:122](fanorona/net/game_connection.py#L122)):

```python
self._conn._emit(("move", Point(int(fr), int(fc)), Point(int(tr), int(tc)), CaptureType[choice]))
return True
```

Dois detalhes: (a) os inteiros e a string que vieram do XML são **reconvertidos**
em `Point` e `CaptureType` aqui; (b) o método **não mexe na tela** — só põe o
evento na `queue.Queue` ([`_emit`](fanorona/net/game_connection.py#L235)) e
devolve `True` na hora.

**8.** O `True` volta como resposta HTTP; a thread de escrita do remetente
desbloqueia e volta a esperar a fila. Como a chamada RPC é **síncrona**, o
`True` significa "o evento já está na fila do outro lado".

**9–10. A thread principal do adversário consome.** Tkinter só pode ser
usado pela thread principal, então ela mesma esvazia a fila:
[`MainApp._poll_events`](fanorona/gui/main_app.py#L92) roda a cada 50 ms
(`root.after`) com `get_nowait()`, e [`_handle_event`](fanorona/gui/main_app.py#L101)
despacha pelo nome do evento:

```python
if kind == "move" and self.active_game_screen is not None:
    _, frm, to, choice = event
    self.active_game_screen.apply_remote_move(frm, to, choice)
```

**11. Aplica a mesma regra.** [`apply_remote_move`](fanorona/gui/game_screen.py#L279):

```python
effective = None if choice == CaptureType.NONE else choice
result = self.engine.try_move(frm, to, effective)       # a MESMA função do passo 2
```

**12.** Registra no histórico, `redraw()`, `_refresh_status()` (de quem é a
vez) e `_check_game_over()`. O adversário vê o lance.

**Latência:** ida e volta da rede + até 50 ms (o intervalo do `_poll_events`).
Em LAN, imperceptível.

### A simetria que vale mostrar

| | o que faz | onde |
| --- | --- | --- |
| **Envio** | GUI → `send_*` → fila de saída → thread de escrita → `proxy.método(...)` | `GameConnection.send_*`, `_write_loop` |
| **Recepção** | servidor → `_GameService.método` → `_emit` → fila de entrada → thread principal | `_GameService`, `_emit`, `MainApp._poll_events` |

O código é o mesmo nos dois processos: não existe "caminho do host" e "caminho
do cliente". A única diferença entre os dois é quem chamou `register` no início.

### Roteiro de fala da seção 6: as três perguntas certas (3 a 4 minutos)

**Colinha: onde ir no código** (`Ctrl+G` + número).

| Pergunta | O que mostrar | Arquivo | Linha |
| --- | --- | --- | --- |
| 1. Tela do outro | valida e aplica local | `game_screen.py` | [157](fanorona/gui/game_screen.py#L157) |
| 1. Tela do outro | manda para a rede | `game_screen.py` | [177](fanorona/gui/game_screen.py#L177) |
| 1. Tela do outro | o outro lado reaplica a mesma regra | `game_screen.py` | [279](fanorona/gui/game_screen.py#L279) |
| 2. Como o RPC funciona | a chamada remota | `game_connection.py` | [266](fanorona/net/game_connection.py#L266) |
| 2. Como o RPC funciona | o método que executa do outro lado | `game_connection.py` | [122](fanorona/net/game_connection.py#L122) |
| 2. Como o RPC funciona | o XML real | README | [seção 8](#8-o-que-vai-de-fato-no-fio-xml-real) |
| 3. Interface sem travar | `send_move` só enfileira | `game_connection.py` | [286](fanorona/net/game_connection.py#L286) |
| 3. Interface sem travar | thread que chama o proxy | `game_connection.py` | [253](fanorona/net/game_connection.py#L253) |
| 3. Interface sem travar | evento entra na fila de entrada | `game_connection.py` | [235](fanorona/net/game_connection.py#L235) |
| 3. Interface sem travar | a janela lê a fila a cada 50 ms | `main_app.py` | [92](fanorona/gui/main_app.py#L92) |

**1. "Como a tela do outro usuário é atualizada?"**

A ideia central: não mando o tabuleiro, mando só a jogada.

> "Quando eu clico, a interface chama o `GameEngine`, que valida e aplica a
> jogada no meu tabuleiro. Eu já vejo o lance na hora, sem esperar a rede. Depois
> envio ao adversário só **cinco números e uma string**: de onde, para onde e o
> tipo de captura. Do outro lado, o servidor recebe isso, coloca numa fila e a
> tela dele chama **o mesmo `try_move`**. Como as regras são determinísticas,
> mesma posição mais mesma jogada dá o mesmo resultado, e os dois tabuleiros
> ficam iguais."

**2. "Como o RPC funciona?"**

> "RPC é chamar um método que roda em outra máquina como se fosse local. Eu
> escrevo `self._peer.move(1, 3, 2, 4, "NONE")`. Esse `_peer` é um **proxy**: ele
> não tem `move`, mas pega o nome e os argumentos, monta um XML, manda por HTTP e
> espera a resposta. Do outro lado, um servidor XML-RPC recebe, acha o método
> `move` na classe `_GameService` e executa. O retorno volta pelo mesmo
> caminho."

**3. "Como a interface se liga ao RPC sem travar?"**

> "A regra é: **a interface nunca toca a rede**. Para enviar, ela só coloca a
> chamada numa fila e segue em frente. Uma thread separada tira da fila e faz a
> chamada RPC, uma por vez, o que garante a ordem. Para receber, o servidor
> também só coloca um evento numa fila. A janela principal esvazia essa fila a
> cada 50 ms. Isso é porque o Tkinter só pode ser mexido pela thread principal."

**Se ele insistir**

- *"E se a jogada chegar fora de ordem?"* "Não chega. Uma thread só faz as
  chamadas, uma de cada vez, então a ordem da fila é a ordem de chegada."
- *"E se os tabuleiros divergirem?"* "O mesmo `GameEngine` roda nos dois lados,
  sem sorteio nem dependência de relógio. Por isso só a jogada trafega."
- *"Quanto demora até o outro ver?"* "A ida e volta da rede mais até 50 ms do
  `_poll_events`. Numa rede local não se percebe."
- *"Por que o `True` de retorno?"* "Significa que o evento já está na fila do
  outro lado. Se a chamada falhar, a thread de escrita detecta e gera o evento
  de desconexão."

**Fechamento**

> "O jogador que joga valida e vê na hora, a rede só carrega a decisão, e o outro
> lado reaplica a mesma regra. A interface nunca fala com a rede, só com filas."

---

## 7. As threads de cada processo

```
                  ┌── fanorona-rpc-server (serve_forever)
                  │      └── uma thread curta por chamada recebida (ThreadingMixIn)
 processo ────────┤              _GameService.move / chat / ... ──► [fila de ENTRADA]
                  │
                  ├── fanorona-rpc-writer ◄── [fila de SAÍDA] ◄── send_move / send_chat / ...
                  │      └── chama os métodos do proxy (inclui o ping)
                  │
                  ├── fanorona-host-thread / fanorona-join-thread   (só durante a conexão)
                  │
                  └── MainThread (Tk) ── _poll_events a cada 50 ms ──► [fila de ENTRADA]
```

| thread | criada em | faz |
| --- | --- | --- |
| principal | `main.py` | **só ela mexe no Tkinter**; esvazia a fila de entrada |
| `fanorona-rpc-server` | [`listen`](fanorona/net/game_connection.py#L174) | `serve_forever`: aceita as chamadas do adversário |
| uma por chamada recebida | `ThreadingMixIn` | executa o método remoto e enfileira o evento |
| `fanorona-rpc-writer` | [`start`](fanorona/net/game_connection.py#L224) | tira da fila de saída e chama o proxy |
| `fanorona-host-thread` | [`NetworkSetup.host`](fanorona/net/network_setup.py#L35) | `wait_for_peer()` sem travar a janela |
| `fanorona-join-thread` | [`NetworkSetup.join`](fanorona/net/network_setup.py#L62) | `connect_to()` sem travar a janela |

**Regra de ouro: o loop da interface nunca toca a rede.**

- Para mandar, a GUI chama `send_*`, que só faz `queue.put`. Retorna na hora.
- Para receber, a GUI esvazia uma `queue.Queue` com `get_nowait()`.

**Por que a fila de saída + uma thread de escrita?** Uma chamada RPC **bloqueia**
até a resposta chegar (até 10 s no pior caso). Se rodasse no clique do mouse, a
janela congelaria com rede lenta. E, como há **uma só** thread fazendo **uma
chamada por vez**, as mensagens chegam **na ordem em que foram feitas**.

**Por que o servidor precisa de uma thread por chamada?** (`ThreadingMixIn`,
[:95](fanorona/net/game_connection.py#L95)) Num servidor de uma thread só, uma
chamada demorada bloquearia todas as seguintes (inclusive o `register` de quem
está tentando entrar). Com uma thread por chamada, cada requisição é atendida
sem esperar as outras.

**Por que a ponte é uma `queue.Queue`?** Porque ela é thread-safe: threads de
rede escrevem, a thread da GUI lê, sem lock manual no estado do jogo. **O
`GameEngine` só é tocado pela thread principal** — por isso ele não tem lock.

Os locks que existem em `net/`:

| lock | protege |
| --- | --- |
| `_events_lock` | `_event_queue` e `_pending` (ver a seguir) |
| `_server_lock` | o desligamento do servidor (não rodar duas vezes) |

**Eventos que chegam antes do `start()`:** o servidor já está no ar durante o
`register`, mas a fila da GUI só é entregue em `start()`
([:224](fanorona/net/game_connection.py#L224)). Se o adversário jogar nesse
intervalo, `_emit` guarda o evento em `_pending` e `start()` o despeja na fila
na ordem. (Testado: 2 eventos chegaram antes do `start`, e saíram em ordem
depois.)

---

## 8. O que vai de fato no fio (XML real)

Gerado com `xmlrpc.client.dumps`, os mesmos bytes que o `ServerProxy` envia.

**Chamada** `move(1, 3, 2, 4, "APPROACH")` — corpo do HTTP POST:

```xml
<?xml version='1.0'?>
<methodCall>
<methodName>move</methodName>
<params>
<param><value><int>1</int></value></param>
<param><value><int>3</int></value></param>
<param><value><int>2</int></value></param>
<param><value><int>4</int></value></param>
<param><value><string>APPROACH</string></value></param>
</params>
</methodCall>
```

**Resposta** (`return True`):

```xml
<?xml version='1.0'?>
<methodResponse>
<params>
<param><value><boolean>1</boolean></value></param>
</params>
</methodResponse>
```

**A apresentação inicial**, `register(41873, "Beto")`:

```xml
<methodCall>
<methodName>register</methodName>
<params>
<param><value><int>41873</int></value></param>
<param><value><string>Beto</string></value></param>
</params>
</methodCall>
```

Pontos para comentar:

- O XML-RPC só tem tipos simples (`int`, `string`, `boolean`, `double`, `array`,
  `struct`...). Por isso **`Point` não atravessa a rede**: viaja como 2 inteiros
  e é reconstruído do outro lado. Idem `CaptureType`, que vai como `string`
  (`"APPROACH"`) e volta com `CaptureType["APPROACH"]`.
- O nome do método (`<methodName>move</methodName>`) é o que o servidor usa
  para escolher a função. Um nome que não exista, ou que comece com `_`, é
  recusado.
- É verboso (a chamada `move` acima tem 336 bytes; a resposta, 129) e legível.
  Numa LAN isso é irrelevante, e dá para mostrar no Wireshark.

---

## 9. Por que os dois tabuleiros ficam iguais

**Não há servidor autoritativo.** Ninguém manda o tabuleiro inteiro. Os dois
lados:

1. começam do mesmo estado (`GameEngine()` em `MainApp._launch_new_game`,
   [main_app.py:56](fanorona/gui/main_app.py#L56));
2. recebem as mesmas jogadas, **na mesma ordem** (uma thread de escrita, uma
   chamada por vez);
3. aplicam a mesma função determinística (`GameEngine.try_move`).

Logo chegam ao mesmo tabuleiro. É replicação por **máquina de estados**: mesmo
estado inicial + mesma sequência de operações = mesmo estado final.

**Consequências de projeto:**

- **A escolha de captura vai resolvida** (`"APPROACH"`/`"WITHDRAWAL"`). Se fosse
  `None`, o engine do adversário devolveria `NEEDS_CHOICE` e não aplicaria nada.
- **`end_turn()` é uma chamada separada.** Numa sequência de capturas, o jogador
  pode parar quando quiser ("Terminar jogada"). O adversário **não tem como
  deduzir** que o jogador decidiu parar (ele poderia só estar pensando), então
  parar é uma mensagem: `_on_end_turn_button`
  ([game_screen.py:196](fanorona/gui/game_screen.py#L196)) chama
  `end_chain_voluntarily()` local + `send_end_turn()`; o outro lado executa
  `apply_remote_end_turn` ([:288](fanorona/gui/game_screen.py#L288)). Sem isso,
  um acharia que é a vez de A e o outro, de B — para sempre.
- **Uma divergência nunca se corrige sozinha.** Por isso tudo que muda o estado
  é uma chamada explícita, e nada é "deduzido".

**E o jogador que joga fora da vez?** Três camadas:

1. entrada: `_handle_point_clicked` retorna se `current_turn is not my_color`;
2. engine local: `try_move` recusa (`INVALID`) peça que não seja do turno;
3. engine remoto: o `try_move` do adversário **revalida tudo** ao receber
   (turno, limites, ligação entre casas, casa vazia, sequência...), então uma
   jogada ilegal que chegue pela rede **não altera o tabuleiro**. Limite
   conhecido: `apply_remote_move` ignora o `Result`, então a tela ainda registra
   a entrada no histórico (seção 17).

---

## 10. Ordem, perda e queda de conexão

XML-RPC roda sobre HTTP sobre TCP, e cada chamada é uma requisição HTTP
independente (**não há conexão aberta permanente** entre as chamadas). Isso
muda o que "queda" significa:

| tema | como o projeto lida |
| --- | --- |
| **ordem** | uma única thread de escrita faz **uma chamada por vez** e só pega a próxima depois que a anterior retornou. Testado: 300 jogadas seguidas chegaram na mesma ordem. |
| **duplicata** | não pode ocorrer: **não há reenvio automático**. Cada mensagem é tentada uma vez. |
| **perda** | se uma chamada falha (rede caiu, timeout), o jogo considera a conexão perdida e encerra a partida; não tenta de novo. |
| **mensagem cortada / delimitador** | inexistente: a biblioteca entrega a chamada inteira ou lança exceção. |

### Detecção de queda

Sem uma conexão aberta, ninguém "percebe" a queda sozinho. Por isso:

- **`ping()`**: se a fila de saída ficar parada por `PING_INTERVAL_S` = 3 s, a
  thread de escrita chama `ping()` no adversário (`queue.Empty` em
  [:257](fanorona/net/game_connection.py#L257)). Os **dois** lados fazem isso.
- **Falha de qualquer chamada** (`RPC_ERRORS`: `OSError`, `xmlrpc.client.Error`,
  `HTTPException`) → [`_report_disconnected`](fanorona/net/game_connection.py#L248)
  → evento `("disconnected", ...)` → `MainApp._handle_event` fecha a conexão,
  mostra "Conexão perdida" e volta para a tela inicial.
- **Timeout:** `CALL_TIMEOUT_S` = 10 s. O `ServerProxy` padrão espera para sempre;
  [`_TimeoutTransport`](fanorona/net/game_connection.py#L82) corrige isso.
  - Servidor do adversário **desligado** (processo fechado): a conexão é
    recusada na hora, a queda é percebida imediatamente (testado).
  - Rede **cortada de verdade** (cabo, Wi-Fi): vale o timeout, até 10 s.
- **`bye()`**: ao sair normalmente, `close()` ([:306](fanorona/net/game_connection.py#L306))
  enfileira a sentinela `_STOP`; a thread de escrita chama `bye()` no adversário
  e encerra. O outro lado percebe na hora, sem esperar o ping (testado:
  `("disconnected", ...)` chega imediatamente).
- **Ao encerrar**, `_shutdown_server` ([:312](fanorona/net/game_connection.py#L312))
  para o `serve_forever` e fecha o socket: a **porta é liberada** e dá para
  hospedar de novo.

Por que não há reconexão: manter o projeto simples. Uma reconexão decente
exigiria numerar as mensagens e reenviar as perdidas, para não aplicar a mesma
jogada duas vezes — complexidade que o enunciado não pede.

---

## 11. Os outros métodos: chat, desistência, fim de sequência, revanche

Mesmo caminho da jogada (GUI → `send_*` → fila → thread de escrita → RPC →
`_GameService` → `_emit` → `_poll_events` → `apply_remote_*`). Só muda o método:

| ação | GUI (quem faz) | RPC | GUI (quem recebe) |
| --- | --- | --- | --- |
| chat | `ChatPanel._send` ([chat_panel.py:56](fanorona/gui/chat_panel.py#L56)) → `GameScreen._send_chat` ([:271](fanorona/gui/game_screen.py#L271)) | `chat(mensagem)` | `apply_remote_chat` ([:294](fanorona/gui/game_screen.py#L294)) |
| desistência | `_on_resign_button` ([:206](fanorona/gui/game_screen.py#L206)) → `_do_resign` ([:212](fanorona/gui/game_screen.py#L212)) | `resign()` | `apply_remote_resign` ([:297](fanorona/gui/game_screen.py#L297)) |
| terminar jogada | `_on_end_turn_button` ([:196](fanorona/gui/game_screen.py#L196)) | `end_turn()` | `apply_remote_end_turn` ([:288](fanorona/gui/game_screen.py#L288)) |
| revanche | `MainApp._rematch` ([main_app.py:70](fanorona/gui/main_app.py#L70)) | `rematch()` | `_handle_event` → `_launch_new_game` |
| sair | `MainApp._exit_to_connect` ([:74](fanorona/gui/main_app.py#L74)) → `close()` | `bye()` | `_handle_event` ("disconnected") |

O **chat não tem canal próprio**: usa a mesma fila de saída, a mesma thread de
escrita e a mesma fila de entrada. Consequência boa: **chat e jogadas ficam na
mesma ordem** dos dois lados — quem escreve "vou te comer" e depois captura faz
o outro ler a mensagem antes de ver a captura.

**Fim de jogo e vencedor:** não há mensagem de "fim". Cada lado calcula pelo
próprio engine (`game_over`, `winner`, `game_over_reason`) e `_check_game_over`
abre a `GameOverScreen`. Na desistência, quem desiste executa
`engine.resign(my_color)` local e quem recebe executa
`engine.resign(my_color.opposite())` — ambos chegam ao mesmo vencedor.

---

## 12. Perguntas prováveis, respostas prontas

**"Onde está o RPC aqui?"**
Em `fanorona/net/game_connection.py`. Cada processo registra um objeto
(`_GameService`) num `SimpleXMLRPCServer`; o adversário o chama por um
`ServerProxy`, como se fosse local: `self._peer.move(1, 3, 2, 4, "NONE")`. A
biblioteca serializa em XML, manda por HTTP e, do outro lado, chama o método.

**"Isso é RMI?"**
É RPC (XML-RPC) com o papel de stub/skeleton do RMI. Não há *registry* (o
endereço é digitado) nem passagem de referências a objetos (só tipos simples).
Seção 2.

**"Por que os dois são servidor e cliente? Não bastava um servidor?"**
Num RPC, só o cliente inicia chamadas. Mas num jogo os **dois** precisam
avisar o outro quando jogam. Sem servidor central, cada um precisa ser
servidor (receber) e cliente (chamar). O `register` resolve o problema de o
host não conhecer o endereço de quem entra (seção 5).

**"Como o host descobre o IP de quem entrou?"**
Pela origem da requisição HTTP (`client_address[0]`), capturada em
`finish_request`. Quem entra informa só a porta do próprio servidor, que foi
escolhida pelo sistema (`listen(0)`).

**"Por que a chamada não é feita direto no clique do mouse?"**
Chamada RPC é bloqueante. Em rede lenta, a janela travaria. Por isso há uma fila
de saída e uma thread de escrita; o clique só enfileira.

**"Por que uma thread só para escrever?"**
Garante **ordem** (uma chamada por vez, só avança quando a anterior
retorna) sem precisar numerar mensagens.

**"Por que o servidor não atualiza a tela diretamente?"**
Tkinter não é thread-safe: só a thread principal pode mexer na interface. O
método remoto roda numa thread do servidor, então só enfileira um evento;
`MainApp._poll_events` aplica na thread certa.

**"Tem condição de corrida?"**
O estado do jogo (`GameEngine`) só é escrito pela thread principal, então não
precisa de lock. A ponte entre threads é `queue.Queue`, que é thread-safe. Os
dois locks que existem protegem a entrega inicial dos eventos (`_events_lock`)
e o desligamento do servidor (`_server_lock`).

**"E se a jogada chegar antes de a tela de jogo existir?"**
`_emit` guarda em `_pending` e `start()` entrega em ordem (seção 7).

**"E se a mensagem for perdida ou chegar duas vezes?"**
Não há reenvio, então não há duplicata. Se uma chamada falha, a conexão é
declarada perdida e a partida encerra. Seção 10.

**"Como sabe que o outro caiu, se não há conexão aberta?"**
`ping()` a cada 3 s de silêncio + qualquer chamada que falhe + `bye()` na saída
normal. Seção 10.

**"Por que enviar só `move(fr, fc, tr, tc, escolha)` e não o tabuleiro?"**
Os dois lados rodam o mesmo `GameEngine` determinístico. Enviar a decisão
basta, e é muito menor. Seção 9.

**"Por que `end_turn` é uma chamada separada?"**
Parar uma sequência de capturas é uma **escolha**, e o adversário não tem como
deduzi-la. Seção 9.

**"E se alguém chamar `move` fora da vez?"**
O `try_move` do receptor revalida e recusa; o tabuleiro não muda. Seção 9.

**"É seguro?"**
Não para internet: o servidor escuta em todas as interfaces e não há
autenticação, então qualquer máquina que alcance a porta pode chamar os
métodos. Para rede de laboratório é aceitável. O que há: só os 8 métodos de
`_GameService` são expostos (nada de `allow_dotted_names`).

**"Por que XML-RPC e não gRPC/Pyro/sockets?"**
Está na biblioteca padrão (sem dependência), a chamada remota parece local, e o
formato é legível (dá para ver no Wireshark). Para dois jogadores trocando
poucas mensagens por minuto, a eficiência de serialização não importa.

**"Quanto tempo leva uma jogada para aparecer no outro lado?"**
Ida e volta da rede + até 50 ms (intervalo do `_poll_events`).

---

## 13. Roteiro de demonstração

1. **Duas máquinas.** Na primeira: aba *Hospedar partida*, nome, porta `5000`,
   **Conectar** (fica "Aguardando outro jogador…"). Na segunda: aba *Entrar em
   partida*, nome, IP da primeira, porta `5000`, **Conectar**. Comentar: "aqui
   aconteceu o `register`".
2. **Uma jogada de cada lado.** Comentar: "do clique até aqui passou por
   `send_move` → fila de saída → RPC `move` → `_emit` → `_poll_events` →
   `apply_remote_move`".
3. **Captura ambígua:** mostrar o diálogo (aproximação ou afastamento) — a
   escolha **vai resolvida** na chamada.
4. **Sequência de capturas + "Terminar jogada":** explicar o `end_turn()`.
5. **Chat** nos dois sentidos, intercalado com uma jogada.
6. **Desistência:** o outro lado recebe `resign()` e a tela de fim de jogo
   aparece nos dois. Mostrar **Revanche** (`rematch()`).
7. **Queda:** fechar uma das janelas no meio da partida → o outro recebe
   `bye()` e aparece "Conexão perdida". Depois hospedar de novo na **mesma
   porta**, para mostrar que ela foi liberada.
8. **Opcional:** Wireshark com filtro `tcp.port == 5000` para mostrar o XML
   (seção 8). Isso mostra só as chamadas **de quem entra para o host**; as do
   host para quem entra vão para a porta aleatória do outro servidor (a mesma
   que foi enviada no `register`).

Plano B (uma máquina só): dois terminais, `python3 main.py` em cada um; um em
*Hospedar*, o outro em *Entrar* com IP `localhost`.

---

## 14. Cola rápida: funções por etapa

Uma jogada, em ordem, com o arquivo de cada função:

| # | etapa | quem joga | quem recebe |
| --- | --- | --- | --- |
| 1 | clique | `BoardCanvas` → `GameScreen._handle_point_clicked` | |
| 2 | valida e aplica local | `GameScreen._attempt_move` → `GameEngine.try_move` | |
| 3 | manda | `GameScreen._apply_local_result` → `GameConnection.send_move` → `_enqueue` | |
| 4 | desenha | `board_canvas.redraw` | |
| 5 | chamada RPC | `_write_loop` → `self._peer.move(...)` (stub) | |
| 6 | recebe e enfileira | | `_GameService.move` → `_emit` → `queue.Queue` |
| 7 | responde | `True` volta e a escrita segue | |
| 8 | consome | | `MainApp._poll_events` → `_handle_event` |
| 9 | aplica | | `GameScreen.apply_remote_move` → `GameEngine.try_move` (a **mesma**) |
| 10 | desenha | | `board_canvas.redraw` |

Constantes ([game_connection.py:67](fanorona/net/game_connection.py#L67), [main_app.py:19](fanorona/gui/main_app.py#L19)):

| constante | valor | para quê |
| --- | --- | --- |
| `PING_INTERVAL_S` | 3 s | fila de saída parada por esse tempo → chama `ping()` |
| `CALL_TIMEOUT_S` | 10 s | tempo máximo esperando a resposta de uma chamada |
| `POLL_INTERVAL_MS` | 50 ms | a cada quanto a GUI esvazia a fila de entrada |
| porta do host | a do campo "Porta" (padrão 5000) | porta do servidor do host |
| porta de quem entra | 0 → o SO escolhe | porta do servidor de quem entra |

---

## 15. Como executar

**Pré-requisitos:** Python 3.10+ e Tkinter (biblioteca gráfica padrão; em
algumas distros Linux vem separada: `sudo apt-get install -y python3-tk`).
Nenhum `pip install`: o projeto usa só a biblioteca padrão (`tkinter`,
`xmlrpc`, `threading`, `queue`).

```
python3 -c "import tkinter; print('tkinter OK')"   # conferir
python3 main.py                                    # na raiz do projeto
```

**Partida em duas máquinas:**

1. Quem hospeda: aba **Hospedar partida**, nome e porta (ex.: 5000) →
   **Conectar**. Joga com as peças **escuras** e começa.
2. Quem entra: aba **Entrar em partida**, nome, **IP do host** e a mesma porta →
   **Conectar**. Joga com as peças **douradas**.

> **Firewall:** quem entra também sobe um servidor RPC, numa porta livre
> escolhida pelo sistema, para o host conseguir chamá-lo de volta. Com firewall
> ativo, é preciso permitir conexões de entrada ao Python nas duas máquinas
> (e liberar a porta escolhida no host).

**Na mesma máquina:** dois terminais com `python3 main.py`; um em *Hospedar*, o
outro em *Entrar* com IP `localhost` (padrão do campo) e a mesma porta.

---

## 16. Regras do Fanorona implementadas

Tudo em [`game_engine.py`](fanorona/model/game_engine.py):

- **Tabuleiro 5×9** (45 intersecções, 22 peças por jogador, casa central
  vazia). Casas vizinhas na horizontal e vertical sempre se ligam; as
  diagonais existem em metade das casas, alternadas (`Board.is_connected`).
- **Movimento simples:** uma peça para casa vazia vizinha ligada por linha;
  só vale se não houver captura e encerra o turno.
- **Captura por aproximação:** peças adversárias em sequência, na direção do
  movimento, logo à frente do destino.
- **Captura por afastamento:** peças adversárias coladas à origem, na direção
  **oposta** ao movimento.
- **Ambiguidade:** se os dois tipos são possíveis, o jogador escolhe
  (`NEEDS_CHOICE` → diálogo).
- **Sequência:** depois de capturar, a mesma peça pode continuar capturando,
  desde que o novo passo capture, não repita casa visitada no turno e não repita
  a direção do passo anterior. O jogador pode parar com "Terminar jogada".
- **Fim de jogo:** o adversário perde todas as peças, não tem jogada legal, ou
  desiste. Depois do fim, dá para pedir **revanche** pela mesma conexão.

---

## 17. Limitações conhecidas

- **Sem reconexão:** se a conexão cair no meio da partida, ela encerra
  (o jogo avisa e volta à tela inicial). Seção 10.
- **Sem autenticação:** qualquer máquina que alcance a porta pode chamar os
  métodos remotos. Adequado para trabalho acadêmico em rede local.
- **Jogada ilegal recebida:** o engine do receptor a rejeita (o tabuleiro não
  muda), mas `apply_remote_move` ignora o resultado e registra a entrada no
  histórico mesmo assim.
- **`register` não é atômico:** `_on_register` verifica `self._peer is not None`
  sem lock. Dois jogadores chamando `register` no mesmo instante poderiam passar
  pela verificação; improvável num jogo com dois colegas.
- **Detecção de queda em rede cortada** pode levar até o timeout (10 s).
- **Quem começa é fixo:** quem hospeda joga primeiro.
- Sem testes automatizados; a validação foi jogando com duas instâncias (e uma
  verificação de rede em `localhost` com host e cliente no mesmo processo).
- Sem placar de partidas anteriores nem replay.
