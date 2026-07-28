## 1. Especificaciones Técnicas y Estado de Implementación

> Chrono Shield Onion es un nodo perimetral de infraestructura crítica en desarrollo activo. Cada componente indica su estado real de implementación y el hardware requerido.

### 1.1 Recolección Real y Capa de Datos
✅ **Implementado y probado** — Endpoint `/metrics` en formato Prometheus con CPU, memoria, disco y conexiones activas en tiempo real vía `psutil`.

🚧 **Roadmap** — Captura de metadatos de red a nivel de kernel vía eBPF. Requiere Linux con soporte BPF completo (no disponible en Android/Termux sin root); planeado para nodos Beelink N100.

### 1.2 Inmutabilidad del Sistema Operativo
🔧 **Código implementado, pendiente de despliegue** — Módulo `btrfs_manager.py` con snapshots atómicos de solo lectura y remontaje read-only. Funcional únicamente en hosts Linux con filesystem btrfs y privilegios de root (Beelink N100). No aplica a nodos móviles Termux.

### 1.3 Escalabilidad (Prometheus + Grafana)
✅ **Implementado y probado** — Endpoint `/metrics` listo para scraping por agentes Prometheus. Integración con dashboards Grafana pendiente de configurar.

### 1.4 Seguridad Crítica, mTLS y Hardware Attestation
🔧 **Código implementado, pendiente de activación** — Generación automática de CA y certificados X.509 vía OpenSSL, y `SSLContext` con `CERT_REQUIRED` a nivel de socket. Pendiente: separar el canal de dashboard (HTTP + JWT) del canal mesh nodo-a-nodo (mTLS estricto).

✅ **Implementado** — Autenticación JWT con login por credenciales, rate limiting, y verificación de integridad de código (SHA-256).

⚠️ **Corrección de alcance** — Lo documentado como "Hardware Attestation" es verificación de integridad de código (checksum del binario en ejecución), no attestation de hardware respaldada por TPM/Secure Boot. Se renombra para reflejar su alcance real.

### 1.5 Distribución en Red Mesh
🚧 **Roadmap** — Failover automático de tráfico entre nodos peer. Actualmente cada nodo opera de forma aislada; la lógica de red mesh distribuida está en diseño.

---
**Leyenda:** ✅ Implementado y probado · 🔧 Código existente, pendiente de despliegue/activación · 🚧 Roadmap, no implementado
