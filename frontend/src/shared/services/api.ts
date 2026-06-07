import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

// ---------------------------------------------------------------------------
// Token management (module-level — no React state here)
// ---------------------------------------------------------------------------

const REFRESH_TOKEN_KEY = "trace_refresh_token";

let in_memory_access_token: string | null = null;

/** Set the current access token (called by AuthProvider). */
export function set_access_token(token: string | null): void {
  in_memory_access_token = token;
}

/** Get the current access token. */
export function get_access_token(): string | null {
  return in_memory_access_token;
}

/** Persist refresh token to localStorage. */
export function set_refresh_token(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

/** Read refresh token from localStorage. */
export function get_refresh_token(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/** Clear all stored tokens. */
export function clear_tokens(): void {
  in_memory_access_token = null;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Request interceptor – attach access token
// ---------------------------------------------------------------------------

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = in_memory_access_token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Response interceptor – transparent refresh on 401
// ---------------------------------------------------------------------------

interface QueueItem {
  resolve: (value: AxiosResponse | PromiseLike<AxiosResponse>) => void;
  config: InternalAxiosRequestConfig;
}

let is_refreshing = false;
let pending_queue: QueueItem[] = [];

function process_queue(new_token: string | null): void {
  pending_queue.forEach(({ resolve, config }) => {
    if (new_token && config.headers) {
      config.headers.Authorization = `Bearer ${new_token}`;
    }
    resolve(api(config));
  });
  pending_queue = [];
}

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original_config = error.config as InternalAxiosRequestConfig | undefined;
    if (!original_config) return Promise.reject(error);

    // Only attempt refresh on 401 and if we haven't already retried
    if (error.response?.status !== 401 || original_config._retry) {
      return Promise.reject(error);
    }

    // If a refresh is already in-flight, queue this request
    if (is_refreshing) {
      return new Promise<AxiosResponse>((resolve) => {
        pending_queue.push({ resolve, config: original_config });
      });
    }

    is_refreshing = true;
    original_config._retry = true;

    try {
      const refresh_token = get_refresh_token();
      if (!refresh_token) {
        throw new Error("No refresh token available");
      }

      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token,
      });

      const new_access: string = data.access_token;
      const new_refresh: string | undefined = data.refresh_token;

      set_access_token(new_access);
      if (new_refresh) {
        set_refresh_token(new_refresh);
      }

      process_queue(new_access);

      // Replay the original request with the new token
      if (original_config.headers) {
        original_config.headers.Authorization = `Bearer ${new_access}`;
      }
      return api(original_config);
    } catch {
      // Refresh failed — clean up and redirect to login
      clear_tokens();
      process_queue(null);

      // Dispatch a custom event so AuthProvider can react
      window.dispatchEvent(new CustomEvent("auth:logout"));

      return Promise.reject(error);
    } finally {
      is_refreshing = false;
    }
  },
);

// Extend InternalAxiosRequestConfig to carry the _retry flag
declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

// ---------------------------------------------------------------------------

