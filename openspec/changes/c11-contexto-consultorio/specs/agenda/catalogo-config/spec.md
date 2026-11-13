# Spec Delta

> Spec canónico: `openspec/specs/agenda/catalogo-config/spec.md`. Este archivo es un delta del change suelto `c11-contexto-consultorio`; la fuente de verdad vigente está en la ruta indicada.

## ADDED Requirements

### Requirement: Contexto administrativo de consultorio único
La API SHALL exponer a secretaria autenticada el identificador y nombre del único consultorio activo de una instalación de sede única. Si hay cero o más de uno SHALL indicar contexto no disponible sin elegir uno. Pacientes y odontólogos SHALL recibir 403 y anónimos 401.

#### Scenario: Único consultorio activo
- **WHEN** una secretaria solicita el contexto y existe exactamente un consultorio activo
- **THEN** recibe su identificador y nombre para crear sillones, incluso si todavía no existen sillones

#### Scenario: Contexto ausente o ambiguo
- **WHEN** no existen consultorios activos o existen dos o más
- **THEN** no se devuelve ningún identificador utilizable ni se crea o modifica un consultorio

#### Scenario: Acceso no autorizado
- **WHEN** un anónimo, paciente u odontólogo solicita contexto administrativo
- **THEN** recibe 401 o 403 según corresponda sin datos del consultorio
