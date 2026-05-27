from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Menu, Permission, ProjectTemplate

ADMIN_CONSOLE_PERMISSION_SEEDS = [
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
]

ADMIN_CONSOLE_MENU_SEEDS = [
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
        if seed["path"] in menus_by_path:
            continue

        parent_id = None
        parent_path = seed["parent_path"]
        if parent_path is not None:
            parent = menus_by_path.get(parent_path)
            if parent is None:
                parent = session.scalar(select(Menu).where(Menu.path == parent_path))
            parent_id = parent.id if parent is not None else None

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
