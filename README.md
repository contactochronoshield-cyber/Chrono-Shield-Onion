## 1. Especificaciones Técnicas y Estado de Implementación

> Chrono Shield Onion es un nodo perimetral de infraestructura crítica en desarrollo activo. Cada componente indica su estado real de implementación, validado por pruebas automatizadas (CI) y pruebas manuales de integración end-to-end.

### 1.1 Recolección Real y Capa de Datos
✅ **Implementado y probado** — Endpoint `/metrics` en formato Prometheus (CPU, memoria, disco, conexiones activas) vía `psutil`. Cubierto por test automatizado en CI.

🚧 **Fase 2 — Diseño en curso** — Captura de metadatos de red a nivel de kernel vía eBPF. Requiere Linux con soporte BPF completo; planeado para nodos Beelink N100.

### 1.2 Inmutabilidad del Sistema Operativo
🔧 **Código implementado, listo para activación en Linux completo** — Módulo `btrfs_manager.py` con snapshots atómicos de solo lectura y remontaje read-only. Requiere host con filesystem btrfs y root (Beelink N100). No aplica a nodos móviles Termux.

### 1.3 Escalabilidad (Prometheus + Grafana)
✅ **Implementado y probado** — Endpoint `/metrics` listo para scraping por agentes Prometheus.

🚧 **Fase 2** — Integración de dashboards Grafana.

### 1.4 Seguridad Crítica: Autenticación, mTLS y Canal Mesh
✅ **Implementado y probado en producción local** — Autenticación por login (usuario + contraseña con hash `scrypt`), emisión de JWT firmado, rate limiting anti fuerza-bruta, y verificación de integridad de código (SHA-256). Suite de tests automatizados corriendo en CI en cada push a `main`.

✅ **Implementado y probado** — **Arquitectura de doble canal**: el dashboard administrativo (puerto 5000) opera sobre autenticación JWT; el canal mesh nodo-a-nodo (puerto 5443) exige mTLS estricto (`CERT_REQUIRED`) a nivel de socket con CA propia generada vía OpenSSL, incluyendo extensiones `keyUsage` y `subjectAltName` correctas para validación estricta de clientes TLS modernos.

✅ **Implementado y probado** — **Auto-registro de nodos peer**: `mesh_client.py` permite que cualquier router nuevo se una a la red generando su propio certificado firmado por la CA local y comenzando a enviar heartbeat automáticamente, sin configuración manual del nodo principal.

⚠️ **Corrección de alcance** — La verificación de integridad de código (checksum SHA-256 del binario en ejecución) se documenta como tal, no como "Hardware Attestation". Attestation de hardware respaldada por TPM/Secure Boot está fuera del alcance actual del hardware disponible.

🔧 **Limitación conocida** — La clave privada de la CA (`ca.key`) reside en el mismo nodo que firma certificados de peers. Para un despliegue multi-sede real, se requiere separar la autoridad de firma del nodo operativo (Fase 3).

### 1.5 Distribución en Red Mesh y Detección de Anomalías
✅ **Implementado y probado end-to-end** — Canal mesh con persistencia SQLite (sobrevive a reinicios del proceso, verificado). Cada nodo peer se autentica por certificado propio y reporta estado vía `/mesh/heartbeat`.

✅ **Implementado y probado** — **Detección distribuida de anomalías**: el nodo principal analiza cada heartbeat en tiempo real y detecta automáticamente (a) CPU anómalo sostenido por encima de umbral configurable, y (b) pérdida de conectividad de un peer (sin heartbeat por más de 30s). Los eventos quedan persistidos y consultables vía `/mesh/anomalies`.

🚧 **Roadmap** — Correlación de anomalías entre múltiples nodos (detectar patrones de ataque coordinado, no solo eventos aislados por nodo).

### 1.6 Resiliencia Operativa
✅ **Implementado y probado** — `supervisor.py`: proceso supervisor en Python que monitorea el dashboard y el canal mesh, reiniciándolos automáticamente si mueren. Verificado matando procesos a la fuerza (`kill -9`) y confirmando recuperación automática en menos de 15 segundos.

### 1.7 Integración Continua (CI/CD)
✅ **Implementado y probado** — Pipeline de GitHub Actions con suite de tests automatizados (login, telemetría autenticada/no autenticada, métricas) y build de imagen Docker condicionado al éxito de los tests. Cache de dependencias pip habilitado.

---
**Leyenda:** ✅ Implementado y probado · 🔧 Código existente, pendiente de despliegue/activación · 🚧 Fase 2/3, en diseño
