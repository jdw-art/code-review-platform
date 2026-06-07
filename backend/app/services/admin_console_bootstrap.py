from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Menu, Permission, ProjectTemplate

ADMIN_CONSOLE_PERMISSION_SEEDS = [
    {
        "name": "查看仪表盘",
        "code": "dashboard:read",
        "resource": "dashboard",
        "action": "read",
        "description": "允许查看后台仪表盘概览统计。",
    },
    {
        "name": "查看项目",
        "code": "project:read",
        "resource": "project",
        "action": "read",
        "description": "允许查看项目列表与详情。",
    },
    {
        "name": "创建项目",
        "code": "project:create",
        "resource": "project",
        "action": "create",
        "description": "允许创建后台管理项目。",
    },
    {
        "name": "更新项目",
        "code": "project:update",
        "resource": "project",
        "action": "update",
        "description": "允许更新项目基本信息与绑定关系。",
    },
    {
        "name": "启停项目",
        "code": "project:status",
        "resource": "project",
        "action": "status",
        "description": "允许启用或停用项目。",
    },
    {
        "name": "删除项目",
        "code": "project:delete",
        "resource": "project",
        "action": "delete",
        "description": "允许删除后台管理项目。",
    },
    {
        "name": "触发项目审查",
        "code": "project:trigger-review",
        "resource": "project",
        "action": "trigger-review",
        "description": "允许手动触发项目默认分支审查并创建真实队列任务。",
    },
    {
        "name": "查看项目模板",
        "code": "project_template:read",
        "resource": "project_template",
        "action": "read",
        "description": "允许查看项目模板列表与详情。",
    },
    {
        "name": "创建项目模板",
        "code": "project_template:create",
        "resource": "project_template",
        "action": "create",
        "description": "允许创建项目模板。",
    },
    {
        "name": "更新项目模板",
        "code": "project_template:update",
        "resource": "project_template",
        "action": "update",
        "description": "允许更新项目模板内容。",
    },
    {
        "name": "启停项目模板",
        "code": "project_template:status",
        "resource": "project_template",
        "action": "status",
        "description": "允许启用或停用项目模板。",
    },
    {
        "name": "删除项目模板",
        "code": "project_template:delete",
        "resource": "project_template",
        "action": "delete",
        "description": "允许删除自定义项目模板。",
    },
    {
        "name": "查看模型配置",
        "code": "llm_model:read",
        "resource": "llm_model",
        "action": "read",
        "description": "允许查看大模型配置列表与详情。",
    },
    {
        "name": "创建模型配置",
        "code": "llm_model:create",
        "resource": "llm_model",
        "action": "create",
        "description": "允许创建大模型配置。",
    },
    {
        "name": "更新模型配置",
        "code": "llm_model:update",
        "resource": "llm_model",
        "action": "update",
        "description": "允许更新大模型配置。",
    },
    {
        "name": "启停模型配置",
        "code": "llm_model:status",
        "resource": "llm_model",
        "action": "status",
        "description": "允许启用或停用大模型配置。",
    },
    {
        "name": "查看通知机器人",
        "code": "notification_bot:read",
        "resource": "notification_bot",
        "action": "read",
        "description": "允许查看通知机器人列表与详情。",
    },
    {
        "name": "创建通知机器人",
        "code": "notification_bot:create",
        "resource": "notification_bot",
        "action": "create",
        "description": "允许创建通知机器人。",
    },
    {
        "name": "更新通知机器人",
        "code": "notification_bot:update",
        "resource": "notification_bot",
        "action": "update",
        "description": "允许更新通知机器人配置。",
    },
    {
        "name": "启停通知机器人",
        "code": "notification_bot:status",
        "resource": "notification_bot",
        "action": "status",
        "description": "允许启用或停用通知机器人。",
    },
    {
        "name": "查看审查记录",
        "code": "review_record:read",
        "resource": "review_record",
        "action": "read",
        "description": "允许查看审查记录列表与详情。",
    },
    {
        "name": "查看审查记录原始数据",
        "code": "review_record:raw",
        "resource": "review_record",
        "action": "raw",
        "description": "允许查看审查记录原始 webhook 与 agent trace 数据。",
    },
    {
        "name": "导入审查记录",
        "code": "review_record:import",
        "resource": "review_record",
        "action": "import",
        "description": "允许导入 mock 审查事件并生成审查记录。",
    },
    {
        "name": "查看成员分析",
        "code": "member_analytics:read",
        "resource": "member_analytics",
        "action": "read",
        "description": "允许查看成员分析统计结果。",
    },
    {
        "name": "查看审计日志",
        "code": "audit_log:read",
        "resource": "audit_log",
        "action": "read",
        "description": "允许查看后台操作审计日志。",
    },
    {
        "name": "清理审计日志",
        "code": "audit_log:purge",
        "resource": "audit_log",
        "action": "purge",
        "description": "允许清理业务审计日志，同时保留系统安全日志。",
    },
    {
        "name": "查看用户",
        "code": "user:read",
        "resource": "user",
        "action": "read",
        "description": "允许查看后台用户列表与详情。",
    },
    {
        "name": "创建用户",
        "code": "user:create",
        "resource": "user",
        "action": "create",
        "description": "允许创建后台用户。",
    },
    {
        "name": "更新用户",
        "code": "user:update",
        "resource": "user",
        "action": "update",
        "description": "允许更新后台用户资料。",
    },
    {
        "name": "删除用户",
        "code": "user:delete",
        "resource": "user",
        "action": "delete",
        "description": "允许删除后台用户，但不允许删除自己或最后一个超级管理员。",
    },
    {
        "name": "修改用户状态",
        "code": "user:status",
        "resource": "user",
        "action": "status",
        "description": "允许启用或禁用后台用户。",
    },
    {
        "name": "重置用户密码",
        "code": "user:reset-password",
        "resource": "user",
        "action": "reset-password",
        "description": "允许重置后台用户密码。",
    },
    {
        "name": "分配用户角色",
        "code": "user:assign-role",
        "resource": "user",
        "action": "assign-role",
        "description": "允许为后台用户分配角色。",
    },
    {
        "name": "查看角色",
        "code": "role:read",
        "resource": "role",
        "action": "read",
        "description": "允许查看角色列表与详情。",
    },
    {
        "name": "创建角色",
        "code": "role:create",
        "resource": "role",
        "action": "create",
        "description": "允许创建角色。",
    },
    {
        "name": "更新角色",
        "code": "role:update",
        "resource": "role",
        "action": "update",
        "description": "允许更新角色信息。",
    },
    {
        "name": "删除角色",
        "code": "role:delete",
        "resource": "role",
        "action": "delete",
        "description": "允许删除非系统角色。",
    },
    {
        "name": "分配角色权限与菜单",
        "code": "role:assign",
        "resource": "role",
        "action": "assign",
        "description": "允许为角色分配权限与菜单。",
    },
    {
        "name": "查看菜单",
        "code": "menu:read",
        "resource": "menu",
        "action": "read",
        "description": "允许查看后台菜单。",
    },
    {
        "name": "创建菜单",
        "code": "menu:create",
        "resource": "menu",
        "action": "create",
        "description": "允许创建后台菜单。",
    },
    {
        "name": "更新菜单",
        "code": "menu:update",
        "resource": "menu",
        "action": "update",
        "description": "允许更新后台菜单。",
    },
    {
        "name": "删除菜单",
        "code": "menu:delete",
        "resource": "menu",
        "action": "delete",
        "description": "允许删除非系统菜单。",
    },
]

ADMIN_CONSOLE_MENU_SEEDS = [
    {
        "name": "仪表盘",
        "path": "/dashboard",
        "component": "dashboard/DashboardOverviewPage",
        "icon": "layout-dashboard",
        "sort": 100,
        "visible": True,
        "redirect": None,
        "meta": {"title": "仪表盘", "permission": "dashboard:read"},
        "parent_path": None,
    },
    {
        "name": "项目管理",
        "path": "/projects",
        "component": "projects/ProjectListPage",
        "icon": "folder-open",
        "sort": 110,
        "visible": True,
        "redirect": None,
        "meta": {"title": "项目管理", "permission": "project:read"},
        "parent_path": None,
    },
    {
        "name": "项目模板管理",
        "path": "/project-templates",
        "component": "projects/ProjectTemplateListPage",
        "icon": "copy",
        "sort": 120,
        "visible": True,
        "redirect": None,
        "meta": {"title": "项目模板管理", "permission": "project_template:read"},
        "parent_path": "/projects",
    },
    {
        "name": "模型管理",
        "path": "/models",
        "component": "models/ModelListPage",
        "icon": "cpu",
        "sort": 130,
        "visible": True,
        "redirect": None,
        "meta": {"title": "模型管理", "permission": "llm_model:read"},
        "parent_path": None,
    },
    {
        "name": "通知机器人",
        "path": "/notification-bots",
        "component": "notifications/NotificationBotListPage",
        "icon": "bot",
        "sort": 140,
        "visible": True,
        "redirect": None,
        "meta": {"title": "通知机器人", "permission": "notification_bot:read"},
        "parent_path": None,
    },
    {
        "name": "审查记录",
        "path": "/review-records",
        "component": "reviews/ReviewRecordListPage",
        "icon": "file-search",
        "sort": 150,
        "visible": True,
        "redirect": None,
        "meta": {"title": "审查记录", "permission": "review_record:read"},
        "parent_path": None,
    },
    {
        "name": "成员分析",
        "path": "/member-analytics",
        "component": "reviews/MemberAnalyticsPage",
        "icon": "users",
        "sort": 160,
        "visible": True,
        "redirect": None,
        "meta": {"title": "成员分析", "permission": "member_analytics:read"},
        "parent_path": None,
    },
    {
        "name": "权限管理",
        "path": "/system",
        "component": "system/SystemLayoutPage",
        "icon": "shield-check",
        "sort": 170,
        "visible": True,
        "redirect": "/system/users",
        "meta": {"title": "权限管理"},
        "parent_path": None,
    },
    {
        "name": "用户管理",
        "path": "/system/users",
        "component": "system/UserListPage",
        "icon": "users",
        "sort": 171,
        "visible": True,
        "redirect": None,
        "meta": {"title": "用户管理", "permission": "user:read"},
        "parent_path": "/system",
    },
    {
        "name": "角色管理",
        "path": "/system/roles",
        "component": "system/RoleListPage",
        "icon": "shield-check",
        "sort": 172,
        "visible": True,
        "redirect": None,
        "meta": {"title": "角色管理", "permission": "role:read"},
        "parent_path": "/system",
    },
    {
        "name": "系统日志",
        "path": "/audit-logs",
        "component": "system/AuditLogPage",
        "icon": "scroll-text",
        "sort": 180,
        "visible": True,
        "redirect": None,
        "meta": {"title": "系统日志", "permission": "audit_log:read"},
        "parent_path": None,
    },
]

SYSTEM_PROJECT_TEMPLATE_SEEDS = [
    {
        "name": "Java 默认模板",
        "code": "java-default",
        "description": "适用于 Java 后端服务的默认审查模板。",
        "file_extensions": [".java", ".xml", ".yml", ".yaml"],
        "review_prompt_template": "请使用中文审查 Java 后端改动，重点关注空指针、事务边界、并发安全、SQL 风险与异常处理。",
        "prompt_metadata": {
            "language": "zh-CN",
            "review_dimensions": ["correctness", "security", "performance"],
        },
    },
    {
        "name": "Vue + TypeScript 模板",
        "code": "frontend-vue-ts",
        "description": "适用于 Vue 与 TypeScript 前端项目的审查模板。",
        "file_extensions": [".vue", ".ts", ".tsx", ".js", ".css"],
        "review_prompt_template": "请使用中文审查前端改动，重点关注类型安全、状态管理、副作用、样式污染与可访问性。",
        "prompt_metadata": {
            "language": "zh-CN",
            "review_dimensions": ["correctness", "maintainability", "ux"],
        },
    },
    {
        "name": "Go 默认模板",
        "code": "go-default",
        "description": "适用于 Go 服务的默认审查模板。",
        "file_extensions": [".go", ".mod", ".sum"],
        "review_prompt_template": "请使用中文审查 Go 改动，重点关注错误处理、并发竞争、上下文取消与资源释放。",
        "prompt_metadata": {
            "language": "zh-CN",
            "review_dimensions": ["correctness", "concurrency", "performance"],
        },
    },
    {
        "name": "全栈通用模板",
        "code": "fullstack-common",
        "description": "适用于多语言全栈仓库的通用审查模板。",
        "file_extensions": [".py", ".ts", ".tsx", ".java", ".go", ".md"],
        "review_prompt_template": "请使用中文审查全栈改动，优先指出高风险缺陷，并补充受影响范围、复现条件与修复建议。",
        "prompt_metadata": {
            "language": "zh-CN",
            "review_dimensions": ["correctness", "security", "maintainability"],
        },
    },
]


def bootstrap_admin_console_resources(session: Session) -> None:
    """初始化后台管理域需要的权限、菜单与系统模板。"""
    _ensure_permissions(session)
    _ensure_menus(session)
    _ensure_system_templates(session)


def _ensure_permissions(session: Session) -> None:
    """按权限编码幂等补齐后台管理域权限。"""
    existing_codes = set(
        session.scalars(select(Permission.code).where(Permission.code.in_(
            [seed["code"] for seed in ADMIN_CONSOLE_PERMISSION_SEEDS]
        ))).all()
    )
    for seed in ADMIN_CONSOLE_PERMISSION_SEEDS:
        if seed["code"] in existing_codes:
            continue
        session.add(Permission(**seed, is_system=True))


def _ensure_menus(session: Session) -> None:
    """按菜单路径幂等补齐项目管理相关菜单。"""
    menus_by_path = {
        menu.path: menu
        for menu in session.scalars(
            select(Menu).where(
                Menu.path.in_([seed["path"] for seed in ADMIN_CONSOLE_MENU_SEEDS])
            )
        ).all()
    }
    for seed in ADMIN_CONSOLE_MENU_SEEDS:
        parent_id = None
        parent_path = seed["parent_path"]
        if parent_path is not None:
            parent = menus_by_path.get(parent_path)
            if parent is None:
                parent = session.scalar(select(Menu).where(Menu.path == parent_path))
            parent_id = parent.id if parent is not None else None

        menu = menus_by_path.get(seed["path"])
        if menu is None:
            menu = Menu(
                parent_id=parent_id,
                name=seed["name"],
                path=seed["path"],
                component=seed["component"],
                icon=seed["icon"],
                sort=seed["sort"],
                visible=seed["visible"],
                redirect=seed["redirect"],
                meta=seed["meta"],
                is_system=True,
            )
            session.add(menu)
            session.flush()
            menus_by_path[menu.path] = menu
        else:
            menu.parent_id = parent_id
            menu.name = seed["name"]
            menu.component = seed["component"]
            menu.icon = seed["icon"]
            menu.sort = seed["sort"]
            menu.visible = seed["visible"]
            menu.redirect = seed["redirect"]
            menu.meta = seed["meta"]
            menu.is_system = True
        menus_by_path[menu.path] = menu


def _ensure_system_templates(session: Session) -> None:
    """按模板编码幂等补齐后台所需系统模板。"""
    existing_codes = set(
        session.scalars(
            select(ProjectTemplate.code).where(
                ProjectTemplate.code.in_(
                    [seed["code"] for seed in SYSTEM_PROJECT_TEMPLATE_SEEDS]
                )
            )
        ).all()
    )
    for seed in SYSTEM_PROJECT_TEMPLATE_SEEDS:
        if seed["code"] in existing_codes:
            continue
        session.add(ProjectTemplate(**seed, is_system=True, is_active=True))
