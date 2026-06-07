## 1. Setup — Feature modules y routing

- [x] 1.1 Crear estructura `features/comision/` con carpetas `{components,hooks,services,pages}`
- [x] 1.2 Crear estructura `features/monitores/` con carpetas `{components,hooks,services,pages}`
- [x] 1.3 Definir rutas en `App.tsx` para `/comision`, `/comision/:materiaId/*`, y `/monitores` con `RequirePermission`
- [x] 1.4 Agregar enlaces al menú lateral (AppLayout) para las nuevas secciones

## 2. Feature: Importación de calificaciones (comision-importacion)

- [x] 2.1 Crear hook `useImportarCalificaciones` con `useMutation` para preview y confirmación
- [x] 2.2 Crear componente `ImportarPage` con formulario de archivo y preview de filas parseadas
- [x] 2.3 Agregar selección de actividades con checkboxes en el preview
- [x] 2.4 Manejar estados: loading, error, success con resumen de importación

## 3. Feature: Umbral de aprobación (comision-umbral)

- [x] 3.1 Crear hook `useUmbralMateria` con `useQuery`/`useMutation` para GET y PUT del umbral
- [x] 3.2 Crear componente `UmbralPage` con input numérico y validación de rango 0-100
- [x] 3.3 Manejar estados: carga del umbral actual, actualización exitosa, error

## 4. Feature: Alumnos atrasados (comision-atrasados)

- [x] 4.1 Crear hook `useAtrasados` con `useQuery` para GET de análisis de atrasados
- [x] 4.2 Crear componente `AtrasadosPage` con tabla de alumnos, columnas de métricas y riesgo
- [x] 4.3 Agregar filtros por nombre, actividad y rango de nota
- [x] 4.4 Manejar estado vacío "No hay alumnos atrasados"

## 5. Feature: Rankings y notas finales (comision-rankings)

- [x] 5.1 Crear hook `useRanking` con `useQuery` para GET de rankings
- [x] 5.2 Crear hook `useNotasFinales` con `useQuery` para GET de notas finales
- [x] 5.3 Crear componente `RankingsPage` con tabla de ranking y toggle a vista de notas finales
- [x] 5.4 Manejar estado vacío "Aún no hay datos de actividades aprobadas"

## 6. Feature: Reportes y exportación (comision-reportes)

- [x] 6.1 Crear hook `useReportes` con `useQuery` para GET de métricas de materia
- [x] 6.2 Crear componente `ReportesPage` con tarjetas de métricas (total alumnos, % aprobación, atrasados, etc.)
- [x] 6.3 Crear botón "Exportar entregas sin corregir" con descarga de CSV
- [x] 6.4 Manejar estado sin datos "Importe calificaciones primero"

## 7. Feature: Comunicaciones a atrasados (comision-comunicaciones)

- [x] 7.1 Crear hook `useComunicaciones` con `useQuery` para historial y `useMutation` para creación
- [x] 7.2 Crear componente `ComunicacionesPage` con historial de comunicaciones y botón "Nueva comunicación"
- [x] 7.3 Crear editor de comunicación con campos asunto, cuerpo y destinatarios seleccionables
- [x] 7.4 Crear preview de comunicación antes del envío
- [x] 7.5 Implementar polling cada 5s del estado de comunicación activa
- [x] 7.6 Mostrar progreso en tiempo real (X de Y enviados) y estado terminal

## 8. Feature: Monitor de seguimiento (monitores-seguimiento-frontend)

- [x] 8.1 Crear hook `useMonitorSeguimiento` con `useQuery` para GET de monitores con filtros
- [x] 8.2 Crear componente `MonitoresPage` con tabla filtrable y todos los filtros del spec
- [x] 8.3 Crear botón "Exportar" con descarga de CSV de datos filtrados
- [x] 8.4 Crear botón "Limpiar filtros" que restablece valores por defecto
- [x] 8.5 Manejar estado vacío "No tienes alumnos asignados actualmente"

## 9. Tests

- [x] 9.1 Test: importación (render, preview, confirmación, error)
- [x] 9.2 Test: umbral (visualizar, actualizar, validación de rango)
- [x] 9.3 Test: atrasados (tabla, filtros, estado vacío)
- [x] 9.4 Test: rankings (ranking, notas finales, estado vacío)
- [x] 9.5 Test: reportes (métricas, export CSV, estado sin datos)
- [x] 9.6 Test: comunicaciones (historial, crear, preview, envío, tracking polling)
- [x] 9.7 Test: monitores (tabla filtrable, export, limpiar filtros, estado vacío)
- [x] 9.8 Verificar que el layout y menú lateral naveguen correctamente a todas las rutas nuevas
