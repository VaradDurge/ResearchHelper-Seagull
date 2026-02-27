/**
 * # API Client
 * 
 * Centralized HTTP client for making API requests to the FastAPI backend.
 */
import axios, { AxiosInstance, AxiosError } from "axios";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 30000, // 30 seconds
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (typeof window !== "undefined") {
          const token = localStorage.getItem("auth_token");
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
          const workspaceId = localStorage.getItem("active_workspace_id");
          if (workspaceId) {
            config.headers["X-Workspace-Id"] = workspaceId;
          }
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // Handle errors
        if (error.response) {
          // Server responded with error
          const message = (error.response.data as any)?.detail || error.message;
          console.error("API Error:", message);
        } else if (error.request) {
          // Request made but no response
          console.error("Network Error:", error.message);
        } else {
          // Something else happened
          console.error("Error:", error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  get<T>(url: string, config?: any) {
    return this.client.get<T>(url, config);
  }

  post<T>(url: string, data?: any, config?: any) {
    return this.client.post<T>(url, data, config);
  }

  put<T>(url: string, data?: any, config?: any) {
    return this.client.put<T>(url, data, config);
  }

  delete<T>(url: string, config?: any) {
    return this.client.delete<T>(url, config);
  }
}

export const apiClient = new ApiClient();
