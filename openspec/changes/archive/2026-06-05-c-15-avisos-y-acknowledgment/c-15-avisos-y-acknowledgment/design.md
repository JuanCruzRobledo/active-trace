## Context

Activia-trace ya cuenta con los módulos de estructura académica (C-06), usuarios y asignaciones (C-07), encuentros (C-13) y comunicaciones (C-12). El módulo de avisos completa el canal de comunicación institucional unidireccional: coordinación emite avisos segmentados, los usuarios los visualizan en su timeline y acknowledge aquellos que lo requieran. Los actores involucrados son COORDINADOR/ADMIN (gestión) y todos los roles autenticados (lectura/ack).

## Goals / Non-Goals

**Goals:**
- Modelar avisos institucionales con alcance (Global/PorMateria/PorCohorte/PorRol), severidad (Info/Advertencia/Crítico), vigencia programada y orden de presentación.
- Permitir al COORDINADOR/ADMIN crear, editar y eliminar avisos.
- Proveer timeline de avisos activos para cada usuario, segmentado por su perfil (rol, materias, cohortes).
- Soportar acknowledgment obligatorio configurable por aviso (RN-19).
- Exponer tracking de acknowledgments con agregados (NN vistos, NN% del curso).
- Eliminación segura: hard delete si nadie vio el aviso, soft delete si ya tuvo visualizaciones.

**Non-Goals:**
- Enviar notificaciones push o emails al crear un aviso (se cubre en C-12 comunicaciones).
- Avisos con destinatarios individuales (siempre son segmentados por alcance/rol).
- Acknowledgment masivo (cada usuario confirma individualmente).
- Editar un aviso después de que algún usuario lo haya visto (solo soft-delete y recrear).

## Decisions

1. **Alcances excluyentes, no acumulativos**: Un aviso tiene un único alcance (Global, PorMateria, PorCohorte o PorRol). No se combinan múltiples alcances en un mismo aviso. Si se necesita segmentación compleja, se crean múltiples avisos. Esto simplifica la query de timeline y evita ambigüedades en la lógica de visibilidad.

2. **Timeline materializado por query, no por tabla denormalizada**: La timeline se calcula consultando avisos activos en vigencia y filtrando por el perfil del usuario. No se pre-generan registros por usuario. Esto es viable porque la cantidad de avisos activos simultáneos es baja (decenas, no miles).

3. **Severidad como enum con orden explícito**: Crítico > Advertencia > Info. La timeline ordena primero por severidad descendente, luego por orden (campo numérico configurable) y luego por fecha de creación descendente. Esto da control flexible a coordinación.

4. **Eliminación híbrida**: Si un aviso nunca tuvo acknowledgments → hard delete (libera el ID). Si ya tuvo visualizaciones → soft delete (deleted_at) para conservar la integridad del tracking histórico.

5. **Agregados calculados, no almacenados**: Los contadores (total_visto, porcentaje) se derivan consultando `AcknowledgmentAviso` contra el universo de destinatarios potenciales. No se almacenan en la tabla `Aviso`. El universo se calcula según el alcance del aviso (todos los usuarios activos del tenant, o filtrados por materia/cohorte/rol).

6. **Sin entidad "audiencia" separada**: La audiencia se define mediante los campos `alcance`, `materia_id`, `cohorte_id` y `rol_destino` directamente en `Aviso`. No se necesita una tabla de relación N:M. Esto es suficiente para los alcances definidos y evita complejidad innecesaria.

7. **Permiso `avisos:ver` para lectura**: Todos los roles autenticados pueden ver el timeline y hacer acknowledge. Esto simplifica la autorización y evita tener que mapear permisos por cada rol individualmente. `avisos:gestionar` queda restringido a COORDINADOR/ADMIN.

## Risks / Trade-offs

- **[Simplicidad vs flexibilidad]** Alcances excluyentes significan que no se puede crear un aviso que sea "para PROFESORES de una materia específica" en un solo paso. → Mitigación: coordinación puede crear dos avisos (uno por materia y otro por rol) con el mismo contenido. Si esto se vuelve un caso de uso frecuente, se puede agregar alcance compuesto en el futuro.
- **[Performance]** El cálculo del universo de destinatarios para el tracking de porcentaje podría ser costoso para avisos globales en tenants con muchos usuarios. → Mitigación: el endpoint de tracking es explícito (no se calcula en cada timeline) y se puede cachear con un TTL corto.
- **[Concurrencia]** Dos usuarios podrían hacer acknowledge casi simultáneamente sobre el mismo aviso. → Mitigación: unique constraint `(aviso_id, usuario_id)` en `AcknowledgmentAviso` + manejo de `IntegrityError` en el repository.
