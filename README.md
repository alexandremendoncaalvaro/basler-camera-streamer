# Basler Camera Streamer

## Visão Geral

Esta aplicação Flask faz streamiQuando `AcquisitionFrameRateEnable=true`, o parâmetro `AcquisitionFrameRate` limita a taxa máxima de frames por segundo, garantindo um fluxo constante conforme especificado (por exemplo, 30 fps) ([Basler Docs][3]).

> **Implementação atual**: O código configura automaticamente `AcquisitionFrameRateEnable = True` e `AcquisitionFrameRate` baseado na variável `ACQUISITION_FRAME_RATE` (padrão: 30.0).g de vídeo de uma câmera Basler usando pypylon e OpenCV, expondo um feed MJPEG multipart em `/video_feed` :contentReference[oaicite:0]{index=0}.

## Pré‑requisitos

- Python 3.12 ou superior
- Pip
- Basler Pylon SDK instalado (https://www.baslerweb.com)
- (Linux) regras udev para câmera USB3:
  ```bash
  SUBSYSTEM=="usb", ATTR{idVendor}=="####", ATTR{idProduct}=="####", MODE="0666", GROUP="plugdev"
  ```

## Instalação

```bash
git clone https://github.com/SEU_USUARIO/basler-camera-streamer.git
cd basler-camera-streamer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz com as variáveis abaixo (todos têm valor padrão):

```dotenv
# rede e boundary
HOST=0.0.0.0
PORT=8080
FRAME_BOUNDARY=frame

# captura
CAMERA_TIMEOUT_MS=1000
ACQUISITION_MODE=Continuous
GRAB_STRATEGY=LatestImageOnly
ACQUISITION_FRAME_RATE_ENABLE=True
ACQUISITION_FRAME_RATE=30.0
MAX_CONNECTIONS=3          # limite de conexões simultâneas

# exposição e ganho
EXPOSURE_AUTO=Continuous   # Continuous | Off
EXPOSURE_TIME=5000         # em µs, só se EXPOSURE_AUTO=Off
GAIN_AUTO=Continuous       # Continuous | Off
GAIN=0                     # em dB, só se GAIN_AUTO=Off

# ajuste de imagem
IMAGE_CONTRAST=1.0         # 1.0 = original, >1.0 mais contraste, <1.0 menos contraste
IMAGE_BRIGHTNESS=0         # 0 = original, valores positivos mais claro, negativos mais escuro
```

## Estrutura do Projeto

```
basler-camera-streamer/
├── capture.py              # Aplicação principal Flask
├── requirements.txt        # Dependências Python
├── README.md              # Documentação
├── .env                   # Variáveis de ambiente (criar)
└── camera/
    └── test_camera_simple.py  # Script de teste da câmera
```

## Parâmetros da Câmera

### AcquisitionMode

Define o modo de aquisição: `SingleFrame` para um único frame ou `Continuous` para aquisição ininterrupta ([Basler Docs][1]).

**Configuração**: `ACQUISITION_MODE` (padrão: `Continuous`)

### GrabStrategy

Determina como os frames são entregues ao usuário:

- `OneByOne`: cada imagem é processada em ordem
- `LatestImageOnly`: descarta frames antigos, sempre retorna o mais recente ([GitHub][2])

**Configuração**: `GRAB_STRATEGY` (padrão: `LatestImageOnly`)

### AcquisitionFrameRate

Controla a taxa de frames por segundo da câmera ([Basler Docs][3]).

**Configuração**:

- `ACQUISITION_FRAME_RATE_ENABLE` (padrão: `True`)
- `ACQUISITION_FRAME_RATE` (padrão: `30.0`)

### ExposureAuto & ExposureTime

- `ExposureAuto=Continuous`: ajusta automaticamente o tempo de exposição ([Basler Docs][4])
- `ExposureAuto=Off`: permite controle manual do tempo de exposição

**Configuração**:

- `EXPOSURE_AUTO` (padrão: `Continuous`)
- `EXPOSURE_TIME` (padrão: `5000` µs, usado apenas se `EXPOSURE_AUTO=Off`)

### GainAuto & Gain

- `GainAuto=Continuous`: ajusta automaticamente o ganho do sensor ([Basler Docs][6])
- `GainAuto=Off`: permite controle manual do ganho em dB

**Configuração**:

- `GAIN_AUTO` (padrão: `Continuous`)
- `GAIN` (padrão: `0` dB, usado apenas se `GAIN_AUTO=Off`)

### Ajustes de Imagem

Controles de pós-processamento aplicados ao frame antes da codificação:

- `IMAGE_CONTRAST`: Controla o contraste (1.0 = original, >1.0 aumenta, <1.0 diminui)
- `IMAGE_BRIGHTNESS`: Controla o brilho (0 = original, positivo clareia, negativo escurece)

**Configuração**:

- `IMAGE_CONTRAST` (padrão: `1.0`)
- `IMAGE_BRIGHTNESS` (padrão: `0`)

### AcquisitionFrameRateEnable & AcquisitionFrameRate

Quando `AcquisitionFrameRateEnable=true`, o parâmetro `AcquisitionFrameRate` limita a taxa máxima de frames por segundo, garantindo um fluxo constante conforme especificado (por exemplo, 30 fps) ([Basler Docs][3]).

### ExposureAuto & ExposureTime

- `ExposureAuto=Continuous`: ajusta automaticamente o tempo de exposição para alcançar o brilho alvo ([Basler Docs][4]).
- `ExposureAuto=Off`: permite definir manualmente `ExposureTime` em microssegundos ([Basler Docs][5]).

> **Implementação atual**: O código configura automaticamente `ExposureAuto = "Continuous"`. A configuração manual `ExposureTime` não está implementada.

### GainAuto & Gain

- `GainAuto=Continuous`: ajusta automaticamente o ganho do sensor para alcançar o brilho alvo ([Basler Docs][6]).
- `GainAuto=Off`: permite definir manualmente `Gain` em dB para controlar a amplificação do sinal ([Basler Docs][7]).

> **Implementação atual**: O código configura automaticamente `GainAuto = "Continuous"`. A configuração manual `Gain` não está implementada.

### PixelFormat & Conversão

Câmeras Basler usam raw Bayer (ex.: `BayerRG8`). É preciso converter para BGR8packed antes de exibir com OpenCV (`converter.OutputPixelFormat = pylon.PixelType_BGR8packed`) ([Roboflow][9]).

> **Implementação atual**: O código utiliza `pylon.ImageFormatConverter()` com `OutputPixelFormat = pylon.PixelType_BGR8packed` automaticamente.

## Uso

1. Ative o virtualenv:

   ```bash
   source .venv/bin/activate
   ```

2. Inicie o servidor:

   ```bash
   python capture.py
   ```

3. Acesse as funcionalidades:

   - **Página de status**: `http://<HOST>:<PORT>/` (ex: http://localhost:8080/)
   - **Stream de vídeo**: `http://<HOST>:<PORT>/video_feed` (ex: http://localhost:8080/video_feed)

### Funcionalidades

- **Streaming MJPEG**: Endpoint `/video_feed` fornece stream multipart em tempo real
- **Página de status**: Endpoint `/` mostra informações da câmera, FPS, conexões ativas e uptime
- **Gerenciamento de conexões**: Limite configurável de conexões simultâneas (`MAX_CONNECTIONS`)
- **Buffer de frames**: Sistema otimizado que mantém sempre o frame mais recente
- **Monitoramento em tempo real**: Estatísticas de FPS e contagem de frames

## Testes

Para testar a conectividade da câmera independentemente do servidor web:

```bash
python camera/test_camera_simple.py
```

Este script verifica:

- Descoberta de dispositivos Basler conectados
- Abertura e configuração básica da câmera
- Captura de frames usando diferentes métodos
- Propriedades da câmera (resolução, formato de pixel)

  [1]: https://docs.baslerweb.com/acquisition-mode?utm_source=chatgpt.com "Acquisition Mode | Basler Product Documentation"
  [2]: https://github.com/basler/pypylon/issues/623?utm_source=chatgpt.com "How do I ensure the captured image is newest ? · Issue #623 - GitHub"
  [3]: https://docs.baslerweb.com/acquisition-frame-rate?utm_source=chatgpt.com "Acquisition Frame Rate | Basler Product Documentation"
  [4]: https://docs.baslerweb.com/exposure-auto?utm_source=chatgpt.com "Exposure Auto | Basler Product Documentation"
  [6]: https://docs.baslerweb.com/gain-auto?utm_source=chatgpt.com "Gain Auto | Basler Product Documentation"
  [9]: https://discuss.roboflow.com/t/complete-basler-integration/6781?utm_source=chatgpt.com "Complete Basler Integration - Feedback - Roboflow"
