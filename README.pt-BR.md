# Cyclone2Tray

**Idioma:** Português | [English](README.md)

Monitor não oficial da bateria do **GameSir Cyclone 2** na área de notificação do Windows. Lê a carga pelo dongle USB de **2,4 GHz**, sem depender de Bluetooth ou do GameSir Connect.

## O que o programa faz

- Mostra a porcentagem da bateria em um ícone colorido na bandeja.
- Indica quando o controle está carregando e quando está desconectado.
- Avisa quando a bateria chega ao limite configurado.
- Redescobre o controle quando necessário e pode iniciar com o Windows.
- Inclui um utilitário para inspecionar as interfaces e relatórios HID.

O foco é o **Cyclone 2 conectado pelo dongle no modo XInput**. Outros modelos, modos de conexão e sistemas operacionais não foram validados. Este repositório não distribui um executável `.exe`: a aplicação roda com Python.

## Como funciona

O dongle e o controle expõem interfaces HID ao Windows. O Cyclone2Tray localiza a coleção vendor apropriada e mantém o fluxo ativo enviando o keep-alive `0F F2` a cada aproximadamente 0,4 segundo. A bateria chega no relatório de entrada `0x12`, com 64 bytes:

| Campo | Significado |
| --- | --- |
| Byte 36 | Porcentagem da bateria, de 0 a 100 |
| Byte 35, bit 0 | `1` enquanto carrega |

Esse mapeamento foi confirmado em Windows 11 com o Cyclone 2 e firmware 1.13 (VID `3537`, PID `100B`, coleção `Col04`). A descoberta considera também os PIDs `0575` e `1053`, que podem aparecer em outros estados ou revisões.

> [!NOTE]
> O programa não usa BLE nem escreve configuração, registros ou firmware. A única escrita HID é o keep-alive necessário para receber os relatórios; o restante é leitura.
>
> O valor `0xFF` no byte 36 tem um tratamento de compatibilidade herdado da investigação do protocolo (100% e carregando), mas não foi observado no firmware 1.13 validado.

## Requisitos

- Windows 11.
- GameSir Cyclone 2 e dongle 2,4 GHz, com o controle ligado no modo XInput (LED verde).
- Python 3.10 ou mais recente. Validado com Python 3.15.2.
- O arquivo `vendor/hidapi.dll`, já incluído no repositório.

Não é necessário instalar o .NET SDK nem compilar uma extensão nativa.

## Instalação e primeiro uso

1. Baixe ou clone o repositório e abra o PowerShell na pasta raiz do projeto.
2. Crie um ambiente Python e instale as dependências:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Conecte o dongle, ligue o controle em modo XInput e feche o **GameSir Connect**, caso esteja aberto (ele pode ocupar a interface HID).
4. Execute o diagnóstico:

   ```powershell
   .\diagnostics.bat
   ```

   Se aparecer `BATTERY: NN%`, salve a coleção encontrada para acelerar as próximas inicializações:

   ```powershell
   .\diagnostics.bat --save
   ```

   A busca automática continua disponível; salvar o caminho é opcional.

5. Inicie o monitor:

   ```powershell
   .\start-monitor.bat
   ```

O ícone pode ficar na área de ícones ocultos da bandeja. Clique na seta `^` ao lado do relógio para encontrá-lo.

## Usar o menu da bandeja

Clique com o botão direito no ícone para consultar o estado e:

- **Atualizar agora**: procurar o dispositivo novamente.
- **Alerta em**: escolher 10%, 15%, 20%, 25% ou 30% (padrão: 20%; alerta crítico: 10%).
- **Iniciar com Windows**: habilitar ou desabilitar a inicialização automática do usuário atual.
- **Sair**: encerrar o monitor.

Os alertas são reiniciados quando o controle começa a carregar ou quando a carga sobe pelo menos 5 pontos acima do limite. As configurações ficam em `%LOCALAPPDATA%\Cyclone2Tray\settings.json`; configurações antigas em `%LOCALAPPDATA%\CycloneTray\settings.json` são lidas como fallback. A inicialização automática usa a chave `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Diagnóstico

`diagnostics.bat` aceita os argumentos abaixo:

| Comando | Uso |
| --- | --- |
| `.\diagnostics.bat --seconds 3` | Aumenta para 3 segundos o teste de cada coleção HID |
| `.\diagnostics.bat --save` | Testa as coleções e salva o caminho que entrega a bateria |
| `.\diagnostics.bat --json` | Exibe os resultados em JSON |
| `.\diagnostics.bat --watch` | Acompanha continuamente as mudanças; encerre com `Ctrl+C` |
| `.\diagnostics.bat --no-heartbeat` | Testa sem enviar o keep-alive (útil para investigação) |

Em `--watch`, os bytes 35 e 36 são impressos em inglês quando mudam. Se o controle estiver desligado ou dormindo, é esperado que não haja leitura de bateria.

## Solução de problemas

- **Nenhuma coleção ou nenhum dispositivo encontrado:** confirme que o dongle está conectado e que o controle está ligado em 2,4 GHz/XInput.
- **O diagnóstico lista o dongle, mas não mostra `BATTERY`:** feche o GameSir Connect, acorde o controle e rode `.\diagnostics.bat --watch`.
- **O ícone não aparece:** verifique os ícones ocultos pela seta `^` da bandeja.
- **O arquivo `.bat` não inicia:** execute os comandos a partir da pasta do projeto e confirme que a instalação criou `.venv\Scripts\python.exe` e `.venv\Scripts\pythonw.exe`.
- **A leitura diverge em outro firmware:** rode o diagnóstico e compare os bytes brutos do relatório `0x12`; os valores confirmados acima correspondem ao firmware 1.13.

## Estrutura do projeto

- `cyclone2tray/protocol.py`: identificadores HID e interpretação da bateria.
- `cyclone2tray/discovery.py` e `reader.py`: descoberta, leitura e reconexão.
- `cyclone2tray/tray.py`: ícone, menu e alertas.
- `cyclone2tray/settings.py`: preferências e inicialização com o Windows.
- `probe.py`: ferramenta de diagnóstico.
- `vendor/hidapi.dll`: biblioteca HID para Windows.
- `diagnostics.bat` e `start-monitor.bat`: atalhos de diagnóstico e execução.

## Créditos e referências

- [broroeror/gamesir-linux-tools](https://github.com/broroeror/gamesir-linux-tools) — principal referência da investigação do protocolo HID do Cyclone 2: canal vendor, relatório `0x12` e keep-alive `0F F2`. A detecção de descritores HID em `cyclone2tray/protocol.py` adapta a função correspondente de [`gs_common.py`](https://github.com/broroeror/gamesir-linux-tools/blob/main/gs_common.py). O projeto de origem é MIT; copyright do trecho adaptado: © 2026 broroeror ([licença original](https://github.com/broroeror/gamesir-linux-tools/blob/main/LICENSE)).
- [bpbp-boop/GameSirBattery](https://github.com/bpbp-boop/GameSirBattery) — referência de experiência de uso para ícone, alertas, configurações e inicialização com o Windows. O protocolo daquele projeto é BLE para o Cyclone Pro (T4cp); **não** é usado para ler o Cyclone 2 neste aplicativo.
- [pyhidapi (`hid`)](https://github.com/apmorton/pyhidapi) e [hidapi](https://github.com/libusb/hidapi) — acesso HID em Python e DLL para Windows. A DLL incluída é a versão 0.15.0; consulte `vendor/HIDAPI-LICENSE.txt` e o [projeto original](https://github.com/libusb/hidapi).
- [pystray](https://github.com/moses-palmer/pystray) — ícone e menu na bandeja do Windows.
- [Pillow](https://python-pillow.org/) — desenho do ícone. O visual toma Material Symbols Rounded como referência; nenhum glifo ou arquivo de fonte externo é distribuído.

<details>
<summary>Aviso MIT do trecho adaptado de gamesir-linux-tools</summary>

Copyright (c) 2026 broroeror

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

</details>
