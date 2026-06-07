import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  set_access_token,
  set_refresh_token,
  get_refresh_token,
  clear_tokens,
} from "@/shared/services/api";
import * as authService from "@/shared/services/authService";
import type { UserInfo, LoginResult } from "@/shared/services/authService";

// ---------------------------------------------------------------------------
// region: Types
// ---------------------------------------------------------------------------

export interface AuthContextType {
  /** Current authenticated user, or null. */
  user: UserInfo | null;
  /** True while the initial session restore is in progress. */
  is_loading: boolean;
  /** Convenience: !is_loading && user !== null. */
  is_authenticated: boolean;
  /** Flat list of permission strings, e.g. ["calificaciones:importar", …]. */
  permissions: string[];
  /**
   * Attempt login. Returns the raw API result so the caller can distinguish
   * between a normal login response and a 2FA-required response.
   */
  login: (email: string, password: string) => Promise<LoginResult>;
  /**
   * Complete 2FA verification and finalise the session.
   */
  complete2FA: (challenge_token: string, code: string) => Promise<void>;
  /** Log out (best-effort server revoke + local clean-up). */
  logout: () => Promise<void>;
  /**
   * Exposed so page components can directly set session after an alternative
   * auth flow (e.g. 2FA verify returns tokens).
   */
  set_session_from_tokens: (access: string, refresh: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextType | null>(null);

// ---------------------------------------------------------------------------
// region: Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, set_user] = useState<UserInfo | null>(null);
  const [is_loading, set_is_loading] = useState(true);

  // -----------------------------------------------------------------------
// region: Session restore on mount
  // -----------------------------------------------------------------------

  const restore_session = useCallback(async () => {
    const stored_refresh = get_refresh_token();
    if (!stored_refresh) {
      set_is_loading(false);
      return;
    }

    try {
      const { access_token, refresh_token } = await authService.refresh({
        refresh_token: stored_refresh,
      });
      set_access_token(access_token);
      if (refresh_token) {
        set_refresh_token(refresh_token);
      }

      const user_info = await authService.getMe();
      set_user(user_info);
    } catch {
      clear_tokens();
    } finally {
      set_is_loading(false);
    }
  }, []);

  useEffect(() => {
    restore_session();
  }, [restore_session]);

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: Listen for auth:logout events from api.ts interceptor
  // -----------------------------------------------------------------------

  useEffect(() => {
    const handle_force_logout = () => {
      set_user(null);
      clear_tokens();
    };
    window.addEventListener("auth:logout", handle_force_logout);
    return () => window.removeEventListener("auth:logout", handle_force_logout);
  }, []);

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: set_session_from_tokens
  // -----------------------------------------------------------------------

  const set_session_from_tokens = useCallback(
    async (access: string, refresh: string) => {
      set_access_token(access);
      set_refresh_token(refresh);
      const user_info = await authService.getMe();
      set_user(user_info);
    },
    [],
  );

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: login
  // -----------------------------------------------------------------------

  const login = useCallback(
    async (email: string, password: string): Promise<LoginResult> => {
      const result = await authService.login({ email, password });

      if ("access_token" in result) {
        // Normal login — set session immediately
        await set_session_from_tokens(result.access_token, result.refresh_token);
      }
      // If 2FA is required, return the result as-is — caller handles redirect
      return result;
    },
    [set_session_from_tokens],
  );

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: complete2FA
  // -----------------------------------------------------------------------

  const complete2FA = useCallback(
    async (challenge_token: string, code: string) => {
      const result = await authService.verify2FA({ challenge_token, code });
      await set_session_from_tokens(result.access_token, result.refresh_token);
    },
    [set_session_from_tokens],
  );

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: logout
  // -----------------------------------------------------------------------

  const logout = useCallback(async () => {
    try {
      const stored_refresh = get_refresh_token();
      if (stored_refresh) {
        await authService.logout({ refresh_token: stored_refresh });
      }
    } catch {
      // Best-effort — clean up locally regardless
    } finally {
      set_user(null);
      clear_tokens();
    }
  }, []);

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  const value: AuthContextType = {
    user,
    is_loading,
    is_authenticated: !!user,
    permissions: user?.permisos ?? [],
    login,
    complete2FA,
    logout,
    set_session_from_tokens,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// region: Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

