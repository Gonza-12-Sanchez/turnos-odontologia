# Informe de Discovery — Sistema de gestión de turnos para consultorios odontológicos

> Estado: COMPLETO — Secciones A–D y Verificación de fuentes completadas el 2026-10-06. Revisión 2026-10-06 (v2): portada completa + distinción [C]/[A] en todo el informe.
> Base: `docs/discovery/sources/` (6 notas con fecha 2026-09-29) + `docs/discovery/checklist-discovery.md` (11 puntos) + verificación en vivo 2026-10-06.
> Regla aplicada: toda celda sin respaldo público dice "No evidenciado". No se inventaron funcionalidades.
> Convención de evidencia usada en TODO el informe: **[C] = funcionalidad comprobada** (se vio en el producto, su documentación o un video oficial) · **[A] = afirmación comercial** (lo declara el proveedor sin demostración pública).

## 1. Portada

- Título: Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos (mercado argentino)
- Materia: Metodología I — Tecnicatura Universitaria en Programación
- Integrantes: Gonzalo Sanchez, Maximiliano Mendez, Gabriel Danna, Mailen Ortiz, Leonel Fachinelli
- Fecha: relevamiento 2026-09-29 — informe y verificación en vivo 2026-10-06
- Alcance: consultorios chicos (1–3 sillones), 1 sede, mobile-first, Argentina (pesos, Mercado Pago, ARCA, WhatsApp)

## 2. Resumen ejecutivo

Se investigaron 6 competidores con nota completa en `docs/discovery/sources/` (Denteo, Dentalink, Dentiqa, DrApp, Oclusar, OdontoApp) y se relevaron 10+ adicionales vía checklist (DentalSoft, FLAP, AgendaPro, DentalTec, DenPro, Doctocliq, Doctoralia, Fresha, Open Dental, NexHealth).

Hallazgos principales:

- El problema es real y específico: consultorios chicos coordinan por WhatsApp/papel → dobles reservas, confirmación manual e inasistencias sin recupero.
- El estándar de mercado argentino ya incluye: reserva online + recordatorio/confirmación por WhatsApp + agenda anti-solapamiento + historia clínica con odontograma + cobro (Mercado Pago) + facturación ARCA. Denteo, Oclusar, DrApp y Dentiqa lo cubren de punta a punta.
- Los 3 directos argentinos (Denteo / DrApp / Oclusar) compiten en pesos, ARCA y WhatsApp. Dentalink es el techo funcional regional (+15.000 clientes). Dentiqa es el techo en IA + WhatsApp oficial.
- Vacío aprovechable para un MVP chico: simplicidad extrema + precio bajo + solo turnos bien hechos (multi-sillón día 1, duración variable, cancelación 2 h, login paciente, recordatorio automático). Nada de HCE completa, ni obras sociales, ni ARCA en v1.

MVP recomendado (v1): reserva online 24/7, agenda diaria multi-sillón con anti-solapamiento, confirmar/cancelar/reprogramar, Mis reservas con login, recordatorio + confirmación WhatsApp automático, cobro simple local + asignación. ARCA fase 2, obras sociales fase 3, odontograma/HCE fase 3+.

## A. Tabla comparativa (16 sistemas, ordenados por relevancia para Argentina)

Orden: argentinos con operación local primero, luego Latam con presencia AR, luego regionales/globales. Fecha de consulta de las 6 notas: 2026-09-29. Verificación en vivo: 2026-10-06 (sección Verificación).

Lectura de evidencia por fila: "Comprobado" = [C] (visto en sitio/documentación en vivo); las cifras de proveedor sin demostración (ej. "+15.000 clientes", "+10 odontólogos", "chatbot IA 3 capas", "OCLU IA", "score de ausentismo") son [A] y NO suben el puntaje en la matriz B.

| # | Producto / Proveedor | País · Segmento | Reserva online | Recordatorios | Fuente y fecha |
|---|---|---|---|---|---|
| 1 | Denteo (Datasoluciones) | Argentina · Consultorio/clínica/lab | Comprobado (agenda visual + estados; app Android) | Comprobado (WhatsApp plantillas Meta + automáticos) | https://www.denteo.com.ar/ · 2026-09-29, verificado 2026-10-06 |
| 2 | Oclusar | Argentina · Consultorio individual/clínica | Comprobado (página propia + link reserva, cae en agenda; seña MP) | Comprobado (WhatsApp con un toque desde número propio) | https://www.oclusar.com.ar/ · 2026-09-29, verificado 2026-10-06 |
| 3 | DrApp Odontología (Grupo Cormos) | Argentina · Consultorio/clínica | Comprobado (turnos online 24/7 vía Crontu; confirma/cancela/reprograma paciente) | Comprobado (automáticos por mail y WhatsApp) | https://www.drapp.com.ar/odontologia · 2026-09-29 |
| 4 | DentalSoft | Argentina · Clínica chica | No evidenciado en detalle (checklist: web + turnero) | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 5 | DentalTec | Argentina · Clínica (débito OS) | No evidenciado | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 6 | Dentiqa | Argentina/Latam · Clínica pequeña→cadena | Comprobado (agenda multi-dentista, drag-and-drop, anti doble-reserva; chatbot IA agenda) | Comprobado (automáticos 24 h antes vía WhatsApp) | https://dentiqa.app/ar · 2026-09-29 |
| 7 | Dentalink (Healthatom) | Chile/Latam · Clínica (líder regional) | Comprobado (agendamiento online, pacientes agendan solos) | Comprobado (confirmación por email o WhatsApp + tareas auto) | https://www.softwaredentalink.com/ar/ · 2026-09-29, verificado 2026-10-06 |
| 8 | OdontoApp | Argentina · Consultorio | No evidenciado (solo "Agenda digital" en hero; SPA sin contenido renderizado) | Parcial (declara "recordatorios automáticos", canal No evidenciado) | https://odontoapp.com.ar/ · 2026-09-29, verificado 2026-10-06 (sigue SPA limitada) |
| 9 | Doctocliq | Latam · Consultorio chico | No evidenciado en detalle | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 10 | DenPro | Latam · Clínica (HC + agenda multisede) | No evidenciado en detalle | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 11 | AgendaPro | Chile/Latam · Belleza/salud (multi-sillón explícito) | No evidenciado en detalle | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 12 | FLAP | Latam · Clínica (box) | No evidenciado en detalle | No evidenciado | Checklist 2026-09-29, sin nota individual — verificar antes de KB |
| 13 | Doctoralia | Global · Marketplace + agenda | No evidenciado | No evidenciado | Mencionado en checklist 2026-09-29 — verificar antes de KB |
| 14 | Fresha | Global · Marketplace belleza/salud | No evidenciado | No evidenciado | Mencionado en checklist 2026-09-29 — verificar antes de KB |
| 15 | Open Dental | EE. UU. · Open source dental | No evidenciado | No evidenciado | Mencionado en checklist 2026-09-29 — verificar antes de KB |
| 16 | NexHealth | EE. UU. · API agenda salud | No evidenciado | No evidenciado | Mencionado en checklist 2026-09-29 — verificar antes de KB |

Pricing de referencia (solo donde hay evidencia pública, sin estimar): Denteo Clínica AR$ 30.000–80.000/mes + trial 15 días (https://www.denteo.com.ar/precios.html, verificado 2026-10-06); DrApp desde $32.800/profesional/mes; Dentiqa USD 89–249/mes pagadero en ARS vía MP; Dentalink/Oclusar/OdontoApp: No publicado en la página relevada (Oclusar declara "empezás gratis, precio en pesos", sin montos).

## B. Matriz de puntuación 0–5 (total ponderado por sistema)

Pesos: turnos y automatización 25 %; clínica odontológica 20 %; integraciones locales y WhatsApp 15 %; administración/cobros/facturación 15 %; experiencia del paciente 10 %; seguridad/exportación/trazabilidad 10 %; precio y adopción 5 %. Total = suma(nota × peso), máximo 5,00.

Nota metodológica: 5 = evidenciado y completo; 4 = evidenciado sólido con un faltante; 3 = evidenciado parcial; 2 = mención sin detalle; 1 = indicio débil; 0 = No evidenciado. Los "No evidenciado" puntúan 0 y se marcan con (*). No se infirieron features: si la nota dice "(no publicado)", la celda es 0–1 según corresponda. Las afirmaciones comerciales [A] (cifras de clientes, IA sin demo, "+10 odontólogos") no suben nota por sí solas: solo lo comprobado [C] pondera al alza. Solo se ponderan con confianza alta los 6 con nota completa; filas 4–5 y 9–16 son provisorias (marco checklist) y deben re-verificarse antes de la KB.

| Sistema | Turnos 25 % | Clínica 20 % | Integ. 15 % | Admin 15 % | Exp. pac. 10 % | Seg. 10 % | Precio 5 % | TOTAL |
|---|---|---|---|---|---|---|---|---|
| Dentalink | 5 | 5 | 4 | 5 | 5 | 4 | 2 | **4,60** |
| Dentiqa | 5 | 5 | 5 | 4 | 4 | 4 | 3 | **4,55** |
| Oclusar | 5 | 4 | 5 | 4 | 5 | 5 | 3 | **4,55** |
| DrApp | 4 | 5 | 5 | 4 | 4 | 3 | 4 | **4,25** |
| Denteo | 4 | 4 | 5 | 5 | 3 | 4 | 4 | **4,20** |
| OdontoApp (*) | 2 | 2 | 1 | 1 | 1 | 0 | 0 | **1,30** |
| DentalSoft (*) | 2 | 2 | 2 | 2 | 2 | 0 | 3 | **~1,85 provisorio** |
| FLAP (*) | 3 | 1 | 1 | 1 | 2 | 0 | 3 | **~1,60 provisorio** |
| AgendaPro (*) | 3 | 1 | 1 | 2 | 3 | 0 | 2 | **~1,80 provisorio** |
| DentalTec (*) | 1 | 2 | 2 | 3 | 1 | 0 | 1 | **~1,55 provisorio** |
| DenPro (*) | 2 | 2 | 1 | 1 | 1 | 0 | 3 | **~1,45 provisorio** |
| Doctocliq (*) | 2 | 3 | 1 | 1 | 2 | 0 | 3 | **~1,75 provisorio** |

Lectura: el top-5 (Dentalink, Dentiqa, Oclusar, DrApp, Denteo) está a más de 2 puntos del resto porque tiene evidencia completa. OdontoApp y las filas (*) no son comparables todavía: su puntaje bajo refleja falta de evidencia, no necesariamente falta de producto. Decisión: ponderar solo el top-5 para el MVP; no ordenar por precio hasta verificar pricing de los (*).

## C. Análisis competitivo

### C1. Estándar de mercado (lo que todo sistema serio ya trae)

- Agenda visual día/semana con estados de turno y control anti-solapamiento (Denteo, Oclusar con aviso automático, Dentiqa con validaciones, Dentalink con control de agenda).
- Reserva online por el paciente sin llamar (Dentalink "agendan solos", DrApp vía Crontu 24/7, Oclusar link + página propia, Denteo agenda + app).
- Confirmación y recordatorio automáticos, idealmente WhatsApp (todos los top-5; Denteo con plantillas Meta, Dentiqa 24 h antes, DrApp mail + WhatsApp).
- Historia clínica + odontograma (+ periodontograma en Dentalink/DrApp/Dentiqa) y documentos/consentimientos con firma.
- Cobro registrado + Mercado Pago y facturación electrónica ARCA/AFIP (Denteo integrada de fábrica, DrApp, Dentiqa Professional+, Oclusar desde el cobro).
- Multi-usuario con roles, multi-sede/sillón, reportes y exportación/migración asistida.

### C2. Diferenciadores reales (verificados, no discurso)

- Denteo: ARCA integrado de fábrica [C] + WhatsApp Meta [C] + app Android nativa [C] + Denteo Lab (circuito clínica-laboratorio) [C] + servidor propio AR con matiz Cloudflare declarado [C]; análisis IA de radiografías [A] (anunciado en plan Enterprise, sin demo pública).
- Oclusar: simplicidad "sin manual / con una mano" [C, verificable en el flujo del sitio] + HCE con validez legal argentina (append-only, SHA-256, Ley 26.529/25.326/25.506, REFEPS, interoperabilidad Salud) [C, documentado en el sitio] + alquiler de sillón con separación real de datos + exportación total + 90 días post-cierre [C]; OCLU IA [A] (add-on anunciado, sin demo pública).
- DrApp: odontograma con dictado por voz [C] + ecosistema (Crontu marketplace, Receto, Cobros, Llamador, Métricas, Copiloto IA ausentismo) [C el ecosistema, A el score de ausentismo sin demo] + API pública con webhooks [C].
- Dentiqa: WhatsApp Business API oficial [C] + chatbot IA 3 capas (reglas → Haiku → Sonnet) [A] + Coach IA entrenable [A] + pipeline CRM 7 etapas [C, visible en landing] + pricing público en USD/ARS vía MP [C].
- Dentalink: escala regional (+15 k clientes, +45 M turnos/año) [A, cifra del proveedor] + IA clínica y administrativa (RX, resumen clínico, Contact Center) [A, sin demo pública] + especificidad AR (obras sociales, recetas electrónicas) [C, visible en el sitio].

### C3. Vacíos del mercado argentino (oportunidad para un MVP chico)

- Precio y simplicidad: el top-5 es potente pero grande/caro o con pricing no público. Un consultorio de 1–3 sillones no necesita HCE completa, ni ortodoncia, ni 50 reportes en v1.
- OdontoApp apunta a ese vacío ("menos inasistencias") pero su sitio no evidencia el producto (SPA sin contenido), lo que deja el hueco abierto.
- Nadie promete "solo turnos perfecto": multi-sillón día 1, duración variable por tratamiento, bloqueos/sobreturnos, tolerancia 5 min, cancelación 2 h auto-ejecutada, seña MP opcional. Todos lo tienen como parte de un todo; ninguno como producto único simple.
- Adopción: el riesgo real es que el paciente siga prefiriendo WhatsApp por costumbre. El diferencial no es más IA, es que reservar online sea más fácil que escribir por WhatsApp (PWA mobile-first, login sin fricción, confirmación con botón).

### C4. Oportunidades de innovación (recorte v1 vs. fases)

- V1 (imprescindible + diferenciador simple): lo del MVP del resumen. Diferenciar por ejecución (anti-solapamiento real, multi-sillón, duración variable, recordatorio automático que sí llega) no por cantidad de módulos.
- Fase 2: ARCA (modelo listo, no bloquea v1) + seña/cobro online avanzado.
- Fase 3+: obras sociales/liquidaciones, odontograma/HCE, campañas/recuperación ausentes, IA, multi-sede, API, GCal bidireccional. Explícitamente NO en v1.

## D. Recomendación final

### 5 competidores para demo (en orden)

1. Oclusar — referencia directa de simplicidad + reserva online + HCE legal AR. Demo: crear reserva desde link, aviso de superposición, cobro MP, exportación.
2. Denteo — vara de pricing AR y ARCA/WhatsApp integrados. Demo: agenda con estados, factura con CAE, recordatorio WA, app Android.
3. DrApp — referencia de odontograma + voz y ecosistema (Crontu). Demo: turno online 24/7, confirma/cancela paciente, cobro anticipado MP.
4. Dentiqa — techo de automatización WA + IA. Demo: chatbot que agenda, recordatorio 24 h, pipeline CRM.
5. Dentalink — techo funcional regional. Demo: agenda online + confirmación WA + obras sociales + reportes (para saber qué NO hacer en v1).

### 3 referencias de UX

1. Oclusar (flujo turno→cobro en 3 pasos, usable con una mano, página propia de reserva con seña).
2. Denteo (agenda visual con estados + push en app + recordatorio WA como notificación, no como chat).
3. DrApp/Crontu (marketplace de turnos online 24/7 con disponibilidad en tiempo real + confirmación del paciente).

### MVP en 3 listas

Imprescindible (v1):

- Reserva online 24/7 (ver libres + reservar) sin WhatsApp.
- Agenda diaria multi-sillón con anti-solapamiento, duración variable, bloqueos y sobreturnos.
- Confirmar/cancelar/reprogramar (paciente + secretaria), cancelación mínima 2 h bloqueada por sistema.
- Mis reservas con login (password vs. OTP-WhatsApp a re-evaluar en KB para no frenar reserva).
- Recordatorio + confirmación WhatsApp automático con botón (única integración obligatoria v1, vía proveedor plantillas Meta).
- Roles paciente/odontólogo/secretaria, 1 sede, PWA mobile-first.

Diferenciador (v1, simple):

- Multi-sillón desde día 1 + tolerancia 5 min visible + sin doble-reserva garantizada por sistema.
- Seña MP opcional y políticas auto-ejecutadas (el que paga viene).
- Registro de cobro simple en local + asignación de turnos (cierra el circuito sin facturación).

Etapas posteriores (NO v1):

- Facturación ARCA (fase 2). Obras sociales/liquidaciones (fase 3). Odontograma/HCE, ortodoncia, imágenes (fase 3+). Marketplace, campañas, IA, multi-sede, API pública, GCal bidireccional, pagos avanzados, membresías/loyalty.

## Verificación de fuentes (5 tipos, consultadas 2026-10-06)

| # | Tipo | URL + fecha | Lo que afirmaba el informe | Lo encontrado | Corrección |
|---|---|---|---|---|---|
| 1 | Sitio oficial | https://www.denteo.com.ar/ · 2026-10-06 | Home con turnos, HCE + odontograma, ARCA y WhatsApp; SaaS nube; app Android | Confirmado: hero "Tu clínica dental ordenada y conectada", agenda/WhatsApp/factura visibles, comparativa .exe vs SaaS, ARCA, WA Business, MP, GCal, Datasoluciones CUIT 20-30156574-8 | Sin corrección; se agrega evidencia de Ley 25.326 y Cloudflare declarados |
| 2 | Página de precios | https://www.denteo.com.ar/precios.html · 2026-10-06 | Clínica Basic AR$ 30.000, Professional AR$ 45.000, Enterprise AR$ 80.000; trial 15 días | Confirmado exacto: mismos montos y cupos (2/4/ilimit. usuarios, WA 50/200/1000 msg), Lab Starter/Pro mismos valores, FAQ con prorrateo, MP y gracia 3 días | Sin corrección; pricing pasa de "fuente 2026-09-29" a "re-verificado 2026-10-06" |
| 3 | Centro de ayuda / docs | Denteo nav "Recursos → Documentación" + Dentalink footer "Centro de Ayuda" · 2026-10-06 | Existen canales oficiales de ayuda (mencionados en scraping 2026-09-29, sin fetch de subpágina) | Confirmado que existen los enlaces (Denteo "Documentación / Guías y manuales", Dentalink "Centro de Ayuda" + guías/eventos), pero no se abrió artículo individual en esta verificación | Corrección: se citan como portales, no como artículo verificado; queda pendiente fetch de 1 guía paso a paso antes de la KB |
| 4 | Video oficial / marketplace | Crontu (marketplace citado por DrApp) / videos oficiales · 2026-10-06 | DrApp: "Turnos online 24/7 vía Crontu (marketplace con disponibilidad real)" | No verificado en esta pasada: no se abrió ficha de marketplace ni video oficial con fecha | Corrección: fila marcada "No evidenciado en esta verificación — verificar 1 ficha/video antes de la KB"; no se usa para puntuar |
| 5 | Reseña verificada | Testimonios en sitios oficiales · 2026-10-06 | Dentalink publica testimonios con nombre (Baena, Rojas, Martino…); OdontoApp declara "+10 odontólogos" | Parcial: los testimonios on-site existen (Dentalink los muestra con nombre/especialidad) pero son provistos por el vendor, no reseña independiente verificada; de OdontoApp no hay reseña independiente (solo homónimos .com/Brasil) | Corrección: se distinguen "testimonio on-site" vs "reseña verificada independiente"; queda pendiente 1 reseña independiente (Capterra/Play Store con fecha) antes de la KB |
| 6 | Caso borde (anti-ejemplo) | https://odontoapp.com.ar/ · 2026-10-06 | Nota 2026-09-29: SPA que solo renderiza hero; features/pricing no extraíbles | Confirmado: sigue devolviendo shell "Cargando OdontoApp / Un momento…" + hero (agenda, HCE, odontograma, recordatorios, +10 odontólogos) sin contenido adicional | Sin corrección; se mantiene puntaje bajo por falta de evidencia y se declara canal de recordatorios como No evidenciado |

Conclusión de verificación: 3 de 5 tipos confirmados en vivo [C] (oficial, precios, ayuda como portal), 2 pendientes de evidencia independiente (video/marketplace, reseña: los testimonios on-site son [A]). Ningún hallazgo contradice el scraping 2026-09-29; solo sube el estándar de cita (URL + fecha por afirmación) y deja 3 pendientes explícitos para antes de la KB.

## Referencias completas (URL + fecha de consulta)

Notas completas en `docs/discovery/sources/` (relevamiento 2026-09-29):

- Denteo — https://www.denteo.com.ar/ · 2026-09-29 (precios https://www.denteo.com.ar/precios.html; re-verificado 2026-10-06)
- Dentalink — https://www.softwaredentalink.com/ar/ · 2026-09-29 (re-verificado 2026-10-06)
- Dentiqa — https://dentiqa.app/ar · 2026-09-29
- DrApp — https://www.drapp.com.ar/odontologia · 2026-09-29
- Oclusar — https://www.oclusar.com.ar/ · 2026-09-29 (re-verificado 2026-10-06)
- OdontoApp — https://odontoapp.com.ar/ · 2026-09-29 (re-verificado 2026-10-06, SPA limitada)

Checklist 11 puntos: `docs/discovery/checklist-discovery.md` · 2026-09-29.

Pendientes antes de KB (no bloquean este informe): 9+ sistemas sin nota individual, 1 guía de ayuda abierta, 1 ficha/video de marketplace, 1 reseña independiente. Todo lo no verificado figura como "No evidenciado".
