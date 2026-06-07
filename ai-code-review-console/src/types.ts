/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type TabId =
  | 'dashboard'
  | 'projects'
  | 'templates'
  | 'models'
  | 'robots'
  | 'records'
  | 'members'
  | 'permissions'
  | 'users'
  | 'roles'
  | 'logs'
  | 'chat';

export interface UserSession {
  username: string;
  role: string;
  avatarUrl?: string;
  token: string;
  isLoggedIn: boolean;
}

// 1. 用户 (users 表)
export interface UserItem {
  id: string; // BIGINT
  username: string;
  nickname: string;
  email: string;
  phone: string;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  last_login_at: string;
  created_at: string;
  updated_at: string;
}

// 2. 角色 (roles 表)
export interface RoleItem {
  id: string; // BIGINT
  name: string;
  code: string;
  description: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// 3. 权限 (permissions 表)
export interface PermissionItem {
  id: string; // BIGINT
  name: string;
  code: string;
  resource: string;
  action: string;
  description: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// 4. 菜单 (menus 表)
export interface MenuItem {
  id: string; // BIGINT
  parent_id?: string;
  name: string;
  path: string;
  component: string;
  icon: string;
  sort: number;
  visible: boolean;
  redirect?: string;
  meta?: any;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// 9. 项目模板 (project_templates 表)
export interface ProjectTemplateItem {
  id: string; // BIGINT
  name: string;
  code: string;
  description: string;
  file_extensions: string[]; // JSONB
  review_prompt_template: string;
  prompt_metadata?: any; // JSONB
  is_system: boolean;
  is_active: boolean;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

// 10. LLM 模型 (llm_models 表)
export interface ModelConfig {
  id: string; // BIGINT
  name: string;
  provider: string; // e.g. Gemini, OpenAI, DeepSeek, Custom
  model_code: string; // Map model_code
  base_url?: string;
  api_key_masked?: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  prompt_template?: string;
  is_default: boolean; // Map is_default
  is_active: boolean;
  last_test_status?: string;
  last_test_message?: string;
  last_test_at?: string;
  created_at?: string;
  updated_at?: string;
  
  // UI helper properties
  isActive?: boolean; // backwards compatible
  queriesCount?: number;
}

// 11. 通知机器人 (notification_bots 表)
export interface NotificationBotItem {
  id: string; // BIGINT
  name: string;
  bot_type: string; // bot_type
  webhook_url: string; // webhook_url
  secret_masked?: string;
  mention_strategy?: string;
  template_config?: any; // JSONB
  is_active: boolean; // is_active
  last_test_status?: string;
  last_test_message?: string;
  last_test_at?: string;
  created_at?: string;
  updated_at?: string;
}

// 12. 项目配置 (projects 表)
export interface ProjectItem {
  id: string; // BIGINT
  name: string;
  key: string; // Unique project key code
  platform_type: string; // platform_type (GitHub / GitLab etc)
  repo_url: string; // repo_url
  default_branch: string; // default_branch
  description: string;
  is_active: boolean; // Map to is_active
  review_enabled: boolean; // review_enabled
  template_id?: string; // template_id
  default_model_id?: string; // default_model_id
  default_bot_id?: string; // default_bot_id
  settings?: any; // JSONB
  created_by?: string;
  created_at?: string;
  updated_at?: string;

  // UI backwards compatibility / helpers
  enabled?: boolean; 
  status?: 'active' | 'inactive';
  language?: string; // client helper
  owner?: string; // owner
  scoreAverage: number;
  lastReviewAt: string;
  repoUrl?: string;
  branch?: string;
}

// 13 & 14. 审查记录 (review_records 表 & review_commits 表)
export interface ReviewRecord {
  id: string; // BIGINT
  project_id: string; // project_id
  project_name?: string; // UI friendly mapping project name / project_name_snapshot
  projectName?: string; // legacy mapping
  event_type?: string; // event_type (push, merge_request, etc)
  external_event_id?: string;
  project_name_snapshot?: string;
  template_id_snapshot?: string;
  template_name_snapshot?: string;
  review_prompt_snapshot?: string;
  author?: string; // author / committer
  committer?: string; // UI backwards compatibility
  title?: string; // title / prTitle
  prTitle?: string; // legacy mapping
  branch: string;
  source_branch?: string;
  target_branch?: string;
  commit_count?: number;
  commit_messages?: any; // JSONB
  score: number;
  review_status?: string; // pending, completed, failed, etc.
  status?: 'excellent' | 'pass' | 'warning' | 'fail'; // legacy UI compatibility
  review_result?: string;
  summary: string;
  url?: string;
  url_slug?: string;
  last_commit_id?: string;
  commitHash?: string; // legacy mapping
  additions?: number; // additions
  deletions?: number; // deletions
  agent_trace?: any;
  webhook_data?: any;
  extra_data?: any;
  created_at?: string;
  updated_at?: string;
  platform_type?: string;
  delivery_status?: string; // delivery_status
  external_project_id?: string;
  external_merge_request_id?: string;
  external_pull_request_id?: string;
  external_commit_sha?: string;
  reviewed_at?: string;
  failed_at?: string;
  error_message?: string;
  retry_count?: number;
  
  // UI feedback helper
  timestamp?: string; // UI legacy date display compatibility
  robotNotifiedView?: boolean;
  robotNotified?: boolean; // legacy matching
}

// 15. 项目成员 (project_members 表)
export interface ProjectMemberItem {
  id: string; // BIGINT
  project_id: string;
  user_id?: string;
  member_name: string;
  member_email: string;
  role_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 16. 审计日志 (audit_logs 表)
export interface SystemLogItem {
  id: string; // BIGINT
  user_id?: string;
  username_snapshot?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  resource_name_snapshot?: string;
  request_path?: string;
  request_method?: string;
  request_payload?: any;
  response_status?: number;
  result?: string; // success, failed e.g.
  error_message?: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;

  // UI backwards compatibility display mapping
  timestamp?: string; 
  level?: 'info' | 'warning' | 'error';
  operator?: string;
  details?: string;
}

export interface DashboardStats {
  totalProjects: number;
  activeProjects: number;
  reviewCount: number;
  averageScore: number;
}
