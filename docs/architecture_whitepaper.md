# Chrono Shield Onion: Arquitectura de Infraestructura Crítica y Red Perimetral

## 1. Resumen Ejecutivo
Chrono Shield Core provee un marco de infraestructura resiliente diseñado para entornos de enrutamiento descentralizado y aislamiento de nodos críticos.

## 2. Componentes del Sistema
- **Backend de Telemetría (Flask):** Extrae métricas del kernel mediante interfaces virtuales (`/proc/loadavg`, `/proc/meminfo`, `/proc/net/tcp`) para garantizar observabilidad en tiempo real sin sobrecarga.
- **Seguridad Perimetral:** Implementación de mitigación DoS mediante control de ventanas temporales por IP (`rate limiting`) y validación de tokens de autorización perimetral.
- **Attestation de Integridad:** Cálculo criptográfico SHA-256 de componentes críticos del sistema operativo para verificar la inmutabilidad en tiempo de ejecución.
- **Frontend Asíncrono:** Interfaz de control web ligera integrada directamente en el servidor para visualización de métricas de rendimiento.

## 3. Topología de Red y Mesh
Diseñado para operar en nodos interconectados mediante túneles cifrados y enrutamiento poronion, asegurando la privacidad de las transacciones de datos y telemetría operativa.
