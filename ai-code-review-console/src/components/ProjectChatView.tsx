/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Send,
  Plus,
  Trash2,
  Cpu,
  User,
  Bot,
  Sparkles,
  GitBranch,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Code2,
  Terminal,
  Activity,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
} from 'lucide-react';
import { ProjectItem } from '../types';

interface ProjectChatViewProps {
  project: ProjectItem;
  onBackToProjects: () => void;
  onAddLog?: (action: string, details: string) => void;
}

interface ChatSession {
  id: string;
  projectId: string;
  title: string;
  branch: string;
  createdAt: string;
  messages: ChatMessage[];
}

interface TraceStep {
  name: string;
  status: 'pending' | 'loading' | 'success' | 'failed';
  duration?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  trace?: {
    thought: string;
    steps: TraceStep[];
  };
}

const DEFAULT_BRANCH_OPTIONS = ['main', 'dev', 'master', 'feature-rbac', 'bugfix-auth', 'release-v1.0'];

export default function ProjectChatView({ project, onBackToProjects, onAddLog }: ProjectChatViewProps) {
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const saved = localStorage.getItem(`chat_sessions_${project.id}`);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // ignore
      }
    }
    return [];
  });

  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const saved = localStorage.getItem(`active_session_id_${project.id}`);
    return saved || null;
  });

  // Sidebar Layout optimization states
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(() => {
    // Show configuration form automatically if no sessions exist
    const saved = localStorage.getItem(`chat_sessions_${project.id}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.length === 0;
      } catch (e) {}
    }
    return true;
  });

  // Create Session Form states
  const [newTitle, setNewTitle] = useState(() => {
    const isDefaultMain = project.default_branch || 'main';
    return `${isDefaultMain}分支仓库助手`;
  });
  const [selectedBranch, setSelectedBranch] = useState(project.default_branch || 'main');
  const [customBranchInput, setCustomBranchInput] = useState('');
  const [showCustomBranch, setShowCustomBranch] = useState(false);

  // Message Sending Form state
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentTraceSteps, setCurrentTraceSteps] = useState<TraceStep[]>([]);
  const [traceExpanded, setTraceExpanded] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync sessions to localStorage
  useEffect(() => {
    localStorage.setItem(`chat_sessions_${project.id}`, JSON.stringify(sessions));
    if (activeSessionId) {
      localStorage.setItem(`active_session_id_${project.id}`, activeSessionId);
    } else {
      localStorage.removeItem(`active_session_id_${project.id}`);
    }
  }, [sessions, activeSessionId, project.id]);

  // Scroll to bottom helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessions, activeSessionId, streamingContent, currentTraceSteps]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  // Handle Session Creation
  const handleCreateSession = (e: React.FormEvent) => {
    e.preventDefault();
    const branchToUse = showCustomBranch && customBranchInput.trim() ? customBranchInput.trim() : selectedBranch;
    const titleToUse = newTitle.trim() || `${branchToUse}分支仓库助手`;

    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      projectId: project.id,
      title: titleToUse,
      branch: branchToUse,
      createdAt: new Date().toISOString().replace('T', ' ').slice(0, 16),
      messages: [
        {
          id: `msg-init-${Date.now()}`,
          role: 'assistant',
          content: `你好！我是针对该项目的专属大语言模型审查代理。当前对话已锁定代码仓库的 **${branchToUse}** 分支。
          
我已经索引了您的项目资源 [\`${project.name}\`] \`${project.repo_url}\`。
          
您可以向我提问关于本分支下的任何技术结构疑问。比如：
1. **"介绍一下这个仓库的核心功能和架构层级。"**
2. **"分析一波这个分支中可能存在的安全漏洞和重构缺陷。"**
3. **"如何针对该分支写一套完整的单元测试校验？"**`,
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
          trace: {
            thought: '模型冷启动，已同步代码仓库并索引相关资源文件',
            steps: [
              { name: '建立仓库只读克隆缓存', status: 'success', duration: '122ms' },
              { name: `锁定仓库目标分支 [${branchToUse}]`, status: 'success', duration: '45ms' },
              { name: '扫描 AST 结构并提取函数签名', status: 'success', duration: '190ms' },
            ],
          },
        },
      ],
    };

    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    if (onAddLog) {
      onAddLog('CHAT_SESSION_CREATED', `创建了针对项目 ${project.name} (分支: ${branchToUse}) 的对话会话.`);
    }

    // Reset title text
    setNewTitle(`${branchToUse}分支仓库助手`);
    setShowCreateForm(false);
  };

  // Delete Session
  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('确定要删除此对话会话吗？历史消息将全部被清空。')) {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
      if (onAddLog) {
        onAddLog('CHAT_SESSION_DELETED', `删除了项目 ${project.name} 的对话会话 ${sessionId}.`);
      }
    }
  };

  // Simulated streaming output generator based on project context
  const getSimulatedResponse = (userMsg: string, branch: string): { content: string; steps: TraceStep[] } => {
    const q = userMsg.toLowerCase();
    const projName = project.name;

    let responseText = '';
    let steps: TraceStep[] = [];

    // Base steps for any AI response
    steps = [
      { name: `抓取本地 git 缓存的分支 [${branch}] 状态`, status: 'success', duration: '85ms' },
      { name: '对比提交差异 (git diff HEAD)', status: 'success', duration: '102ms' },
      { name: '代码语义索引检索 & 关联核心客体', status: 'success', duration: '160ms' },
      { name: '加载定制大语言模型「Gemini 2.5 Pro」推理引擎', status: 'success', duration: '280ms' },
    ];

    if (q.includes('核心功能') || q.includes('架构') || q.includes('功能和架构') || q.includes('做什么') || q.includes('介绍')) {
      responseText = `### 📦 \`${projName}\` 专属代码分析报告 [分支: ${branch}]

围绕您的项目，我已经完成了全面的语义和静态抽象语法树(AST)索引。以下是为您梳理的架构特征：

1. **项目定位与核心使命**:
   * **项目名**: \`${project.name}\`
   * **开发主导语言**: \`${project.language || 'TypeScript'}\`
   * **说明**: ${project.description}

2. **代码库关键模块与文件分布 (AI 静态推演)**:
   * **开发视图层**: 主要是面向高效敏捷的模块化划分。
   * **类型定义**: 统一收拢于主模块以规范接口输入。
   * **功能机制**: 预置了细粒度的属性约束检查。

3. **重构建议**:
   * 当前代码组织良好，但对于大规模的高并发支持，建议在处理管道上增加自适应节流阀；
   * 接口级属性可以进一步合并，以规避重复转译的额外开销。`;
    } else if (q.includes('安全') || q.includes('漏洞') || q.includes('bug') || q.includes('缺陷') || q.includes('重构')) {
      let specificLeak = '';
      if (projName === 'access-context-rbac') {
        specificLeak = `* **[严重级: 高] JWT与上下文认证越权漏洞**: 在 \`ContextMatcher\` 类中，角色属性在匹配时存在未隔离外部入参的风险，可能导致管理员操作接口被低特权用户绕过；
   * **防范方案**: 应在鉴权拦截器中强制转换为不可变的上下文信息，切断入参污染途径。`;
      } else if (projName === 'local-postgres-syncer') {
        specificLeak = `* **[严重级: 中] SQL 参数拼接注入隐患**: 在同步数据库模式时，部分 DDL 触发器是由字符串模板动态渲染拼接的；
   * **防范方案**: 建议改用预编译防注入参数绑定语法，或在 Drizzle / SQL 端加入元数据严格转义策略。`;
      } else if (projName === 'ai-code-reviewer') {
        specificLeak = `* **[严重级: 低] API 请求超时导致的连接池枯竭**: 针对大文件全量审查时，代理节点串行处理，可能会阻塞后续触发器的回调。
   * **防范方案**: 建议增加自适应超时退避，重构为基于 Redis 等队列的异步分析模式。`;
      } else {
        specificLeak = `* **[严重级: 中] 静态依赖缺失与内存泄漏**: 大量监听器在项目销毁时缺少反注册操作，可能会持续占用运行时内存。
   * **防范方案**: 应确保在析构函数或垃圾回收钩子中显式释放所有的文件轮询器和系统桥接服务。`;
      }

      responseText = `### 🛡️ 代码安全与质量缺陷报告 [分支: ${branch}]

已针对该分支拉取最新的 \`HEAD\` 提交并启动安全探针分析。以下是重点排查结果：

1. **发现的主要安全缺陷**:
${specificLeak}

2. **静态代码层面的重构要点 (AST 分析)**:
   * **大文件检测**: 部分组件长度超过 400 行，违反单职责设计原则，可合理拆分为独立逻辑；
   * **变量泄露**: 发现了部分存在作用域不纯粹的临时变量，极易引发无限循环，应当使用原始类型或只读代理保护。

3. **修复引导**:
\`\`\`typescript
// 安全修补示例
export function sanitizeContext(input: RawContext): SafeContext {
  return {
    userId: String(input.userId).replace(/[^a-zA-Z0-9_-]/g, ''),
    roleCode: String(input.roleCode).trim(),
    actionAllowed: Array.isArray(input.actions) ? [...input.actions] : []
  };
}
\`\`\`
*(注意：以上修补方案已兼容您的项目环境。)*`;
    } else if (q.includes('测试') || q.includes('单元测试') || q.includes('test') || q.includes('用例')) {
      responseText = `### 🧪 \`${projName}\` 单元测试方案推荐 [分支: ${branch}]

针对当前分支的代码，推荐采用以下全栈测试套件进行覆盖验证：

1. **测试框架技术选型**:
   * 对于该技术栈项目，首选 **Jest** 或 **Vitest**；
   * 采用 \`ts-jest\` 作为 TypeScript 转译预处理器，保障强类型检查在测试执行中不丢失。

2. **单元测试编写模版 (AST 匹配提取)**:
\`\`\`typescript
import { describe, it, expect, vi } from 'vitest';
import { handleTriggerReview } from './actions';

describe('Project Review Audit Core', () => {
  it('should correctly compound state scores within 75 to 99 range', async () => {
    const mockProject = { id: 'test-1', name: 'demo-repo' };
    const result = await handleTriggerReview(mockProject.id);
    
    expect(result.score).toBeGreaterThanOrEqual(75);
    expect(result.score).toBeLessThanOrEqual(100);
    expect(result.status).not.toBeNull();
  });
});
\`\`\`

3. **集成自动化测试流水线 (CI/CD)**:
   * 建议在 \`.github/workflows/\` 下新建监控拉取动作，每次向 \`${branch}\` 提 PR 时，均阻断式执行本测试。`;
    } else {
      responseText = `### 🤝 您好！我已接收到您的核心诉求

因为当前会话锁定在了项目的 **\`${branch}\`** 分支，针对您说的主题：*"${userMsg}"*，我已将对应的上下文链对齐。

1. **项目状态对齐**:
   * 关联仓库：\`${project.name}\` (\`${project.language || 'TypeScript'}\`)
   * 当前连接会话：\`${activeSession?.title || '未命名'}\`

2. **解答导言**:
   为了更精准地解决该疑问，建议您进一步指定相关的范围。通常我会提供深入的方法级审计、安全漏洞修复，或者是编写测试脚手架的能力。

您是否希望我：
* **提取该分支下的核心函数并编写详细文档**？
* **审查并自动重组现有的鉴权/核心处理环路**？
* **提供多端自动化机器人在本分支的监听挂载配置**？

请随时告诉我！`;
    }

    return { content: responseText, steps };
  };

  // Handle Send Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !activeSessionId || isStreaming) return;

    const userMessageText = inputMessage;
    setInputMessage('');
    setIsStreaming(true);
    setStreamingContent('');

    // Append user message immediately
    const userMessage: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: userMessageText,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
    };

    // Update session messages locally
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          return { ...s, messages: [...s.messages, userMessage] };
        }
        return s;
      })
    );

    // Get mock target response
    const { content: assistantResponseText, steps: finalSteps } = getSimulatedResponse(
      userMessageText,
      activeSession?.branch || 'main'
    );

    // Prepare steps loading visualization
    const stepsToDisplay: TraceStep[] = finalSteps.map((step) => ({ ...step, status: 'pending' }));
    setCurrentTraceSteps(stepsToDisplay);

    // Sequence through loading steps to look super realistic
    for (let i = 0; i < stepsToDisplay.length; i++) {
      setCurrentTraceSteps((prevSteps) => {
        const copy = [...prevSteps];
        copy[i] = { ...copy[i], status: 'loading' };
        return copy;
      });
      // wait a bit
      await new Promise((resolve) => setTimeout(resolve, 350));

      setCurrentTraceSteps((prevSteps) => {
        const copy = [...prevSteps];
        copy[i] = { ...copy[i], status: 'success' };
        return copy;
      });
    }

    // Now stream the response
    let charIndex = 0;
    const typingSpeed = 15; // ms per character
    const streamInterval = setInterval(() => {
      if (charIndex < assistantResponseText.length) {
        setStreamingContent((prev) => prev + assistantResponseText.charAt(charIndex));
        charIndex++;
      } else {
        clearInterval(streamInterval);
        setIsStreaming(false);

        // Save completed streaming message into session history
        const assistantMessage: ChatMessage = {
          id: `msg-ai-${Date.now()}`,
          role: 'assistant',
          content: assistantResponseText,
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
          trace: {
            thought: '分析匹配关联的静态源码树和模板结构',
            steps: finalSteps,
          },
        };

        setSessions((prev) =>
          prev.map((s) => {
            if (s.id === activeSessionId) {
              return { ...s, messages: [...s.messages, assistantMessage] };
            }
            return s;
          })
        );
        setStreamingContent('');
        setCurrentTraceSteps([]);

        if (onAddLog) {
          onAddLog('CHAT_COMPLETED', `完成了针对 ${project.name} 分支 ${activeSession?.branch} 的一轮 AI 会话交互`);
        }
      }
    }, typingSpeed);
  };

  const currentBranches = DEFAULT_BRANCH_OPTIONS.includes(project.default_branch || 'main')
    ? DEFAULT_BRANCH_OPTIONS
    : [project.default_branch || 'main', ...DEFAULT_BRANCH_OPTIONS.filter((b) => b !== project.default_branch)];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4 animate-in fade-in duration-300">
      {/* Upper Navigation Card - Compact Optimized Layout */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white py-3 px-5 rounded-xl border border-slate-200/90 shadow-3xs gap-3">
        <div className="flex items-center gap-3.5 min-w-0">
          <button
            onClick={onBackToProjects}
            className="p-1 px-2 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-700 rounded-lg transition-all cursor-pointer flex items-center gap-1 text-[11px] font-semibold tracking-tight shrink-0 shadow-3xs"
            title="返回项目管理"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>返回</span>
          </button>
          <div className="flex items-center gap-2 min-w-0 flex-wrap">
            <h2 className="text-[14px] font-bold text-slate-800 animate-in slide-in-from-left duration-200">仓库对话工作区</h2>
            <span className="text-[10px] bg-indigo-600 text-white font-bold px-2 py-0.5 rounded font-mono shadow-3xs shrink-0">
              {project.name}
            </span>
            <span className="text-slate-300 hidden md:inline">|</span>
            <p className="text-[11px] text-slate-400 truncate hidden md:inline leading-none">
              对当前项目进行自动多轮审计与架构重构安全演练
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-auto">
          <span className={`w-1.5 h-1.5 rounded-full ${activeSession ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}`} />
          <span className="text-[10px] text-slate-550 font-bold font-mono tracking-wider">
            STATUS: {isStreaming ? 'STREAMING' : activeSession ? 'CONNECTED' : 'STANDBY'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Control Panel Column (Slim 3-col width structure) */}
        {sidebarOpen && (
          <div className="lg:col-span-3 space-y-4 animate-in fade-in slide-in-from-left duration-200">
            {/* Create Session Control */}
            {!showCreateForm ? (
              <button
                type="button"
                onClick={() => setShowCreateForm(true)}
                className="w-full py-2.5 px-4 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-xs font-bold border border-indigo-150 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-2xs active:scale-[0.98]"
              >
                <Plus className="w-4 h-4" />
                <span>+ 新建仓库对话</span>
              </button>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3.5">
                <div className="flex justify-between items-center border-b border-slate-100 pb-1.5">
                  <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Plus className="w-3.5 h-3.5 text-indigo-500" />
                    <span>配置新会话</span>
                  </h3>
                  {sessions.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setShowCreateForm(false)}
                      className="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer hover:underline"
                    >
                      取消
                    </button>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 leading-relaxed">
                  对话在整个生命周期内锁定到特定分支，安全分析与重构推演均在此范围内生效。
                </p>

                <form onSubmit={handleCreateSession} className="space-y-3">
                  {/* Session Title */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-650 block">会话标题</label>
                    <input
                      type="text"
                      required
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder="例如: 主分支仓库助手"
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-md focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-slate-800 font-semibold"
                    />
                  </div>

                  {/* Select Branch */}
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <label className="text-[10px] font-bold text-slate-650">选择目标分支</label>
                      <button
                        type="button"
                        onClick={() => {
                          setShowCustomBranch(!showCustomBranch);
                          if (!showCustomBranch) {
                            setNewTitle(`${customBranchInput || 'custom'}分支仓库助手`);
                          } else {
                            setNewTitle(`${selectedBranch}分支仓库助手`);
                          }
                        }}
                        className="text-[9px] text-indigo-600 hover:underline cursor-pointer"
                      >
                        {showCustomBranch ? '预选列表' : '自定义分支'}
                      </button>
                    </div>

                    {!showCustomBranch ? (
                      <select
                        value={selectedBranch}
                        onChange={(e) => {
                          setSelectedBranch(e.target.value);
                          setNewTitle(`${e.target.value}分支仓库助手`);
                        }}
                        className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-md focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-slate-800 font-semibold"
                      >
                        {currentBranches.map((b) => (
                          <option key={b} value={b}>
                            {b === project.default_branch ? `${b} (默认)` : b}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="relative">
                        <input
                          type="text"
                          value={customBranchInput}
                          onChange={(e) => {
                            setCustomBranchInput(e.target.value);
                            setNewTitle(`${e.target.value || 'custom'}分支仓库助手`);
                          }}
                          placeholder="例如: feature/rbac"
                          className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-md focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-slate-800 font-mono"
                        />
                        <GitBranch className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-2.5" />
                      </div>
                    )}
                  </div>

                  {/* Create Button */}
                  <button
                    type="submit"
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold cursor-pointer transition-all hover:shadow-xs active:scale-[0.98] flex items-center justify-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>启动持续对话</span>
                  </button>
                </form>
              </div>
            )}

            {/* Existing Sessions Container */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
              <div className="flex justify-between items-center border-b border-slate-100 pb-1.5">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-indigo-500" />
                  <span>已有对话记录</span>
                </h3>
                <span className="text-[10px] text-slate-400 font-mono bg-slate-50 px-1.5 py-0.2 rounded border border-slate-200/50">
                  {sessions.length}
                </span>
              </div>

              {sessions.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400 leading-relaxed">
                  还没有建立过会话，可以在上面“新建对话”。
                </div>
              ) : (
                <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                  {sessions.map((s) => {
                    const isActive = s.id === activeSessionId;
                    return (
                      <div
                        key={s.id}
                        onClick={() => {
                          setActiveSessionId(s.id);
                          setShowCreateForm(false);
                        }}
                        className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all flex justify-between items-center group ${
                          isActive
                            ? 'border-indigo-300 bg-indigo-50/45 shadow-2xs'
                            : 'border-slate-100 hover:bg-slate-50'
                        }`}
                      >
                        <div className="space-y-1 grow min-w-0 pr-2">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                            <h4 className={`text-xs truncate block ${isActive ? 'font-bold text-indigo-950' : 'text-slate-700 font-medium'}`}>
                              {s.title}
                            </h4>
                          </div>
                          <div className="flex items-center gap-1 text-[9px] text-slate-450 font-mono pl-5">
                            <GitBranch className="w-2.5 h-2.5 text-indigo-500 shrink-0" />
                            <span className="truncate max-w-[70px]">{s.branch}</span>
                            <span className="text-slate-300">•</span>
                            <span className="shrink-0">{s.createdAt.slice(5)}</span>
                          </div>
                        </div>

                        <button
                          onClick={(e) => handleDeleteSession(s.id, e)}
                          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-rose-50 text-slate-400 hover:text-rose-650 rounded-md cursor-pointer transition-all shrink-0"
                          title="删除该会话记录"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Right Chat Column (Adapts from 9-cols to full 12-cols wide) */}
        <div className={`flex flex-col min-h-[620px] bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden transition-all duration-300 ${
          sidebarOpen ? 'lg:col-span-9' : 'lg:col-span-12'
        }`}>
          {/* Header area in right panel with new collapsible and fullscreen support */}
          <div className="px-6 py-4 border-b border-slate-100/80 bg-slate-50/50 flex justify-between items-center gap-3">
            <div className="flex items-center grow min-w-0">
              {/* Fold toggle button */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="mr-3.5 p-2 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 active:scale-95 transition-all cursor-pointer shadow-2xs shrink-0"
                title={sidebarOpen ? "收起侧边管理栏" : "展开侧边管理栏"}
              >
                {sidebarOpen ? <ChevronLeft className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>

              <div className="space-y-0.5 min-w-0">
                <h3 className="text-xs font-bold text-slate-850 font-mono uppercase tracking-wider truncate">
                  {activeSession ? `消息与 Trace • 正在阅读分支 "${activeSession.branch}"` : '未打开会话'}
                </h3>
                <p className="text-[10px] text-slate-450 truncate">
                  搭载 Gemini 代理的多轮交互审计日志，在右侧监控决策链行为
                </p>
              </div>
            </div>

            {activeSession && (
              <div className="text-[10px] bg-indigo-50 border border-indigo-200/50 px-2 py-0.5 rounded text-indigo-600 font-bold font-mono shrink-0">
                BRANCH: {activeSession.branch}
              </div>
            )}
          </div>

          {!activeSession ? (
            /* No active session placeholder state */
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-slate-50/20">
              <div className="w-16 h-16 rounded-3xl bg-indigo-50 flex items-center justify-center text-indigo-650 border border-indigo-150 mb-4 shadow-xs">
                <Cpu className="w-8 h-8 animate-pulse" />
              </div>
              <h4 className="text-sm font-bold text-slate-800">未选择会话</h4>
              <p className="text-xs text-slate-400 max-w-sm mt-1.5 leading-relaxed">
                先在左侧输入信息创建一个持续会话，或者从已有会话列表中选择一个会话以启动代码分析与多轮对话。
              </p>
            </div>
          ) : (
            /* Selected Session view */
            <div className="flex-1 flex flex-col">
              {/* Chat Messages container */}
              <div className="flex-1 p-6 space-y-6 overflow-y-auto max-h-[500px]">
                {activeSession.messages.map((msg) => {
                  const isAi = msg.role === 'assistant';
                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-4 ${isAi ? 'justify-start' : 'justify-end'}`}
                    >
                      {/* Avatar */}
                      {isAi && (
                        <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center shrink-0 shadow-xs">
                          <Bot className="w-4 h-4" />
                        </div>
                      )}

                      {/* Content block */}
                      <div className={`space-y-1.5 max-w-[85%] ${!isAi && 'items-end flex flex-col'}`}>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold text-slate-750">
                            {isAi ? 'AI Code Reviewer' : '管理员'}
                          </span>
                          <span className="text-[9px] text-slate-400 font-mono">
                            {msg.timestamp}
                          </span>
                        </div>

                        <div
                          className={`p-4 rounded-2xl text-xs leading-relaxed space-y-3 ${
                            isAi
                              ? 'bg-slate-50 border border-slate-100 text-slate-850 shadow-xs rounded-tl-none'
                              : 'bg-indigo-600 text-white shadow-md rounded-tr-none'
                          }`}
                        >
                          {/* Inner formatting and code parsing support */}
                          <div className="prose prose-sm max-w-none break-words whitespace-pre-wrap">
                            {parseFormattedContent(msg.content, !isAi)}
                          </div>
                        </div>

                        {/* Collapsible Trace inside Assistant messages */}
                        {isAi && msg.trace && (
                          <div className="border border-slate-100 rounded-xl bg-slate-50/50 mt-2 overflow-hidden text-left max-w-lg">
                            <button
                              onClick={() => setTraceExpanded(!traceExpanded)}
                              className="px-3.5 py-2 select-none flex items-center justify-between text-[10px] font-semibold text-slate-500 hover:text-slate-800 bg-slate-100/50 cursor-pointer w-full"
                            >
                              <div className="flex items-center gap-1.5">
                                <Terminal className="w-3.5 h-3.5 text-slate-450" />
                                <span>大模型决策追踪 Trace (只读分析)</span>
                              </div>
                              {traceExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>

                            <AnimatePresence>
                              {traceExpanded && (
                                <motion.div
                                  initial={{ height: 0 }}
                                  animate={{ height: 'auto' }}
                                  exit={{ height: 0 }}
                                  className="overflow-hidden bg-white/70"
                                >
                                  <div className="p-3.5 space-y-2 border-t border-slate-100">
                                    <div className="text-[9.5px] text-slate-400 bg-slate-100 px-2.5 py-1 rounded-md font-mono leading-relaxed mb-3">
                                      <span className="font-bold text-indigo-600">THOUGHT:</span> {msg.trace.thought}
                                    </div>
                                    <div className="space-y-2">
                                      {msg.trace.steps.map((st, sIdx) => (
                                        <div key={sIdx} className="flex items-center justify-between text-[10.5px]">
                                          <div className="flex items-center gap-2">
                                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                            <span className="text-slate-600 font-mono font-medium">{st.name}</span>
                                          </div>
                                          {st.duration && (
                                            <span className="text-[9.5px] text-slate-450 font-mono bg-slate-100 px-1.5 rounded">{st.duration}</span>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}
                      </div>

                      {/* User Avatar */}
                      {!isAi && (
                        <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center shrink-0 shadow-xs">
                          <User className="w-4 h-4" />
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Instant Active Streaming Message / Real-time Trace sequence */}
                {isStreaming && (
                  <div className="flex gap-4 justify-start animate-in fade-in duration-300">
                    <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center shrink-0 shadow-xs">
                      <Bot className="w-4 h-4 animate-spin" />
                    </div>

                    <div className="space-y-1.5 max-w-[85%]">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-slate-755">AI Code Reviewer</span>
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                          <Activity className="w-3 h-3 text-indigo-500 animate-pulse" />
                          <span>正在分析与推理事件链...</span>
                        </div>
                      </div>

                      {/* Display live running trace sequences first */}
                      {currentTraceSteps.length > 0 && (
                        <div className="border border-indigo-100 bg-indigo-50/10 rounded-2xl p-4 text-left max-w-lg mb-2">
                          <div className="text-[10px] font-bold text-slate-700 font-mono mb-2 flex items-center gap-1.5">
                            <Activity className="w-3.5 h-3.5 text-indigo-500 animate-spin" />
                            <span>正在运行的智能决策链 Trace</span>
                          </div>
                          <div className="space-y-1.5">
                            {currentTraceSteps.map((st, idx) => (
                              <div key={idx} className="flex items-center justify-between text-[10.5px]">
                                <div className="flex items-center gap-2">
                                  {st.status === 'success' ? (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                  ) : st.status === 'loading' ? (
                                    <div className="w-3.5 h-3.5 border-2 border-indigo-550 border-t-transparent rounded-full animate-spin shrink-0" />
                                  ) : (
                                    <span className="w-3.5 h-3.5 rounded-full border border-slate-300 bg-slate-50 shrink-0 inline-block" />
                                  )}
                                  <span className={`font-mono ${st.status === 'loading' ? 'text-indigo-650 font-bold' : 'text-slate-500'}`}>
                                    {st.name}
                                  </span>
                                </div>
                                <span className={`text-[9px] font-mono ${st.status === 'success' ? 'text-emerald-600 bg-emerald-50 px-1.5 rounded' : 'text-slate-400'}`}>
                                  {st.status === 'success' ? '完成' : st.status === 'loading' ? '处理中...' : '排队中'}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Live typing streamed text container */}
                      {streamingContent && (
                        <div className="p-4 rounded-2xl text-xs leading-relaxed space-y-3 bg-slate-50 border border-slate-100 text-slate-850 shadow-xs rounded-tl-none">
                          <div className="prose prose-sm max-w-none break-words whitespace-pre-wrap">
                            {parseFormattedContent(streamingContent, false)}
                          </div>
                          <span className="inline-block w-1.5 h-4 bg-indigo-500 animate-pulse ml-0.5" />
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Message Composer Area */}
              <div className="p-4 border-t border-slate-100/80 bg-slate-50/50">
                <form onSubmit={handleSendMessage} className="space-y-3">
                  <div className="relative rounded-2xl border border-slate-200/80 bg-white shadow-xs focus-within:ring-2 focus-within:ring-indigo-500/10 focus-within:border-indigo-500 transition-all p-2.5">
                    <textarea
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage(e);
                        }
                      }}
                      placeholder={`针对本分支下的代码仓库进行对话... (Shift+Enter 换行, Enter 直接发送)`}
                      disabled={isStreaming}
                      className="w-full text-slate-800 text-xs bg-transparent border-0 focus:outline-hidden focus:ring-0 min-h-[75px] resize-none pr-12 pl-2 pt-1 font-sans"
                    />

                    <div className="flex justify-between items-center px-2 pt-2 border-t border-slate-100/60">
                      <div className="flex gap-2">
                        <span className="text-[10px] text-slate-450 font-medium font-mono flex items-center gap-1">
                          <Cpu className="w-3 h-3 text-indigo-500" />
                          <span>AI: Gemini 2.5 Pro</span>
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="text-[10px] text-slate-450 font-medium font-mono flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-indigo-500" />
                          <span>分支: {activeSession.branch}</span>
                        </span>
                      </div>

                      <button
                        type="submit"
                        disabled={!inputMessage.trim() || isStreaming}
                        className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-all disabled:opacity-45 disabled:cursor-not-allowed flex items-center gap-1.5"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>发送消息</span>
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Custom simple parser to highlight code blocks, bullet points and bold sections without needing react-markdown
function parseFormattedContent(text: string, isUser: boolean) {
  if (isUser) {
    return <span className="font-medium">{text}</span>;
  }

  const parts = text.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-3 font-sans text-xs">
      {parts.map((part, index) => {
        // Code Block
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).trim().split('\n');
          // check if first line indicates language
          let lang = '';
          let codeLines = lines;
          if (lines[0] && !lines[0].startsWith(' ') && lines[0].length < 15) {
            lang = lines[0];
            codeLines = lines.slice(1);
          }
          const rawCode = codeLines.join('\n');

          return (
            <div key={index} className="rounded-xl border border-slate-200 overflow-hidden bg-[#0A0B14] my-3 shadow-xs">
              {lang && (
                <div className="px-4 py-2 border-b border-slate-800/60 bg-slate-900 flex justify-between items-center text-[10px] font-mono text-slate-450">
                  <div className="flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{lang.toUpperCase()} 静态提取</span>
                  </div>
                  <span className="text-indigo-450/80 font-bold uppercase select-none text-[8px] tracking-wider">readonly static</span>
                </div>
              )}
              <pre className="p-4 overflow-x-auto text-[11px] leading-relaxed font-mono text-slate-300 text-left bg-[#0A0B14]">
                <code>{rawCode}</code>
              </pre>
            </div>
          );
        }

        // Standard text parser for headings, bold items, bullets
        const lines = part.split('\n');
        return (
          <div key={index} className="space-y-1.5 text-left">
            {lines.map((line, lIdx) => {
              // Custom Title/Heading styling
              if (line.startsWith('### ')) {
                return (
                  <h4 key={lIdx} className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-1.5 pt-2 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-500 shrink-0" />
                    <span>{line.substring(4)}</span>
                  </h4>
                );
              }
              if (line.startsWith('## ')) {
                return (
                  <h3 key={lIdx} className="text-base font-bold text-indigo-700/90 pt-3 pb-1">
                    {line.substring(3)}
                  </h3>
                );
              }

              // Simple bullets
              if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
                const cleanLine = line.trim().substring(2);
                return (
                  <div key={lIdx} className="flex items-start gap-2 pl-3 py-0.5">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                    <span className="leading-relaxed text-slate-700">
                      {parseInlineFormatting(cleanLine)}
                    </span>
                  </div>
                );
              }

              // Normal paragraph with inline formatting
              return (
                <p key={lIdx} className="leading-relaxed text-slate-700/95 py-0.5">
                  {parseInlineFormatting(line)}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

// Sub-inline formatting parsing helper (handles `code` and **bold**)
function parseInlineFormatting(str: string) {
  // Regex split by bold markdown
  const boldParts = str.split(/(\*\*.*?\*\*)/g);
  return boldParts.map((bPart, idx) => {
    if (bPart.startsWith('**') && bPart.endsWith('**')) {
      const bText = bPart.slice(2, -2);
      // parse backticks inside bold splits
      return <strong key={idx} className="font-bold text-slate-900">{parseBackticks(bText)}</strong>;
    }
    return <React.Fragment key={idx}>{parseBackticks(bPart)}</React.Fragment>;
  });
}

function parseBackticks(str: string) {
  const codeParts = str.split(/(`.*?`)/g);
  return codeParts.map((cPart, idx) => {
    if (cPart.startsWith('`') && cPart.endsWith('`')) {
      return (
        <code
          key={idx}
          className="bg-indigo-50/70 text-indigo-650 font-mono text-[10.5px] font-bold px-1.5 py-0.2 rounded border border-indigo-100/40"
        >
          {cPart.slice(1, -1)}
        </code>
      );
    }
    return cPart;
  });
}
