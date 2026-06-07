/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Cpu, CheckCircle2, AlertCircle, Plus, Sliders, RefreshCcw, Layout, Network, Key, StickyNote, Edit2, Trash2 } from 'lucide-react';
import { ModelConfig } from '../types';

interface ModelManagementViewProps {
  models: ModelConfig[];
  onActivateModel: (id: string) => void;
  onAddModel: (newModel: Omit<ModelConfig, 'id' | 'created_at' | 'updated_at'>) => void;
  onUpdateModelParams: (id: string, temp: number, tokens: number) => void;
  onUpdateModel?: (updatedModel: ModelConfig) => void;
  onDeleteModel?: (id: string) => void;
}

export default function ModelManagementView({
  models,
  onActivateModel,
  onAddModel,
  onUpdateModelParams,
  onUpdateModel,
  onDeleteModel,
}: ModelManagementViewProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null);

  // Form states aligned with llm_models table columns
  const [mName, setMName] = useState('');
  const [mProvider, setMProvider] = useState('Gemini');
  const [mModelCode, setMModelCode] = useState('gemini-2.5-pro');
  const [mBaseUrl, setMBaseUrl] = useState('');
  const [mApiKeyMasked, setMApiKeyMasked] = useState('••••••••••••••••');
  const [mTemp, setMTemp] = useState(0.2);
  const [mTokens, setMTokens] = useState(16384);
  const [mPromptTemplate, setMPromptTemplate] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!mName.trim() || !mModelCode.trim()) return;

    onAddModel({
      name: mName,
      provider: mProvider,
      model_code: mModelCode,
      base_url: mBaseUrl,
      api_key_masked: mApiKeyMasked,
      temperature: mTemp,
      max_tokens: mTokens,
      prompt_template: mPromptTemplate,
      is_default: false,
      is_active: false,
      isActive: false, // backwards compatibility
      queriesCount: 0,
    });

    setMName('');
    setMModelCode('');
    setMBaseUrl('');
    setMPromptTemplate('');
    setShowAddForm(false);
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header Block info */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5 font-sans">
            <Cpu className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>审查模型与计算智能矩阵</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            配置并调整用于自动代码审查的 LLM 模型。参数属性对齐 PostgreSQL <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">llm_models</code> 表结构。
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3.5 py-1.5 bg-[#0c0d1b] hover:bg-slate-900 text-white text-[11px] font-bold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>部署新模型智算</span>
        </button>
      </div>

      {/* Add New Model Overlay Modal */}
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
              <div className="flex justify-between items-center border-b border-slate-150 pb-3">
                <h4 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                  <Plus className="w-5 h-5 text-indigo-500" />
                  <span>部署新的审查 AI 节点</span>
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-left">
                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      模型展示别名 (name)
                    </label>
                    <input
                      type="text"
                      required
                      value={mName}
                      onChange={(e) => setMName(e.target.value)}
                      placeholder="例如: DeepSeek R1 满血版"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      接口提供商 (provider)
                    </label>
                    <select
                      value={mProvider}
                      onChange={(e) => setMProvider(e.target.value)}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 outline-hidden focus:ring-2 focus:ring-indigo-55"
                    >
                      <option value="Gemini">Google Gemini SDK</option>
                      <option value="DeepSeek">DeepSeek API</option>
                      <option value="OpenAI">OpenAI Endpoint</option>
                      <option value="Custom">接入自建大模型</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      唯一接口代码标识 (model_code)
                    </label>
                    <input
                      type="text"
                      required
                      value={mModelCode}
                      onChange={(e) => setMModelCode(e.target.value)}
                      placeholder="例如: deepseek-reasoner"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      自建 Base URL 端点 (可选) (base_url)
                    </label>
                    <input
                      type="text"
                      value={mBaseUrl}
                      onChange={(e) => setMBaseUrl(e.target.value)}
                      placeholder="https://api.deepseek.com/v1"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      密钥令牌掩码 (加密保存) (api_key_masked)
                    </label>
                    <input
                      type="password"
                      required
                      value={mApiKeyMasked}
                      onChange={(e) => setMApiKeyMasked(e.target.value)}
                      placeholder="自动保存加密上下文"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      核温系数 (temperature)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="1.5"
                      value={mTemp}
                      onChange={(e) => setMTemp(parseFloat(e.target.value))}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      约束标记 (max_tokens)
                    </label>
                    <input
                      type="number"
                      step="1024"
                      min="1024"
                      max="131072"
                      value={mTokens}
                      onChange={(e) => setMTokens(parseInt(e.target.value))}
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-[11px] font-bold text-slate-700 block">
                      特选 Prompt 模板 (可选) (prompt_template)
                    </label>
                    <input
                      type="text"
                      value={mPromptTemplate}
                      onChange={(e) => setMPromptTemplate(e.target.value)}
                      placeholder="不填则使用系统预置 project_templates 主模板"
                      className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:ring-2 focus:ring-indigo-55 focus:border-indigo-55 outline-hidden"
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
                    部署生效
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Model Cards List Grid (Compact 3-column Layout) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-12">
        {models.map((model) => {
          const isActiveNode = model.is_active ?? model.isActive ?? false;
          const isDefaultNode = model.is_default ?? false;
          return (
            <div
              key={model.id}
              className={`bg-white rounded-2xl p-6 border transition-all flex flex-col justify-between space-y-5 ${
                isActiveNode
                  ? 'border-indigo-500 ring-2 ring-indigo-500/5 shadow-md'
                  : 'border-slate-200 shadow-xs hover:border-slate-300'
              }`}
            >
              <div className="space-y-4">
                {/* Header Row: Provider Badge and Active Status Toggle */}
                <div className="flex justify-between items-center gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[9px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 bg-slate-100 text-slate-600 rounded-sm truncate">
                      {model.provider}
                    </span>
                    {isDefaultNode && (
                      <span className="text-[9px] font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded-sm border border-indigo-100/60 shrink-0">
                        DEFAULT
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => onActivateModel(model.id)}
                    className={`px-2.5 py-1 flex items-center gap-1.5 text-[10px] font-bold rounded-full border cursor-pointer shrink-0 transition-colors ${
                      isActiveNode
                        ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                        : 'text-indigo-600 bg-white border-indigo-200 hover:bg-indigo-50'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${isActiveNode ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`}></span>
                    <span>{isActiveNode ? '活动中' : '设为激活'}</span>
                  </button>
                </div>

                {/* Model Title and code identifier */}
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="truncate">{model.name}</span>
                  </h3>
                  <p className="text-[10px] font-mono text-slate-400 truncate">CODE: {model.model_code}</p>
                </div>

                {/* Parameters configuration read-only blocks */}
                <div className="space-y-2 pt-3 border-t border-slate-100 text-[11px] text-slate-600">
                  <div className="flex justify-between font-light">
                    <span className="text-slate-450">接口端点 (base_url)</span>
                    <span className="font-mono text-slate-700 max-w-[130px] truncate" title={model.base_url || '系统集成 SDK'}>
                      {model.base_url || '系统集成 SDK'}
                    </span>
                  </div>

                  <div className="flex justify-between font-light">
                    <span className="text-slate-450">采样核温 (temperature)</span>
                    <span className="font-semibold text-slate-800 font-mono">{model.temperature}</span>
                  </div>

                  <div className="flex justify-between font-light">
                    <span className="text-slate-450">标记限制 (max_tokens)</span>
                    <span className="font-semibold text-slate-800 font-mono">{model.max_tokens}</span>
                  </div>

                  <div className="flex justify-between font-light">
                    <span className="text-slate-450">累计调阅 (queries)</span>
                    <span className="font-semibold text-indigo-600 font-mono">{model.queriesCount ?? 0} 次</span>
                  </div>

                  <div className="flex justify-between font-light items-center pt-1.5">
                    <span className="text-slate-450">最近校验状态</span>
                    <span className="text-emerald-600 font-medium text-[9.5px] flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>通过 (PASSED)</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Robust Footer Action buttons */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setEditingModel(model)}
                  className="flex-1 py-1.5 bg-slate-50 hover:bg-indigo-50/50 hover:text-indigo-600 text-slate-600 text-[11px] font-semibold rounded-xl border border-slate-200 transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-3xs"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  <span>编辑参数配置</span>
                </button>

                {!isDefaultNode && onDeleteModel && (
                  <button
                    type="button"
                    onClick={() => onDeleteModel(model.id)}
                    className="p-1.5 text-rose-600 bg-rose-50/30 hover:bg-rose-50 border border-transparent hover:border-rose-200 rounded-xl transition-all cursor-pointer"
                    title="注销删除此模型"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Elegant Edit Overlay Modal Dialog */}
      {editingModel && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl w-full max-w-2xl border border-slate-250 shadow-2xl p-6 md:p-8 space-y-5 animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                <Edit2 className="w-5 h-5 text-indigo-500" />
                <span>编辑智算审查节点配置 ({editingModel.name})</span>
              </h3>
              <button
                onClick={() => setEditingModel(null)}
                className="text-slate-400 hover:text-slate-600 font-bold p-1 cursor-pointer text-base rounded-full hover:bg-slate-100 w-8 h-8 flex items-center justify-center transition-colors"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (onUpdateModel) {
                  onUpdateModel(editingModel);
                }
                setEditingModel(null);
              }}
              className="space-y-5"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">模型展示别名 (name)</label>
                  <input
                    type="text"
                    required
                    value={editingModel.name}
                    onChange={(e) => setEditingModel({ ...editingModel, name: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-sans outline-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">接口提供商 (provider)</label>
                  <select
                    value={editingModel.provider}
                    onChange={(e) => setEditingModel({ ...editingModel, provider: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-sans outline-indigo-500 focus:border-indigo-500"
                  >
                    <option value="Gemini">Google Gemini SDK</option>
                    <option value="DeepSeek">DeepSeek API</option>
                    <option value="OpenAI">OpenAI Endpoint</option>
                    <option value="Custom">接入自建大模型</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">唯一代码标识 (model_code)</label>
                  <input
                    type="text"
                    required
                    value={editingModel.model_code}
                    onChange={(e) => setEditingModel({ ...editingModel, model_code: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono outline-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">自建 Base URL 端点 (可选)</label>
                  <input
                    type="text"
                    value={editingModel.base_url || ''}
                    onChange={(e) => setEditingModel({ ...editingModel, base_url: e.target.value })}
                    placeholder="系统默认集成 SDK"
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono outline-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">密钥令牌掩码 (api_key_masked)</label>
                  <input
                    type="text"
                    required
                    value={editingModel.api_key_masked || ''}
                    onChange={(e) => setEditingModel({ ...editingModel, api_key_masked: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-mono outline-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5 font-sans">
                  <label className="text-[11px] font-bold text-slate-700 block">特选模板 (prompt_template)</label>
                  <input
                    type="text"
                    value={editingModel.prompt_template || ''}
                    onChange={(e) => setEditingModel({ ...editingModel, prompt_template: e.target.value })}
                    placeholder="缺省：使用核心工程配置模版"
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 font-sans outline-indigo-500 focus:border-indigo-500 align-middle"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">采样核温 (temperature)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1.5"
                    value={editingModel.temperature}
                    onChange={(e) => setEditingModel({ ...editingModel, temperature: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-700 block">标记限制 (max_tokens)</label>
                  <input
                    type="number"
                    step="1024"
                    min="1024"
                    max="131072"
                    value={editingModel.max_tokens}
                    onChange={(e) => setEditingModel({ ...editingModel, max_tokens: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingModel(null)}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-semibold select-none transition cursor-pointer"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-2xs select-none transition cursor-pointer"
                >
                  保存更新
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
