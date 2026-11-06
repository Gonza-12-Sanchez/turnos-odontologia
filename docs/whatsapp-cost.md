# Costo WhatsApp (C-08)

Proveedor recomendado para etapa 6: Meta Cloud API directa o un BSP (360dialog/Twilio) según disponibilidad de cuenta WABA (IN-10-02).

Costo estimado: USD 0.005-0.015 por mensaje de plantilla (varía por país/categoría; Argentina ~ USD 0.008). IN-10-04 (quién paga) queda abierto para el piloto.

Reintentos: máximo 5 con backoff exponencial; luego se marca fallido y no se reencola. Monitorear vía conteo de RecordatorioWA.
