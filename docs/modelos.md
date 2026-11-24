# Modelos testados

Aparelhos de ar-condicionado já testados com este projeto, com o protocolo do controle remoto e a plataforma
`climate` usada no YAML.

| Ar-condicionado | Protocolo | Plataforma | Status | Observações |
|---|---|---|---|---|
| Super Split SS009 | Mirage, modelo KKG9AC1 | [`mirage`](../components/mirage) (deste repositório) | Funciona | Frio, aquecer, desumidificar, ventilar e automático. 16 a 32 °C. O controle original atualiza o Home Assistant. Testado com o ESPHome 2026.10.2. |
| Midea (modelo não anotado), com controle Carrier | Coolix | [`coolix`](https://esphome.io/components/climate/climate_ir/) | Em teste | Ventilação e oscilação funcionam pelo Home Assistant. Os quadros de frio, ventilar e desligar são iguais aos do controle Carrier, mas ainda falta confirmar que o ar gela com o comando do ESP32. A plataforma `midea_ir` não controlou o aparelho. 17 a 30 °C. O controle original atualiza o Home Assistant. Testado com o ESPHome 2026.10.2. |

**Status**
- **Funciona:** ligar, desligar, modo, temperatura e ventilação testados pelo Home Assistant.
- **Parcial:** funciona com limitações, descritas nas observações.
- **Em teste:** protocolo identificado, mas os testes pelo Home Assistant ainda não terminaram.
- **Não funciona:** nenhuma plataforma testada controlou o aparelho.

## Como adicionar um modelo

1. Descubra o protocolo seguindo a seção "Descobrir o protocolo" do [guia do ar-condicionado](ar-condicionado.md#descobrir-o-protocolo).
2. Teste pelo Home Assistant: ligar, desligar, cada modo, a temperatura mínima e a máxima, e cada velocidade de
   ventilação.
3. Acrescente uma linha na tabela com o modelo da etiqueta do aparelho, o protocolo que apareceu no log, a plataforma
   usada e o resultado.

## Protocolo Mirage (KKG9AC1)

Mapa dos 14 bytes, montado com a documentação do
[IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Mirage.h) e conferido com
capturas do controle do Super Split SS009. O checksum vem depois dos 14 bytes e é a soma de todos os nibbles.

| Byte | Bits | Conteúdo |
|---|---|---|
| 0 | todos | Cabeçalho, sempre `0x56` |
| 1 | todos | Temperatura + `0x5C` (16 °C = `0x6C`, 32 °C = `0x7C`) |
| 3 | 3 | Alterna o display. Só vem ligado no quadro do botão de display |
| 4 | 4–7 | Modo: 1 aquecer, 2 frio, 3 desumidificar, 4 automático, 5 ventilar |
| 4 | 0–1 | Ventilação: 0 automática, 1 alta, 2 baixa, 3 média |
| 5 | 1–7 | Aleta: 3, 5, 7, 9 e 11 são posições fixas, de baixo para cima, e 13 é o movimento contínuo. Valores a partir de `0x5F` indicam desligado. |
| 8 e 10 | todos | Sempre `0x0C` |
| 11 a 13 | todos | Segundos, minutos e horas do relógio do controle, em binário. O aparelho ignora. |

Os bytes 2, 6, 7 e 9 ficaram em zero em todas as capturas. O byte 3 só muda no botão de display.

Detalhes do SS009 que diferem da documentação do IRremoteESP8266:
- **Desligar:** o controle sempre envia `0xC0` no byte 5, qualquer que seja a posição da aleta.
- **Ventilação:** a ordem é a do modelo KKG29AC1 (2 baixa, 3 média), não a do KKG9AC1.
- **Relógio:** os campos vêm em binário, não em BCD.
- **Desumidificar:** nesse modo, o controle sempre envia 17 °C.

## Protocolo Coolix (Midea com controle Carrier)

Quadros de 3 bytes capturados do controle Carrier com `dump: all`. O ESPHome mostra cada um como
`Received Coolix: 0x...`. Os quadros enviados pela plataforma `coolix` saem iguais.

| Botão no controle | Quadro | Conteúdo |
|---|---|---|
| Desligar | `0xB27BE0` | Desligado |
| Frio, 21 °C, ventilação alta | `0xB23F60` | Frio |
| Frio, 21 °C, ventilação automática | `0xB2BF60` | Frio |
| Modo | `0xB21F64` | Desumidificar |
| Modo | `0xB2BF6C` | Aquecer |
| Modo | `0xB2BFE4` | Ventilar |
| Modo | `0xB21F68` | Automático |

O botão de modo segue a ordem frio, desumidificar, aquecer, ventilar e automático.

## Protocolo Carrier Ecosplit (barramento do controlador)

Mapa parcial, montado a partir de capturas feitas com o
[`tools/captura_rs485.py`](../tools/captura_rs485.py). O guia do projeto está em
[carrier-ecosplit.md](carrier-ecosplit.md).

RS-485 a **9600 baud, 8N1**. Os 8.690 quadros capturados seguem o formato abaixo, sem nenhum erro de verificação.

| Byte | Conteúdo |
|---|---|
| 0 e 1 | Início, sempre `9A 56` |
| 2 | Endereço de origem (provável) |
| 3 | Endereço de destino (provável) |
| 4 | Tamanho do quadro inteiro, em bytes |
| 5 até o antepenúltimo | Dados |
| Penúltimo | XOR de todos os bytes anteriores |
| Último | Soma, módulo 256, de todos os bytes anteriores, incluindo o XOR |

### Endereços e ciclo

O barramento repete sempre o mesmo ciclo de 4 quadros a cada 656 ms:

| Ordem | Origem → destino | Tamanho | Conteúdo |
|---|---|---|---|
| 1 | `01` → `C1` | 9 | Consulta, com os dados `FF FF` |
| 2 | `C1` → `FE` | 13 | Resposta do controlador, 35 ms depois |
| 3 | `01` → `F1` | 9 | Consulta, com os dados `FF FF`. Ninguém responde |
| 4 | `01` → `FE` | 31 | Leituras da placa da evaporadora |

- `01`: placa da evaporadora (provável). Ela comanda o barramento.
- `C1`: controlador da parede.
- `F1`: não responde nesta instalação. Pode ser a vaga de um segundo controlador.
- `FE`: todos.

### Quadro do controlador (`C1` → `FE`, 13 bytes)

Exemplo: `9A 56 C1 FE 0D 19 01 01 00 00 03 E4 BE`, com 25 °C desejados, 25,7 °C no ambiente e modo ventilar.

| Byte | Conteúdo | Situação |
|---|---|---|
| 5 | Bit 7 (`80`): ligado. Bits 0 a 6: temperatura desejada em °C. `19` = desligado, 25 °C. `99` = ligado, 25 °C. `94` = ligado, 20 °C. `14` = desligado, 20 °C | Confirmado com 25, 23 e 20 °C, ligado e desligado |
| 6 e 7 | Temperatura ambiente medida no controlador, em décimos de °C, byte mais alto primeiro. `01 01` = 25,7 °C | Confirmado: `01 02` = 25,8 °C, como na tela. A tela atualiza mais devagar que o barramento |
| 8 e 9 | `00 00`, ligado ou desligado. Talvez a ventilação | A descobrir |
| 10 | Modo: `01` frio, `02` aquecer, `03` ventilar. Segue a ordem do botão de modo | Confirmado |

### Quadro da evaporadora (`01` → `FE`, 31 bytes)

Exemplo com o compressor 2 funcionando em frio: `9A 56 01 FE 1F 30 00 4F 54 4E 5B 56 52 13 00 1C 06 0F 00 02 BC 98 5A
00 0C 01 07 00 00 66 A0`.

As temperaturas vêm em °C + 55, um byte cada: `4E` = 78 − 55 = 23 °C. As correntes vêm em passos de 0,25 A. As duas
codificações foram conferidas com os valores da tela no fim de uma captura com o compressor 2 funcionando:

| Tela | Byte | Valor | Conta |
|---|---|---|---|
| Externa 23 °C | 7 | `4E` | 78 − 55 = 23 |
| Condensador 29 °C | 8 | `54` | 84 − 55 = 29 |
| Sucção 21 °C | 9 | `4C` | 76 − 55 = 21 |
| Descarga 1: 42 °C | 10 | `60` | 96 − 55 = 41. A descarga subia 1 °C a cada 7 s |
| Descarga 2: 33 °C | 11 | `58` | 88 − 55 = 33 |
| Corrente 1: 0,0 A | 14 | `00` | 0 × 0,25 = 0,0 |
| Corrente 2: 6,7 A | 15 | `1B` | 27 × 0,25 = 6,75. A tela corta para 6,7 |

| Byte | Comportamento nas capturas | Hipótese |
|---|---|---|
| 7 | `4A` às 8 h, `4F` ao meio-dia | **Confirmado:** temperatura externa, °C + 55 |
| 8 | Subiu de `4F` para `54` com o compressor funcionando | **Confirmado:** condensador, °C + 55 |
| 9 | Desceu de `4F` para `4C` com o compressor funcionando | **Confirmado:** sucção, °C + 55 |
| 10 | Subiu de `50` para `60` com o compressor funcionando | **Confirmado:** descarga 1, °C + 55 |
| 11 | Subiu de `50` para `58` com o compressor funcionando | **Confirmado:** descarga 2, °C + 55 |
| 12 | `51` a `53` (26 a 28 °C) | Provável: dissipador do inverter, °C + 55. O valor bate com o que o controlador do outro aparelho mostra. Falta ver ele subir com o inverter funcionando por mais tempo |
| 13 | `13`, fixo em todas as capturas, inclusive com a externa a 25 °C | Não é a externa. Talvez configuração |
| 14 | `00` | **Confirmado:** corrente do compressor 1, em passos de 0,25 A |
| 15 | `00` desligado. Pulou para `42` na partida e ficou entre `17` e `1C` | **Confirmado:** corrente do compressor 2, em passos de 0,25 A. Conferido com 7,0 A (`1C`) e 6,7 A (`1B`). O `42` = 16,5 A é o pico da partida |
| 17 | `00` desligado, `08` ao ligar, `0C` 70 s depois de passar para frio, `0D` e `0F` antes da partida do compressor | Bits de estado. `08` = ventilador da evaporadora. Os outros ainda não se sabe quais são |
| 20 | `BA` a `C0`, oscilando em torno de `BD`, também com o aparelho desligado | Provável: tensão do barramento DC do inverter, em passos de 3 V. `BD` = 189 × 3 = 567 V. O controlador do outro aparelho mostrava 572 V |
| 21 | Subiu de `00` até `9E` em 35 s, depois do bit `04` do byte 17, e ficou entre `96` e `9B` | Talvez a frequência do compressor inverter, ou a velocidade do ventilador da condensadora |
| 22 | `00`, depois `14` 20 s depois de passar para frio, depois `5A` | Desconhecido. Talvez a frequência pedida ao inverter |
| 26 | Muda sozinho de 1 em 1, às vezes subindo e às vezes descendo, de `00` a `09` | Desconhecido |

Os outros bytes não mudaram em nenhuma captura. Ainda faltam o código de erro e a ventilação. O
[`tools/monitor_ecosplit.py`](../tools/monitor_ecosplit.py) mostra esses valores ao vivo.
