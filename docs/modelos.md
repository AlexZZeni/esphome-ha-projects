# Modelos testados

Aparelhos de ar-condicionado já testados com este projeto, com o protocolo do controle remoto e a plataforma
`climate` usada no YAML.

| Ar-condicionado | Protocolo | Plataforma | Status | Observações |
|---|---|---|---|---|
| Super Split SS009 | Mirage, modelo KKG9AC1 | [`mirage`](../components/mirage) (deste repositório) | Funciona | Frio, aquecer, desumidificar, ventilar e automático. 16 a 32 °C. O controle original atualiza o Home Assistant. Testado com o ESPHome 2026.10.2. |

**Status**
- **Funciona:** ligar, desligar, modo, temperatura e ventilação testados pelo Home Assistant.
- **Parcial:** funciona com limitações, descritas nas observações.
- **Em teste:** protocolo identificado, mas os testes pelo Home Assistant ainda não terminaram.
- **Não funciona:** nenhuma plataforma testada controlou o aparelho.

## Como adicionar um modelo

1. Descubra o protocolo seguindo a seção "Descobrir o protocolo" do [README](../README.md#descobrir-o-protocolo).
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
| 4 | 4–7 | Modo: 1 aquecer, 2 frio, 3 desumidificar, 4 automático, 5 ventilar |
| 4 | 0–1 | Ventilação: 0 automática, 1 alta, 2 baixa, 3 média |
| 5 | 1–7 | Aleta: 3, 5, 7, 9 e 11 são posições fixas, de baixo para cima, e 13 é o movimento contínuo. Valores a partir de `0x5F` indicam desligado. |
| 8 e 10 | todos | Sempre `0x0C` |
| 11 a 13 | todos | Segundos, minutos e horas do relógio do controle, em binário. O aparelho ignora. |

Os bytes 2, 3, 6, 7 e 9 ficaram em zero em todas as capturas.

Detalhes do SS009 que diferem da documentação do IRremoteESP8266:
- **Desligar:** o controle sempre envia `0xC0` no byte 5, qualquer que seja a posição da aleta.
- **Ventilação:** a ordem é a do modelo KKG29AC1 (2 baixa, 3 média), não a do KKG9AC1.
- **Relógio:** os campos vêm em binário, não em BCD.
- **Desumidificar:** nesse modo, o controle sempre envia 17 °C.
