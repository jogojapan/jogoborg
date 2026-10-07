// API payload types (mirror the Flask backend response shapes).

export interface LoginResponse {
  token: string;
  message?: string;
}

export interface Repository {
  id: number;
  name: string;
  path: string;
  created_at?: string;
  archives_count: number;
}

export interface Archive {
  name: string;
  created_at: string;
  size?: number | null;
  files_count?: number | null;
}

export interface JobLog {
  started_at: string;
  finished_at?: string | null;
  status: string;
  create_duration?: number | null;
  create_max_memory?: number | null;
  prune_duration?: number | null;
  prune_max_memory?: number | null;
  compact_duration?: number | null;
  compact_max_memory?: number | null;
  db_dump_duration?: number | null;
  db_dump_max_memory?: number | null;
  error_message?: string | null;
}

export interface S3Config {
  provider?: string; // 'aws' | 'minio'
  endpoint?: string;
  bucket?: string;
  region?: string;
  access_key?: string;
  secret_key?: string;
  storage_class?: string;
  max_concurrent_requests?: number;
  max_queue_size?: number;
  multipart_chunk_size?: number | string;
}

export interface DbConfig {
  type?: string; // 'postgresql' | 'mariadb'
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database?: string;
  tables?: string[];
}

export interface Job {
  id: number;
  name: string;
  schedule: string;
  compression: string;
  exclude_patterns?: string | null;
  keep_daily: number;
  keep_monthly: number;
  keep_yearly: number;
  source_directories: string[];
  pre_command?: string | null;
  post_command?: string | null;
  s3_config?: S3Config | null;
  db_config?: DbConfig | null;
  created_at?: string;
  updated_at?: string;
}

export interface JobPayload {
  name: string;
  schedule: string;
  compression: string;
  exclude_patterns: string;
  keep_daily: number;
  keep_monthly: number;
  keep_yearly: number;
  source_directories: string[];
  pre_command: string;
  post_command: string;
  repository_passphrase: string;
  s3_config: S3Config | null;
  db_config: DbConfig | null;
}

export interface SourceItem {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number | null;
  permissions?: string | null;
  last_modified?: string | null;
}

export interface SmtpConfig {
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  sender_email?: string;
  recipient_email?: string;
  security?: string;
}

export interface WebhookConfig {
  url?: string;
  token?: string;
  success_priority?: string;
  error_priority?: string;
}

export interface NotificationSettings {
  smtp_config?: SmtpConfig;
  webhook_config?: WebhookConfig;
}