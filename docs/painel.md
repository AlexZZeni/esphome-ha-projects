# Painel de atalhos com a Cheap Yellow Display

Tela de toque com atalhos para o Home Assistant: liga e desliga os dois ares-condicionados, muda a temperatura deles,
e liga e desliga a luz e o ventilador de teto.

```
┌──────────────────────────────────────┐
│ 24.5 °C                 desconectado │
│ ┌──────────────┐  ┌──────────────┐   │
│ │Ar-condicionado│  │   Squad 1    │   │
│ │     23°      │  │     22°      │   │
│ │ [-] [⏻] [+]  │  │ [-] [⏻] [+]  │   │
│ └──────────────┘  └──────────────┘   │
│ [      Luz     ]  [  Ventilador  ]   │
└──────────────────────────────────────┘
```

O botão de liga/desliga fica laranja quando o aparelho está ligado, conforme o estado que o Home Assistant informa.
O aviso "desconectado" some quando o Home Assistant se conecta à placa.

## Placa

A **ESP32-2432S028R**, conhecida como Cheap Yellow Display (CYD): ESP32 sem PSRAM, tela de 2.8" 320×240 e toque
resistivo. A tela fica deitada, com o conector USB à direita.

Algumas versões trazem outro controlador de tela, principalmente as que têm dois conectores USB. Se a tela ficar
branca ou com as cores trocadas, mude o `model` em [`packages/cyd.yaml`](../packages/cyd.yaml) para
`ESP32-2432S028-7789` ou `ESP32-2432S028-9342`.

## Configurar

1. Em [`painel.yaml`](../painel.yaml), confira as entidades nas substituições. Os nomes padrão seguem as placas deste
   repositório. Se você renomeou alguma no Home Assistant, use o nome novo, que aparece em
   **Configurações > Dispositivos e serviços > Entidades**.
2. Grave a placa pelo USB:

   ```sh
   .venv/bin/esphome run painel.yaml
   ```

3. No Home Assistant, adicione a placa nova em **Configurações > Dispositivos e serviços**.
4. Ainda lá, abra a integração ESPHome, clique em **Configurar** na placa Painel e marque
   **Allow the device to perform Home Assistant actions**. Sem isso, a tela mostra os estados, mas os botões não
   fazem nada.

## Calibrar o toque

Cada placa responde um pouco diferente. Com a placa no USB, acompanhe o log:

```sh
.venv/bin/esphome logs painel.yaml
```

Cada toque aparece assim: `Toque em x=..., y=... (cru x=..., y=...)`.

- **O toque cai longe do dedo ou em um eixo invertido:** toque nos quatro cantos e anote os valores crus. Coloque o
  menor e o maior de cada eixo em `calibration` no `cyd.yaml`. Se um eixo continuar invertido, troque `x_min` com
  `x_max` (ou `y_min` com `y_max`) desse eixo.
- **Os eixos estão trocados, como quando um toque na horizontal move na vertical:** acrescente `transform:` com
  `swap_xy: true` no toque.

Quando o toque estiver certo, você pode apagar o `on_touch` do `cyd.yaml`.

## Tela apagada

Depois de 60 s sem toque, a luz de fundo apaga e o LVGL para de desenhar. O primeiro toque só acende a tela de novo,
sem acionar o botão que estiver embaixo do dedo. O tempo fica em `on_idle` no
[`painel-ui.yaml`](../packages/painel-ui.yaml).

A luz de fundo também aparece no Home Assistant como a luz **Tela**, para ajustar o brilho.

## Textos na tela

A fonte que vem com o LVGL não tem letras acentuadas. Se você mudar um texto da tela, como `ar1_nome`, escreva sem
acento, ou a letra some.
