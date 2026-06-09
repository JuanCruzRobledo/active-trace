import { api } from "./api";

// ---------------------------------------------------------------------------
// region: Types
// ---------------------------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

export interface Login2FARequired {
  /** Backend envía "twofa_required" (sin underscore, sin dígito 2). */
  twofa_required: boolean;
  challenge_token: string;
}

export type LoginResult = LoginResponse | Login2FARequired;

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token?: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface Verify2FARequest {
  challenge_token: string;
  code: string;
}

export interface Verify2FAResponse {
  access_token: string;
  refresh_token: string;
}

export interface Enroll2FAResponse {
  secret: string;
  qr_code: string; // base64 PNG
}

export interface Confirm2FARequest {
  code: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface UserInfo {
  id: string;
  email: string;
  nombre: string;
  roles: string[];
  permisos: string[];
  tenant_id: string;
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// region: Auth API functions
// ---------------------------------------------------------------------------

export async function login(data: LoginRequest): Promise<LoginResult> {
  const response = await api.post<LoginResult>("/auth/login", data);
  return response.data;
}

export async function refresh(data: RefreshRequest): Promise<RefreshResponse> {
  const response = await api.post<RefreshResponse>("/auth/refresh", data);
  return response.data;
}

export async function logout(data: LogoutRequest): Promise<void> {
  await api.post("/auth/logout", data);
}

export async function verify2FA(data: Verify2FARequest): Promise<Verify2FAResponse> {
  const response = await api.post<Verify2FAResponse>("/auth/2fa/verify", data);
  return response.data;
}

export async function enroll2FA(): Promise<Enroll2FAResponse> {
  const response = await api.post<Enroll2FAResponse>("/auth/2fa/enroll");
  return response.data;
}

export async function confirm2FA(data: Confirm2FARequest): Promise<void> {
  await api.post("/auth/2fa/confirm", data);
}

export async function forgotPassword(data: ForgotPasswordRequest): Promise<void> {
  await api.post("/auth/forgot", data);
}

export async function resetPassword(data: ResetPasswordRequest): Promise<void> {
  await api.post("/auth/reset", data);
}

export async function getMe(): Promise<UserInfo> {
  const response = await api.get<UserInfo>("/auth/me");
  return response.data;
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

