# Proposal: c-23-frontend-coordinacion

## Problema / Oportunidad

El sistema tiene todo el backend de coordinación implementado (equipos docentes, avisos, tareas internas, encuentros, coloquios, guardias, programas y fechas académicas) pero carece de la interfaz frontend que permita a los roles COORDINADOR y ADMIN gestionar estas funcionalidades. Sin este frontend, los usuarios coordinadores no pueden operar el sistema más allá de lo que ya tienen disponible en la vista de comisiones y monitores.

## Solución Propuesta

Implementar los módulos frontend para las funcionalidades de coordinación y administración académica, siguiendo la misma arquitectura feature-based de C-22: TanStack Query para fetching, React Hook Form + Zod para formularios, y Tailwind CSS para estilos. Cada módulo se implementa como un feature module independiente dentro de `frontend/src/features/`.

## Alcance

- [ ] Incluir:
  - Módulo `equipos-docentes`: mis equipos (vista docente), gestión de asignaciones (coordinación), asignación masiva, clonar equipo, modificar vigencia, exportar equipo
  - Módulo `avisos`: ABM completo de avisos con alcance, severidad, vigencia, roles destino, acknowledgment tracking
  - Módulo `tareas`: vista de mis tareas, asignar tarea, administración global (coordinación), workflow de estados + comentarios
  - Módulo `encuentros-admin`: vista transversal de todos los encuentros del tenant
  - Módulo `coloquios`: panel de métricas, convocatorias, importar alumnos, listado de convocatorias, administración global
  - Módulo `guardias`: registro y consulta de guardias
  - Módulo `programas`: subir y asociar programas por materia/carrera/cohorte
  - Módulo `fechas-academicas`: gestión de fechas de evaluaciones (parciales, TP, coloquios)
  - Módulo `monitores`: vista transversal F2.7 (monitor general de actividades) y F2.9 (monitor de seguimiento para coordinación/admin con filtro de rango de fechas)
  - Setup de cuatrimestre FL-03: flujo guiado para inicio de período
  - Sidebar / menú de navegación para features de coordinación
- [ ] Excluir:
  - Backend: no se tocan modelos, servicios, repositorios ni endpoints existentes
  - Módulo de liquidaciones (C-24)
  - Módulo de administración de usuarios del tenant (C-24)
  - Panel de auditoría y métricas (ya implementado en backend, frontend va en C-24)

## Impacto

- **Frontend**: 8 nuevos feature modules + mejoras al módulo monitores existente + nuevo menú de navegación
- **Backend**: Sin cambios — todos los endpoints necesarios ya existen (C-08, C-13, C-14, C-15, C-16, C-17)
- **Riesgo**: Duplicación de lógica si no se comparten hooks/services entre módulos
  - **Mitigación**: Identificar patrones comunes (tablas filtrables, formularios de selección materia/cohorte) y crear componentes compartidos en `frontend/src/shared/components/`
