import base64

def protect(data, key="DanielCEO"):
    # Cifrado por flujo basado en ciclos
    cifrado = ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))
    return base64.b64encode(cifrado.encode()).decode()

def reveal(data, key="DanielCEO"):
    decoded = base64.b64decode(data).decode()
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(decoded))

print("--- [MOTOR DE CIFRADO NATIVO LISTO] ---")
