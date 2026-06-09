import { useState } from "react";
import { SeguimientoView } from "@/features/monitores/components/SeguimientoView";
import { GeneralView } from "@/features/monitores/components/GeneralView";

type Tab = "general" | "seguimiento";

export function MonitoresPage() {
  const [tab, set_tab] = useState<Tab>("seguimiento");

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 border-b border-gray-200">
        <button
          type="button"
          onClick={() => set_tab("seguimiento")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            tab === "seguimiento"
              ? "border-b-2 border-brand-600 text-brand-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Seguimiento
        </button>
        <button
          type="button"
          onClick={() => set_tab("general")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            tab === "general"
              ? "border-b-2 border-brand-600 text-brand-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          General
        </button>
      </div>

      {tab === "seguimiento" ? <SeguimientoView /> : <GeneralView />}
    </div>
  );
}
