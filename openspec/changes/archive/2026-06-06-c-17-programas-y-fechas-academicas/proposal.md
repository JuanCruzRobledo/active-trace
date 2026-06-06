## Why

Coordinación académica necesita un repositorio centralizado de programas de materia (documentos oficiales por materia × carrera × cohorte) y un calendario de fechas evaluativas (parciales, TP, coloquios) que permita visualización tabular y en calendario, además de generar contenido ready para publicar en el aula virtual del LMS. Actualmente estos datos se gestionan fuera del sistema sin trazabilidad ni vista unificada. Este change implementa los módulos de **ProgramaMateria** y **FechaAcademica** para cubrir F5.3 y F5.4 del catálogo de funcionalidades.

## What Changes

- Nuevo modelo `ProgramaMateria` (documento por materia × carrera × cohorte, con título, referencia a archivo en almacenamiento y timestamp de carga).
- Nuevo modelo `FechaAcademica` (instancia evaluativa: parcial, TP, coloquio o recuperatorio — por materia × cohorte × número, con fecha y título).
- API REST `/api/programas`: subir y asociar programa oficial (upload + metadatos), listar, obtener detalle y eliminar. Guard `estructura:gestionar` (COORDINADOR, ADMIN).
- API REST `/api/fechas-academicas`: CRUD completo de fechas evaluativas, listado tabular con filtros (materia, cohorte, tipo, período), y endpoint de generación de fragmento HTML ready para LMS.
- Salida: generación de contenido formateado para el aula virtual del LMS a partir de las fechas registradas (F5.4).
- Migración Alembic con tablas `programa_materia` y `fecha_academica`.
- Auditoría con códigos `PROGRAMA_SUBIR`, `PROGRAMA_ELIMINAR`, `FECHA_ACADEMICA_CREAR`, `FECHA_ACADEMICA_MODIFICAR`, `FECHA_ACADEMICA_ELIMINAR`.

## Capabilities

### New Capabilities
- `programas-materia`: Gestión de programas oficiales de materia — upload de documento, asociación a materia × carrera × cohorte, listado y eliminación. Consultable por actores autorizados.
- `fechas-academicas`: Gestión de fechas evaluativas (parciales, TP, coloquios, recuperatorios) — CRUD por materia × cohorte × número, listado tabular + calendario, generación de contenido para LMS.

### Modified Capabilities
- *(ninguna — no se modifican capacidades existentes)*

## Impact

- **Modelos nuevos**: `ProgramaMateria`, `FechaAcademica` en `backend/app/models/`
- **Migración nueva**: tabla `programa_materia`, `fecha_academica`
- **API nueva**: `/api/programas/*`, `/api/fechas-academicas/*`
- **Permiso existente**: `estructura:gestionar` ya cubre COORDINADOR/ADMIN — se reutiliza para programas y fechas
- **Auditoría nueva**: `PROGRAMA_SUBIR`, `PROGRAMA_ELIMINAR`, `FECHA_ACADEMICA_CREAR`, `FECHA_ACADEMICA_MODIFICAR`, `FECHA_ACADEMICA_ELIMINAR`
- **Dependencia**: C-06 (estructura académica) — necesario para relación con Materia, Carrera y Cohorte
