# 10 — Preguntas Abiertas y Decisiones de Producto Pendientes

> **Propósito**: registrar las decisiones de diseño de producto que aún no están cerradas, ordenadas por impacto sobre el modelo de dominio. Cada ítem es una pregunta genuina que el equipo de producto debe resolver antes de (o durante) la implementación. Las decisiones ya cerradas aparecen en los archivos correspondientes de la KB y en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md); no se repiten acá. Este archivo es un tablero vivo: cuando una pregunta se cierra, se documenta la resolución en el archivo temático correspondiente y se retira de acá.

---

## Prioridad ALTA — bloqueantes para el modelo de dominio

### PA-01 — ¿Cómo se organiza el catálogo de materias y cuál es la fuente de verdad?

El sistema parece operar con (al menos) dos agrupaciones distintas de materias:

- Una lista con códigos cortos del tipo `PROG_I`, `AYSO`, etc., ligada a la estructura de carreras y cohortes.
- Otra lista con nombres descriptivos del tipo "Programación – Python", "Programación – Java", orientada al seguimiento de actividades de aprendizaje.

**Preguntas abiertas**:

- ¿Son dos catálogos independientes (uno por carrera/plan y otro por instancia de dictado) o es una sola entidad con distintas vistas?
- ¿Existe una relación formal entre ambas agrupaciones? Si un alumno tiene una calificación en "Programación – Python", ¿a qué materia del plan corresponde?
- ¿Cuál de las dos representa la materia a efectos del plan de estudios y cuál representa la instancia de cursado?
- ¿Las calificaciones viajan entre una y otra, o cada una tiene su propio registro?

**Impacto**: define si el modelo de datos necesita una entidad `Materia` (del plan) y una entidad separada `InstanciaDictado` (o `Comisión` extendida), o si alcanza con una sola.

---

### PA-07 — ¿Las cohortes pertenecen a una carrera o son transversales?

Las cohortes (ej.: "MAR-2026") pueden pertenecer a una carrera específica o ser compartidas entre varias.

**Preguntas abiertas**:

- ¿Una cohorte es exclusiva de un programa académico?
- ¿Puede un alumno estar en la misma cohorte con materias de distintas carreras?
- ¿La cohorte define el ciclo lectivo o también el plan de estudios vigente?

**Impacto**: afecta la cardinalidad entre `Cohorte`, `Carrera` y `Alumno` en el modelo de datos ([04_modelo_de_datos.md](04_modelo_de_datos.md)).

---

---

## Prioridad MEDIA — refinamiento del modelo

### PA-05 — ¿Cómo y desde dónde se crea una guardia?

El módulo de guardias muestra el listado de guardias registradas por docente, pero el flujo de creación no está especificado.

**Preguntas abiertas**:

- ¿Las guardias se crean desde el módulo de encuentros, desde un formulario dedicado, o ambos?
- ¿Quién puede crear una guardia: solo el docente que la cubre, o también el COORDINADOR en su nombre?
- ¿Requiere aprobación posterior?

---

### PA-08 — ¿Cuál es el ciclo de vida de una Tarea?

El módulo de tareas tiene un filtro de estado, pero los valores posibles del ciclo de vida no están definidos.

**Preguntas abiertas**:

- ¿Cuáles son los estados posibles de una tarea? (ej.: `abierta → en progreso → completada → archivada`)
- ¿Las transiciones son libres o tienen reglas (ej.: solo el creador puede cerrarla)?
- ¿Hay notificaciones automáticas al cambiar de estado?

---

### PA-09 — ¿Qué permite la funcionalidad de comunicación por grupos en el módulo de equipos?

Dentro del módulo de equipos docentes existe una funcionalidad de comunicación grupal cuyo alcance no está especificado.

**Preguntas abiertas**:

- ¿Es para enviar mensajes masivos al equipo docente de una comisión?
- ¿O es comunicación entre pares (docentes entre sí)?
- ¿Requiere aprobación previa como las comunicaciones hacia alumnos?

---

### PA-11 — ¿Qué es el "criterio de clasificación" en el monitor general?

El monitor general permite configurar un criterio de clasificación mediante un modal.

**Preguntas abiertas**:

- ¿Qué criterios se pueden configurar? (ej.: por porcentaje de avance, por cantidad de entregas, por calificación promedio)
- ¿La configuración es personal (por usuario) o global (por tenant)?
- ¿Afecta qué alumnos se consideran "atrasados" o es solo una vista?

---

### PA-12 — ¿Qué incluye la vista administrativa de encuentros?

El módulo de encuentros tiene una vista con permisos ampliados respecto a la vista docente estándar.

**Preguntas abiertas**:

- ¿Permite ver y editar los encuentros de todos los docentes de una comisión o de todo el tenant?
- ¿Permite crear encuentros en nombre de otro docente?
- ¿Tiene capacidad de aprobación o solo de consulta?

---

### PA-13 — ¿Qué es el contexto de agrupación de tareas?

El módulo de tareas permite filtrar por un contexto de agrupación cuya semántica no está definida.

**Preguntas abiertas**:

- ¿El contexto de agrupación es una cohorte, una materia, un equipo docente, o algún otro concepto?
- ¿Una tarea puede pertenecer a más de un contexto?

---

### PA-14 — ¿Cómo reserva un alumno una instancia de coloquio?

El sistema muestra reservas activas y cupos disponibles para instancias de evaluación, pero el flujo de reserva del alumno no está especificado.

**Preguntas abiertas**:

- ¿El alumno reserva desde dentro del sistema o desde un canal externo (ej.: Moodle, link público)?
- ¿Hay restricciones para reservar (ej.: cantidad máxima de intentos, estado de regularidad requerido)?
- ¿El alumno puede cancelar su reserva?

---

### PA-15 — ¿El módulo de corrección automática está integrado con las calificaciones?

El sistema contempla la posibilidad de integrar un módulo de corrección automática de actividades.

**Preguntas abiertas**:

- ¿Las calificaciones generadas por el corrector automático se importan al sistema directamente o requieren revisión y aprobación docente?
- ¿El corrector opera sobre entregas ya subidas al sistema o sobre entregas del LMS (Moodle)?
- ¿Cómo se audita una calificación generada automáticamente vs. una ingresada manualmente?

---

### PA-24 — ¿Las facturas se asocian a comisiones o son globales por docente?

En el módulo de facturas existe un campo de detalle con texto libre, pero no está claro si hay una asociación formal con el trabajo realizado.

**Preguntas abiertas**:

- ¿Una factura debe vincularse a una comisión específica, a un período, o puede ser un concepto genérico?
- ¿Cómo se concilia la factura con el cálculo de liquidación?
- ¿El sistema valida que el monto de la factura no supere el total liquidado?

---

## Prioridad BAJA — pulido y definición de detalles

### PA-16 — ¿Cuáles son los niveles de severidad de los avisos y qué efecto tienen?

**Preguntas abiertas**:

- ¿Los valores de severidad son un enumerado fijo (`info`, `advertencia`, `error`) o es configurable?
- ¿La severidad afecta el comportamiento del sistema (ej.: un aviso de error bloquea al alumno hasta que lo confirme)?
- ¿Hay notificaciones adicionales disparadas por severidad?

---

### PA-17 — ¿El tipo de facturación del docente afecta el cálculo de liquidación?

Algunos docentes pueden emitir comprobantes fiscales (ej.: monotributistas), lo cual puede tener implicancias en el cálculo.

**Preguntas abiertas**:

- ¿El tipo de facturación modifica algún concepto del cálculo (ej.: agrega retenciones, modifica la base)?
- ¿O es solo un atributo informativo para el módulo de FINANZAS sin impacto en la fórmula?

---

### PA-18 — ¿El CUIL del docente se calcula automáticamente o se carga manualmente?

**Preguntas abiertas**:

- ¿El sistema calcula el CUIL a partir del DNI aplicando la regla estándar (`prefijo-DNI-dígito verificador`)?
- ¿O el CUIL es un campo de carga manual sin validación automática?
- Si se calcula, ¿qué pasa cuando el CUIL real difiere del calculado (ej.: personas con CUIL de tipo empresa)?

---

### PA-19 — ¿Qué pasa con las asignaciones vigentes cuando se desactiva un docente?

**Preguntas abiertas**:

- ¿Las asignaciones vigentes se cierran automáticamente (se les pone fecha de fin) al desactivar el usuario?
- ¿O quedan en estado inconsistente hasta que el ADMIN las gestione manualmente?
- ¿El sistema emite una alerta al COORDINADOR cuando uno de sus docentes es desactivado?

---

## Decisiones ya cerradas (referencia)

Las siguientes preguntas que existían en versiones anteriores de este documento ya fueron resueltas y su resolución está documentada en los archivos correspondientes:

| Código original | Resolución | Dónde está documentado |
|-----------------|-----------|------------------------|
| PA-02 | El rol TUTOR existe formalmente en el catálogo; ver descripción de capacidades | [03_actores_y_roles.md](03_actores_y_roles.md) |
| PA-04 | Login por email + contraseña; 2FA opcional (TOTP); recuperación por token de un solo uso; alta solo administrativa en MVP | [07_flujos_principales.md](07_flujos_principales.md), [`docs/ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md) |
| PA-06 | Fórmula de liquidación: Base (por rol) + Plus (por clave × rol); ver RN-31 a RN-38 | [05_reglas_de_negocio.md](05_reglas_de_negocio.md) |
| PA-21 | Impersonación via parámetro de petición: eliminada. La impersonación legítima requiere permiso explícito, sesión diferenciada y auditoría completa | [03_actores_y_roles.md §4](03_actores_y_roles.md), [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md) |
| PA-22 | Catálogo de claves de Plus como entidad configurable por tenant (`ClavePlus`). 8 claves por defecto: PROG, BD, ING, MAT, RED, WEB, GES, IDI, PRA. Cada materia se asocia opcionalmente mediante `clave_plus_id` (nullable). Si no tiene clave asignada, no genera plus. Lo define el ADMIN del tenant en la grilla salarial. | [04_modelo_de_datos.md §E3 y §E18.5](04_modelo_de_datos.md), [05_reglas_de_negocio.md RN-33 y RN-34](05_reglas_de_negocio.md) |
| PA-23 | Se acumula N veces el plus sin tope (`3 comisiones PROG → 3 × Plus(PROG, PROFESOR)`). La lógica es la misma para PROFESOR y TUTOR. COORDINADOR y NEXO no generan plus (no dictan comisiones). | [05_reglas_de_negocio.md RN-33 y RN-34](05_reglas_de_negocio.md) |
| PA-25 | NEXO es enlace administrativo asociado a carreras/cohortes (no a comisiones). Acceso solo lectura a datos de alumnos de su cohorte. No asigna docentes ni modifica calificaciones. Tiene base salarial propia pero no genera plus. Puede coexistir con otros roles. Se visibiliza separado en liquidaciones pero suma al total (RN-36). | [03_actores_y_roles.md](03_actores_y_roles.md), [05_reglas_de_negocio.md RN-32 y RN-36](05_reglas_de_negocio.md) |

---

## Cómo cerrar estas preguntas

Para resolver las preguntas pendientes se recomienda:

1. **Una sesión de trabajo con el responsable de producto** — cubre las preguntas de dominio (PA-01, PA-22, PA-23, PA-25 son prioritarias).
2. **Revisión del modelo de datos con el equipo técnico** — para validar las entidades y relaciones de [04_modelo_de_datos.md](04_modelo_de_datos.md).
3. **Sesión de refinamiento con FINANZAS** — para cerrar PA-17, PA-18, PA-24 que afectan el módulo de liquidaciones.
4. **Cuando se cierre una pregunta**: documentar la resolución en el archivo temático correspondiente y moverla a la tabla de "Decisiones ya cerradas" de este archivo.
