# Basler Camera Streamer

## Visão Geral
Esta aplicação Flask faz streaming de vídeo de uma câmera Basler usando pypylon e OpenCV, expondo-os via um feed MJPEG multipart em `/video_feed`.

## Pré-requisitos
- **Python 3.7 ou superior** instalado na máquina.
- **Pip** para gerenciamento de pacotes Python.
- **Basler Pylon SDK** instalado (disponível no site oficial da Basler).
- Para sistemas Linux, crie regras udev para permitir acesso à câmera USB3:
  ```bash
  SUBSYSTEM=="usb", ATTR{idVendor}=="####", ATTR{idProduct}=="####", MODE="0666", GROUP="plugdev"
  ```
- **Dependências Python**:
  ```bash
  pip install pypylon opencv-python flask python-dotenv
  ```

## Instalação
Clone o repositório, configure um ambiente virtual e instale as dependências:
```bash
git clone https://github.com/SEU_USUARIO/basler-camera-streamer.git
cd basler-camera-streamer
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
```

## Arquivo de Dependências
No `requirements.txt`, inclua:
```
Flask
pypylon
opencv-python
python-dotenv
```

## Configuração
Defina as variáveis de ambiente (pode usar um arquivo `.env` na raiz do projeto):
```dotenv
HOST=0.0.0.0
PORT=8080
FRAME_BOUNDARY=frame
CAMERA_TIMEOUT_MS=1000
```

## Uso
Inicie o servidor:
```bash
python app.py
```
Acesse `http://<HOST>:<PORT>/video_feed` no navegador ou player compatível para ver o streaming.

