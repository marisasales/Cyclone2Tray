# CycloneTray

Monitor da bateria do **GameSir Cyclone 2** na system tray do Windows 11, usando o **dongle 2.4 GHz** — sem Bluetooth e sem abrir o GameSir Connect.

## Descoberta do caso

- O projeto [bpbp-boop/GameSirBattery](https://github.com/bpbp-boop/GameSirBattery) lê a bateria do **Cyclone Pro (T4cp)** por **BLE**, nos UUIDs `0x8650`/`0x865F`. Esse código não serve para o dongle do Cyclone 2.
- O [gamesir-linux-tools](https://github.com/broroeror/gamesir-linux-tools) documenta o protocolo do Cyclone 2 em modo XInput (`VID 3537`, PIDs `0575`/`100b`/`1053`): a bateria vem no **relatório HID de entrada `0x12`**, nos bytes **36** (porcentagem) e **35** (bit 0 = carregando). Mapeamento **confirmado no seu dongle** em 2026-11-23 (PID `100B`, Col04, fw 1.13).
- O relatório `0x12` **só fica populado com um keep-alive** `0F F2` enviado periodicamente (a cada ~0,4 s) na interface que declara os report IDs `0x0F`/`0x10`/`0x12`.
- No Windows existem várias coleções HID com o mesmo VID; o `probe.py` testa cada uma e descobre qual entrega a bateria.

A implementação usa apenas leitura do relatório + keep-alive. **Não envia comandos de configuração, escrita de registro nem firmware.**

## Como usar

1. Feche o **GameSir Connect** (ele pode manter o handle HID ocupado).
2. Conecte o dongle, ligue o controle e confirme o modo **XInput / LED verde**.
3. Rode `Diagnóstico.bat`. Ele lista as coleções HID e mostra qual responde com bateria.
4. Se aparecer `BATERIA: NN%`, rode `Iniciar monitor.bat`. O ícone aparece na bandeja (eventualmente na área de overflow `^`).

O monitor procura o dispositivo automaticamente na inicialização; o `Diagnóstico.bat --save` fixa a coleção encontrada em `settings.json` para acelerar esse passo.

Opções do diagnóstico:

```bat
Diagnóstico.bat --seconds 3
Diagnóstico.bat --no-heartbeat
Diagnóstico.bat --json
Diagnóstico.bat --save
Diagnóstico.bat --watch
```

`--watch` mantém a leitura aberta e imprime só as mudanças de `byte35`/`byte36`; é a forma mais rápida de validar o parser ligando/desligando o controle e comparando com o app oficial.

## Diagnóstico validado nesta máquina

- Controle desligado: dongle em `VID 3537 / PID 0575`, `Col03` (`Usage Page FFF0`, fw 1.13), `0x12` zerado (`byte35=0`, `byte36=0`, último byte `CC`) — o "dongle vazio" documentado no projeto de referência.
- Controle ligado no dongle: o dispositivo reaparece como `VID 3537 / PID 100B`, `MI 01 / Col04` (`Usage Page FFF0`, fw 1.13), entregando `0x12` continuamente.
- Leitura confirmada: `byte36=100` com a bateria em 100%; `byte35` foi `0x00` com `carregando=False` e `0x01` com `carregando=True`, batendo com o GameSir Connect.
- A coleção correta foi fixada em `settings.json` por `Diagnóstico.bat --save`.

O `probe.py` também mostra as coleções `MI_01/Col01..Col03` (gamepad, teclado, consumer), que não entregam o relatório de bateria. A descoberta automática já prioriza a coleção vendor com `PID 100B`.

## Menu da bandeja

- status e detalhe do dispositivo;
- **Atualizar agora** — força nova descoberta;
- **Alerta em** — 10/15/20/25/30% (padrão 20%, crítico em 10%);
- **Iniciar com Windows** — chave `HKCU\...\Run`;
- **Sair**.

Configurações: `%LOCALAPPDATA%\CycloneTray\settings.json`.

## Instalação / desenvolvimento

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe probe.py
.\.venv\Scripts\pythonw.exe run_tray.py
```

A DLL `vendor/hidapi.dll` (hidapi 0.15.0, [libusb/hidapi](https://github.com/libusb/hidapi)) está incluída porque o pacote `hidapi` de Python não tem wheel para Python 3.15. Licença em `vendor/HIDAPI-LICENSE.txt`.

## Observações finais

Os bytes 35/36 foram validados no seu Cyclone 2 (fw 1.13) e conferem com o GameSir Connect. O fallback `byte36=0xFF => 100% carregando`, herdado da engenharia reversa no Linux, não apareceu neste teste e está apenas documentado em `cyclonetray/protocol.py`. Se outro firmware apresentar divergência, `Diagnóstico.bat --watch` imprime as mudanças de `byte35`/`byte36` e `Diagnóstico.bat` mostra a amostra bruta para ajustar o parser.
