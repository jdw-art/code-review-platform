/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Search,
  Plus,
  GitBranch,
  Settings,
  Trash2,
  CheckCircle,
  Play,
  FileCode,
  Link,
  Tag,
  BookOpen,
  Globe,
  Fingerprint,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { ProjectItem } from '../types';

interface ProjectManagementViewProps {
  projects: ProjectItem[];
  onToggleProject: (id: string) => void;
  onAddProject: (newProj: Omit<ProjectItem, 'id' | 'lastReviewAt' | 'scoreAverage' | 'created_at' | 'updated_at'>) => void;
  onDeleteProject: (id: string) => void;
  onTriggerReview: (id: string) => void;
}

export default function ProjectManagementView({
  projects,
  onToggleProject,
  onAddProject,
  onDeleteProject,
  onTriggerReview,
}: ProjectManagementViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLang, setSelectedLang] = useState('All');
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(6);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedLang, pageSize]);

  // Form states matching postgresql columns
  const [newName, setNewName] = useState('');
  const [newKey, setNewKey] = useState('');
  const [newPlatformType, setNewPlatformType] = useState('GitHub');
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [newBranch, setNewBranch] = useState('main');
  const [newLanguage, setNewLanguage] = useState('TypeScript');
  const [newDesc, setNewDesc] = useState('');
  const [newReviewEnabled, setNewReviewEnabled] = useState(true);

  const availableLanguages = ['All', ...Array.from(new Set(projects.map((p) => p.language || 'TypeScript')))];

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.repo_url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase());
    
    const projectLang = p.language || 'TypeScript';
    const matchesLang = selectedLang === 'All' || projectLang === selectedLang;
    return matchesSearch && matchesLang;
  });

  const totalItems = filteredProjects.length;
  const indexOfLastItem = currentPage * pageSize;
  const indexOfFirstItem = Math.max(0, indexOfLastItem - pageSize);
  const currentProjects = filteredProjects.slice(indexOfFirstItem, indexOfLastItem);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newRepoUrl.trim() || !newKey.trim()) return;

    onAddProject({
      name: newName,
      key: newKey.toUpperCase(),
      platform_type: newPlatformType,
      repo_url: newRepoUrl,
      default_branch: newBranch,
      branch: newBranch, // Backwards-compatible
      language: newLanguage, // client UI visual helper
      is_active: true,
      enabled: true, // Backwards-compatible
      review_enabled: newReviewEnabled,
      description: newDesc || 'No description provided.',
      owner: 'jdw-art',
    });

    // Reset states
    setNewName('');
    setNewKey('');
    setNewPlatformType('GitHub');
    setNewRepoUrl('');
    setNewBranch('main');
    setNewLanguage('TypeScript');
    setNewDesc('');
    setNewReviewEnabled(true);
    setShowAddForm(false);
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Page Header text details */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <FileCode className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>仓库代码项目管理</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            在此配置并开启自动 PR/MR 监听审查。核心字段已对齐 PostgreSQL <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">projects</code> 表结构。
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3.5 py-1.5 bg-[#0a0b14] hover:bg-slate-900 text-white text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>添加审查仓库</span>
        </button>
      </div>

      {/* Add New Repository Overlay Modal */}
      <AnimatePresence>
        {showAddForm && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            {/* Backdrop Layer */}
            <div className="absolute inset-0" onClick={() => setShowAddForm(false)} />
            
            <motion.div
              initial={{ scale: 0.95, y: 15, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 15, opacity: 0 }}
              transition={{ type: 'spring', duration: 0.35, bounce: 0.1 }}
              className="relative bg-white rounded-3xl w-full max-w-3xl border border-slate-250 shadow-2xl p-6 md:p-8 space-y-6 max-h-[90vh] overflow-y-auto z-10"
            >
              <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                <h4 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                  <Plus className="w-5 h-5 text-indigo-500" />
                  <span>添加新监控审查代码库</span>
                </h4>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="text-slate-400 hover:text-slate-600 font-bold p-1 cursor-pointer text-base rounded-full hover:bg-slate-100 w-8 h-8 flex items-center justify-center transition-colors border-none"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">项目名称 (name)</label>
                    <input
                      type="text"
                      required
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="例如: access-context-rbac"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">唯一项目标识代码 (key - 唯一约束)</label>
                    <input
                      type="text"
                      required
                      value={newKey}
                      onChange={(e) => setNewKey(e.target.value)}
                      placeholder="例如: ACR (须保持大写英文唯一标识)"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono font-bold outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">托管平台类型 (platform_type)</label>
                    <select
                      value={newPlatformType}
                      onChange={(e) => setNewPlatformType(e.target.value)}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                    >
                      <option value="GitHub">GitHub Platform</option>
                      <option value="GitLab">GitLab Self-hosted</option>
                      <option value="Gitea">Gitea Server</option>
                      <option value="Custom">Custom Server (其他托管)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">默认分析分支 (default_branch)</label>
                    <input
                      type="text"
                      required
                      value={newBranch}
                      onChange={(e) => setNewBranch(e.target.value)}
                      placeholder="例如: main"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 md:col-span-2 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">Git 仓库 URL (repo_url)</label>
                    <input
                      type="url"
                      required
                      value={newRepoUrl}
                      onChange={(e) => setNewRepoUrl(e.target.value)}
                      placeholder="例如: https://github.com/jdw-art/access-context-rbac.git"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">偏好展示主要语言</label>
                    <select
                      value={newLanguage}
                      onChange={(e) => setNewLanguage(e.target.value)}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                    >
                      <option value="TypeScript">TypeScript</option>
                      <option value="React">React/JSX</option>
                      <option value="Go">Go Language</option>
                      <option value="Python">Python</option>
                      <option value="Java">Java</option>
                      <option value="Rust">Rust</option>
                      <option value="SQL">Postgres/SQL</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">是否启用审查拦截 (review_enabled)</label>
                    <select
                      value={newReviewEnabled ? 'true' : 'false'}
                      onChange={(e) => setNewReviewEnabled(e.target.value === 'true')}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                    >
                      <option value="true">是 (主动挂载 LLM 机器人)</option>
                      <option value="false">否 (只同步分析不触发审查)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 md:col-span-2 text-left">
                    <label className="text-[11px] font-bold text-slate-700 block">项目说明 (description)</label>
                    <input
                      type="text"
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                      placeholder="例如: 用于验证 RBAC 初始化树的独立编译模块"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-semibold select-none transition cursor-pointer"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-2xs select-none transition cursor-pointer"
                  >
                    确认保存
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Toolbar filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white px-6 py-4 rounded-xl border border-slate-200/85">
        {/* Search */}
        <div className="relative w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索项目名称、唯一标识 key 或是 仓库链接..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 text-slate-800 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-xs"
          />
        </div>

        {/* Filters */}
        <div className="flex gap-2 items-center w-full md:w-auto overflow-x-auto select-none">
          {availableLanguages.map((lang) => (
            <button
              key={lang}
              onClick={() => setSelectedLang(lang)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-all shrink-0 ${
                selectedLang === lang
                  ? 'bg-indigo-500/10 text-indigo-600 font-bold border border-indigo-200'
                  : 'bg-slate-50 text-slate-500 hover:text-slate-800 border border-slate-200/60'
              }`}
            >
              {lang === 'All' ? '全部语言' : lang}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Projects */}
      {currentProjects.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-xs shadow-3xs">
          暂无匹配的项目库数据
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {currentProjects.map((p) => {
              const isEnabled = p.enabled ?? true;
              const isReviewEnabled = p.review_enabled ?? true;
              return (
                <div
                  key={p.id}
                  className={`bg-white rounded-2xl border transition-all flex flex-col justify-between overflow-hidden shadow-xs hover:shadow-md ${
                    isEnabled ? 'border-slate-200/80' : 'border-slate-200/50 opacity-80'
                  }`}
                >
                  {/* Top Indicator */}
                  <div className="p-6 space-y-4">
                    <div className="flex justify-between items-start gap-4">
                      <div className="space-y-1 grow min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-slate-100 font-bold border border-slate-200 rounded text-slate-500 px-1 font-mono">
                            {p.platform_type || 'GitHub'}
                          </span>
                          <span className="text-[10px] bg-indigo-50 font-bold text-indigo-600 px-1.5 py-0.2 rounded font-mono">
                            KEY: {p.key}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 truncate flex items-center gap-1.5 mt-1.5">
                          <FileCode className="w-4 h-4 text-indigo-500 shrink-0" />
                          <span>{p.name}</span>
                        </h3>
                      </div>

                      {/* Status Toggle Button visualizer */}
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <button
                          type="button"
                          onClick={() => onToggleProject(p.id)}
                          className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                            isEnabled ? 'bg-emerald-500' : 'bg-slate-300'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                              isEnabled ? 'translate-x-5' : 'translate-x-0'
                            }`}
                          />
                        </button>
                        <span className="text-[8.5px] font-mono text-slate-450 uppercase font-semibold">
                          {isEnabled ? 'is_active: t' : 'is_active: f'}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-500 leading-relaxed font-light min-h-[40px]">
                      {p.description}
                    </p>

                    {/* Tag and path descriptors */}
                    <div className="space-y-2 pt-2 border-t border-slate-100/80">
                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400 flex items-center gap-1">主要语言 <code className="text-[9px] text-slate-400 font-mono">(language)</code></span>
                        <span className="font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-sm text-[10px]">
                          {p.language || 'TypeScript'}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400 flex items-center gap-1">主审核状态 <code className="text-[9px] text-slate-400 font-mono">(review_enabled)</code></span>
                        <span className={`font-semibold text-[10px] ${isReviewEnabled ? 'text-emerald-600' : 'text-slate-400'}`}>
                          {isReviewEnabled ? '开启审查中' : '已禁用审查'}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400">平均评分指标</span>
                        <span className="font-bold text-indigo-600 font-mono text-[11px]">
                          {p.scoreAverage ? `${p.scoreAverage}分` : '暂无数据'}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400">最近审查时间</span>
                        <span className="text-slate-650 font-mono text-[10px]">
                          {p.lastReviewAt ? p.lastReviewAt : '从未审查'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Actions layout */}
                  <div className="px-6 py-4 bg-slate-50 border-t border-slate-100/80 flex justify-between items-center">
                    <span className="text-[10px] text-slate-400 font-mono bg-slate-200 px-1.5 py-0.5 rounded-xs truncate max-w-[120px]">
                      ID: {p.id} / 归属: {p.owner || 'jdw-art'}
                    </span>

                    <div className="flex gap-2">
                       <button
                        onClick={() => onTriggerReview(p.id)}
                        disabled={!isEnabled}
                        title="立即触发 AI 代码全量审查"
                        className="p-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>立即监测</span>
                      </button>

                      <button
                        onClick={() => onDeleteProject(p.id)}
                        title="移除此审查配置"
                        className="p-1.5 hover:bg-red-50 text-slate-400 hover:text-red-600 rounded-lg cursor-pointer transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination bar */}
          {(() => {
            const totalPages = Math.ceil(totalItems / pageSize) || 1;
            return (
              <div className="flex flex-col sm:flex-row items-center justify-between border border-slate-200 bg-white px-6 py-4 rounded-2xl text-xs gap-4 select-none shadow-3xs">
                <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                  <div>
                    显示 <span className="font-semibold text-slate-800">{indexOfFirstItem + 1}</span> 至{' '}
                    <span className="font-semibold text-slate-800">{Math.min(indexOfLastItem, totalItems)}</span> 个，
                    共 <span className="font-semibold text-slate-800">{totalItems}</span> 个项目库
                  </div>
                  <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                    <span>每页显示:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className="border border-slate-200 bg-slate-50 text-slate-800 rounded-md px-2 py-1 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    >
                      <option value={3}>3 条</option>
                      <option value={6}>6 条</option>
                      <option value={12}>12 条</option>
                      <option value={24}>24 条</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>上一页</span>
                  </button>
                  <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                    <span className="font-bold text-indigo-605">{currentPage}</span>
                    <span className="text-slate-300">/</span>
                    <span>{totalPages}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <span>下一页</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
