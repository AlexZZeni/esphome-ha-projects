# Ar-condicionado central Carrier Ecosplit pelo barramento do controlador

> **Em andamento.** Ainda não há placa nem pacote. Este guia registra o que já foi descoberto e o plano para
> controlar os aparelhos pelo Home Assistant.

O objetivo é controlar dois aparelhos centrais Carrier Ecosplit pelo Home Assistant: modo, temperatura,
ventilação e as resistências de aquecimento. Os aparelhos não têm controle infravermelho, então a ideia é ligar um
ESP32 no mesmo cabo do controlador com fio da parede.

## Equipamentos

| Peça | Modelo | Observação |
|---|---|---|
| Unidade externa (condensadora) | 38EVC10386S | 10 TR, 380 V |
| Unidade interna (evaporadora) | 40VX10HHG236V1V | Linha Ecosplit, com resistências de aquecimento |
| Controlador com fio | Não identificado | Cabo de 4 fios: 12V, GND, Y/A e G/B. Controla frio, ventilação e aquecimento |

O comando do aparelho trabalha em 12 V: o controlador é alimentado pelo fio de 12V e as contatoras são de 12 V.

Além da temperatura ambiente, do modo e da temperatura desejada, o controlador mostra dados da unidade externa:

- temperatura externa
- temperatura do condensador
- temperatura de sucção
- código de erro da unidade externa
- temperaturas de descarga 1 e 2

Os dois aparelhos são do mesmo modelo, e cada um tem dois compressores: um inverter (1º estágio) e um fixo (2º
estágio). Mesmo assim, os controladores não mostram as mesmas leituras extras:

| Aparelho | Leituras extras no controlador |
|---|---|
| Este, já capturado | Corrente 1 e corrente 2 |
| O outro | Frequência do compressor, corrente do compressor, temperatura do dissipador e tensão do barramento DC |

Como o equipamento é igual, a diferença deve estar no controlador (versão ou configuração). O barramento deste
aparelho provavelmente já leva os dados do inverter em bytes ainda não identificados.

São dois conjuntos iguais. A captura indica que cada aparelho tem o seu cabo e o seu controlador.

O [manual do Ecosplit](https://cdn.carrierdobrasil.com.br/downloads_docs/1196f-CT-Ecosplit-Inverter-J-11-14--view-.pdf)
lista a 38EVC10386S como condensadora compatível com as evaporadoras 40VX. Não foi encontrado o esquema de ligação
do controlador.

## O que passa no cabo do controlador

Medições com o multímetro em tensão contínua, com o aparelho ligado e desligado e em todos os modos:

| Entre | Tensão |
|---|---|
| GND e Y/A | 4,4 V, sem variação |
| GND e G/B | 0,32 V, sem variação |

Conclusão: Y/A e G/B são as linhas A e B de um barramento **RS-485 de 5 V**, e não sinais de termostato.

- Se o controlador fosse um termostato, o Y iria a 12 V, a tensão do comando, quando o compressor fosse chamado.
  Aqui a tensão não muda e nunca chega perto de 12 V. Quem aciona as contatoras é a placa da evaporadora.
- Um termostato precisaria de um fio a mais para o aquecimento, o W. O cabo só tem dois sinais e ainda assim
  controla as resistências.
- O controlador mostra temperaturas e o código de erro da unidade externa. Esses dados chegam a ele pelo cabo, então
  a comunicação vai nos dois sentidos. Um termostato só mandaria pedidos e não receberia nada.
- Em repouso, o RS-485 mantém a linha A perto da alimentação e a linha B perto do GND, o que bate com 4,4 V e
  0,32 V. O multímetro mostra a média, então a comunicação não aparece quando os dados são poucos.

Como o barramento é digital, a placa da evaporadora continua decidindo quando ligar a resistência e mantém as
proteções do aparelho, como não ligar a resistência com o ventilador parado. O ESP32 só envia os mesmos pedidos que
o controlador.

O protocolo não está documentado e está sendo descoberto por captura, como foi feito com o controle
[Mirage](modelos.md#protocolo-mirage-kkg9ac1). A primeira captura confirmou RS-485 a 9600 baud, 8N1. O mapa dos
quadros está em [modelos.md](modelos.md#protocolo-carrier-ecosplit-barramento-do-controlador).

Não é o protocolo XYE da Midea, que era uma das hipóteses: o XYE usa 4800 baud e quadros que começam com `AA`. Aqui os
quadros começam com `9A 56`.

## Plano

1. **Capturar pelo PC.** Um adaptador USB para RS-485 escuta o barramento em paralelo com o controlador. Ele não
   transmite nada, então não interfere no funcionamento. Pelo PC é mais fácil descobrir a velocidade (baud rate) e
   comparar os bytes de cada comando. Para a velocidade, testar as mais comuns: 4800, 9600 e 19200 baud. Um
   analisador lógico barato (clone do Saleae) mede a largura do bit direto e confirma que o sinal é diferencial.
2. **Mapear o protocolo.** Usar o controlador da parede enquanto a captura roda: ligar, desligar, cada modo,
   aquecimento, temperatura mínima e máxima e cada velocidade de ventilação. Passar também por cada tela de leitura
   e anotar no log o valor mostrado, por exemplo "externa 31, sucção 8, corrente 12,4". Assim dá para achar o byte de
   cada valor. Ele pode vir com deslocamento, multiplicado por 2 ou por 10, ou como leitura bruta do sensor. Algumas
   leituras podem passar no cabo só enquanto a tela correspondente está aberta. O mapa dos bytes vai para
   [modelos.md](modelos.md).
3. **Ler pelo Home Assistant.** Um ESP32 com um módulo MAX485 escuta o barramento e mostra o estado real de cada
   aparelho, ainda sem enviar comandos. Além do modo e das temperaturas ambiente e desejada, as leituras da unidade
   externa viram sensores no Home Assistant: temperatura externa, do condensador e de sucção, código de erro e
   corrente dos compressores. Com isso dá para acompanhar o funcionamento e receber um alerta quando aparecer um
   erro. O ESP32 é alimentado por uma fonte externa, e não pelo 12V do cabo. O GND
   do MAX485 (e da fonte) precisa ser ligado ao GND do cabo do controlador. Sem esse GND em comum, a referência fica
   solta e a leitura pode falhar ou dar erros.
4. **Controlar.** No RS-485, só um lado pode comandar por vez. Depois da captura, escolher entre trocar o controlador
   pelo ESP32 ou enviar comandos sem atrapalhar o controlador. A placa da evaporadora consulta um endereço `F1` que
   ninguém responde. Se ele for a vaga de um segundo controlador, o ESP32 pode responder como `F1` sem brigar com o
   controlador da parede. Isso só pode ser testado transmitindo.

## Captura pelo PC

### Peça

- Adaptador USB para RS-485, encontrado como "conversor USB RS485 CH340"

### Ligações

Em paralelo com o controlador, sem desligar nada:

| Adaptador | Cabo do controlador |
|---|---|
| A (ou D+) | Y/A |
| B (ou D−) | G/B |
| GND | GND |

- Não ligue o 12V no adaptador. Ele é alimentado pela USB. Isole a ponta desse fio enquanto mexe: se ele encostar
  em A ou B, o adaptador pode queimar.
- Se o adaptador não tiver GND, ligue só A e B.
- Os adaptadores rotulam A e B de jeitos diferentes. Se a captura mostrar só lixo em todas as velocidades, inverta
  os dois fios.
- Se for usar um notebook, deixe-o na bateria durante a captura para evitar diferença de terra com o aparelho.
- Mexa só no cabo do controlador. A alimentação do aparelho é de 380 V.
- Nunca ligue esses fios direto em um GPIO do ESP32. O ESP32 usa 3,3 V e precisa do módulo MAX485 no meio.

### Teste do adaptador

O adaptador comprado foi testado na bancada, ainda fora do barramento:

- O Windows reconhece como "USB-SERIAL CH340" (VID 1A86, PID 7523) e instala o driver sozinho. O número da porta
  COM muda de um PC para outro.
- **O transmissor só liga com o RTS ativo.** O adaptador não detecta o envio sozinho. Com o RTS desligado, ele só
  escuta e não mexe no barramento.
- Medições com A e B soltos, enviando `0x00` sem parar a 9600 baud:

  | Situação | A–GND | B–GND | A–B |
  |---|---|---|---|
  | Repouso (sem polarização no adaptador) | — | — | 0,07 V |
  | Enviando com RTS e DTR desligados | — | — | 0 V |
  | Enviando com o RTS ligado | 1,0 V | 3,9 V | −2,8 V |

  O valor de A–B é negativo porque o `0x00` deixa a linha em 0 em 90% do tempo, e o multímetro mostra a média.
- Os bytes enviados não voltam pela mesma porta. O receptor desliga enquanto o transmissor está ligado, então a
  recepção só pode ser testada no barramento.

> **Atenção na captura:** muitos programas ligam o RTS e o DTR sozinhos ao abrir a porta, como o `pyserial` por
> padrão e o PuTTY. Com o adaptador no cabo do controlador, isso faz ele forçar o barramento e atrapalha a
> comunicação do aparelho. Abra a porta com os dois desligados. No `pyserial`, configure antes de abrir:
>
> ```python
> import serial
>
> porta = serial.Serial()
> porta.port = "COM6"
> porta.baudrate = 9600
> porta.rts = False
> porta.dtr = False
> porta.open()
> ```

### Script de captura

O [`tools/captura_rs485.py`](../tools/captura_rs485.py) escuta o barramento sem nunca transmitir. Ele abre a porta
com o RTS e o DTR desligados e não escreve nada nela.

No Windows, instale o Python e o `pyserial` uma vez:

```powershell
winget install Python.Python.3.13
py -m pip install pyserial
```

Primeiro descubra a velocidade. A varredura escuta 15 segundos em cada velocidade comum, de 1200 a 115200 baud.
Use o controlador da parede durante a varredura para gerar tráfego:

```powershell
py tools\captura_rs485.py COM6 --varrer
```

Para cada velocidade, o script mostra quantos quadros chegaram, quantos se repetem e a média de transições de bit
por byte. Na velocidade certa, os quadros de consulta periódica costumam se repetir iguais. Em velocidade alta demais,
cada bit real vira vários bits iguais, e os bytes viram quase só `00`, `80`, `E0` e `F8`. Eles também se repetem, mas
têm poucas transições, e o script marca essas velocidades como "rápida demais". Confira se os quadros fazem sentido.
Se nada ficar claro, repita com `--paridade E`. No Ecosplit, a velocidade certa foi 9600 baud.

Depois, capture na velocidade encontrada:

```powershell
py tools\captura_rs485.py COM6 --baud 4800 --so-novos
```

- Cada quadro vai para um arquivo `captura-DATA-HORA.txt`, com o horário e o tempo desde o quadro anterior.
- Quadros nunca vistos antes são marcados com `*`. Com `--so-novos`, a tela mostra só esses, e o log continua com
  todos.
- Digite uma anotação e aperte Enter antes de cada ação no controlador, por exemplo "liguei frio". Ela entra no log
  no horário certo e mostra quais quadros novos vieram depois dela.
- Ctrl+C encerra e grava um resumo com cada quadro diferente e quantas vezes apareceu.

Se os quadros vierem quebrados em pedaços, aumente o silêncio que separa um quadro do outro, por exemplo com
`--pausa 50` (em milissegundos).

Abra o script antes de ligar A e B no cabo do controlador e deixe ele aberto durante a sessão. Assim, se o sistema
mexer no RTS no instante em que a porta abre, isso acontece com o adaptador ainda solto.

### Monitor ao vivo

O [`tools/monitor_ecosplit.py`](../tools/monitor_ecosplit.py) lê o barramento pelo adaptador e mostra os valores já
convertidos, atualizando a tela a cada meio segundo. Ele usa o
[mapa do protocolo](modelos.md#protocolo-carrier-ecosplit-barramento-do-controlador) e também nunca transmite.

```powershell
py tools\monitor_ecosplit.py COM6
py tools\monitor_ecosplit.py COM6 --csv leituras.csv
```

- Mostra ligado, modo, temperatura desejada e ambiente, as temperaturas da unidade externa e as duas correntes.
  Os valores que ainda são hipótese aparecem marcados.
- Mostra os quadros brutos do controlador e da evaporadora, com os bytes que mudaram desde o início em amarelo. Isso
  ajuda a achar o que ainda falta, como o código de erro.
- Descarta quadros com o XOR ou a soma errados.
- Com `--csv`, grava uma linha por ciclo, separada por ponto e vírgula e com vírgula decimal, para abrir no Excel.

## Pendências

- Fotos do controlador por trás e da régua de bornes da evaporadora, para achar o modelo do controlador e da placa
- Saber se os dois aparelhos estão no mesmo cabo. A primeira captura indica que não: só um controlador (`C1`)
  responde no barramento.
- Capturar o outro aparelho com o compressor funcionando, anotando a frequência do compressor, a corrente do
  compressor, a temperatura do dissipador e a tensão do barramento DC no mesmo instante em que aparecem na tela.
  Os candidatos neste aparelho são os bytes 12, 20, 21 e 22 do quadro da evaporadora
- Saber o que as correntes 1 e 2 medem. Na captura, a corrente 2 teve um pico de partida típico de compressor fixo
- Medição opcional em tensão alternada entre Y/A e G/B com o aparelho ligado: qualquer valor acima de zero confirma
  que há dados passando
