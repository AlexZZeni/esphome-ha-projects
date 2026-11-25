# Captura do barramento pelo PC

Como o protocolo do Carrier Ecosplit foi descoberto e como capturar o barramento com um adaptador USB para RS-485.
O mapa dos quadros está em [protocolo.md](protocolo.md), e o guia de montagem das placas está no [README](README.md).

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
[Mirage](../ar-condicionado/modelos.md#protocolo-mirage-kkg9ac1). A primeira captura confirmou RS-485 a 9600 baud, 8N1. O mapa dos
quadros está em [protocolo.md](protocolo.md).

Não é o protocolo XYE da Midea, que era uma das hipóteses: o XYE usa 4800 baud e quadros que começam com `AA`. Aqui os
quadros começam com `9A 56`.

## Adaptador USB

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
- Nunca ligue esses fios direto em um GPIO do ESP32. O ESP32 precisa de um módulo RS-485 no meio, como mostra o
  [guia de montagem](README.md#ligações).

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

O [`tools/captura_rs485.py`](../../tools/captura_rs485.py) escuta o barramento sem nunca transmitir. Ele abre a porta
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

O [`tools/monitor_ecosplit.py`](../../tools/monitor_ecosplit.py) lê o barramento pelo adaptador e mostra os valores já
convertidos, atualizando a tela a cada meio segundo. Ele usa o
[mapa do protocolo](protocolo.md) e também nunca transmite.

```powershell
py tools\monitor_ecosplit.py COM6
py tools\monitor_ecosplit.py COM6 --csv leituras.csv
```

- Mostra os valores já confirmados no mapa, como ligado, modo, temperaturas, correntes e os dados do inverter.
  Os bytes que ainda são hipótese aparecem à parte, com o valor bruto ao lado.
- Mostra os quadros brutos do controlador e da evaporadora, com os bytes que mudaram desde o início em amarelo. Isso
  ajuda a achar o que ainda falta, como o código de erro.
- Descarta quadros com o XOR ou a soma errados.
- Com `--csv`, grava uma linha por ciclo, separada por ponto e vírgula e com vírgula decimal, para abrir no Excel.
