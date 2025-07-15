from pypylon import pylon

# 1. Descobre dispositivos conectados
devices = pylon.TlFactory.GetInstance().EnumerateDevices()
print(f"Câmeras encontradas: {len(devices)}")
for i, dev in enumerate(devices):
    print(f"  {i}: {dev.GetFriendlyName()}")

if not devices:
    print("→ Nenhuma câmera encontrada. Verifique conexão e drivers.")
    exit(1)

# 2. Abre a primeira câmera
camera = pylon.InstantCamera(
    pylon.TlFactory.GetInstance().CreateDevice(devices[0])
)
camera.Open()
print("Câmera aberta:", camera.IsOpen())

# 3. Lê propriedades básicas
print("  Largura :", camera.Width.Value)
print("  Altura  :", camera.Height.Value)
print("  Pixel   :", camera.PixelFormat.Value)

# 4A. Teste direto com GrabOne (síncrono, sem StartGrabbing)
try:
    result = camera.GrabOne(2000)  # timeout em ms
    print("GrabOne OK:", result.GrabSucceeded())
    if result.GrabSucceeded():
        print("  Tamanho do buffer:", result.GetBufferSize())
    result.Release()
except Exception as e:
    print("Erro no GrabOne:", e)

# 4B. Teste usando StartGrabbing / RetrieveResult
camera.StartGrabbingMax(1)  
print("IsGrabbing após StartGrabbingMax:", camera.IsGrabbing())

if camera.IsGrabbing():
    res = camera.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)
    print("RetrieveResult OK:", res.GrabSucceeded())
    res.Release()
else:
    print("→ Falha ao iniciar grabbing")

camera.Close()
print("Câmera fechada:", not camera.IsOpen())
