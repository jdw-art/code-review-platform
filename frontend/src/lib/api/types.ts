/**
 * 这里集中定义前端会直接消费的后端 API 契约，避免认证、路由和页面各自维护一份类型。
 */
export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  request_id?: string | null;
}

/**
 * 登录与刷新接口共用的 JWT 令牌对。
 */
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  must_change_password: boolean;
}

export interface CurrentUserSummary {
  id: number;
  username: string;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export interface CurrentUserRoleSummary {
  id: number;
  name: string;
  code: string;
}

/**
 * RBAC 菜单树节点，直接对应 `/me/access-context` 返回结构。
 */
export interface MenuNode {
  id: number;
  parent_id: number | null;
  name: string;
  path: string;
  component: string | null;
  icon: string | null;
  sort: number;
  visible: boolean;
  redirect: string | null;
  meta: Record<string, unknown> | null;
  is_system: boolean;
  children: MenuNode[];
}

export interface AccessContextResponse {
  user: CurrentUserSummary;
  roles: CurrentUserRoleSummary[];
  permissions: string[];
  menus: MenuNode[];
  must_change_password: boolean;
}

export interface CurrentUserProfileResponse {
  id: number;
  username: string;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  roles: CurrentUserRoleSummary[];
}

/**
 * 后台列表页统一使用的分页结构。
 */
export interface PageResponse<ItemT> {
  items: ItemT[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectTemplateSummary {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  review_prompt_configured: boolean;
}

export interface PlatformOptionResponse {
  label: string;
  value: string;
}

export interface ProjectTemplateOptionResponse {
  id: number;
  name: string;
  code: string;
  description: string | null;
  file_extensions: string[];
}

export interface ProjectOptionsResponse {
  platform_types: PlatformOptionResponse[];
  template_options: ProjectTemplateOptionResponse[];
}

export interface ProjectTemplateOptionsResponse {
  common_file_extensions: string[];
  prompt_metadata_presets: Record<string, string[]>;
}

export interface ProjectSettingsResponse {
  language?: string | null;
  owner?: string | null;
  average_score?: number | null;
  last_review_at?: string | null;
  [key: string]: unknown;
}

export interface ProjectResponse {
  id: number;
  name: string;
  key: string;
  platform_type: string;
  repo_url: string | null;
  default_branch: string;
  description: string | null;
  is_active: boolean;
  review_enabled: boolean;
  template: ProjectTemplateSummary | null;
  settings?: ProjectSettingsResponse | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgentSessionResponse {
  id: number;
  project_id: number;
  title: string;
  status: string;
  branch: string;
  provider: string | null;
  model: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface AgentMessageResponse {
  id: number;
  session_id: number;
  run_id: number | null;
  role: string;
  content: string;
  status: string;
  sequence: number;
  content_format: string;
  created_at: string;
}

export interface AgentSSEEventPayload {
  id?: number;
  run_id?: number;
  session_id: number;
  sequence?: number;
  role?: string;
  content?: string;
  status?: string;
  created_at?: string;
  payload?: Record<string, unknown>;
}

export interface AgentSSEEvent {
  event: string;
  data: AgentSSEEventPayload;
}

export interface ProjectTemplateResponse {
  id: number;
  name: string;
  code: string;
  description: string | null;
  file_extensions?: string[] | null;
  review_prompt_template: string | null;
  review_prompt_configured: boolean;
  prompt_metadata: Record<string, unknown>;
  is_system: boolean;
  is_active: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface LlmModelResponse {
  id: number;
  name: string;
  provider: string;
  model_code: string;
  base_url: string | null;
  api_key_masked: string | null;
  temperature: number | null;
  max_tokens: number | null;
  top_p: number | null;
  prompt_template: string | null;
  is_default: boolean;
  is_active: boolean;
  queries_count?: number | null;
  last_test_status: string | null;
  last_test_message: string | null;
  last_test_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationBotResponse {
  id: number;
  name: string;
  bot_type: string;
  webhook_url: string;
  secret_masked: string | null;
  mention_strategy: string | null;
  template_config: Record<string, unknown>;
  is_active: boolean;
  last_test_status: string | null;
  last_test_message: string | null;
  last_test_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLogResponse {
  id: number;
  user_id: number | null;
  username_snapshot: string | null;
  action: string;
  resource_type: string;
  resource_id: number | null;
  resource_name_snapshot: string | null;
  request_path: string | null;
  request_method: string | null;
  request_payload: Record<string, unknown>;
  response_status: number | null;
  result: string | null;
  error_message: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface DashboardOverviewResponse {
  total_projects: number;
  active_projects: number;
  total_review_records: number;
  average_score: number | null;
  active_model_name: string | null;
  recent_reviews?: DashboardRecentReviewItem[] | null;
  project_chart?: DashboardChartPoint[] | null;
  member_chart?: DashboardChartPoint[] | null;
  models?: DashboardModelSummary[] | null;
  repo_health?: DashboardRepoHealthItem[] | null;
}

export interface DashboardChartPoint {
  project_id: number | null;
  name: string;
  commits: number;
  avg_score: number | null;
  additions: number;
  deletions: number;
}

export interface DashboardRecentReviewItem {
  id: number;
  project_name: string;
  title: string | null;
  branch: string | null;
  commit_hash: string | null;
  committer: string | null;
  score: number | null;
  review_status: string;
  summary: string | null;
  created_at: string;
}

export interface DashboardModelSummary {
  id: number;
  name: string;
  provider: string;
  temperature: number | null;
  is_default: boolean;
  is_active: boolean;
}

export interface DashboardRepoHealthItem {
  project_id: number;
  name: string;
  is_active: boolean;
  review_count: number;
  average_score: number | null;
  last_review_at: string | null;
}

export interface ReviewRecordAuthorOption {
  label: string;
  value: string;
}

export interface ReviewRecordFiltersResponse {
  event_types: string[];
  authors: ReviewRecordAuthorOption[];
}

export interface ReviewCommitResponse {
  id: number;
  commit_id: string;
  short_commit_id: string | null;
  author: string | null;
  message: string | null;
  timestamp: string | null;
  sequence: number;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ReviewRecordListItemResponse {
  id: number;
  project_id: number;
  event_type: string;
  external_event_id: string | null;
  project_name_snapshot: string;
  template_id_snapshot: number | null;
  template_name_snapshot: string | null;
  author: string;
  title: string | null;
  branch: string | null;
  source_branch: string | null;
  target_branch: string | null;
  commit_count: number;
  commit_messages?: string[] | null;
  score: number | null;
  review_status: string;
  review_result: string | null;
  summary: string | null;
  url: string | null;
  url_slug: string | null;
  last_commit_id: string | null;
  additions: number;
  deletions: number;
  created_at: string;
  updated_at: string;
}

export interface ReviewRecordDetailResponse extends ReviewRecordListItemResponse {
  review_prompt_snapshot: string | null;
  commits?: ReviewCommitResponse[] | null;
}

export interface MemberAnalyticsRecentReviewResponse {
  review_record_id: number;
  event_type: string;
  title: string | null;
  url_slug: string | null;
  score: number | null;
  review_status: string;
  updated_at: string;
}

export interface MemberAnalyticsListItemResponse {
  project_member_id: number;
  project_id: number;
  project_name: string;
  member_name: string;
  member_email: string | null;
  role_name: string | null;
  review_count: number;
  average_score: number | null;
  total_additions: number;
  total_deletions: number;
  last_review_at: string | null;
}

export interface MemberAnalyticsDetailResponse
  extends MemberAnalyticsListItemResponse {
  recent_reviews?: MemberAnalyticsRecentReviewResponse[] | null;
}

export interface PermissionResponse {
  id: number;
  name: string;
  code: string;
  resource: string;
  action: string;
  description: string | null;
  is_system: boolean;
}

export interface RoleResponse {
  id: number;
  name: string;
  code: string;
  description: string | null;
  is_system: boolean;
  permissions?: PermissionResponse[] | null;
  menus?: MenuNode[] | null;
}

export interface UserRoleSummary {
  id: number;
  name: string;
  code: string;
}

export interface UserResponse {
  id: number;
  username: string;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  roles?: UserRoleSummary[] | null;
}
