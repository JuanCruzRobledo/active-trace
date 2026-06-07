export interface CarreraOption {
  id: string;
  nombre: string;
}

export interface WizardStepInfo {
  key: number;
  label: string;
}

export const STEPS: WizardStepInfo[] = [
  { key: 1, label: "Crear cohorte" },
  { key: 2, label: "Clonar equipo" },
  { key: 3, label: "Ajustar asignaciones" },
  { key: 4, label: "Cargar programas" },
  { key: 5, label: "Cargar fechas" },
  { key: 6, label: "Publicar aviso" },
  { key: 7, label: "Resumen" },
];
