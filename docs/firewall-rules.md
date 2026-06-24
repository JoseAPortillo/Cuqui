# Firewall Rules — Hetzner

Cuando crees la VM en Hetzner, antes o después, crea un **Firewall** desde
el panel de Hetzner → "Firewalls" → "Create Firewall".

## Reglas necesarias

### Inbound (tráfico entrante)

| Puerto | Protocolo | Fuente | Propósito |
|---|---|---|---|
| 22 | TCP | 0.0.0.0/0 | SSH (acceso a la VM) |
| 8000 | TCP | 0.0.0.0/0 | App Cuqui (HTTP) |

### Outbound (tráfico saliente)
- Permitir todo (por defecto)

## Notas
- El puerto 8000 solo va HTTP. El HTTPS lo gestiona Cloudflare Tunnel.
- Si usas Cloudflare Tunnel, puedes **cerrar el puerto 8000** también
  (el túnel no necesita puertos abiertos).
