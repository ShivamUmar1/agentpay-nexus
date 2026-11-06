export interface Agent {
  id: string;
  name: string;
  description: string;
  category: string;
  capabilities: string[];
  supported_tasks: string[];
  pricing_model: string;
  price: number;
  currency: string;
  availability: 'available' | 'busy' | 'offline';
  rating: number;
  completed_tasks: number;
  icon: string;
  estimated_time: string;
}

export interface TaskStep {
  id: string;
  task_id: string;
  step_name: string;
  assigned_agent_id: string | null;
  dependencies: string[];
  input_data: any;
  output_data: any;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description: string;
  budget: number;
  currency: string;
  status: 'draft' | 'planning' | 'planned' | 'executing' | 'awaiting_payment' | 'paid' | 'completed' | 'failed' | 'cancelled';
  current_step: string;
  execution_plan: {
    objective_summary?: string;
    complexity_tier?: string;
    estimated_total_cost?: number;
    subtasks?: Array<{
      step_name: string;
      assigned_agent_id: string;
      agent_category: string;
      objective: string;
      dependencies: string[];
      estimated_cost: number;
    }>;
  } | null;
  final_output: {
    title?: string;
    description?: string;
    report_markdown?: string;
    executive_summary?: string;
    key_takeaways?: string[];
    strategic_recommendations?: string[];
    research_data?: any;
    analysis_data?: {
      computed_metrics?: Record<string, any>;
      market_share_breakdown?: Array<{ label: string; value: number; category?: string }>;
      chart_revenue_projections?: Array<{ year: string; revenue_bn: number; volume_units_k: number }>;
      key_findings?: string[];
    };
    qa_audit?: {
      audit_status: string;
      completeness_score: number;
      factual_coherence_score: number;
      feedback: string;
    };
    invoice?: any;
    delivered_at?: string;
  } | null;
  total_cost: number;
  created_at: string;
  updated_at: string;
  steps: TaskStep[];
}

export interface InvoiceLineItem {
  agent_id: string;
  agent_name: string;
  category: string;
  description: string;
  unit_price: number;
  quantity: number;
  total: number;
}

export interface PaymentSummary {
  task_id: string;
  task_title: string;
  subtotal: number;
  platform_fee: number;
  total_amount: number;
  currency: string;
  items: InvoiceLineItem[];
  is_budget_exceeded: boolean;
  budget: number;
}

export interface Transaction {
  id: string;
  user_id: string;
  task_id: string;
  paypal_order_id: string | null;
  paypal_capture_id: string | null;
  amount: number;
  currency: string;
  payment_status: 'pending' | 'completed' | 'failed' | 'simulated_completed';
  provider: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityLog {
  id: string;
  task_id: string | null;
  agent_id: string | null;
  event_type: string;
  message: string;
  metadata_json: string | null;
  created_at: string;
}

export interface SystemStatus {
  service: string;
  environment: string;
  database: {
    status: string;
    type: string;
  };
  ai_orchestration: {
    provider: string;
    status: string;
    model: string;
  };
  payment_gateway: {
    provider: string;
    mode: string;
    configured: boolean;
    status: string;
    client_id_set: boolean;
  };
  version: string;
}
