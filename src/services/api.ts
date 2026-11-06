import { Agent, Task, PaymentSummary, Transaction, ActivityLog, SystemStatus } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    throw new Error(errorDetail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Agents
  async getAgents(params?: { category?: string; search?: string; max_price?: number; sort_by?: string }): Promise<{ agents: Agent[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.search) query.append('search', params.search);
    if (params?.max_price) query.append('max_price', params.max_price.toString());
    if (params?.sort_by) query.append('sort_by', params.sort_by);
    const res = await fetch(`${API_BASE}/api/agents?${query.toString()}`);
    return handleResponse(res);
  },

  async getAgent(id: string): Promise<Agent> {
    const res = await fetch(`${API_BASE}/api/agents/${id}`);
    return handleResponse(res);
  },

  async getCategories(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/api/agents/categories`);
    return handleResponse(res);
  },

  // Tasks
  async createTask(data: { title: string; description: string; budget: number; currency?: string; constraints?: string }): Promise<Task> {
    const res = await fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getTasks(): Promise<{ tasks: Task[]; total: number }> {
    const res = await fetch(`${API_BASE}/api/tasks`);
    return handleResponse(res);
  },

  async getTask(id: string): Promise<Task> {
    const res = await fetch(`${API_BASE}/api/tasks/${id}`);
    return handleResponse(res);
  },

  async advanceTask(id: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/tasks/${id}/advance`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async cancelTask(id: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/tasks/${id}/cancel`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  // Workflow
  async getTaskProgress(taskId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}/progress`);
    return handleResponse(res);
  },

  async getTaskActivity(taskId: string): Promise<ActivityLog[]> {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}/activity`);
    return handleResponse(res);
  },

  async getTaskResults(taskId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/tasks/${taskId}/results`);
    return handleResponse(res);
  },

  // Payments
  async getPaymentSummary(taskId: string): Promise<PaymentSummary> {
    const res = await fetch(`${API_BASE}/api/payments/summary/${taskId}`);
    return handleResponse(res);
  },

  async createPayPalOrder(taskId: string): Promise<{ order_id: string; status: string; amount: number; currency: string; provider: string; approval_url?: string }> {
    const res = await fetch(`${API_BASE}/api/payments/paypal/create-order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    });
    return handleResponse(res);
  },

  async capturePayPalOrder(taskId: string, orderId: string): Promise<{ success: boolean; transaction_id: string; capture_id?: string; order_id: string; status: string; amount: number; currency: string; provider: string; message: string }> {
    const res = await fetch(`${API_BASE}/api/payments/paypal/capture-order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, order_id: orderId }),
    });
    return handleResponse(res);
  },

  async getTransactions(): Promise<Transaction[]> {
    const res = await fetch(`${API_BASE}/api/payments/transactions`);
    return handleResponse(res);
  },

  // System
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/api/system/status`);
    return handleResponse(res);
  },
};
