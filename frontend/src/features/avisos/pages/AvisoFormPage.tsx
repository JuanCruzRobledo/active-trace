import { useParams, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  useAvisoById,
  useCrearAviso,
  useActualizarAviso,
} from "@/features/avisos/hooks/useAvisos";
import {
  AvisoCreateSchema,
  type AvisoCreate,
} from "@/features/avisos/types/avisos";
import { AvisoFormBody } from "@/features/avisos/components/AvisoFormBody";

export function AvisoFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const avisoQuery = useAvisoById(id ?? "");
  const crearAviso = useCrearAviso();
  const actualizarAviso = useActualizarAviso();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<AvisoCreate>({
    resolver: zodResolver(AvisoCreateSchema),
    values: isEdit && avisoQuery.data
      ? {
          alcance: avisoQuery.data.alcance as AvisoCreate["alcance"],
          materia_id: avisoQuery.data.materia_id ?? undefined,
          cohorte_id: avisoQuery.data.cohorte_id ?? undefined,
          rol_destino: avisoQuery.data.rol_destino ?? undefined,
          severidad: avisoQuery.data.severidad as AvisoCreate["severidad"],
          titulo: avisoQuery.data.titulo,
          cuerpo: avisoQuery.data.cuerpo,
          inicio_en: avisoQuery.data.inicio_en,
          fin_en: avisoQuery.data.fin_en,
          orden: avisoQuery.data.orden,
          requiere_ack: avisoQuery.data.requiere_ack,
        }
      : {
          alcance: "global",
          severidad: "info",
          titulo: "",
          cuerpo: "",
          inicio_en: "",
          fin_en: "",
          orden: 0,
          requiere_ack: false,
        },
  });

  const onSubmit = async (data: AvisoCreate) => {
    if (isEdit) {
      await actualizarAviso.mutateAsync({ id: id!, data });
    } else {
      await crearAviso.mutateAsync(data);
    }
    navigate("/avisos");
  };

  if (isEdit && avisoQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  if (isEdit && avisoQuery.isError) {
    return (
      <ErrorMessage
        message={avisoQuery.error?.message ?? "Error al cargar el aviso"}
      />
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? "Editar Aviso" : "Nuevo Aviso"}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {isEdit
            ? "Actualizá los datos del aviso"
            : "Creá un nuevo aviso para comunicar a los docentes"}
        </p>
      </div>

      <AvisoFormBody
        register={register}
        errors={errors}
        watch={watch}
        isEdit={isEdit}
        isPending={isEdit ? actualizarAviso.isPending : crearAviso.isPending}
        onSubmit={handleSubmit(onSubmit)}
        onCancel={() => navigate("/avisos")}
      />
    </div>
  );
}
