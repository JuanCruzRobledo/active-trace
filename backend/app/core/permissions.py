"""Permissions catalog — all domain permissions as constants.
Filled by C-04 (rbac-permisos-finos).
"""

# ===== Authentication & Profile =====
PERM_VER_ESTADO_ACADEMICO = "ver_estado_academico"
PERM_RESERVAR_EVALUACION = "reservar_evaluacion"
PERM_CONFIRMAR_AVISOS = "confirmar_avisos"

# ===== Grades =====
PERM_CALIFICACIONES_IMPORTAR = "calificaciones:importar"

# ===== Students at risk =====
PERM_ATRASADOS_VER = "atrasados:ver"
PERM_ENTREGAS_SIN_CORREGIR = "entregas_sin_corregir"

# ===== Communications =====
PERM_COMUNICACION_ENVIAR = "comunicacion:enviar"
PERM_COMUNICACION_APROBAR = "comunicacion:aprobar"

# ===== Encuentros & Guardias =====
PERM_ENCUENTROS_GESTIONAR = "encuentros:gestionar"
PERM_GUARDIAS_REGISTRAR = "guardias:registrar"

# ===== Tasks =====
PERM_TAREAS_GESTIONAR = "tareas:gestionar"

# ===== Avisos =====
PERM_AVISOS_PUBLICAR = "avisos:publicar"

# ===== Equipos Docentes =====
PERM_EQUIPOS_ASIGNAR = "equipos:asignar"

# ===== Academic Structure =====
PERM_ESTRUCTURA_GESTIONAR = "estructura:gestionar"

# ===== Users =====
PERM_USUARIOS_GESTIONAR = "usuarios:gestionar"

# ===== Audit =====
PERM_AUDITORIA_VER = "auditoria:ver"
PERM_IMPERSONACION_USAR = "impersonacion:usar"

# ===== Payroll & Liquidations =====
PERM_GRILLA_SALARIAL_OPERAR = "grilla_salarial:operar"
PERM_LIQUIDACIONES_CALCULAR = "liquidaciones:calcular"
PERM_LIQUIDACIONES_CERRAR = "liquidaciones:cerrar"
PERM_LIQUIDACIONES_EXPORTAR = "liquidaciones:exportar"
PERM_LIQUIDACIONES_VER = "liquidaciones:ver"
PERM_FACTURAS_GESTIONAR = "facturas:gestionar"

# ===== Tenant Config =====
PERM_TENANT_CONFIGURAR = "tenant:configurar"

# ===== Catalog for seed =====
PERMISOS_CATALOGO = [
    {"codigo": PERM_VER_ESTADO_ACADEMICO, "descripcion": "Ver estado académico propio"},
    {"codigo": PERM_RESERVAR_EVALUACION, "descripcion": "Reservar instancia de evaluación"},
    {"codigo": PERM_CONFIRMAR_AVISOS, "descripcion": "Confirmar avisos (acknowledgment)"},
    {"codigo": PERM_CALIFICACIONES_IMPORTAR, "descripcion": "Importar calificaciones"},
    {"codigo": PERM_ATRASADOS_VER, "descripcion": "Ver alumnos atrasados"},
    {"codigo": PERM_ENTREGAS_SIN_CORREGIR, "descripcion": "Detectar entregas sin corregir"},
    {"codigo": PERM_COMUNICACION_ENVIAR, "descripcion": "Enviar comunicaciones a alumnos"},
    {"codigo": PERM_COMUNICACION_APROBAR, "descripcion": "Aprobar comunicaciones masivas"},
    {"codigo": PERM_ENCUENTROS_GESTIONAR, "descripcion": "Gestionar encuentros"},
    {"codigo": PERM_GUARDIAS_REGISTRAR, "descripcion": "Registrar guardias"},
    {"codigo": PERM_TAREAS_GESTIONAR, "descripcion": "Gestionar tareas internas"},
    {"codigo": PERM_AVISOS_PUBLICAR, "descripcion": "Publicar avisos"},
    {"codigo": PERM_EQUIPOS_ASIGNAR, "descripcion": "Gestionar equipos docentes"},
    {"codigo": PERM_ESTRUCTURA_GESTIONAR, "descripcion": "Gestionar estructura académica"},
    {"codigo": PERM_USUARIOS_GESTIONAR, "descripcion": "Gestionar usuarios del tenant"},
    {"codigo": PERM_AUDITORIA_VER, "descripcion": "Ver auditoría"},
    {"codigo": PERM_IMPERSONACION_USAR, "descripcion": "Usar impersonación"},
    {"codigo": PERM_GRILLA_SALARIAL_OPERAR, "descripcion": "Operar grilla salarial"},
    {"codigo": PERM_LIQUIDACIONES_CALCULAR, "descripcion": "Calcular liquidaciones"},
    {"codigo": PERM_LIQUIDACIONES_CERRAR, "descripcion": "Cerrar liquidaciones"},
    {"codigo": PERM_LIQUIDACIONES_EXPORTAR, "descripcion": "Exportar liquidaciones"},
    {"codigo": PERM_LIQUIDACIONES_VER, "descripcion": "Ver liquidaciones"},
    {"codigo": PERM_FACTURAS_GESTIONAR, "descripcion": "Gestionar facturas"},
    {"codigo": PERM_TENANT_CONFIGURAR, "descripcion": "Configurar el tenant"},
]
