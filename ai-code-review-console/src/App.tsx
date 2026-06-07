/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  TabId,
  UserSession,
  ProjectItem,
  ReviewRecord,
  ModelConfig,
  SystemLogItem,
  DashboardStats,
} from './types';
import {
  initialStats,
  initialProjects,
  initialReviews,
  initialModels,
  initialLogs,
} from './data/mockData';
import LoginView from './components/LoginView';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import ProjectManagementView from './components/ProjectManagementView';
import ModelManagementView from './components/ModelManagementView';
import SystemLogsView from './components/SystemLogsView';
import { RobotsView, ReviewRecordsFullView, MemberAnalysisView, RBACMatrixView } from './components/SecondaryViews';
import ProjectChatView from './components/ProjectChatView';
import TemplateManagementView from './components/TemplateManagementView';

export default function App() {
  // Session State
  const [session, setSession] = useState<UserSession>(() => {
    const saved = localStorage.getItem('ai_code_review_session');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // ignore
      }
    }
    return {
      username: '',
      role: '',
      token: '',
      isLoggedIn: false,
    };
  });

  // Global State
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [stats, setStats] = useState<DashboardStats>(initialStats);
  const [projects, setProjects] = useState<ProjectItem[]>(initialProjects);
  const [reviews, setReviews] = useState<ReviewRecord[]>(initialReviews);
  const [models, setModels] = useState<ModelConfig[]>(() => {
    const saved = localStorage.getItem('ai_code_review_models');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // ignore
      }
    }
    return initialModels;
  });
  const [logs, setLogs] = useState<SystemLogItem[]>(initialLogs);
  const [activeChatProjectId, setActiveChatProjectId] = useState<string | null>(() => {
    return localStorage.getItem('active_chat_project_id');
  });

  // Keep activeChatProjectId synced in localStorage
  useEffect(() => {
    if (activeChatProjectId) {
      localStorage.setItem('active_chat_project_id', activeChatProjectId);
    } else {
      localStorage.removeItem('active_chat_project_id');
    }
  }, [activeChatProjectId]);

  // Sync session with local storage
  useEffect(() => {
    localStorage.setItem('ai_code_review_session', JSON.stringify(session));
  }, [session]);

  // Sync models with local storage
  useEffect(() => {
    localStorage.setItem('ai_code_review_models', JSON.stringify(models));
  }, [models]);

  const addLog = (action: string, details: string, level: 'info' | 'warning' | 'error' = 'info') => {
    const newLogObj: SystemLogItem = {
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      level,
      operator: session.username || 'system',
      action,
      details,
    };
    setLogs((prev) => [newLogObj, ...prev]);
  };

  const handleLoginSuccess = (userSession: UserSession) => {
    setSession(userSession);
    setActiveTab('dashboard');

    // Create custom login security audit log
    const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
    const newLoginLog: SystemLogItem = {
      id: `log-${Date.now()}`,
      timestamp,
      level: 'info',
      operator: userSession.username,
      action: 'USER_LOGIN',
      details: `User approved via access JWT context. Granted role: ${userSession.role}. Initialized sidebar dynamic tabs.`,
    };
    setLogs((prev) => [newLoginLog, ...prev]);
  };

  const handleLogout = () => {
    const logoutLog: SystemLogItem = {
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      level: 'info',
      operator: session.username || 'admin',
      action: 'USER_LOGOUT',
      details: 'User session logged out. JWT context cleared. Dynamic menu tree released.',
    };
    setLogs((prev) => [logoutLog, ...prev]);

    setSession({
      username: '',
      role: '',
      token: '',
      isLoggedIn: false,
    });
  };

  // Toggle active/inactive project review status
  const handleToggleProject = (id: string) => {
    setProjects((prev) =>
      prev.map((p) => {
        if (p.id === id) {
          const nextState = !p.enabled;
          addLog(
            'PROJECT_MUTATED',
            `Repository ${p.name} monitoring status set to ${nextState ? 'ENABLED / ACTIVE' : 'DISABLED / INACTIVE'}`
          );
          return { ...p, enabled: nextState, status: nextState ? 'active' : 'inactive' };
        }
        return p;
      })
    );
  };

  // Create new Monitored Project
  const handleAddProject = (newProj: Omit<ProjectItem, 'id' | 'lastReviewAt' | 'scoreAverage'>) => {
    const addedProj: ProjectItem = {
      ...newProj,
      id: `proj-${Date.now()}`,
      lastReviewAt: '',
      scoreAverage: 0,
    };

    setProjects((prev) => [addedProj, ...prev]);
    setStats((prev) => ({
      ...prev,
      totalProjects: prev.totalProjects + 1,
    }));

    addLog('PROJECT_CREATED', `New code review repository was successfully deployed: ${newProj.name}`);
  };

  const handleDeleteProject = (id: string) => {
    const target = projects.find((p) => p.id === id);
    if (!target) return;

    setProjects((prev) => prev.filter((p) => p.id !== id));
    setStats((prev) => ({
      ...prev,
      totalProjects: Math.max(0, prev.totalProjects - 1),
    }));

    addLog('PROJECT_REMOVED', `Project registration removed from active review context: ${target.name}`, 'warning');
  };

  // Switch default LLM Model Configuration
  const handleActivateModel = (id: string) => {
    setModels((prev) => {
      const target = prev.find((m) => String(m.id) === String(id));
      const isTargetCurrentlyActive = target ? (target.is_active ?? target.isActive ?? false) : false;
      const nextActiveState = !isTargetCurrentlyActive;

      return prev.map((m) => {
        if (String(m.id) === String(id)) {
          addLog(
            'MODEL_SWITCH',
            nextActiveState
              ? `Successfully switched default review processor to: ${m.name}`
              : `Deactivated review processor: ${m.name}`
          );
          return { ...m, isActive: nextActiveState, is_active: nextActiveState };
        }
        // If activating a model, deactivate other models (since only one default reviewer is active)
        if (nextActiveState) {
          return { ...m, isActive: false, is_active: false };
        }
        return m;
      });
    });
  };

  const handleUpdateModelParams = (id: string, temp: number, tokens: number) => {
    setModels((prev) =>
      prev.map((m) => {
        if (String(m.id) === String(id)) {
          addLog(
            'MODEL_CONFIG_MUTATED',
            `Fine-tuning parameters changed for ${m.name}. Temp: ${temp}, MaxTokens: ${tokens}`
          );
          return { ...m, temperature: temp, maxTokens: tokens, max_tokens: tokens };
        }
        return m;
      })
    );
  };

  const handleUpdateModel = (updated: ModelConfig) => {
    setModels((prev) =>
      prev.map((m) => (String(m.id) === String(updated.id) ? updated : m))
    );
    addLog('MODEL_MUTATED', `Successfully updated dynamic model parameters for: ${updated.name}`);
  };

  const handleDeleteModel = (id: string) => {
    const target = models.find((m) => String(m.id) === String(id));
    if (!target) return;
    setModels((prev) => prev.filter((m) => String(m.id) !== String(id)));
    addLog('MODEL_REMOVED', `Model configuration deleted: ${target.name}`, 'warning');
  };

  // Trigger manual immediate file scan review
  const handleTriggerReview = (id: string) => {
    const target = projects.find((p) => p.id === id);
    if (!target) return;

    addLog('SCAN_TRIGGERED', `Manually triggered code audit review for ${target.name}`, 'info');

    // Simulate review completion and output score after delay
    setTimeout(() => {
      // Pick a random randomized commit review score
      const score = Math.floor(Math.random() * 25) + 75; // 75 - 99 score
      const newReview: ReviewRecord = {
        id: `rev-${Date.now()}`,
        project_id: id,
        projectName: target.name,
        prTitle: `automated: immediate code check scan on manual trigger`,
        committer: session.username || 'admin',
        commitHash: Math.random().toString(16).slice(2, 9),
        branch: target.branch,
        score,
        status: score >= 90 ? 'excellent' : 'pass',
        timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
        summary: `Trigger scan completed. Code exhibits optimal component modularity. Temperature variables calibrated successfully.`,
        robotNotified: true,
      };

      setReviews((prev) => [newReview, ...prev]);

      // Update project statistics & average scores
      setProjects((prev) =>
        prev.map((p) => {
          if (p.id === id) {
            return {
              ...p,
              lastReviewAt: newReview.timestamp,
              scoreAverage: p.scoreAverage ? parseFloat(((p.scoreAverage + score) / 2).toFixed(1)) : score,
            };
          }
          return p;
        })
      );

      setStats((prev) => ({
        ...prev,
        reviewCount: prev.reviewCount + 1,
        averageScore: parseFloat(((prev.averageScore + score) / 2).toFixed(1)),
      }));

      addLog(
        'REVIEW_COMPLETE',
        `Review diagnostics complete for ${target.name}. Score: ${score}, Status: ${newReview.status}`
      );
      alert(`🎉 审核成功! 项目 [${target.name}] 已评阅完毕，得分: ${score}。结果已同步至通知频道。`);
    }, 800);
  };

  const handleClearLogs = () => {
    setLogs([]);
    addLog('LOG_CLEAR', 'System audit logs cleared by administrator.');
  };

  const handleEnterProjectChat = (id: string) => {
    const target = projects.find((p) => p.id === id);
    if (!target) return;
    setActiveChatProjectId(id);
    setActiveTab('chat');
    addLog('CHAT_START', `已为项目 [${target.name}] 成功部署并挂载持续双向对话工作区环境`, 'info');
  };

  const currentActiveTabClass = (tab: TabId) => {
    return activeTab === tab ? 'bg-indigo-600 text-white' : 'hover:bg-slate-100 text-slate-500';
  };

  return (
    <AnimatePresence mode="wait">
      {!session.isLoggedIn ? (
        <motion.div
          key="login"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="w-full min-h-screen"
        >
          <LoginView onLoginSuccess={handleLoginSuccess} />
        </motion.div>
      ) : (
        <motion.div
          key="workspace"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex min-h-screen bg-[#f1f5f9] text-slate-800"
        >
          {/* Main Sidebar left menu navigation */}
          <Sidebar
            activeTab={activeTab}
            onTabChange={setActiveTab}
            session={session}
            onLogout={handleLogout}
          />

          {/* Right main panel wrapper */}
          <div className="flex-1 flex flex-col min-h-screen overflow-y-auto">
            {/* Top Bar Header */}
            <Header
              session={session}
              activeTab={activeTab}
              onLogout={handleLogout}
              onRefreshData={() => {
                addLog('DATA_REFRESHED', 'Dynamic context metrics re-synchronized with backend server.');
                alert('数据刷新成功！正在重新对齐 access-context 认证树。');
              }}
            />

            {/* Render router-like tab panels */}
            <main className="flex-1 pb-16">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  {activeTab === 'dashboard' && (
                    <DashboardView
                      username={session.username}
                      stats={stats}
                      recentReviews={reviews}
                      allProjects={projects}
                      modelConfigs={models}
                      onNavigateTab={setActiveTab}
                      onToggleProject={handleToggleProject}
                    />
                  )}

                  {activeTab === 'projects' && (
                    <ProjectManagementView
                      projects={projects}
                      onToggleProject={handleToggleProject}
                      onAddProject={handleAddProject}
                      onDeleteProject={handleDeleteProject}
                      onTriggerReview={handleEnterProjectChat}
                    />
                  )}

                  {activeTab === 'models' && (
                    <ModelManagementView
                      models={models}
                      onActivateModel={handleActivateModel}
                      onAddModel={(newModel) => {
                        const m: ModelConfig = {
                          ...newModel,
                          id: `model-${Date.now()}`,
                          queriesCount: 0,
                        };
                        setModels((prev) => [...prev, m]);
                        addLog('MODEL_DEPLOYED', `Deployed a new smart calculation model node: ${m.name}`);
                      }}
                      onUpdateModelParams={handleUpdateModelParams}
                      onUpdateModel={handleUpdateModel}
                      onDeleteModel={handleDeleteModel}
                    />
                  )}

                  {activeTab === 'logs' && (
                    <SystemLogsView
                      logs={logs}
                      onClearLogs={handleClearLogs}
                      onAddCustomLog={(act, det) => addLog(act, det, 'info')}
                    />
                  )}

                  {activeTab === 'templates' && (
                    <TemplateManagementView onAddLog={(act, det, lvl) => addLog(act, det, lvl || 'info')} />
                  )}

                  {activeTab === 'robots' && (
                    <RobotsView onAddLog={(act, det) => addLog(act, det, 'info')} />
                  )}

                  {activeTab === 'records' && (
                    <ReviewRecordsFullView records={reviews} />
                  )}

                  {activeTab === 'members' && (
                    <MemberAnalysisView />
                  )}

                  {(activeTab === 'users' || activeTab === 'roles') && (
                    <RBACMatrixView
                      tabId={activeTab as 'users' | 'roles'}
                      onAddLog={(act, det) => addLog(act, det, 'info')}
                    />
                  )}

                  {activeTab === 'chat' && (
                    (() => {
                      const chatProj = projects.find((p) => p.id === activeChatProjectId) || projects[0] || initialProjects[0];
                      return (
                        <ProjectChatView
                          project={chatProj}
                          onBackToProjects={() => setActiveTab('projects')}
                          onAddLog={(act, det) => addLog(act, det, 'info')}
                        />
                      );
                    })()
                  )}
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
