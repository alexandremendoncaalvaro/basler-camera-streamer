from pypylon import pylon

# 1. Liste todas as câmeras conectadas
devices = pylon.TlFactory.GetInstance().EnumerateDevices()
print(f"Câmeras encontradas: {len(devices)}")
for idx, dev in enumerate(devices):
    print(f"  {idx}: {dev.GetFriendlyName()} ({dev.GetModelName()})")

if not devices:
    print("Nenhuma câmera disponível. Verifique conexão e drivers.")
    exit(1)

# 2. Pegue a primeira câmera, abra e verifique
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
camera.Open()
print("Camera aberta:", camera.IsOpen())

# 3. Leia algumas configurações básicas
print("  Width :", camera.Width.Value)
print("  Height:", camera.Height.Value)
print("  Pixel Format:", camera.PixelFormat.Value)

# 4. Teste rápido de grabbing
camera.StartGrabbingMax(1)   # capturar um frame
print("IsGrabbing após StartGrabbingMax:", camera.IsGrabbing())

if camera.IsGrabbing():
    result = camera.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)
    print("GrabSucceeded:", result.GrabSucceeded())
    if result.GrabSucceeded():
        print("Frame obtenível, tamanho em bytes:", result.GetBufferSize())
    result.Release()
else:
    print("Não conseguiu iniciar o grabbing.")

camera.Close()
print("Camera fechada:", not camera.IsOpen())
