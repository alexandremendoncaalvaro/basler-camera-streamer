# Basler Camera Streamer

## Visão Geral  
Esta aplicação Flask faz streaming de vídeo de uma câmera Basler usando pypylon e OpenCV, expondo um feed MJPEG multipart em `/video_feed` :contentReference[oaicite:0]{index=0}.

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

# exposição e ganho
EXPOSURE_AUTO=Continuous
EXPOSURE_TIME=5000         # em µs, só se EXPOSURE_AUTO=Off
GAIN_AUTO=Continuous
GAIN=0                     # em dB, só se GAIN_AUTO=Off

# ajuste de imagem
IMAGE_CONTRAST=1.0    # 1.0 = original
IMAGE_BRIGHTNESS=0    # 0 = original
```

## Parâmetros da Câmera

### AcquisitionMode

Define o modo de aquisição: `SingleFrame` para um único frame ou `Continuous` para aquisição ininterrupta ([Basler Docs][1]).

### GrabStrategy

Determina como os frames são entregues ao usuário:

* `OneByOne`: cada imagem é processada em ordem
* `LatestImageOnly`: descarta frames antigos, sempre retorna o mais recente ([GitHub][2])

### AcquisitionFrameRateEnable & AcquisitionFrameRate

Quando `AcquisitionFrameRateEnable=true`, o parâmetro `AcquisitionFrameRate` limita a taxa máxima de frames por segundo, garantindo um fluxo constante conforme especificado (por exemplo, 30 fps) ([Basler Docs][3]).

### ExposureAuto & ExposureTime

* `ExposureAuto=Continuous`: ajusta automaticamente o tempo de exposição para alcançar o brilho alvo ([Basler Docs][4]).
* `ExposureAuto=Off`: permite definir manualmente `ExposureTime` em microssegundos ([Basler Docs][5]).

### GainAuto & Gain

* `GainAuto=Continuous`: ajusta automaticamente o ganho do sensor para alcançar o brilho alvo ([Basler Docs][6]).
* `GainAuto=Off`: permite definir manualmente `Gain` em dB para controlar a amplificação do sinal ([Basler Docs][7]).

### TriggerMode

Controla aquisição via software ou hardware:

* `TriggerMode=Off`: free‑run (aquisição contínua interna)
* `TriggerMode=On` + `TriggerSource=Software`: captura quando chamado `ExecuteSoftwareTrigger()` ([Basler Docs][8]).

### PixelFormat & Conversão

Câmeras Basler usam raw Bayer (ex.: `BayerRG8`). É preciso converter para BGR8packed antes de exibir com OpenCV (`converter.OutputPixelFormat = pylon.PixelType_BGR8packed`) ([Roboflow][9]).

## Uso

1. Ative o virtualenv e carregue as variáveis:

   ```bash
   source .venv/bin/activate
   source .env
   ```
2. Inicie o servidor:

   ```bash
   python capture.py
   ```
3. Acesse no navegador ou em um player MJPEG:

   ```
   http://<HOST>:<PORT>/video_feed
   ```


   [1]: https://docs.baslerweb.com/acquisition-mode?utm_source=chatgpt.com "Acquisition Mode | Basler Product Documentation"
[2]: https://github.com/basler/pypylon/issues/623?utm_source=chatgpt.com "How do I ensure the captured image is newest ? · Issue #623 - GitHub"
[3]: https://docs.baslerweb.com/acquisition-frame-rate?utm_source=chatgpt.com "Acquisition Frame Rate | Basler Product Documentation"
[4]: https://docs.baslerweb.com/exposure-auto?utm_source=chatgpt.com "Exposure Auto | Basler Product Documentation"
[5]: https://docs.baslerweb.com/exposure-time-%28dart-e%29?utm_source=chatgpt.com "Exposure Time (dart E) - Basler Product Documentation"
[6]: https://docs.baslerweb.com/gain-auto?utm_source=chatgpt.com "Gain Auto | Basler Product Documentation"
[7]: https://docs.baslerweb.com/gain?utm_source=chatgpt.com "Gain | Basler Product Documentation"
[8]: https://docs.baslerweb.com/triggered-image-acquisition?utm_source=chatgpt.com "Triggered Image Acquisition | Basler Product Documentation"
[9]: https://discuss.roboflow.com/t/complete-basler-integration/6781?utm_source=chatgpt.com "Complete Basler Integration - Feedback - Roboflow"