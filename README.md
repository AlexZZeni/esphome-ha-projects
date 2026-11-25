# Projetos com ESPHome e Home Assistant

Dispositivos feitos com ESP32 e [ESPHome](https://esphome.io/) para controlar a casa pelo Home Assistant.

## Projetos

| Projeto | Placa | Guia |
|---|---|---|
| Ar-condicionado por infravermelho, com sensor de temperatura e humidade | [`ar-condicionado.yaml`](ar-condicionado.yaml) | [docs/ar-condicionado](docs/ar-condicionado/README.md) |
| Ventilador de teto com luz por infravermelho | [`ar-condicionado.yaml`](ar-condicionado.yaml) | [docs/ventilador](docs/ventilador/README.md) |
| Ar-condicionado Midea com controle Carrier (protocolo Coolix), com sensor de temperatura e humidade | [`esp32-squad-1.yaml`](esp32-squad-1.yaml) | [docs/ar-condicionado](docs/ar-condicionado/README.md) |
| Ar-condicionado central Carrier Ecosplit pelo barramento RS-485 do controlador, só leitura, com sensor de temperatura e humidade (em andamento) | [`evap-1.yaml`](evap-1.yaml) e [`evap-2.yaml`](evap-2.yaml) | [docs/carrier-ecosplit](docs/carrier-ecosplit/README.md) |

## Estrutura

```
ar-condicionado.yaml    uma placa = um arquivo, que inclui os pacotes de que ela precisa
packages/               partes reutilizáveis: rede, IR, sensores e aparelhos
components/             componentes próprios do ESPHome, como a plataforma mirage e a leitura do ecosplit
docs/<projeto>/         guia (README.md), diagramas e mapas de protocolo de cada projeto
tools/                  scripts para usar no PC, como a captura do barramento RS-485
secrets.yaml            senhas e chaves usadas por todas as placas (fica fora do git)
```

| Pacote | Conteúdo |
|---|---|
| [`base.yaml`](packages/base.yaml) | Log, conexão com o Home Assistant, gravação pelo Wi-Fi e rede de emergência. Toda placa inclui este. |
| [`ir.yaml`](packages/ir.yaml) | Emissor IR no GPIO4 e receptor IR no GPIO27 |
| [`sht31.yaml`](packages/sht31.yaml) | I²C no GPIO21 e GPIO22, com o sensor SHT31 (id `temperatura_ambiente`) |
| [`ar-ir.yaml`](packages/ar-ir.yaml) | Ar-condicionado por IR. Precisa do `ir.yaml`, de um sensor com o id `temperatura_ambiente` e da substituição `ac_platform` |
| [`mirage-display.yaml`](packages/mirage-display.yaml) | Botão que acende ou apaga o display do ar. Só para `ac_platform: mirage` |
| [`ventilador.yaml`](packages/ventilador.yaml) | Ventilador de teto com luz por IR. Precisa do `ir.yaml` |
| [`ecosplit.yaml`](packages/ecosplit.yaml) | Leitura do Carrier Ecosplit pelo barramento RS-485, com o módulo no GPIO16. Só escuta |

## Preparar o ambiente

No Debian e no Ubuntu, inclusive no WSL, instale o suporte a ambientes virtuais do Python. O ESPHome também precisa
dele para compilar o firmware do ESP32:

```sh
sudo apt install python3-venv
```

Na raiz do repositório, instale o ESPHome e crie o arquivo de senhas:

```sh
python3 -m venv .venv && .venv/bin/pip install esphome
cp secrets.yaml.example secrets.yaml   # e preencha os valores
```

O `.venv` guarda o caminho da pasta. Se a pasta do repositório mudar de nome ou de lugar, apague o `.venv` e rode o
primeiro comando de novo.

## Gravar uma placa

```sh
.venv/bin/esphome run ar-condicionado.yaml
```

Na primeira vez, a placa precisa estar no USB. Se não tiver permissão para acessar a porta serial, adicione seu
usuário ao grupo `dialout` e entre na sessão de novo. Depois disso, as gravações podem ser feitas pelo Wi-Fi.

## Adicionar uma placa

1. Crie um YAML na raiz com o nome da placa, como `quarto.yaml`, com os blocos `esphome` e `esp32` e os pacotes de que
   ela precisa. Use o [`ar-condicionado.yaml`](ar-condicionado.yaml) como modelo.
2. Dê à placa um `name` que nenhuma outra use. Duas placas com o mesmo nome na rede confundem o Home Assistant.
3. Coloque o que for específico de um aparelho em um pacote novo em `packages/`, para que outra placa possa
   reaproveitar.
4. Crie uma pasta em `docs/` com o nome do projeto, escreva o guia no `README.md` dela e acrescente o projeto à
   tabela acima.
