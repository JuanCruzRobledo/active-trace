import type { ReactNode } from "react";
import { useAuth } from "@/shared/hooks/useAuth";

interface RequirePermissionProps {
  /** Permission string in the format `modulo:accion`. */
  permission: string;
  children: ReactNode;
  /** Optional fallback to render instead of a generic 403. */
  fallback?: ReactNode;
}

export function RequirePermission({
  permission,
  children,
  fallback,
}: RequirePermissionProps) {
  const { permissions } = useAuth();

  if (!permissions.includes(permission)) {
    if (fallback) return <>{fallback}</>;

    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="max-w-md text-center">
          <h1 className="text-6xl font-bold text-gray-300">403</h1>
          <p className="mt-4 text-lg text-gray-600">
            No tenés permisos para acceder a esta sección.
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Si creés que esto es un error, contactá al administrador.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

