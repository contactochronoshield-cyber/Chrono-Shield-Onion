## 1. Especificaciones Técnicas y Estado de Implementación

> Chrono Shield Onion es un nodo perimetral de infraestructura crítica en desarrollo activo. Cada componente indica su estado real de implementación, validado por pruebas automatizadas (CI) y pruebas manuales de integración.

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

✅ **Implementado y probado** — **Arquitectura de doble canal**: el dashboard administrativo (puerto 5000) opera sobre autenticación JWT; el canal mesh nodo-a-nodo (puerto 5443) exige mTLS estricto (`CERT_REQUIRED`) a nivel de socket con CA propia generada vía OpenSSL. Verificado manualmente: conexiones sin certificado cliente son rechazadas en el handshake TLS, antes de llegar a la aplicación.

⚠️ **Corrección de alcance** — La verificación de integridad de código (checksum SHA-256 del binario en ejecución) se documenta como tal, no como "Hardware Attestation". Attestation de hardware respaldada por TPM/Secure Boot está fuera del alcance actual del hardware disponible.

### 1.5 Distribución en Red Mesh
🔧 **Canal de comunicación implementado, lógica de red pendiente** — El endpoint `/mesh/heartbeat` recibe y registra el estado de nodos peer autenticados por mTLS. Pendiente: descubrimiento automático de peers, failover de tráfico y sincronización de estado distribuido.

### 1.6 Integración Continua (CI/CD)
✅ **Implementado y probado** — Pipeline de GitHub Actions con suite de tests automatizados (login, telemetría autenticada/no autenticada, métricas) y build de imagen Docker condicionado al éxito de los tests. Cache de dependencias pip habilitado.

---
**Leyenda:** ✅ Implementado y probado · 🔧 Código existente, pendiente de despliegue/activación · 🚧 Fase 2, en diseño
