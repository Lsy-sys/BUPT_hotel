/**
 * HTTP 请求封装
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import { API_BASE_URL } from '../config';

// 创建 axios 实例
const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等
    return config;
  },
  (error) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse<any>) => {
    const { data } = response;

    // 后端多数直接返回业务对象或 { message: xxx } / { error: xxx }
    if (data && typeof data === 'object') {
      if ('error' in data) {
        return Promise.reject(new Error((data as { error?: string }).error || '请求失败'));
      }
      if ('code' in data && (data as { code?: number }).code !== 200) {
        const payload = data as { message?: string };
        return Promise.reject(new Error(payload.message || '请求失败'));
      }
      // 如果包含 data 字段，返回内部 data，否则返回原始对象
      if ('data' in data) {
        return (data as { data: any }).data;
      }
    }
    return data;
  },
  (error) => {
    console.error('响应错误:', error);

    let message = '请求失败';
    if (error.response) {
      const respData = error.response.data || {};
      if (typeof respData === 'object' && 'error' in respData) {
        message = respData.error;
      } else {
        switch (error.response.status) {
          case 400:
            message = '请求参数错误';
            break;
          case 404:
            message = '请求的资源不存在';
            break;
          case 500:
            message = '服务器内部错误';
            break;
          default:
            message = respData.message || '请求失败';
        }
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      message = '网络连接失败，请检查后端服务是否启动';
    }

    return Promise.reject(new Error(message));
  }
);

// 封装请求方法
export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config);
  },

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config);
  },

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config);
  },

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config);
  }
};

export default request;

