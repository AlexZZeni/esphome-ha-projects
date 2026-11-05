# Ar-condicionado por infravermelho para Home Assistant

Controla um ar-condicionado sem conectividade usando um ESP32 com ESPHome. O ar aparece no Home Assistant como
uma entidade `climate`, com modo, temperatura e ventilação.

## Peças

- ESP32 DevKit
- LED IR de 940 nm (TSAL6200 ou similar)
- Transistor NPN 2N2222
- Resistores de 1 kΩ e 47 Ω
- Receptor IR de 38 kHz (TSOP38238 ou VS1838B)

## Ligações

```
Emissor
  GPIO4 ── 1 kΩ ── base do 2N2222
  5V (VIN) ── 47 Ω ── LED IR (+)
  LED IR (−) ── coletor do 2N2222
  emissor do 2N2222 ── GND

Receptor
  VCC ── 3V3 (não use 5 V: a saída vai direto no GPIO)
  GND ── GND
  OUT ── GPIO27
```

Confira a pinagem do transistor e do receptor no datasheet do seu componente, porque ela muda entre modelos.

## Primeira gravação

```sh
python3 -m venv .venv && .venv/bin/pip install esphome
cp secrets.yaml.example secrets.yaml   # e preencha os valores
.venv/bin/esphome run ar-condicionado.yaml
```

Com a placa no USB, escolha a porta serial. Se não tiver permissão de acesso, adicione seu usuário ao grupo
`dialout` e entre na sessão de novo. As próximas gravações podem ser feitas pelo Wi-Fi.

## Descobrir o protocolo

1. Com o log aberto (`.venv/bin/esphome logs ar-condicionado.yaml`), aponte o controle para o receptor e aperte
   alguns botões.
2. Procure a linha com o nome do protocolo, como `Received Coolix: ...`.
3. Altere `ac_platform` no YAML para a [plataforma correspondente](https://esphome.io/components/climate/climate_ir/)
   e grave de novo. Algumas plataformas pedem opções extras, como `model` na `gree`.
4. Teste ligar, desligar e mudar a temperatura. Depois, remova o `dump: all`.

Se o log mostrar só códigos brutos (`Received Raw`), o protocolo não foi reconhecido. Tente a plataforma da marca
ou a [`heatpumpir`](https://esphome.io/components/climate/climate_ir/#heatpumpir). Se nenhuma funcionar, os
códigos brutos capturados podem ser enviados como botões.

## Home Assistant

Nos exemplos abaixo, `climate.ar_condicionado` é o ID esperado da entidade. Confira o seu em **Configurações →
Dispositivos e serviços → ESPHome → Ar-condicionado**. Os demais IDs (`sensor.*`, `binary_sensor.*`) são exemplos e
precisam ser trocados pelos seus.

### Adicionar o dispositivo

1. Em **Configurações → Dispositivos e serviços**, o dispositivo deve aparecer como descoberto. Clique em
   **Adicionar**.
2. Se ele não aparecer, vá em **Adicionar integração → ESPHome** e informe `ar-condicionado.local` ou o IP do ESP32,
   com a porta `6053`.
3. Informe o `api_key` do `secrets.yaml` quando for solicitado.

Se o Home Assistant estiver em outra VLAN ou sub-rede, a descoberta por mDNS pode não funcionar. Nesse caso, use o IP
e reserve um endereço fixo para o ESP32 no roteador.

### Testar os comandos

Em **Ferramentas de desenvolvedor → Ações**, execute cada ação no modo YAML e confira a resposta do ar:

```yaml
action: climate.set_hvac_mode
target:
  entity_id: climate.ar_condicionado
data:
  hvac_mode: cool
```

```yaml
action: climate.set_temperature
target:
  entity_id: climate.ar_condicionado
data:
  temperature: 23
```

```yaml
action: climate.turn_off
target:
  entity_id: climate.ar_condicionado
```

### Adicionar ao painel

No painel, clique em **Editar → Adicionar cartão → Por entidade** e escolha o ar-condicionado. Pelo editor YAML:

```yaml
type: thermostat
entity: climate.ar_condicionado
```

### Mostrar a temperatura ambiente

O ESP32 pode usar a temperatura de um sensor que já exista no Home Assistant. Ela aparece como temperatura atual na
entidade `climate`. Em `ar-condicionado.yaml`, adicione `sensor` ao bloco `climate` e crie o bloco `sensor`:

```yaml
climate:
  - platform: ${ac_platform}
    name: None
    transmitter_id: ir_tx
    receiver_id: ir_rx
    sensor: temperatura_ambiente

sensor:
  - platform: homeassistant
    id: temperatura_ambiente
    entity_id: sensor.sala_temperatura
```

Grave o firmware de novo depois da alteração. O sensor precisa estar no mesmo cômodo do ar, longe da saída de ar.

### Confirmar se o ar está ligado

O estado da entidade `climate` é presumido. Se houver um medidor de potência no circuito do ar, dá para criar um
sensor com o estado real em `configuration.yaml`:

```yaml
template:
  - binary_sensor:
      - name: "Ar-condicionado em funcionamento"
        device_class: running
        state: "{{ states('sensor.medidor_ar_potencia_ativa_total') | float(0) > 100 }}"
        availability: "{{ has_value('sensor.medidor_ar_potencia_ativa_total') }}"
        delay_off: "00:05:00"
```

Ajuste os `100` W olhando o consumo do seu aparelho com o ar ligado e desligado. O `delay_off` evita que o sensor
desligue nas paradas curtas do compressor. Se o aparelho desliga o compressor ao atingir a temperatura, aumente esse
tempo ou reduza o limite para acima do consumo em espera. Depois de editar o arquivo, recarregue em **Ferramentas de
desenvolvedor → YAML → Entidades de template**.

### Automações

Crie em **Configurações → Automações e cenas → Criar automação → ⋮ → Editar em YAML**.

Desligar quando ninguém estiver em casa (usa as pessoas cadastradas com rastreamento de presença):

```yaml
alias: Ar-condicionado - desligar sem ninguém em casa
triggers:
  - trigger: numeric_state
    entity_id: zone.home
    below: 1
    for: "00:15:00"
actions:
  - action: climate.turn_off
    target:
      entity_id: climate.ar_condicionado
mode: single
```

Desligar quando a janela ficar aberta:

```yaml
alias: Ar-condicionado - desligar com janela aberta
triggers:
  - trigger: state
    entity_id: binary_sensor.janela_sala
    to: "on"
    for: "00:02:00"
actions:
  - action: climate.turn_off
    target:
      entity_id: climate.ar_condicionado
mode: single
```

## Solução de problemas

- **O ar não responde:** olhe o LED pela câmera do celular enquanto envia um comando. Ele deve piscar (algumas
  câmeras filtram IR; se não enxergar, teste com outra). Se piscar, aproxime e aponte melhor para o receptor do ar.
- **Nada aparece no log:** confira a alimentação e a pinagem do receptor.
- **O estado no Home Assistant está errado:** o IR não confirma o recebimento, então o estado é presumido. Uso do
  controle original só é captado quando o receptor enxerga o sinal e o protocolo tem suporte a recepção.
