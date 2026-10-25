Política de seguridad
Reportar una vulnerabilidad
Escribe a contactochronoshield@gmail.com con el asunto "SECURITY: Chrono Shield Onion". Incluye pasos para reproducirlo, el commit o versión afectada y el impacto. Por favor no abras un issue público para vulnerabilidades sin corregir.
Alcance
El código de este repositorio: dashboard (JWT), canal mesh (mTLS), detección de anomalías y warrant canary.
Limitaciones conocidas (declaradas, no son hallazgos nuevos)
La clave privada de la CA (ca.key) reside en el mismo nodo que firma los certificados de los peers. Separar la autoridad de firma es Fase 3.
La verificación de integridad es un checksum SHA-256 del código en ejecución, no attestation de hardware (el hardware actual no tiene TPM ni Secure Boot).
El warrant canary es una señal técnica de integridad, no un instrumento legal.
Versiones
Las correcciones de seguridad se aplican sobre la rama main.
