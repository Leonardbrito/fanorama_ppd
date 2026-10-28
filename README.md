# Fanorona via RMI/RPC — roteiro de apresentação

Projeto de PPD (Programação Paralela e Distribuída, IFCE). Dois processos, um
por jogador (em máquinas diferentes da mesma rede), conversando **somente por
RPC** (`xmlrpc` da biblioteca padrão do Python): tabuleiros sincronizados,
controle de turno, desistência, revanche e chat em tempo real. Interface em
Tkinter.

> **Não há servidor do jogo. Há dois pares simétricos que se chamam
> mutuamente; a "verdade" é a regra do jogo, rodando igual dos dois lados.**

**Como usar este documento:** README no segundo monitor, código no notebook.
No código, `Ctrl+G` + número da linha. As tabelas "Colinha" de cada seção
dizem para onde ir.

---

## Roteiro da apresentação (cerca de 9 minutos)

A apresentação principal é o pipeline das seções **3, 4 e 5**. O resto do
documento fica de reserva para as perguntas.

| # | Bloco | Tempo | Frase-chave | Mostrar no código | Seção |
| --- | --- | --- | --- | --- | --- |
| 0 | Abertura | 30 s | "Não há servidor do jogo. E RPC é chamar um método de outra máquina como se fosse local." | nada, só a frase-tese acima | [1](#1-resumo-de-30-segundos), [2](#2-rpc-rmi-stub-e-skeleton) |
| 1 | Cliente e servidor | 2 min | "Cada máquina tem um servidor para receber e um proxy para chamar." | [`listen` 174](fanorona/net/game_connection.py#L174), [`_make_proxy` 206](fanorona/net/game_connection.py#L206), [chamada 266](fanorona/net/game_connection.py#L266) | [3](#3-por-que-os-dois-são-cliente-e-servidor) |
| 2 | Conexão (`register`) | 3 min | "Para o host me ligar de volta, eu informo a minha porta." | [network_setup 41](fanorona/net/network_setup.py#L41), [68](fanorona/net/network_setup.py#L68); [game_connection 196](fanorona/net/game_connection.py#L196), [103](fanorona/net/game_connection.py#L103), [215](fanorona/net/game_connection.py#L215) | [4](#4-conexão-e-o-register) |
| 3 | Uma jogada | 3 a 4 min | "Valido e vejo na hora; a rede só carrega a decisão." | [game_screen 157](fanorona/gui/game_screen.py#L157), [177](fanorona/gui/game_screen.py#L177), [279](fanorona/gui/game_screen.py#L279); [game_connection 266](fanorona/net/game_connection.py#L266), [122](fanorona/net/game_connection.py#L122) | [5](#5-uma-jogada-do-clique-à-tela-do-outro) |

Feche com a última frase da fala curta da seção 5: *"O jogador que joga valida e vê na hora, a
rede só carrega a decisão, e o outro lado reaplica a mesma regra. A interface
nunca fala com a rede, só com filas."*

### Se perguntarem

| Se o professor perguntar... | Vá para |
| --- | --- |
| O que é RPC, RMI, stub, skeleton? Isso é RMI de verdade? | seção [2](#2-rpc-rmi-stub-e-skeleton) |
| Por que fila e thread? Por que a interface não chama a rede? | seção [6](#6-threads-e-filas) (a resposta curta já está na pergunta 3 da seção 5) |
| O que vai de fato pela rede? | seção [7](#7-o-que-vai-no-fio) (XML real) |
| Por que os tabuleiros ficam iguais? E jogada fora da vez? Por que `end_turn`? | seção [8](#8-por-que-os-tabuleiros-ficam-iguais) |
| E se a conexão cair? Mensagem perdida ou duplicada? | seção [9](#9-queda-de-conexão) |
| Qualquer outra pergunta | seção [10](#10-perguntas-prováveis) |
| Demonstração ao vivo | seção [11](#11-roteiro-de-demonstração) |
| Métodos remotos, constantes, chat, como executar, limitações | seção [12](#12-referência) |

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

| | |
| --- | --- |
| processos | 2, simétricos (host e quem entra) |
| servidores RPC | 2 (um em cada processo) |
| métodos remotos | 8: `register`, `move`, `end_turn`, `resign`, `rematch`, `chat`, `ping`, `bye` |
| biblioteca | `xmlrpc.server.SimpleXMLRPCServer` + `xmlrpc.client.ServerProxy` (sem `pip install`) |
| transporte | XML sobre HTTP sobre TCP |
| camadas | `model/` (regras, não sabe da rede), `net/` (RPC, não sabe do jogo), `gui/` (cola) |

---

## 2. RPC, RMI, stub e skeleton

- **RPC** (*Remote Procedure Call*): chamar uma função que roda em **outra
  máquina** como se fosse local. A biblioteca serializa os argumentos, manda
  pela rede, executa lá, devolve o resultado.
- **RMI** (*Remote Method Invocation*): a mesma ideia orientada a objetos (nome
  vindo do Java): chama-se um método de um **objeto remoto** por meio de um
  representante local, o *stub* (ou *proxy*).

Stub e skeleton são conceitos de RPC em geral. Neste projeto, as duas peças do
XML-RPC fazem esses papéis, sem nenhuma classe com esses nomes:

| Conceito | Classe | Papel | No código |
| --- | --- | --- | --- |
| **Stub / proxy** (lado cliente) | `ServerProxy` | representa o servidor **do outro lado**; chamar um método dele dispara a chamada de rede | [`_make_proxy` 206](fanorona/net/game_connection.py#L206) |
| **Skeleton** (lado servidor) | `SimpleXMLRPCServer` + `register_instance` | recebe a chamada, acha o método e o executa no objeto registrado | [`_ThreadedXMLRPCServer` 95](fanorona/net/game_connection.py#L95) e [`_GameService` 107](fanorona/net/game_connection.py#L107) |

Escrever `self._peer.move(1, 3, 2, 4, "NONE")` parece uma chamada local, mas faz:
monta o XML → HTTP POST → o adversário executa `_GameService.move` → devolve a
resposta. O proxy não conhece os métodos de antemão: ele aceita o nome e manda.
Por isso o código usa `getattr(self._peer, method)(*args)`
([266](fanorona/net/game_connection.py#L266)).

**"Isso é RMI de verdade?"** Não. É RPC (XML-RPC) com o papel de stub e
skeleton. Faltam duas coisas do RMI do Java:

| | RMI (Java) | Este projeto (XML-RPC) |
| --- | --- | --- |
| linguagem | só Java | qualquer uma (XML sobre HTTP) |
| *registry* | existe: procura-se o objeto por nome | não existe: o endereço é o IP + porta digitados |
| o que trafega | objetos (serialização ou referência) | só tipos simples (inteiros, strings, booleanos) |
| stub e skeleton | gerados a partir da interface | prontos na biblioteca |

Por isso `move` recebe `fr, fc, tr, tc` e não um objeto `Point`.

---

## 3. Por que os dois são cliente e servidor

**Cliente e servidor são papéis de uma chamada, não tipos de máquina.**

- **Cliente:** quem chama o método (`proxy.move(...)`) e espera a resposta.
- **Servidor:** quem escuta numa porta e executa o método.

Num RPC clássico a conversa só começa pelo cliente; o servidor só responde e
não tem como avisar o cliente por conta própria. Num jogo, os **dois** precisam
avisar o outro quando jogam. Sem servidor central, cada máquina precisa dos dois
papéis, com um canal em cada sentido:

```
Jogador A                                Jogador B
[servidor RPC: move, chat, ...]  <----   [proxy de A]
[proxy de B]  ---------------------->    [servidor RPC: move, chat, ...]
```

O papel muda conforme o momento da partida:

| Momento | Papel | O que acontece |
| --- | --- | --- |
| eu jogo | **cliente** | `send_move` enfileira; `_write_loop` chama `peer.move(...)` |
| o adversário joga | **servidor** | o `move` dele roda aqui, gera o evento e a tela atualiza |
| 3 s sem nada a enviar | **cliente** | `_write_loop` chama `ping()` no adversário |
| o adversário sai | **servidor** | o `bye()` dele chega e vira `"disconnected"` |

O servidor fica sempre de pé numa thread própria; o cliente fica sempre pronto
para chamar. Como o Fanorona é por turnos, parece que alternamos, mas os dois
papéis ficam ativos a partida inteira.

**Colinha: onde ir no código** (`Ctrl+G` + número).

| Papel | O que mostrar | Arquivo | Linha |
| --- | --- | --- | --- |
| **servidor** | a classe do servidor, uma thread por chamada | `game_connection.py` | [95-104](fanorona/net/game_connection.py#L95-L104) |
| **servidor** | os métodos que o adversário pode chamar | `game_connection.py` | [107-147](fanorona/net/game_connection.py#L107-L147) |
| **servidor** | `listen`: sobe o servidor e fica escutando | `game_connection.py` | [174-179](fanorona/net/game_connection.py#L174-L179) |
| **cliente** | onde o proxy fica guardado | `game_connection.py` | [154](fanorona/net/game_connection.py#L154) |
| **cliente** | `_make_proxy`: cria o proxy com `http://IP:porta` | `game_connection.py` | [206-209](fanorona/net/game_connection.py#L206-L209) |
| **cliente** | a chamada remota em si | `game_connection.py` | [266](fanorona/net/game_connection.py#L266) |
| **cliente** | `send_move`: só enfileira | `game_connection.py` | [286](fanorona/net/game_connection.py#L286) |
| **cliente** | `ping()` quando a fila fica parada | `game_connection.py` | [258-259](fanorona/net/game_connection.py#L258-L259) |
| **servidor** | `bye()` recebido: vira `"disconnected"` | `game_connection.py` | [145-147](fanorona/net/game_connection.py#L145-L147) |

Os dois papéis lado a lado, no mesmo arquivo:

```python
# SERVIDOR: game_connection.py, linhas 176-179 (listen)
server = _ThreadedXMLRPCServer(("", port), logRequests=False, allow_none=True)
server.register_instance(_GameService(self))     # expõe os métodos de _GameService
threading.Thread(target=server.serve_forever, ...).start()   # fica escutando

# CLIENTE: game_connection.py, linhas 206-209 (_make_proxy) e 266 (_write_loop)
xmlrpc.client.ServerProxy(f"http://{host}:{port}", ...)      # o proxy do adversário
getattr(self._peer, method)(*args)               # chama o método no servidor dele
```

**Antes (sockets) e agora (RPC):**

| | Sockets TCP (versão anterior) | XML-RPC (agora) |
| --- | --- | --- |
| conexão | uma, aberta a partida inteira | nenhuma fixa: cada chamada é uma requisição HTTP |
| mensagens | texto à mão (`MOVE 2 2 2 3 NONE`) com *parsing* | chamada de método; a biblioteca monta e lê o XML |
| papéis | host = servidor, quem entra = cliente, só até conectar | os dois são servidor e cliente a partida inteira |
| thread de leitura | própria, bloqueada em `readline()` | não existe: o servidor cria uma thread por chamada |
| detectar queda | automático (`readline()` termina) | manual: `ping()` e `bye()` |
| porta acessível | só a do host | **as duas** (o host chama de volta) |

O que **não** mudou: a fila de saída e a thread de escrita, a fila de entrada
com os mesmos eventos, o `root.after(50 ms)` na janela e os métodos `send_*`.

**Fala (2 min)**

> "Num RPC clássico só o cliente começa a conversa. Mas num jogo os dois
> precisam avisar o outro. Então cada máquina faz os dois papéis: um **servidor**
> que recebe as chamadas do adversário e um **proxy** que representa o servidor
> dele. Quando eu jogo, sou cliente. Quando ele joga, sou servidor. O servidor
> fica sempre escutando; o cliente fica sempre pronto para chamar."

**Fala curta: o que cada trecho faz (1 min 30 s)** *(na ordem da colinha)*

*Servidor, o lado que recebe:*

1. *(linhas 95-104)* "Esta classe é o servidor. O `SimpleXMLRPCServer` é o que o
   Python já traz: ele escuta numa porta, recebe a requisição HTTP com o XML,
   acha o método pedido e o executa. Eu acrescentei o `ThreadingMixIn`, para
   cada chamada rodar na sua própria thread, e guardo o IP de quem chamou."
2. *(linhas 107-147)* "Estes são os métodos que o adversário pode chamar em mim:
   `move`, `chat`, `resign`... Cada um só coloca um evento numa fila e devolve
   `True`. Fica numa classe separada para que só esses métodos fiquem expostos."
3. *(linhas 174-179)* "O `listen` junta tudo: cria o servidor na porta, registra
   esta classe como o objeto que atende as chamadas e deixa o `serve_forever`
   rodando numa thread. A partir daqui a máquina está escutando."

*Cliente, o lado que chama:*

4. *(linha 154)* "Aqui fica guardado o proxy do adversário. Começa vazio e é
   preenchido na conexão."
5. *(linhas 206-209)* "O `_make_proxy` cria esse proxy a partir de um endereço
   `http://IP:porta`, com um limite de 10 segundos de espera."
6. *(linha 286)* "O `send_move` não usa a rede. Só transforma a jogada em
   números e texto e coloca na fila de saída."
7. *(linha 266)* "Esta é a chamada de verdade. A thread de escrita tira da fila e
   chama o método no proxy. Quem executa é a outra máquina, e esta linha espera a
   resposta."

*Quando não há jogada:*

8. *(linhas 258-259)* "Se a fila ficar 3 segundos parada, a thread chama `ping()`
   no adversário, só para saber se ele ainda está lá."
9. *(linhas 145-147)* "E o `bye()` é o aviso de que o adversário saiu. Ele vira
   o evento 'desconectado' e a partida volta para a tela inicial."

---

## 4. Conexão e o register

**Por que preciso do IP e da porta do adversário?** O RPC, por baixo, é uma
requisição HTTP, e ela só chega se disser **para qual máquina** (IP) e **para
qual programa** (porta). O proxy é criado com `http://IP:porta`
([208](fanorona/net/game_connection.py#L208)). Na mesma máquina o IP é o mesmo
(`localhost`) e só a porta muda.

**O problema:** o RPC é pedido-resposta e os dois lados precisam se chamar. Quem
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

**Colinha: onde ir no código** (`Ctrl+G` + número).

Tudo começa no botão **Conectar** ([connect_screen.py:84](fanorona/gui/connect_screen.py#L84)),
que chama `NetworkSetup.host` ([35](fanorona/net/network_setup.py#L35)) ou
`NetworkSetup.join` ([62](fanorona/net/network_setup.py#L62)). Cada um roda numa
thread própria para não travar a janela. A coluna "Passo" usa a numeração do
diagrama acima.

| Passo | Quem | O que mostrar | Arquivo | Linha |
| --- | --- | --- | --- | --- |
| 1-2 | host | sobe o servidor e espera | `network_setup.py` | [41](fanorona/net/network_setup.py#L41), [43](fanorona/net/network_setup.py#L43) |
| 3 | quem entra | sobe o próprio servidor (porta 0) | `network_setup.py` | [68](fanorona/net/network_setup.py#L68) |
| 4-5 | quem entra | cria o proxy do host e chama `register(minha_porta, meu_nome)` | `game_connection.py` | [195-196](fanorona/net/game_connection.py#L195-L196) |
| 6 | host | ao receber a requisição, guarda o IP de quem chamou | `game_connection.py` | [103](fanorona/net/game_connection.py#L103) |
| 6 | host | a chamada cai em `_GameService.register` e vai para `_on_register` | `game_connection.py` | [117-120](fanorona/net/game_connection.py#L117-L120), [211](fanorona/net/game_connection.py#L211) |
| 6 | host | cria o proxy de volta | `game_connection.py` | [215](fanorona/net/game_connection.py#L215) |
| 6-7 | host | acorda o `wait_for_peer` e devolve o nome | `game_connection.py` | [216-218](fanorona/net/game_connection.py#L216-L218) |

Entre os passos 5 e 6 a chamada **atravessa a rede**: daí em diante o código roda
na outra máquina.

**Como o host descobre o IP de quem chamou?** Pela própria requisição HTTP:
`_ThreadedXMLRPCServer.finish_request`
([100](fanorona/net/game_connection.py#L100)) guarda `client_address[0]` numa
`threading.local` (`_request_ctx`). Roda na thread da requisição, então cada
chamada vê o seu IP. Quem entra só informa a **porta**.

**Terceiro jogador:** `_on_register` levanta `RuntimeError`
([213-214](fanorona/net/game_connection.py#L213-L214)); o `xmlrpc` transforma
isso num `Fault` e o terceiro vê *"Esta partida já tem dois jogadores"*. Isso só
é possível porque o servidor do host continua no ar a partida inteira.

**Quem é quem:** o host joga com `Color.WHITE` (desenhada como peça **escura**) e
começa; quem entra joga com `Color.BLACK` (desenhada **dourada**)
([connect_screen.py:100](fanorona/gui/connect_screen.py#L100) e
[114](fanorona/gui/connect_screen.py#L114)). Quem começa é decidido por
convenção, sem troca de mensagem.

**Fala curta: o que cada trecho faz (2 a 3 min)** *(na ordem da colinha)*

> Abertura: "Para eu ligar para você, preciso saber o seu número. Quando a
> partida começa, o host não sabe onde está o adversário. O `register` resolve
> isso."

*No host:*

1. *(linhas 41 e 43)* "O host sobe o servidor na porta escolhida e fica parado,
   esperando alguém se registrar."

*Em quem entra:*

2. *(linha 68)* "Quem entra também sobe um servidor, numa porta livre que o
   sistema escolhe. É o 'ramal' onde o host vai poder me ligar de volta."
3. *(linhas 195-196)* "Aqui eu crio o proxy do host, com o IP e a porta que o
   usuário digitou, e chamo `register` passando a minha porta e o meu nome. É a
   primeira chamada RPC da partida. Daqui em diante o código roda na outra
   máquina."

*De volta ao host:*

4. *(linha 103)* "Antes do `register` executar, o servidor já guardou o IP de quem
   chamou. Pense num identificador de chamadas: a porta eu informei, o IP ele
   enxerga sozinho. Fica numa `threading.local` porque cada chamada roda numa
   thread."
5. *(linhas 117-120 e 211)* "A chamada cai no `register` e vai para o
   `_on_register`. Ali o host confere que ainda não tem adversário; se já
   tiver, recusa com erro (linhas 213-214)."
6. *(linha 215)* "Com IP e porta, o host cria o proxy de volta. **Nesse instante o
   host passa a ser cliente também.**"
7. *(linhas 216-218)* "Por fim, acorda o `wait_for_peer` e devolve o nome. Quem
   entra recebe esse nome como retorno da chamada, e as duas telas de jogo
   abrem."

> Fechamento: "Depois disso não existe mais 'caminho do host' ou 'caminho de quem
> entrou'. Os dois lados se chamam do mesmo jeito."

**Se perguntarem**

- *"E se um terceiro jogador tentar entrar?"* O erro atravessa a rede como
  `Fault`; o terceiro vê "esta partida já tem dois jogadores".
- *"Funciona entre redes diferentes?"* Na mesma rede, sim. Entre redes, o host
  precisa chamar de volta o IP de quem entrou, então firewall ou NAT dele pode
  impedir. Com sockets isso não acontecia, porque só o host precisava de porta
  aberta.

---

## 5. Uma jogada, do clique à tela do outro

Como os dois lados são simétricos, **um fluxo só** descreve os dois sentidos.
Exemplo: o host move a peça de (1,3) para (2,4), sem captura.

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

**Colinha: onde ir no código**

| Passo | O que mostrar | Arquivo | Linha |
| --- | --- | --- | --- |
| 1 | filtra o clique (fim de jogo? minha vez?) | `game_screen.py` | [121](fanorona/gui/game_screen.py#L121) |
| 2 | valida e aplica no tabuleiro local | `game_screen.py` | [157](fanorona/gui/game_screen.py#L157) → `try_move` ([game_engine.py:96](fanorona/model/game_engine.py#L96)) |
| 3 | manda para a rede | `game_screen.py` | [171](fanorona/gui/game_screen.py#L171), [177](fanorona/gui/game_screen.py#L177) |
| 3 | `send_move` só enfileira | `game_connection.py` | [286](fanorona/net/game_connection.py#L286) |
| 5-6 | a thread faz a chamada RPC | `game_connection.py` | [253](fanorona/net/game_connection.py#L253), [266](fanorona/net/game_connection.py#L266) |
| 7 | o método que executa no adversário | `game_connection.py` | [122](fanorona/net/game_connection.py#L122) |
| 7 | o evento entra na fila de entrada | `game_connection.py` | [235](fanorona/net/game_connection.py#L235) |
| 9-10 | a janela lê a fila e despacha | `main_app.py` | [92](fanorona/gui/main_app.py#L92), [101](fanorona/gui/main_app.py#L101) |
| 11 | o adversário reaplica a regra | `game_screen.py` | [279](fanorona/gui/game_screen.py#L279) |

**Fala curta: o que cada trecho faz (3 min)** *(na ordem da colinha)*

*Em quem joga:*

1. *(linha 121)* "O clique chega aqui. Primeiro filtro: o jogo acabou? É a minha
   vez? Se não for, ignora."
2. *(linha 157, e `try_move` na linha 96 do engine)* "Aqui eu valido e aplico a
   jogada no meu tabuleiro. Se a captura for ambígua, o diálogo abre antes de
   qualquer coisa ir para a rede."
3. *(linhas 171 e 177)* "Se a jogada foi válida, mando para a rede com
   `send_move`. Quem jogou já vê o lance na tela, sem esperar resposta."
4. *(linha 286)* "O `send_move` não usa a rede. Só transforma a jogada em números e
   texto e coloca na fila de saída."
5. *(linhas 253 e 266)* "A thread de escrita tira da fila e faz a chamada de
   verdade: `self._peer.move(...)`. Quem executa é a outra máquina."

*No adversário:*

6. *(linha 122)* "Uma thread do servidor executa o `move`. Ele reconstrói o
   `Point` e o `CaptureType` a partir do que veio no XML, põe o evento na fila e
   devolve `True`. Não mexe na tela."
7. *(linha 235)* "O `_emit` é quem põe o evento na fila de entrada."
8. *(`main_app.py`, linhas 92 e 101)* "A janela principal esvazia essa fila a cada
   50 ms e despacha pelo nome do evento. Só a thread principal mexe no Tkinter."
9. *(linha 279)* "O `apply_remote_move` chama o **mesmo** `try_move`. Mesma regra,
   mesmo estado, mesmo resultado. Redesenha, e o adversário vê o lance."

> Fechamento: "O jogador que joga valida e vê na hora, a rede só carrega a decisão,
> e o outro lado reaplica a mesma regra. A interface nunca fala com a rede, só com
> filas."

**Detalhes que valem dizer**

- **Passos 1-2:** se houver captura ambígua (aproximação *e* afastamento), o
  engine devolve `NEEDS_CHOICE` e a GUI abre um diálogo **antes de qualquer
  coisa ir para a rede**. Por isso a escolha vai **resolvida** na chamada.
- **Passo 3:** `send_move` não usa a rede, só achata os argumentos e enfileira:

  ```python
  choice_name = "NONE" if choice is None else choice.name
  self._enqueue(("move", frm.row, frm.col, to.row, to.col, choice_name))
  ```

- **Passo 4:** quem jogou vê o lance na hora, sem esperar a rede. Não precisa:
  o outro lado vai aplicar a mesma regra (seção 8).
- **Passo 7:** os inteiros e a string que vieram do XML são **reconvertidos** em
  `Point` e `CaptureType`; o método **não mexe na tela**, só enfileira e devolve
  `True`.
- **Passo 8:** a chamada RPC é **síncrona**; o `True` significa "o evento já
  está na fila do outro lado".
- **Latência:** ida e volta da rede + até 50 ms (o `_poll_events`). Em rede
  local, imperceptível.

**Se perguntarem: as três perguntas certas**

**1. "Como a tela do outro usuário é atualizada?"** A ideia central: não mando o
tabuleiro, mando só a jogada.

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

---

## 6. Threads e filas

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
| `fanorona-rpc-server` | [`listen` 174](fanorona/net/game_connection.py#L174) | `serve_forever`: aceita as chamadas do adversário |
| uma por chamada recebida | `ThreadingMixIn` ([95](fanorona/net/game_connection.py#L95)) | executa o método remoto e enfileira o evento |
| `fanorona-rpc-writer` | [`start` 224](fanorona/net/game_connection.py#L224) | tira da fila de saída e chama o proxy |
| `fanorona-host-thread` | [`NetworkSetup.host` 35](fanorona/net/network_setup.py#L35) | `wait_for_peer()` sem travar a janela |
| `fanorona-join-thread` | [`NetworkSetup.join` 62](fanorona/net/network_setup.py#L62) | `connect_to()` sem travar a janela |

**Regra de ouro: o loop da interface nunca toca a rede.** Para mandar, a GUI
chama `send_*`, que só faz `queue.put`. Para receber, a GUI esvazia uma
`queue.Queue` com `get_nowait()`.

- **Por que a fila de saída e uma thread de escrita?** Uma chamada RPC
  **bloqueia** até a resposta chegar (até 10 s no pior caso). No clique do
  mouse, a janela congelaria com rede lenta. E, como há **uma só** thread
  fazendo **uma chamada por vez**, as mensagens chegam **na ordem em que foram
  feitas**.
- **Por que o servidor precisa de uma thread por chamada?** Com uma só, uma
  chamada demorada bloquearia todas as seguintes, inclusive o `register` de
  quem está tentando entrar.
- **Por que a ponte é uma `queue.Queue`?** É thread-safe: as threads de rede
  escrevem, a da GUI lê, sem lock manual. **O `GameEngine` só é tocado pela
  thread principal**, por isso não tem lock.
- **Locks que existem em `net/`:** `_events_lock` (protege `_event_queue` e
  `_pending`) e `_server_lock` (o desligamento do servidor não roda duas vezes).
- **Eventos antes do `start()`:** o servidor já está no ar durante o `register`,
  mas a fila da GUI só é entregue em `start()`
  ([224](fanorona/net/game_connection.py#L224)). Se o adversário jogar nesse
  intervalo, `_emit` guarda o evento em `_pending` e `start()` o despeja na fila,
  na ordem.

---

## 7. O que vai no fio

Gerado com `xmlrpc.client.dumps`, os mesmos bytes que o `ServerProxy` envia.

**Chamada** `move(1, 3, 2, 4, "APPROACH")`, corpo do HTTP POST:

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

Pontos para comentar:

- O XML-RPC só tem tipos simples. Por isso **`Point` não atravessa a rede**:
  viaja como 2 inteiros e é reconstruído do outro lado. Idem `CaptureType`, que
  vai como `string` (`"APPROACH"`) e volta com `CaptureType["APPROACH"]`.
- O nome do método (`<methodName>move</methodName>`) é o que o servidor usa para
  escolher a função. Um nome que não exista, ou que comece com `_`, é recusado.
- É verboso (a chamada acima tem 336 bytes; a resposta, 129) e legível. Numa LAN
  isso é irrelevante, e dá para mostrar no Wireshark.

---

## 8. Por que os tabuleiros ficam iguais

**Não há servidor autoritativo.** Ninguém manda o tabuleiro inteiro. Os dois
lados:

1. começam do mesmo estado (`GameEngine()` em `MainApp._launch_new_game`,
   [main_app.py:56](fanorona/gui/main_app.py#L56));
2. recebem as mesmas jogadas, **na mesma ordem** (uma thread de escrita, uma
   chamada por vez);
3. aplicam a mesma função determinística (`GameEngine.try_move`).

É replicação por **máquina de estados**: mesmo estado inicial + mesma sequência
de operações = mesmo estado final.

**Consequências de projeto:**

- **A escolha de captura vai resolvida** (`"APPROACH"`/`"WITHDRAWAL"`). Se fosse
  `None`, o engine do adversário devolveria `NEEDS_CHOICE` e não aplicaria nada.
- **`end_turn()` é uma chamada separada.** Numa sequência de capturas, o jogador
  pode parar quando quiser ("Terminar jogada"), e o adversário **não tem como
  deduzir** isso (ele poderia só estar pensando). `_on_end_turn_button`
  ([game_screen.py:196](fanorona/gui/game_screen.py#L196)) chama
  `end_chain_voluntarily()` local + `send_end_turn()`; o outro lado executa
  `apply_remote_end_turn` ([288](fanorona/gui/game_screen.py#L288)). Sem isso, um
  acharia que é a vez de A e o outro, de B, para sempre.
- **Uma divergência nunca se corrige sozinha.** Por isso tudo que muda o estado
  é uma chamada explícita, e nada é "deduzido".

**E o jogador que joga fora da vez?** Três camadas:

1. entrada: `_handle_point_clicked` retorna se `current_turn is not my_color`;
2. engine local: `try_move` recusa (`INVALID`) peça que não seja do turno;
3. engine remoto: o `try_move` do adversário **revalida tudo** ao receber
   (turno, limites, ligação entre casas, casa vazia, sequência...), então uma
   jogada ilegal que chegue pela rede **não altera o tabuleiro**. Limite
   conhecido: `apply_remote_move` não confere se o resultado foi `INVALID`, então
   a tela ainda registra a entrada no histórico (seção 12, limitações).

---

## 9. Queda de conexão

XML-RPC roda sobre HTTP sobre TCP, e cada chamada é uma requisição HTTP
independente (**não há conexão aberta permanente**). Isso muda o que "queda"
significa:

| tema | como o projeto lida |
| --- | --- |
| **ordem** | uma única thread de escrita faz **uma chamada por vez** e só pega a próxima depois que a anterior retornou. Testado: 300 jogadas seguidas chegaram na mesma ordem. |
| **duplicata** | não pode ocorrer: **não há reenvio automático**. Cada mensagem é tentada uma vez. |
| **perda** | se uma chamada falha (rede caiu, timeout), o jogo considera a conexão perdida e encerra a partida; não tenta de novo. |
| **mensagem cortada** | inexistente: a biblioteca entrega a chamada inteira ou lança exceção. |

Como o projeto descobre que o outro caiu:

- **`ping()`:** se a fila de saída ficar parada por `PING_INTERVAL_S` = 3 s, a
  thread de escrita chama `ping()` no adversário (`queue.Empty` em
  [258](fanorona/net/game_connection.py#L258)). Os **dois** lados fazem isso.
- **Falha de qualquer chamada** (`RPC_ERRORS`: `OSError`, `xmlrpc.client.Error`,
  `HTTPException`) → [`_report_disconnected` 248](fanorona/net/game_connection.py#L248)
  → evento `("disconnected", ...)` → `MainApp._handle_event` fecha a conexão,
  mostra "Conexão perdida" e volta para a tela inicial.
- **Timeout:** `CALL_TIMEOUT_S` = 10 s. O `ServerProxy` padrão espera para sempre;
  [`_TimeoutTransport` 82](fanorona/net/game_connection.py#L82) corrige isso.
  Servidor do adversário **desligado**: a conexão é recusada na hora. Rede
  **cortada de verdade** (cabo, Wi-Fi): vale o timeout, até 10 s.
- **`bye()`:** ao sair normalmente, `close()`
  ([306](fanorona/net/game_connection.py#L306)) enfileira a sentinela `_STOP`; a
  thread de escrita chama `bye()` no adversário e encerra. O outro lado percebe
  na hora, sem esperar o ping.
- **Ao encerrar,** `_shutdown_server`
  ([312](fanorona/net/game_connection.py#L312)) para o `serve_forever` e fecha o
  socket: a **porta é liberada** e dá para hospedar de novo.

Não há reconexão de propósito: uma reconexão decente exigiria numerar as
mensagens e reenviar as perdidas, para não aplicar a mesma jogada duas vezes.

**Fala (1 min)**

> "Sem conexão aberta, ninguém percebe a queda sozinho. Então a thread de escrita
> chama `ping()` quando a fila fica 3 segundos parada, e qualquer chamada que
> falhe vira o evento 'disconnected'. Quando alguém sai normalmente, chama
> `bye()`, e o outro lado percebe na hora."

---

## 10. Perguntas prováveis

**"Onde está o RPC aqui?"**
Em `fanorona/net/game_connection.py`. Cada processo registra um objeto
(`_GameService`) num `SimpleXMLRPCServer`; o adversário o chama por um
`ServerProxy`, como se fosse local: `self._peer.move(1, 3, 2, 4, "NONE")`.

**"Isso é RMI?"**
É RPC (XML-RPC) com o papel de stub e skeleton. Não há *registry* (o endereço é
digitado) nem passagem de referências a objetos. Seção 2.

**"Por que os dois são servidor e cliente? Não bastava um servidor?"**
Num RPC, só o cliente inicia chamadas. Num jogo os **dois** precisam avisar o
outro. Sem servidor central, cada um é servidor (recebe) e cliente (chama).
Seção 3.

**"Por que preciso do IP e da porta do adversário? E como o host descobre o IP de quem entrou?"**
O proxy manda uma requisição HTTP, que precisa de endereço: o IP diz a máquina e
a porta diz o programa. O host lê o IP na origem da requisição
(`client_address[0]`, em `finish_request`); quem entra informa só a porta
(`listen(0)`). Seção 4.

**"Como a tela do outro é atualizada?"**
Só a jogada trafega; o outro lado reaplica a mesma regra no mesmo `GameEngine`.
Seção 5.

**"Por que a chamada não é feita direto no clique do mouse?"**
RPC bloqueia. Em rede lenta, a janela travaria. O clique só enfileira.

**"Por que uma thread só para escrever?"**
Garante **ordem** (uma chamada por vez) sem precisar numerar mensagens.

**"Por que o servidor não atualiza a tela diretamente?"**
Tkinter não é thread-safe. O método remoto só enfileira um evento;
`MainApp._poll_events` aplica na thread principal.

**"Tem condição de corrida?"**
O `GameEngine` só é escrito pela thread principal, então não precisa de lock. A
ponte entre threads é `queue.Queue`, thread-safe. Os dois locks existentes
protegem a entrega inicial dos eventos e o desligamento do servidor.

**"E se a jogada chegar antes de a tela de jogo existir?"**
`_emit` guarda em `_pending` e `start()` entrega em ordem (seção 6).

**"E se a mensagem for perdida ou chegar duas vezes?"**
Não há reenvio, então não há duplicata. Se uma chamada falha, a partida
encerra. Seção 9.

**"Como sabe que o outro caiu, se não há conexão aberta?"**
`ping()` a cada 3 s de silêncio, qualquer chamada que falhe e `bye()` na saída
normal. Seção 9.

**"Por que enviar só `move(fr, fc, tr, tc, escolha)` e não o tabuleiro?"**
Os dois rodam o mesmo `GameEngine` determinístico. A decisão basta, e é muito
menor. Seção 8.

**"Por que `end_turn` é uma chamada separada?"**
Parar uma sequência de capturas é uma **escolha**, e o adversário não tem como
deduzi-la. Seção 8.

**"E se alguém chamar `move` fora da vez?"**
O `try_move` do receptor revalida e recusa; o tabuleiro não muda. Seção 8.

**"É seguro?"**
Não para internet: o servidor escuta em todas as interfaces e não há
autenticação. Para rede de laboratório é aceitável. Só os 8 métodos de
`_GameService` são expostos (nada de `allow_dotted_names`).

**"Funciona entre redes diferentes?"**
Os dois lados precisam ser alcançáveis, porque o host chama de volta. Firewall
ou NAT de quem entra impede. Seção 4.

**"Por que XML-RPC e não gRPC, Pyro ou sockets?"**
Está na biblioteca padrão (sem dependência), a chamada remota parece local e o
formato é legível (dá para ver no Wireshark). Para dois jogadores trocando
poucas mensagens por minuto, a eficiência não importa.

**"Quanto tempo leva uma jogada para aparecer no outro lado?"**
Ida e volta da rede + até 50 ms (intervalo do `_poll_events`).

---

## 11. Roteiro de demonstração

1. **Duas máquinas.** Na primeira: aba *Hospedar partida*, nome, porta `5000`,
   **Conectar** (fica "Aguardando outro jogador…"). Na segunda: aba *Entrar em
   partida*, nome, IP da primeira, porta `5000`, **Conectar**. Comentar: "aqui
   aconteceu o `register`".
2. **Uma jogada de cada lado.** Comentar: "do clique até aqui passou por
   `send_move` → fila de saída → RPC `move` → `_emit` → `_poll_events` →
   `apply_remote_move`".
3. **Captura ambígua:** mostrar o diálogo (aproximação ou afastamento). A escolha
   **vai resolvida** na chamada.
4. **Sequência de capturas + "Terminar jogada":** explicar o `end_turn()`.
5. **Chat** nos dois sentidos, intercalado com uma jogada.
6. **Desistência:** o outro lado recebe `resign()` e a tela de fim de jogo
   aparece nos dois. Mostrar **Revanche** (`rematch()`).
7. **Queda:** fechar uma das janelas no meio da partida; o outro recebe `bye()` e
   aparece "Conexão perdida". Depois hospedar de novo na **mesma porta**, para
   mostrar que ela foi liberada.
8. **Opcional:** Wireshark com filtro `tcp.port == 5000` para mostrar o XML
   (seção 7). Isso mostra só as chamadas **de quem entra para o host**; as do
   host para quem entra vão para a porta aleatória do outro servidor (a mesma
   que foi enviada no `register`).

**Plano B (uma máquina só):** veja "Na mesma máquina" na seção [12](#12-referência).

---

## 12. Referência

### Métodos remotos

São os métodos públicos de [`_GameService` 107](fanorona/net/game_connection.py#L107).
**É o adversário quem chama; a execução acontece na minha máquina.**

| método | linha | quem chama / quando | o que faz no lado que recebe | evento gerado |
| --- | --- | --- | --- | --- |
| `register(porta, nome)` | [117](fanorona/net/game_connection.py#L117) | quem entra, **uma vez** | guarda o nome, cria o proxy de volta, acorda o host, devolve o nome do host | — |
| `move(fr, fc, tr, tc, escolha)` | [122](fanorona/net/game_connection.py#L122) | a cada jogada | enfileira o evento e retorna `True` | `("move", Point, Point, CaptureType)` |
| `end_turn()` | [126](fanorona/net/game_connection.py#L126) | encerra a sequência de capturas | idem | `("endturn",)` |
| `resign()` | [130](fanorona/net/game_connection.py#L130) | desiste | idem | `("resign",)` |
| `rematch()` | [134](fanorona/net/game_connection.py#L134) | pede revanche | idem | `("rematch",)` |
| `chat(mensagem)` | [138](fanorona/net/game_connection.py#L138) | mensagem de chat | idem | `("chat", texto)` |
| `ping()` | [142](fanorona/net/game_connection.py#L142) | 3 s sem nada a enviar | só devolve `True` | — |
| `bye()` | [145](fanorona/net/game_connection.py#L145) | sai da partida | marca que o adversário saiu | `("disconnected", ...)` |

`escolha` é `"NONE"`, `"APPROACH"` ou `"WITHDRAWAL"`, **já resolvida** por quem
jogou.

Por que `_GameService` é uma classe separada de `GameConnection`: o `xmlrpc`
expõe **todos os métodos públicos** do objeto registrado. Se registrássemos a
`GameConnection`, o adversário poderia chamar `send_move`, `close`, `cancel`...
Nomes começando com `_` nunca são expostos.

### Correspondência com o protocolo de texto antigo

| texto (sockets) | RPC |
| --- | --- |
| `HELLO nome` | `register(porta, nome)` |
| `MOVE fr fc tr tc escolha` | `move(fr, fc, tr, tc, escolha)` |
| `ENDTURN` / `RESIGN` / `REMATCH` | `end_turn()` / `resign()` / `rematch()` |
| `CHAT texto` | `chat(texto)` |
| (não existia) | `ping()` e `bye()` |

### Constantes

([game_connection.py:67](fanorona/net/game_connection.py#L67), [main_app.py:19](fanorona/gui/main_app.py#L19))

| constante | valor | para quê |
| --- | --- | --- |
| `PING_INTERVAL_S` | 3 s | fila de saída parada por esse tempo → chama `ping()` |
| `CALL_TIMEOUT_S` | 10 s | tempo máximo esperando a resposta de uma chamada |
| `POLL_INTERVAL_MS` | 50 ms | a cada quanto a GUI esvazia a fila de entrada |
| porta do host | a do campo "Porta" (padrão 5000) | porta do servidor do host |
| porta de quem entra | 0 → o SO escolhe | porta do servidor de quem entra |

### Os outros métodos (chat, desistência, fim de sequência, revanche)

Mesmo caminho da jogada (GUI → `send_*` → fila → thread de escrita → RPC →
`_GameService` → `_emit` → `_poll_events` → `apply_remote_*`). Só muda o método:

| ação | GUI (quem faz) | RPC | GUI (quem recebe) |
| --- | --- | --- | --- |
| chat | `ChatPanel._send` ([chat_panel.py:56](fanorona/gui/chat_panel.py#L56)) → `GameScreen._send_chat` ([271](fanorona/gui/game_screen.py#L271)) | `chat(mensagem)` | `apply_remote_chat` ([294](fanorona/gui/game_screen.py#L294)) |
| desistência | `_on_resign_button` ([206](fanorona/gui/game_screen.py#L206)) → `_do_resign` ([212](fanorona/gui/game_screen.py#L212)) | `resign()` | `apply_remote_resign` ([297](fanorona/gui/game_screen.py#L297)) |
| terminar jogada | `_on_end_turn_button` ([196](fanorona/gui/game_screen.py#L196)) | `end_turn()` | `apply_remote_end_turn` ([288](fanorona/gui/game_screen.py#L288)) |
| revanche | `MainApp._rematch` ([main_app.py:70](fanorona/gui/main_app.py#L70)) | `rematch()` | `_handle_event` → `_launch_new_game` |
| sair | `MainApp._exit_to_connect` ([74](fanorona/gui/main_app.py#L74)) → `close()` | `bye()` | `_handle_event` ("disconnected") |

O **chat não tem canal próprio**: usa a mesma fila de saída, a mesma thread de
escrita e a mesma fila de entrada. Consequência boa: **chat e jogadas ficam na
mesma ordem** dos dois lados.

**Fim de jogo e vencedor:** não há mensagem de "fim". Cada lado calcula pelo
próprio engine e `_check_game_over` abre a `GameOverScreen`. Na desistência,
quem desiste executa `engine.resign(my_color)` local e quem recebe executa
`engine.resign(my_color.opposite())`; ambos chegam ao mesmo vencedor.

### Como executar

**Pré-requisitos:** Python 3 (testado na 3.12) e Tkinter (em algumas distros Linux vem
separado: `sudo apt-get install -y python3-tk`). Nenhum `pip install`: o projeto
usa só a biblioteca padrão (`tkinter`, `xmlrpc`, `threading`, `queue`).

```
python3 -c "import tkinter; print('tkinter OK')"   # conferir
python3 main.py                                    # na raiz do projeto
```

**Duas máquinas:**

1. Quem hospeda: aba **Hospedar partida**, nome e porta (ex.: 5000) →
   **Conectar**. Joga com as peças **escuras** e começa.
2. Quem entra: aba **Entrar em partida**, nome, **IP do host** e a mesma porta →
   **Conectar**. Joga com as peças **douradas**.

> **Firewall:** quem entra também sobe um servidor RPC, numa porta livre
> escolhida pelo sistema, para o host conseguir chamá-lo de volta. Com firewall
> ativo, é preciso permitir conexões de entrada ao Python nas duas máquinas (e
> liberar a porta escolhida no host).

**Na mesma máquina:** dois terminais com `python3 main.py`; um em *Hospedar*, o
outro em *Entrar* com IP `localhost` (padrão do campo) e a mesma porta.

### Regras do Fanorona implementadas

Tudo em [`game_engine.py`](fanorona/model/game_engine.py):

- **Tabuleiro 5×9** (45 intersecções, 22 peças por jogador, casa central
  vazia). Vizinhas na horizontal e vertical sempre se ligam; as diagonais
  existem em metade das casas, alternadas (`Board.is_connected`).
- **Movimento simples:** uma peça para casa vazia vizinha ligada por linha, quando
  o movimento não captura nada; só vale como primeiro movimento do turno e
  encerra o turno.
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

### Limitações conhecidas

- **Sem reconexão:** se a conexão cair no meio da partida, ela encerra.
- **Sem autenticação:** qualquer máquina que alcance a porta pode chamar os
  métodos remotos. Adequado para trabalho acadêmico em rede local.
- **Os dois lados precisam ser alcançáveis:** o host chama de volta quem entrou,
  então firewall ou NAT do jogador que entra impede a conexão.
- **Jogada ilegal recebida:** o engine do receptor a rejeita (o tabuleiro não
  muda), mas `apply_remote_move` não confere o tipo do resultado e registra a
  entrada no histórico mesmo assim.
- **`register` não é atômico:** `_on_register` verifica `self._peer is not None`
  sem lock. Dois jogadores chamando `register` no mesmo instante poderiam passar
  pela verificação; improvável num jogo com dois colegas.
- **Detecção de queda em rede cortada** pode levar até o timeout (10 s).
- **Captura não é obrigatória:** o engine aceita um movimento simples mesmo
  quando há captura disponível em outra peça (`try_move` só olha o movimento
  pedido).
- **Quem começa é fixo:** quem hospeda joga primeiro.
- Sem testes automatizados; a validação foi jogando com duas instâncias.
- Sem placar de partidas anteriores nem replay.
