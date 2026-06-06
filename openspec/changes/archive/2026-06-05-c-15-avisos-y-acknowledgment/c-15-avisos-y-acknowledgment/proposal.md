## Why

Coordinación y administración necesitan una herramienta centralizada para comunicar avisos institucionales a segmentos específicos de usuarios (global, por materia, por cohorte, por rol) con control de vigencia, severidad y acuse de recibo. Actualmente no existe este mecanismo — las comunicaciones urgentes se manejan por canales informales. Este change implementa el módulo de avisos para cubrir F3.5 del catálogo de funcionalidades.

## What Changes

- Nuevos modelos `Aviso` (alcance, severidad, vigencia, orden, requiere ack) y `AcknowledgmentAviso` con su migración Alembic.
- API REST para ABM de avisos: crear, editar, eliminar (hard delete si no tuvo visualizaciones, soft delete si ya se vio).
- Timeline de avisos activos para cada rol: solo avisos dentro de vigencia, ordenados por severidad descendente y luego por orden/fecha.
- Segmentación de audiencia por alcance (Global/PorMateria/PorCohorte/PorRol), materia/cohorte específica y rol destino.
- Acknowledge individual: el usuario confirma lectura y el sistema expone tracking con agregados (visto por NN% del curso).
- RBAC con permisos `avisos:gestionar` (COORDINADOR/ADMIN) y `avisos:ver` (todos los roles autenticados).
- Auditoría: `AVISO_CREAR`, `AVISO_ACK`.

## Capabilities

### New Capabilities
- `avisos`: Gestión de avisos institucionales segmentables con alcance, severidad, vigencia, orden de presentación, acknowledgment obligatorio y timeline por rol.

### Modified Capabilities
- *(ninguna — no se modifican capacidades existentes)*

## Impact

- **Modelos nuevos**: `Aviso`, `AcknowledgmentAviso` en `backend/app/models/`
- **Migración nueva**: tabla `aviso`, `acknowledgment_aviso`
- **API nueva**: `/api/avisos/*` con endpoints CRUD, timeline, acknowledge, tracking de agregados
- **Permisos nuevos**: `avisos:gestionar`, `avisos:ver` — agregar a seed de roles
- **Dependencia**: C-07 (usuarios) — necesario para relación con `Usuario`
