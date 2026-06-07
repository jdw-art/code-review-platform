/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, FormEvent } from 'react';
import {
  FileJson,
  Plus,
  Search,
  Edit3,
  Trash2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info,
  Check,
  X,
  FileCode,
  CheckCircle2
} from 'lucide-react';
import { ProjectTemplateItem } from '../types';

interface TemplateManagementViewProps {
  onAddLog: (action: string, details: string, level?: 'info' | 'warning' | 'error') => void;
}

const initialTemplates: ProjectTemplateItem[] = [
  {
    id: 'tpl-1',
    name: '通用代码规范与缺陷审查模板',
    code: 'DEFAULT_GENERAL',
    description: '适用于各类主流编程语言的通用审查规则，重点关注语法错误、空指针异常、安全高危漏洞审计等。',
    file_extensions: ['ts', 'tsx', 'js', 'jsx', 'go', 'py', 'java', 'sql'],
    review_prompt_template: '你是一个资深的研发主管与代码安全专家。请对以下 PR/MR 的 diff 进行细致的安全与规范性审查。\n你的审查应覆盖以下核心要点：\n1. 【缺陷与漏洞】重大的逻辑缺陷、未捕获的空指针/异常、内存泄露风险等。\n2. 【规范与设计】命名风格、长方法重构、过于复杂的条件嵌套、必要的代码注释验证。\n3. 【代码性能】更合理的算法实现、并发/协程处理、资源加载与未释放风险。',
    is_active: true,
    is_system: true,
  },
  {
    id: 'tpl-2',
    name: 'React / TS 性能与依赖项审查模板',
    code: 'FRONTEND_REACT',
    description: '专属于 Web 前端 React 和 TypeScript 项目，严格检查 React 闭包、useEffect 依赖、不必要重渲染问题。',
    file_extensions: ['ts', 'tsx', 'js', 'jsx', 'css'],
    review_prompt_template: '请分析并重审以下现代前端 JSX/TSX 模块的代码修改。请特别挑出如下隐患：\n1. 导致无限重渲染的 useEffect/useMemo 声明和状态更新循环。\n2. 缺失 Hooks 依赖项进而引发的闭包变量或未捕获 of 旧引用。\n3. TypeScript 中不当的 `any` 转换以及非空断言滥用。\n4. 针对移动端触摸目标响应式设计、Tailwind 主题类匹配的优化建议。',
    is_active: true,
    is_system: true,
  },
  {
    id: 'tpl-3',
    name: '高并发高可靠后端安全阻断模板',
    code: 'BACKEND_HIGH_PERF',
    description: '针对后端高流量核心微服务的审查策略，审查并发加锁、SQL 慢查询、高风险拼接及熔断防护手段。',
    file_extensions: ['go', 'java', 'sql', 'py'],
    review_prompt_template: '以下提交涉及数据库访问、网络 I/O 或高负载计算，请结合后端分布式可用性原则提供报告：\n1. 【SQL 质量】是否存在大表的全表扫描、复杂关联慢查询以及无防注入防注入处理。\n2. 【并发死锁】检查加锁解锁逻辑是否闭环、是否存在嵌套调用导致死锁。\n3. 【性能熔断】是否对外部依赖服务存在延迟兜底或超时设置、缓存击穿防御手段是否恰当。',
    is_active: false,
    is_system: true,
  }
];

const LANGUAGE_PRESETS = [
  { name: 'React / Web 前端', extensions: 'ts, tsx, js, jsx, css, html', code: 'FRONTEND_REACT' },
  { name: 'Golang 核心后端', extensions: 'go, sql, proto, yaml', code: 'BACKEND_GO' },
  { name: 'Enterprise Java', extensions: 'java, xml, sql, properties', code: 'BACKEND_JAVA' },
  { name: 'Python 机器学习', extensions: 'py, ipynb, json, txt', code: 'PYTHON_ML' },
];

export default function TemplateManagementView({ onAddLog }: TemplateManagementViewProps) {
  const [templates, setTemplates] = useState<ProjectTemplateItem[]>(() => {
    const saved = localStorage.getItem('review_templates');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // Fallback
      }
    }
    return initialTemplates;
  });

  const [search, setSearch] = useState('');
  const [expandedTplId, setExpandedTplId] = useState<string | null>(null);

  // Form states for Add / Edit
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProjectTemplateItem | null>(null);

  // Modal Inputs
  const [formName, setFormName] = useState('');
  const [formCode, setFormCode] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formExtensionsText, setFormExtensionsText] = useState('');
  const [formPrompt, setFormPrompt] = useState('');
  const [formActive, setFormActive] = useState(true);

  const saveTemplates = (newTemplates: ProjectTemplateItem[]) => {
    setTemplates(newTemplates);
    localStorage.setItem('review_templates', JSON.stringify(newTemplates));
  };

  const openAddModal = () => {
    setEditingTemplate(null);
    setFormName('');
    setFormCode('');
    setFormDesc('');
    setFormExtensionsText('ts, tsx, js, jsx');
    setFormPrompt('你是一个资深的研发主管。请对以下代码进行详细审查并提供建议：');
    setFormActive(true);
    setIsModalOpen(true);
  };

  const openEditModal = (tpl: ProjectTemplateItem) => {
    setEditingTemplate(tpl);
    setFormName(tpl.name);
    setFormCode(tpl.code);
    setFormDesc(tpl.description);
    setFormExtensionsText(tpl.file_extensions.join(', '));
    setFormPrompt(tpl.review_prompt_template);
    setFormActive(tpl.is_active);
    setIsModalOpen(true);
  };

  const handleSaveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formCode.trim() || !formPrompt.trim()) return;

    const file_extensions = formExtensionsText
      .split(',')
      .map((ext) => ext.trim().toLowerCase())
      .filter((ext) => ext.length > 0);

    if (editingTemplate) {
      // Edit
      const updated = templates.map((t) => {
        if (t.id === editingTemplate.id) {
          return {
            ...t,
            name: formName.trim(),
            code: formCode.trim().toUpperCase(),
            description: formDesc.trim(),
            file_extensions,
            review_prompt_template: formPrompt,
            is_active: formActive,
          };
        }
        return t;
      });
      saveTemplates(updated);
      onAddLog('TEMPLATE_MUTATED', `模板已手动编辑: ${formName} (${formCode})`, 'info');
    } else {
      // Add
      const newTpl: ProjectTemplateItem = {
        id: `tpl-${Date.now()}`,
        name: formName.trim(),
        code: formCode.trim().toUpperCase(),
        description: formDesc.trim(),
        file_extensions,
        review_prompt_template: formPrompt,
        is_active: formActive,
        is_system: false,
      };
      saveTemplates([...templates, newTpl]);
      onAddLog('TEMPLATE_CREATED', `成功部署了自定义审查模板: ${newTpl.name}`, 'info');
    }

    setIsModalOpen(false);
  };

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`确认删除审查模板“${name}”吗？这会影响绑定此类模板的审查工作。`)) {
      const filtered = templates.filter((t) => t.id !== id);
      saveTemplates(filtered);
      onAddLog('TEMPLATE_DELETED', `删除了审查模板: ${name}`, 'warning');
    }
  };

  const toggleActive = (id: string, currentStatus: boolean, name: string) => {
    const updated = templates.map((t) => {
      if (t.id === id) {
        return { ...t, is_active: !currentStatus };
      }
      return t;
    });
    saveTemplates(updated);
    onAddLog(
      'TEMPLATE_STATE_CHANGED',
      `模板 ${name} 状态更改为 [${!currentStatus ? '启用' : '禁用'}]`,
      'info'
    );
  };

  const filtered = templates.filter((tpl) => {
    const searchLower = search.toLowerCase();
    return (
      tpl.name.toLowerCase().includes(searchLower) ||
      tpl.code.toLowerCase().includes(searchLower) ||
      tpl.description.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header card with responsive minimal metrics */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5 font-sans">
            <FileJson className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>审查模板与规则链控制中心</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            在此配置并开启自动 PR/MR 定制审查规则。核心字段名完全对齐 PostgreSQL <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">project_templates</code> 表结构。
          </p>
        </div>
        <button
          onClick={openAddModal}
          className="px-3.5 py-1.5 bg-[#0a0b14] hover:bg-slate-900 text-white text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>添加审查模板</span>
        </button>
      </div>

      {/* Global Filter Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-3xs flex items-center gap-2">
        <Search className="w-4 h-4 text-slate-400 ml-1.5" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="检索规则名称、大写特征码(code)或核心说明..."
          className="w-full bg-transparent text-xs text-slate-800 border-none outline-hidden focus:outline-hidden placeholder-slate-400"
        />
      </div>

      {/* Grid List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-xl border border-slate-200/85 text-slate-400 text-xs">
            暂无匹配的代码片段和审查约束模板
          </div>
        ) : (
          filtered.map((tpl) => {
            const isExpanded = expandedTplId === tpl.id;
            return (
              <div
                key={tpl.id}
                className="bg-white rounded-xl border border-slate-200 shadow-3xs hover:border-slate-300 transition-all divide-y divide-slate-100"
              >
                {/* Primary Panel */}
                <div className="p-4 md:p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div className="space-y-1.5 grow min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-800 text-sm">{tpl.name}</span>
                      <span className="font-mono text-[9px] bg-indigo-50 text-indigo-600 px-1.5 py-0.2 rounded border border-indigo-100/50 font-semibold uppercase">
                        {tpl.code}
                      </span>
                      {tpl.is_system && (
                        <span className="text-[9px] font-semibold bg-slate-150 text-slate-600 px-1.5 rounded-xs">
                          系统自带
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-2 md:line-clamp-1 leading-normal font-light">
                      {tpl.description || '暂无详细描述信息。'}
                    </p>

                    {/* Meta information tags */}
                    <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-400 pt-0.5 select-none">
                      <span className="font-medium text-slate-500 font-mono">后缀拦截:</span>
                      <div className="flex flex-wrap gap-1">
                        {tpl.file_extensions.map((ext) => (
                          <span
                            key={ext}
                            className="bg-slate-100 text-slate-600 px-1.5 rounded-xs text-[9.5px] font-mono"
                          >
                            .{ext}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Actions & switches */}
                  <div className="flex items-center gap-4 shrink-0 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 pt-3 md:pt-0">
                    {/* Active Toggle Switch */}
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold tracking-wider text-slate-400">STATUS</span>
                      <button
                        onClick={() => toggleActive(tpl.id, tpl.is_active, tpl.name)}
                        className={`w-9 h-5 rounded-full p-0.5 transition-colors cursor-pointer relative ${
                          tpl.is_active ? 'bg-indigo-600' : 'bg-slate-200'
                        }`}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full shadow-3xs transition-transform transform ${
                            tpl.is_active ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    <div className="flex items-center gap-1">
                      {/* View Code Toggle */}
                      <button
                        onClick={() => setExpandedTplId(isExpanded ? null : tpl.id)}
                        className="p-1.5 hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-md text-slate-500 hover:text-slate-700 transition"
                        title={isExpanded ? '收起 Review Prompt' : '展开 Review Prompt'}
                      >
                        <FileCode className="w-3.5 h-3.5" />
                      </button>

                      {/* Edit */}
                      <button
                        onClick={() => openEditModal(tpl)}
                        className="p-1.5 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-150 rounded-md text-indigo-650 hover:text-indigo-700 transition"
                        title="编辑模板参数"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(tpl.id, tpl.name)}
                        className="p-1.5 hover:bg-rose-50 border border-slate-200 hover:border-rose-150 rounded-md text-rose-650 hover:text-rose-700 transition"
                        title="删除模板"
                        disabled={tpl.is_system}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Details Prompt Panel */}
                {isExpanded && (
                  <div className="p-4 bg-slate-50/50 p-4 border-t border-slate-100 flex flex-col gap-2">
                    <div className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                      <span>代码审计系统大模型元提示词 (review_prompt_template)</span>
                    </div>
                    <pre className="text-[11px] text-slate-600 bg-white border border-slate-200/80 rounded-lg p-3 whitespace-pre-wrap font-mono leading-relaxed max-h-[240px] overflow-y-auto">
                      {tpl.review_prompt_template}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Editor Modal Popup Container */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-205 w-full max-w-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
            {/* Modal Head */}
            <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-650 font-semibold shadow-3xs">
                  <FileJson className="w-4 h-4 text-indigo-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    {editingTemplate ? '编辑审查决策模板参数' : '部署高级自定义审查模板'}
                  </h3>
                  <p className="text-[10px] text-slate-450 font-sans mt-0.5">挂载模型规则链对所有匹配 PR 分支代码实施拦截审查与安全阻断</p>
                </div>
              </div>
              <button
                type="button"
                className="text-slate-400 hover:text-slate-600 transition p-1 rounded-lg hover:bg-slate-100/80 cursor-pointer"
                onClick={() => setIsModalOpen(false)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body Form */}
            <form onSubmit={handleSaveSubmit} className="p-6 space-y-4.5 overflow-y-auto flex-1 text-left">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Template Name */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 block">
                    模板公开名称 <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="例如: Go 微服务代码规范模板"
                    className="w-full px-3.5 py-2 text-xs bg-white text-slate-800 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 font-sans shadow-3xs/5 transition"
                  />
                </div>

                {/* Template Code */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 block">
                    特征大写标识码 (code) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value)}
                    placeholder="例如: GO_MICRO_STANDARD"
                    className="w-full px-3.5 py-2 text-xs bg-white text-slate-800 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 font-mono shadow-3xs/5 uppercase transition"
                  />
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 block">审查范围描述与核心方向</label>
                <textarea
                  rows={2}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="针对此类模板所应用的业务场景、过滤侧重点补充说明语..."
                  className="w-full px-3.5 py-2 text-xs bg-white text-slate-800 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 font-sans shadow-3xs/5 transition"
                />
              </div>

              {/* File Extensions */}
              <div className="space-y-1.5 bg-slate-50/50 p-3.5 rounded-xl border border-slate-200/60 shadow-3xs/5">
                <div className="flex justify-between items-center flex-wrap gap-1">
                  <label className="text-xs font-semibold text-slate-700 block">
                    匹配拦截文件后缀 (由英文逗号 `,` 分隔) <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[10px] text-slate-400">点击下方预设快速填入:</span>
                </div>

                {/* Preset languages click badges */}
                <div className="flex flex-wrap gap-1.5 pt-1 pb-2">
                  {LANGUAGE_PRESETS.map((p) => (
                    <button
                      key={p.name}
                      type="button"
                      onClick={() => {
                        setFormExtensionsText(p.extensions);
                        if (!formName) {
                          setFormName(`${p.name}代码规范审查模版`);
                        }
                        if (!formCode) {
                          setFormCode(p.code);
                        }
                      }}
                      className="px-2 py-0.8 rounded text-[10px] bg-white hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 text-slate-600 hover:text-indigo-650 cursor-pointer transition shadow-3xs"
                    >
                      {p.name}
                    </button>
                  ))}
                </div>

                <input
                  type="text"
                  required
                  value={formExtensionsText}
                  onChange={(e) => setFormExtensionsText(e.target.value)}
                  placeholder="ts, tsx, js, jsx, css"
                  className="w-full px-3.5 py-2 text-xs bg-white text-slate-800 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 font-mono shadow-3xs/5 transition"
                />
                <p className="text-[10.5px] text-slate-400 mt-1 leading-normal font-sans">
                  只有后缀名在列表内的修改文件，才会被大模型纳入该模板审查流程中。
                </p>
              </div>

              {/* Review Prompt Template */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-slate-700 block">
                    审查大模型系统级提示词模板 (review_prompt_template) <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[10px] text-indigo-600 font-mono font-medium">System Prompt</span>
                </div>
                <textarea
                  rows={5}
                  required
                  value={formPrompt}
                  onChange={(e) => setFormPrompt(e.target.value)}
                  placeholder="请输入用于审查的核心 Prompt..."
                  className="w-full px-3.5 py-2.5 text-xs bg-white text-slate-800 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 font-mono shadow-3xs/5 leading-relaxed transition"
                />
                <p className="text-[10px] text-slate-400">大模型扮演的角色声明、缺陷扫描深度度量标准或安全基线提示。</p>
              </div>

              {/* Status Switch Option Inside Form */}
              <div className="flex items-center justify-between bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 transition shadow-3xs">
                <div className="space-y-0.5 text-left">
                  <label className="text-xs font-bold text-slate-700 block select-none">
                    立即启用该项目审查决策模版配置 (is_active)
                  </label>
                  <p className="text-[10px] text-slate-400">
                    启用后，系统检测到匹配该后缀拦截的 PR 自动交由该模型模版流转。
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFormActive(!formActive)}
                  className={`w-9 h-5 rounded-full p-0.5 transition-colors cursor-pointer relative shrink-0 ${
                    formActive ? 'bg-indigo-650' : 'bg-slate-200'
                  }`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full shadow-3xs transition-transform transform ${
                      formActive ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Buttons panel */}
              <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-650 hover:text-slate-800 text-xs font-semibold rounded-lg cursor-pointer transition active:scale-98"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-650 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs font-bold rounded-lg cursor-pointer shadow-sm shadow-indigo-600/15 transition active:scale-98"
                >
                  确认保存并挂载到规则中
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
