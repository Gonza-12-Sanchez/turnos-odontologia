# Ficha de Investigación: Integración de Skill y Servidor MCP en el Proyecto Odontológico

> **Materia:** Metodología I (Tecnicatura Universitaria en Programación - UTN)  
> **Change de aplicación:** `C-02 core-models` (Modelos del Dominio e Invariantes)  
> **Proyecto:** Sistema de Gestión y Reserva de Turnos Odontológicos (`turnos-odontologia`)

---

## 1. Contexto y Necesidad Detectada

### El problema real en la clínica odontológica
El sistema tiene como objetivo gestionar la asignación de turnos en consultorios que disponen de múltiples sillones odontológicos en paralelo. En este dominio, el fallo más grave que puede ocurrir es la **doble reserva simultánea en un mismo sillón** (*overbooking*). Si dos pacientes son citados al mismo sillón a la misma hora, el flujo clínico colapsa, afectando a profesionales y pacientes.

Comúnmente, los asistentes de Inteligencia Artificial intentan resolver esto con validaciones simples en el código de la aplicación (por ejemplo, haciendo un `SELECT` previo en Python antes de guardar). Este enfoque es peligroso: en situaciones de concurrencia (dos pacientes reservando a la vez por la web), ambas consultas ven el horario libre y ambas reservas se confirman. 

Para garantizar seguridad absoluta, la regla de negocio **RN-TU-01** exige que la restricción resida **en el motor de la base de datos PostgreSQL** mediante una restricción de exclusión física (`EXCLUDE USING GIST`), la cual rechaza matemáticamente cualquier solapamiento temporal en el mismo sillón. A esto se suman otras tres reglas críticas del proyecto:
1. **Fechas con zona horaria (`TIMESTAMPTZ`):** Evita que los turnos cambien de horario por diferencias de husos horarios entre servidores y clientes.
2. **Dinero en enteros/centavos (`INTEGER/NUMERIC`):** Prohíbe tipos flotantes (`float`) para no perder dinero por errores de redondeo en cobros y señas (RN-CO-03).
3. **Privacidad de datos sintéticos (RN-GL-02):** Prohíbe terminantemente datos reales de pacientes en pruebas y migraciones.

### ¿Por qué necesitamos una Skill y un MCP para resolverlo?
Para que el agente de IA no cometa errores humanos ni genere código inseguro, necesitamos dos complementos complementarios:
* **Una Skill propia (`turnos-core-guardian`):** Funciona como un **"inspector de aduana"**. Es un conjunto de directivas y scripts que guían al agente para que valide automáticamente el código y los modelos antes de darlos por buenos, bloqueando código con fechas sin zona horaria, dinero en flotantes o validaciones superficiales de turnos.
* **Un Servidor MCP (`PostgreSQL MCP Server`):** Funciona como un **"cable de conexión seguro"** entre la IA y la base de datos de desarrollo. Le da al agente la capacidad de consultar directamente las tablas reales creadas, inspeccionar sus restricciones físicas y verificar que la protección anti-solapamiento esté verdaderamente activa en PostgreSQL.

---

## 2. Change Elegido: C-02 (`core-models`)

En la metodología *Spec-Driven Development (SDD)* del proyecto, el trabajo se divide en *Changes* atómicos documentados en [CHANGES.md](../../CHANGES.md). 

Habiendo completado y archivado el cimiento inicial (`C-01 foundation-setup`), el siguiente paso del camino crítico es **C-02 (`core-models`)**. 
* **Alcance del Change:** Definir las tablas y modelos esenciales en SQLAlchemy 2.x (`Consultorio`, `Sillon`, `Tratamiento`, `Usuario`, `Paciente`, `Turno`, `Cobro`), configurar la migración inicial con Alembic y asentar el constraint físico de anti-solapamiento.
* **Justificación de la elección:** Es el momento fundacional del esquema de datos. Si estos modelos se crean sin las restricciones duras, los changes posteriores (disponibilidad C-05, reserva pública C-06, cobro de señas C-09) arrastrarán vulnerabilidades estructurales. La Skill y el MCP actúan de manera sinérgica aquí: **la Skill establece y audita la regla; el MCP comprueba que el motor de base de datos la cumpla en vivo.**

---

## 3. Skill Creadora y Diseño de la Skill Propia

### ¿Qué es una Skill?
Una *Skill* es una extensión de conocimiento procedural y ejecutable que se le otorga al agente. En lugar de darle instrucciones gigantescas en cada mensaje, la skill le enseña cómo realizar una tarea técnica especializada paso a paso, bajo qué condiciones activarse y con qué criterios evaluar el resultado.

### Skill Creadora: `skill-creator` (Anthropic)
* **Origen:** Repositorio oficial `anthropics/skills` (`https://github.com/anthropics/skills`).
* **Instalación:** Se instaló mediante el gestor estándar ejecutando:
  ```bash
  npx skills add https://github.com/anthropics/skills --skill skill-creator
  ```
* **Utilidad y Aporte:** Esta herramienta es un "meta-asistente" para fabricar otras skills. Aportó la estructura modular moderna recomendada por la industria:
  1. `SKILL.md`: Guía rápida y directa de activación y procedimiento (<500 líneas para no saturar la memoria de contexto).
  2. `references/`: Documentación técnica de soporte en profundidad que el agente solo lee cuando lo necesita (*progressive disclosure*).
  3. `scripts/`: Herramientas ejecutables que el agente puede correr de forma autónoma.

### Skill Propia Diseñada: `turnos-core-guardian`
Ubicada en `.agents/skills/turnos-core-guardian/`, fue concebida para proteger las reglas duras del sistema odontológico:

```
.agents/skills/turnos-core-guardian/
├── SKILL.md                          # Workflow de auditoría en 4 pasos y formato de veredicto
├── references/
│   ├── invariantes.md                # Matriz explicativa de reglas de negocio (RN-TU, RN-CO, RN-GL)
│   └── postgres-exclude.md           # Guía de implementación de EXCLUDE, GiST, btree_gist y pruebas
└── scripts/
    └── check_turnos_invariants.py    # Script en Python que analiza el código y detecta violaciones
```

* **Cuándo se activa:** Automáticamente al crear o revisar modelos de datos en SQLAlchemy, migraciones de Alembic, seeds o artefactos de diseño de turnos (C-02, C-04, C-05, C-06).
* **Entradas necesarias:** Archivos de modelos (`backend/app/models/*.py`), scripts de migración o propuestas de especificación.
* **Procedimiento:**
  1. Ejecuta el script `check_turnos_invariants.py` para analizar el código mediante AST (árbol sintáctico) sin necesidad de levantar bases de datos.
  2. Verifica que las fechas sean `TIMESTAMPTZ` (con zona horaria) y nunca `DateTime()` ingenuas.
  3. Verifica que los montos sean `INTEGER` (centavos) o `NUMERIC`, jamás `Float` ni tipo `money`.
  4. Comprueba que el modelo `Turno` declare la extensión `btree_gist` y el constraint `ExcludeConstraint`.
  5. Asegura que los datos de prueba usen dominios seguros (`@example.com`) sin identificadores reales.
* **Resultado esperado y criterio de revisión:** El agente emite un informe estructurado con veredicto binario:
  * `[VEREDICTO: OK]` si todas las reglas fueron respetadas.
  * `[VEREDICTO: BLOQUEADO]` si se detecta alguna omisión, impidiendo avanzar a la implementación hasta que el error sea subsanado.

---

## 4. Comparación de Servidores MCP y Elección Justificada

### ¿Qué es un Servidor MCP (Model Context Protocol)?
El *Model Context Protocol* (MCP) es un estándar abierto desarrollado por Anthropic que actúa como un "adaptador universal". Permite que un modelo de IA se conecte de forma controlada a herramientas y fuentes de datos externas (como el sistema de archivos, GitHub o un motor de base de datos), llamando funciones específicas (*tools*) y recibiendo respuestas en tiempo real sin salir de su entorno.

### Comparación de alternativas evaluadas

| Criterio | Servidor 1: PostgreSQL Oficial (`@modelcontextprotocol/server-postgres`) — **ELEGIDO** | Servidor 2: Context7 (Documentación Remota) |
| :--- | :--- | :--- |
| **Tipo y Propósito** | **Local.** Conector directo de inspección a la base de datos PostgreSQL del proyecto en modo seguro. | **Remoto.** Proveedor de documentación oficial y ejemplos de librerías actualizadas. |
| **Capacidades expuestas** | • `schema`: Describe tablas, columnas, tipos e índices.<br>• `query`: Ejecuta consultas SQL exclusivamente en modo `READ ONLY`. | • `search_docs`: Busca artículos y guías oficiales.<br>• `get_doc`: Recupera fragmentos de manuales técnicos. |
| **Aporte directo al Change C-02** | **Alto y comprobable en el motor:** Permite al agente ejecutar `SELECT` sobre el catálogo del sistema (`pg_constraint`), confirmar que la restricción de exclusión física existe y verificar la estructura real de las tablas. | **Informativo / Teórico:** Ayuda a consultar la sintaxis de SQLAlchemy o PostgreSQL, pero no tiene forma de comprobar si nuestro código funcionó en la base real. |
| **Permisos y Riesgos** | Transacción forzada en `READ ONLY`. No permite `INSERT`, `UPDATE`, `DELETE` ni `DROP`. Riesgo bajo si se limita el volumen de datos de prueba. | Solo lectura de documentación pública en internet. Riesgo nulo de alteración del proyecto. |
| **Costos y Licencia** | Código abierto y gratuito (licencia MIT / npm oficial de Model Context Protocol). | Gratuito con límites de cuota de consulta. |

### Justificación de la Elección
Se seleccionó **PostgreSQL MCP Server** porque aporta una capacidad única que ninguna instrucción ni documentación puede dar: **verificación viva de los invariantes en el motor de base de datos**. Mientras que la documentación (Context7) explica cómo se debería escribir el código, el MCP de Postgres le permite al agente auditar el resultado concreto y asegurar que no haya fallas de diseño en el esquema.

### Límites de Seguridad Establecidos
1. **Ambiente Aislado:** El MCP se conecta únicamente a la base de datos local efímera de desarrollo/pruebas (`turnos_test` levantada en Docker), jamás a entornos productivos.
2. **Acceso de Solo Lectura:** El servidor MCP rechaza cualquier sentencia de modificación (`INSERT`, `UPDATE`, `ALTER`, etc.). Las modificaciones del esquema solo pueden realizarse mediante migraciones formales de Alembic versionadas en código.
3. **Control de Consultas:** Se exige el uso de cláusulas `LIMIT` (entre 5 y 100 registros) y un tiempo de espera (*timeout*) de 5 segundos para evitar bloqueos del motor.
4. **Datos Sintéticos:** Toda consulta o prueba se realiza sobre los datos de muestra del consultorio ficticio definidos en `knowledge-base/04_modelo_de_datos.md`.

---

## 5. Instalación y Configuración del Servidor MCP

### Requisitos previos
* Node.js v18 o superior con `npx` disponible.
* Motor PostgreSQL 16 activo (levantado mediante `docker compose up -d db`).
* Base de datos local disponible en `postgresql://turnos:turnos@localhost:5432/turnos_test`.

### Configuración en el cliente (`opencode` / entorno del agente)
El servidor se configura en el archivo de integración del cliente (por ejemplo, en `opencode.json` o la configuración MCP correspondiente) indicando el comando ejecutable oficial de npm:

```json
{
  "mcp": {
    "postgres": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://turnos:turnos@localhost:5432/turnos_test"
      ],
      "enabled": true
    }
  }
}
```

*(Se incluye una plantilla reproducible y sin credenciales sensibles en [docs/skills-mcp/mcp-postgres.opencode.example.json](mcp-postgres.opencode.example.json)).*

### Procedimiento de comprobación y uso
1. **Comprobar la conexión:** Ejecutar en el terminal `opencode mcp list`. El estado del servidor debe figurar como `postgres connected`.
2. **Uso por parte del agente:** El usuario puede solicitar directamente:
   > *"Usa la herramienta postgres para describir las columnas y restricciones de la tabla turno"*  
   o bien:
   > *"Ejecuta mediante postgres una consulta sobre pg_constraint para verificar si existe el constraint anti-solapamiento"*.
3. El agente invoca automáticamente la herramienta interna `query` o `schema` y razona sobre los datos devueltos por el motor.

---

## 6. Archivos de la Fundación que se Actualizarán

La incorporación de estas dos herramientas no altera las decisiones de negocio previas, sino que refuerza las reglas existentes en la documentación del repositorio:

| Archivo de la Fundación | Modificación Prevista | Motivo |
| :--- | :--- | :--- |
| `.atl/skill-registry.md` | Registrar `turnos-core-guardian` con su ruta, activadores (*triggers*) y reglas compactas. | Para que el orquestador y los subagentes conozcan la existencia de la skill y sepan cuándo cargarla. |
| `AGENTS.md` / `CLAUDE.md` | Incorporar la skill en la matriz de roles y documentar el servidor MCP de Postgres como integración técnica del entorno. | Establecer formalmente que la revisión con la skill y la verificación con el MCP son pasos obligatorios para el Change C-02. |
| `README.md` | Añadir sección sobre configuración y uso del servidor MCP local para desarrollo. | Garantizar la reproducibilidad para cualquier otro integrante del equipo docente o de desarrollo. |
| `CHANGES.md` | Registrar el Change C-02 en estado preparado (con enlaces a sus artefactos de diseño y especificaciones). | Mantener el roadmap de avance del proyecto fiel a la metodología SDD. |

---

## 7. Fuentes y Repositorios Oficiales Consultados

* **Skill Creator (Anthropic):**  
  * *Repositorio oficial:* https://github.com/anthropics/skills (Consultado: 16/10/2026 y revalidado 27/10/2026).  
  * *Directorio de habilidades:* https://skills.sh/anthropics/skills.
* **Model Context Protocol (PostgreSQL Server):**  
  * *Implementación de referencia:* https://github.com/modelcontextprotocol/servers (Consultado: 16/10/2026).  
  * *Paquete oficial npm:* https://www.npmjs.com/package/@modelcontextprotocol/server-postgres (v0.6.2, modo de ejecución `READ ONLY`).
* **Documentación Oficial de PostgreSQL 16:**  
  * *Tipos de Rangos (`tstzrange`):* https://www.postgresql.org/docs/16/rangetypes.html.  
  * *Restricciones de Exclusión (`EXCLUDE USING GIST`):* https://www.postgresql.org/docs/16/sql-createtable.html.
* **Documentación Interna del Proyecto:**  
  * `knowledge-base/04_modelo_de_datos.md` (Esquema conceptual y ERD).  
  * `knowledge-base/05_reglas_de_negocio.md` (Reglas RN-TU-01, RN-CO-03, RN-GL-01 y RN-GL-02).  
  * `CHANGES.md` (Roadmap del sistema y dependencias de C-02).
