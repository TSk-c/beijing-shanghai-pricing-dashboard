import 'axios';

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 为 true 时不在全局拦截器里 message.error / setError（便于调用方自行回退 Mock） */
    skipErrorToast?: boolean;
  }
}
