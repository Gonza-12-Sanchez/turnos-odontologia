# Discovery — turnos-odontologia

**Fecha**: 2026-09-29
**Fuentes investigadas**: 6 competidores con nota completa en `docs/discovery/sources/` (Denteo, Dentalink, Dentiqa, DrApp, Oclusar, OdontoApp) + 12 adicionales relevados vía investigación mercado (DentalSoft, AgendaPro, FLAP, DentalTec, DenPro, Doctoralia, Feegow, Ninsaúde, SaludTools, Doctocliq, Fresha, Booksy, Open Dental, Dentrix, Curve, NexHealth). Ver informe completo presentado en chat 2026-09-29 (tabla 18, matriz ponderada, análisis C y recomendación D).

## 1. Problema que resuelve

Consultorios odontológicos chicos (1-3 sillones) coordinan turnos por WhatsApp/papel, lo que genera dobles reservas, tiempo perdido confirmando manualmente cada turno e inasistencias sin recupero.

## 2. Usuarios / roles

- **Paciente**: reserva online sin WhatsApp y ve sus reservas asignadas (con login).
- **Odontólogo/dueño**: ve su agenda del día.
- **Secretaria**: confirma/cancela turnos, asigna turnos y registra cobros.

## 3. Casos de uso

1. Como paciente, quiero ver horarios libres para reservar sin tener que escribir por WhatsApp.
2. Como odontólogo, quiero ver mi agenda del día para saber cuántos pacientes tengo y a qué hora.
3. Como secretaria, quiero confirmar/cancelar turnos para mantener la agenda real.
4. Como paciente, quiero ver mis reservas asignadas para controlar mis citas.
5. Como secretaria, quiero cobrar y asignar turnos para cerrar el circuito en el local.

## 4. Competidores / soluciones existentes

| Competidor | Problema que resuelve | Pricing | Diferenciadores |
|---|---|---|---|
| Denteo | Gestión desordenada consultorio/clínica/lab | AR$ 30k-80k/mes, trial 15 días | SaaS nube, ARCA integrado, WhatsApp Meta, app Android |
| DentalSoft | Operación clínica chica desordenada | Gratis + $30k-$75k ARS/mes | Multi-sucursal, OS+liquidaciones, MP+GCal, web+turnero |
| FLAP | Gestión por box con cruces | Gratis + $12k-$68.9k ARS/mes | Box anti-superposición, lista espera auto, check-in QR, PWA |
| DrApp | Gestión dispersa con doble carga | Desde $32.8k/prof/mes, 15 días gratis | Odontograma+voz, agenda+ HCE+ARCA, ecosistema |
| Oclusar | Papeles/Excel/sistemas complicados | Gratis arranque, pesos sin tarjeta | Simplicidad una mano, OCLU IA, hecho por odontólogos |
| Dentalink | Operación con varios programas | Cotización | Líder Latam +15k clientes, todo-en-uno + IA + OS AR |
| Dentiqa | WhatsApp personal + agenda separada + Excel | USD 89-249/mes en ARS vía MP | Reemplaza Dentalink+Kommo+ManyChat, WA oficial + IA |
| AgendaPro | Captación y agenda belleza/salud | $13.9k-$314.9k ARS/mes + WA add-on | Marketplace, multi-sillón explícito, escala regional |
| DentalTec | Débitos OS y facturación | No publicado, demo a solicitar | Validación OS tiempo real, nomencladores AR, jerarquía CORA |
| Doctocliq | Consultorio chico sin sistema integral | Freemium + trial | WA gratis declarado, odontograma FDI+ADA + presupuestos x WA |
| OdontoApp | Inasistencias | No publicado (SPA) | Foco ausentismo, +10 odontólogos declarado |
| DenPro | HC + agenda simple multisede | $19.9k-$29.9k/mes | Precio simple, usuarios ilimitados Team |

**Notas**: Denteo/DrApp/Oclusar son los más directos argentinos (pesos, ARCA, WhatsApp). Dentalink es techo funcional. Diferencial elegido para este producto: simplicidad + precio + funcionalidades concretas (recordatorio auto v1, ARCA después).

## 5. Funcionalidades necesarias

- Reserva online 24/7 sin WhatsApp (ver libres + reservar).
- Vista agenda diaria para odontólogo.
- Confirmación/cancelación/reprogramación (paciente + secretaria).
- Mis reservas para paciente logueado.
- Recordatorio + confirmación WhatsApp automático con botón.
- Registro cobro simple en local + asignación turnos.
- Agenda multi-sillón día 1, duración variable por tratamiento, bloqueos, sobreturnos, anti-solapamiento.
- Roles paciente/odontólogo/secretaria, una sede, PWA mobile-first.

## 6. Funcionalidades opcionales

- Facturación ARCA (fase 2, modelo listo, no bloquea v1).
- Obras sociales/liquidaciones (fase 3).
- Odontograma/HCE completa, ortodoncia, imágenes (fase 3+).
- Marketplace barrial, campañas/recuperación ausentes, IA, multi-sede, API pública, GCal bidireccional.
- Pagos online avanzados, membresías/giftcards, loyalty.

## 7. Reglas de negocio

- Cancelación mínima 2hs antes (bloqueada por sistema).
- Sin doble-reserva mismo sillón/horario.
- Tolerancia llegada tarde 5 min visible.
- Multi-sillón desde día 1.
- Duración turno varía por tratamiento.
- Paciente con login (nombre+teléfono no alcanza).
- Seña MP opcional, políticas auto-ejecutadas.

## 8. Integraciones

- WhatsApp automático (recordatorios/confirmaciones) — única obligatoria v1, vía proveedor plantillas Meta, costo por mensaje.
- Nada más para v1. Mercado Pago para seña/cobro simple. Resto (GCal, ARCA, OS) fases posteriores.

## 9. Restricciones

- Presupuesto acotado, proyecto chico, tiene que andar bien en celular.
- Libertad total de stack/plazo fuera de eso, mobile-first implícito.

## 10. Riesgos

- **Supuesto sin probar**: que pacientes prefieran reservar online en vez de seguir por WhatsApp por costumbre — no validado con usuarios reales.
- **Riesgo**: si secretaria/odontólogo no mantiene agenda al día, muestra libres falsos.
- **Riesgo**: costo/bloqueo WhatsApp auto por spam + complejidad ARCA futura.
- Supuesto costo mensajes sin presupuesto techo — quién lo paga debe definirse.

## 11. Preguntas abiertas

- Ninguna pendiente al cierre 2026-09-29 — se cerraron cancelación 2hs, multi-sillón, login sí, duración variable. Si aparece algo en KB, se anota ahí.
- Re-evaluar en KB: login password vs OTP-WhatsApp para no frenar reserva.
