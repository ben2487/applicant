export interface Run {
  id: number;
  application_id: number | null;
  initial_url: string;
  headless: boolean;
  started_at: string;
  ended_at: string | null;
  result_status: 'IN_PROGRESS' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
  summary: string | null;
  raw: string | null;
  created_at: string;
}

export interface RunEvent {
  id: number;
  run_id: number;
  ts: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  category: 'BROWSER' | 'FORM' | 'NETWORK' | 'SYSTEM';
  message: string;
  code: string | null;
  data: any | null;
  created_at: string;
}

export interface UserProfile {
  id: number;
  slug: string;
  display_name: string;
  meta: any | null;
  created_at: string;
  updated_at: string;
}

export interface CreateRunRequest {
  initial_url: string;
  headless?: boolean;
}

export interface CreateRunEventRequest {
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  category: 'BROWSER' | 'FORM' | 'NETWORK' | 'SYSTEM';
  message: string;
  code?: string;
  data?: any;
}

export interface CreateUserRequest {
  slug: string;
  display_name: string;
  meta?: any;
}
