# Ventilador de teto com luz por infravermelho

Controla um ventilador de teto com luz que vem com controle remoto IR. No Home Assistant, o aparelho aparece como
duas entidades: um `fan` com 3 velocidades e uma `light` com brilho e temperatura de cor. O receptor IR também capta
o controle original, e o Home Assistant acompanha o que for feito por ele.

Não precisa de peça nova. O pacote usa o mesmo emissor e o mesmo receptor do
[ar-condicionado](ar-condicionado.md#ligações), e uma placa só controla os dois aparelhos. A condição é que o LED IR
alcance o receptor dos dois. Se não alcançar, aponte o LED para um ponto entre eles ou para o teto, ou ligue um
segundo LED em paralelo.

## Como usar

O pacote é o [`packages/ventilador.yaml`](../packages/ventilador.yaml). Ele precisa do `ir.yaml` e entra na lista de
pacotes da placa:

```yaml
packages:
  base: !include packages/base.yaml
  ir: !include packages/ir.yaml
  ventilador: !include packages/ventilador.yaml
```

Depois da primeira gravação, aperte **NW** no controle original. A placa não sabe em que estado a luz está, e o NW
deixa a luz acesa, com cor no meio e brilho máximo, que é a posição que ela assume no começo.

## Como funciona

O aparelho não responde aos comandos, então a placa guarda o estado em que acredita que ele está.

**Ventilador:** os botões de velocidade ligam o ventilador direto, e o Home Assistant usa esses botões para ligar e
mudar a velocidade. O botão liga/desliga só alterna, então é usado apenas para desligar.

**Luz:** o brilho e a cor mudam um passo por toque, em cerca de 10 passos. A placa transforma o valor pedido pelo
Home Assistant num número de passos e manda um toque a cada 0,3 s até chegar lá. Por isso, ir do mínimo ao máximo
leva uns 3 segundos.

| Home Assistant | No aparelho |
|---|---|
| Brilho de 1% a 100% | Passos 0 (brilho mínimo) a 10 (máximo). Cada passo vale uns 9%, e o mínimo aparece como 9% |
| Temperatura de 6000 K a 3000 K | Passos 0 (W, mais branca) a 10 (WW, mais amarela). O NW fica no passo 5 |
| Acender | Liga/desliga. A luz volta com o brilho e a cor de antes |

Os valores em kelvin são aproximados. O aparelho não informa a temperatura real.

Para não acumular erro na contagem, a placa manda 2 toques a mais quando o brilho vai para o máximo ou a cor vai para
uma ponta. Para o brilho mínimo, usa o botão próprio. Os botões WW, NW e W do controle original também acertam a
contagem, porque levam a luz a uma posição conhecida.

## Códigos do controle

Protocolo NEC, endereço `0xFF00`. Nos logs e no YAML, o ESPHome mostra o comando como "inverso << 8 | código". O botão
`0x08`, por exemplo, aparece como `0xF708`.

| Botão | Código | No ESPHome | Observação |
|---|---|---|---|
| Liga/desliga luz | `0x46` | `0xB946` | Alterna |
| Luz WW | `0x44` | `0xBB44` | Acende, cor mais amarela, brilho máximo |
| Luz NW | `0x40` | `0xBF40` | Acende, cor no meio, brilho máximo |
| Luz W | `0x43` | `0xBC43` | Acende, cor mais branca, brilho máximo |
| Brilho mínimo | `0x47` | `0xB847` | Não acende a luz |
| Aumenta brilho | `0x09` | `0xF609` | |
| Diminui brilho | `0x07` | `0xF807` | |
| Muda cor (+ branco) | `0x0D` | `0xF20D` | |
| Muda cor (− branco) | `0x16` | `0xE916` | |
| Liga/desliga ventilador | `0x18` | `0xE718` | Alterna |
| Velocidade 1 | `0x08` | `0xF708` | Liga o ventilador |
| Velocidade 2 | `0x1C` | `0xE31C` | Liga o ventilador |
| Velocidade 3 | `0x5A` | `0xA55A` | Liga o ventilador |

Para capturar os códigos de outro controle, siga os passos de
[Descobrir o protocolo](ar-condicionado.md#descobrir-o-protocolo). Fique a menos de 1 metro do receptor, com o
controle apontado de frente. De mais longe, boa parte dos toques chega com ruído e não é decodificada.

## Limitações

- **O estado é presumido.** Se o controle original for usado fora do alcance do receptor, o Home Assistant fica com
  o estado errado. Para acertar, use o controle perto do receptor: o NW para a luz e qualquer velocidade para o
  ventilador.
- **O interruptor de parede não é visto.** Se ele cortar a energia, a placa continua achando que o aparelho está
  como antes. Desligar e ligar o interruptor rápido duas vezes volta a luz a uma configuração padrão, que a placa
  também não acompanha.
- **O receptor capta o próprio sinal.** Por isso, a placa ignora os códigos recebidos até meio segundo depois de cada
  transmissão. Um toque no controle original nesse intervalo não é registrado.
