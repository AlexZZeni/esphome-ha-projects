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

São dois conjuntos iguais. Ainda não se sabe se os dois ficam no mesmo cabo ou se cada um tem o seu controlador.

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

- Em um termostato convencional, o Y vai a 12 V quando o compressor é chamado. Aqui a tensão não muda.
- Um termostato precisaria de um fio a mais para o aquecimento, o W. O cabo só tem dois sinais e ainda assim
  controla as resistências.
- Em repouso, o RS-485 mantém a linha A perto da alimentação e a linha B perto do GND, o que bate com 4,4 V e
  0,32 V. O multímetro mostra a média, então a comunicação não aparece quando os dados são poucos.

Como o barramento é digital, a placa da evaporadora continua decidindo quando ligar a resistência e mantém as
proteções do aparelho, como não ligar a resistência com o ventilador parado. O ESP32 só envia os mesmos pedidos que
o controlador.

O protocolo não está documentado. Ele precisa ser descoberto por captura, como foi feito com o controle
[Mirage](modelos.md#protocolo-mirage-kkg9ac1).

## Plano

1. **Capturar pelo PC.** Um adaptador USB para RS-485 escuta o barramento em paralelo com o controlador. Ele não
   transmite nada, então não interfere no funcionamento. Pelo PC é mais fácil descobrir a velocidade (baud rate) e
   comparar os bytes de cada comando.
2. **Mapear o protocolo.** Usar o controlador da parede enquanto a captura roda: ligar, desligar, cada modo,
   aquecimento, temperatura mínima e máxima e cada velocidade de ventilação. O mapa dos bytes vai para
   [modelos.md](modelos.md).
3. **Ler pelo Home Assistant.** Um ESP32 com um módulo MAX485 escuta o barramento e mostra o estado real de cada
   aparelho, ainda sem enviar comandos.
4. **Controlar.** No RS-485, só um lado pode comandar por vez. Depois da captura, escolher entre trocar o controlador
   pelo ESP32 ou enviar comandos sem atrapalhar o controlador.

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

- Não ligue o 12V no adaptador. Ele é alimentado pela USB.
- Se o adaptador não tiver GND, ligue só A e B.
- Se for usar um notebook, deixe-o na bateria durante a captura para evitar diferença de terra com o aparelho.
- Mexa só no cabo do controlador. A alimentação do aparelho é de 380 V.
- Nunca ligue esses fios direto em um GPIO do ESP32. O ESP32 usa 3,3 V e precisa do módulo MAX485 no meio.

## Pendências

- Fotos do controlador por trás e da régua de bornes da evaporadora, para achar o modelo do controlador e da placa
- Saber se os dois aparelhos estão no mesmo cabo
- Medição opcional em tensão alternada entre Y/A e G/B com o aparelho ligado: qualquer valor acima de zero confirma
  que há dados passando

## Modelo de exemplo

Unidade External: 38EVC10386S
Unidade Interna: 40VX10HHG236V1V
Controlador: Não consegui achar o modelo porem ele é conectado por 4 fios (12v, GND, Y/A, G/B)