# Denteo

- **URL**: https://www.denteo.com.ar/
- **Fecha de investigación**: 2026-09-29

## Problema que resuelve

Gestión desordenada de consultorios, clínicas y laboratorios dentales: centraliza turnos, historia clínica, facturación electrónica ARCA/AFIP y comunicación por WhatsApp en una plataforma SaaS en la nube, sin instaladores por PC.

## Usuarios objetivo

Consultorios y clínicas odontológicas de Argentina (chicas, en crecimiento y multi-sede), laboratorios dentales, y profesionales/recepcionistas que usan agenda móvil (Android).

## Features detectadas

- Agenda visual con estados de turno y agenda diaria/semanal
- Historia clínica con odontograma
- Facturación electrónica ARCA/AFIP integrada (Tipos A, B, C, con CAE)
- WhatsApp con plantillas aprobadas por Meta y recordatorios automáticos
- Presupuestos, recetas digitales (documento de la clínica) y reportes avanzados
- Denteo Lab: trabajos con QR para subida móvil, roles y permisos granulares, portal para clínicas, facturación a clínicas, cobranzas con recordatorios
- Denteo App nativa para Android (agenda, push en tiempo real, gestión de turnos); iPhone aún no disponible
- Integraciones visibles: Google Calendar, WhatsApp Business, MercadoPago
- Backup diario, SaaS multi-tenant sin instalación, soporte en español

## Pricing

Público en https://www.denteo.com.ar/precios.html (AR$, por mes). Trial gratis 15 días sin tarjeta en ambas líneas.

Denteo Clínica:
- **Free Trial**: Gratis 15 días — hasta 2 usuarios, 50 pacientes, 25 facturas, WhatsApp 50 mensajes en la prueba, 1 GB
- **Basic**: AR$ 30.000/mes — hasta 2 usuarios, 300 pacientes, 300 facturas, WhatsApp 50 mensajes/mes, 1 GB
- **Professional** (más elegido): AR$ 45.000/mes — hasta 4 usuarios, 1.500 pacientes/facturas, WhatsApp 200 mensajes/mes, recetas digitales, reportes avanzados, 5 GB
- **Enterprise**: AR$ 80.000/mes — usuarios/pacientes/facturas ilimitados, WhatsApp 1.000 mensajes/mes, análisis con IA (radiografías y cefalometría), almacenamiento ilimitado

Denteo Lab:
- **Free Trial**: Gratis 15 días — 1 técnico, 10 trabajos/mes
- **Lab Starter**: AR$ 30.000/mes — hasta 2 técnicos, 60 trabajos/mes
- **Lab Pro** (más elegido): AR$ 45.000/mes — hasta 5 técnicos, 200 trabajos/mes, cobranzas con recordatorios, reportes PDF
- **Lab Enterprise**: A medida / cotización personalizada — técnicos y trabajos ilimitados, onboarding asistido, SLA <2h

Pagos vía MercadoPago (manual o débito automático); cambio de plan sin prorrateo; migración desde Excel/Bilog/Eyon/Easy Dental ofrecida sin costo.

## Posicionamiento

"Tu clínica dental ordenada y conectada" / "Una plataforma. Tres herramientas. Cero fricción." — Se presenta como plataforma moderna argentina en la nube frente al software tradicional con instalador .exe; "Precios simples y honestos", "Hecho en Argentina".

## Diferenciadores

Según su propio discurso: SaaS multi-tenant en la nube con actualizaciones automáticas vs. instalador .exe; ARCA integrado de fábrica (no módulo extra); WhatsApp con plantillas Meta aprobadas; app móvil nativa Android incluida; Denteo Lab del mismo equipo (clínica + laboratorio + paciente en un circuito); servidor propio en Argentina para base/historia clínica bajo Ley 25.326; prueba gratis 15 días sin tarjeta y migración asistida.

## Notas del investigador

- Fetch de la home (2026-09-29) exitoso vía WebFetch; pricing complementado con fetch puntual de /precios.html vinculada desde la home (no crawling masivo). Campos completos sin necesidad de inferir.
- Matiz de datos declarado por ellos mismos en FAQ: base/historia clínica en servidor propio en Argentina, pero imágenes/adjuntos/backups cifrados en Cloudflare R2 fuera del país y tráfico vía red Cloudflare (Ley 25.326 art. 12).
- Empresa detrás: Datasoluciones · Servicios Tecnológicos, Reconquista, Santa Fe, CUIT 20-30156574-8.
- Relevante para turnos-odontologia: competidor directo local con cobertura turnos + historia + facturación + WhatsApp; el pricing AR$ y la integración ARCA/MercadoPago son la vara a comparar en la Q&A de Discovery.
