import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

export const ACCESS_TOKEN_KEY = 'softmeter_token';

const api = axios.create({
  baseURL: import.meta.env?.VITE_API_URL ?? 'http://localhost:3001',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // envia o cookie HTTPOnly de refresh token
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const response = await axios.post(
    `${api.defaults.baseURL}/api/v1/auth/refresh`,
    {},
    { withCredentials: true },
  );
  const newToken = response.data.access_token as string;
  localStorage.setItem(ACCESS_TOKEN_KEY, newToken);
  return newToken;
}

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const originalRequest = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const isAuthRoute = originalRequest?.url?.includes('/auth/');

    if (err.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthRoute) {
      originalRequest._retry = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken();
        const newToken = await refreshPromise;
        refreshPromise = null;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch {
        refreshPromise = null;
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  },
);

export default api;
