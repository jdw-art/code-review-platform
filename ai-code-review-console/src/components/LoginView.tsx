/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Lock, User, Eye, EyeOff, ShieldCheck, Sparkles } from 'lucide-react';
import { UserSession } from '../types';

interface LoginViewProps {
  onLoginSuccess: (session: UserSession) => void;
}

export default function LoginView({ onLoginSuccess }: LoginViewProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin2026');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setErrorMsg('请输入用户名');
      return;
    }
    setLoading(true);
    setErrorMsg('');

    setTimeout(() => {
      setLoading(false);
      onLoginSuccess({
        username: username,
        role: username === 'admin' ? '超级管理员' : '开发工程师',
        avatarUrl: `https://api.dicebear.com/7.x/bottts/svg?seed=${username}`,
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token-simulation-jdw-art-review',
        isLoggedIn: true,
      });
    }, 900);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 bg-[#fafafa] relative overflow-hidden selection:bg-indigo-150 selection:text-indigo-900">
      {/* Elegantly restrained grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.015)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      
      {/* Subtle radial ambient light */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full bg-indigo-500/5 blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md bg-white border border-slate-200/60 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.02)] p-8 relative z-10"
      >
        {/* Decorative dynamic badge */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-50 border border-slate-200/40 text-[10px] text-slate-500 font-mono tracking-tight">
            <Sparkles className="w-3 h-3 text-indigo-500" />
            <span>Platform Auth Node</span>
          </div>
        </div>

        {/* Minimalist Header */}
        <div className="text-center mb-8 space-y-2">
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            AI Code Review Console
          </h1>
          <p className="text-xs text-slate-400 font-light max-w-[280px] mx-auto leading-relaxed">
            极简、安全、端到端的全功能代码分析与管理平台
          </p>
        </div>

        {/* Error message banner */}
        {errorMsg && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-5 p-3 bg-red-50/60 border border-red-100 text-red-700 text-xs rounded-xl flex items-center gap-2 font-medium"
          >
            <div className="w-1 h-1 bg-red-500 rounded-full" />
            <span>{errorMsg}</span>
          </motion.div>
        )}

        {/* Form elements */}
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-500 tracking-wider uppercase block">
              用户名
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <User className="w-4 h-4 text-slate-400" />
              </div>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (errorMsg) setErrorMsg('');
                }}
                placeholder="请输入管理员或工程师账号"
                className="w-full pl-9 pr-4 py-2.5 bg-slate-50/40 hover:bg-slate-50 focus:bg-white border border-slate-200 text-slate-800 rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all text-xs font-semibold"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-[11px] font-semibold text-slate-500 tracking-wider uppercase block">
                密码
              </label>
              <button
                type="button"
                className="text-[10px] text-indigo-600 hover:text-indigo-700 font-medium transition-colors cursor-pointer"
              >
                忘记密码？
              </button>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4 text-slate-400" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errorMsg) setErrorMsg('');
                }}
                placeholder="请输入您的登录密码"
                className="w-full pl-9 pr-9 py-2.5 bg-slate-50/40 hover:bg-slate-50 focus:bg-white border border-slate-200 text-slate-800 rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all text-xs font-semibold"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Quick preset account switcher - beautifully clean */}
          <div className="py-2.5 px-3 bg-slate-50 border border-slate-200/50 rounded-xl flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-mono">预设工作账号:</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setUsername('admin');
                  setPassword('admin2026');
                  setErrorMsg('');
                }}
                className={`px-2 py-0.5 rounded-md border text-[10px] transition-all cursor-pointer ${
                  username === 'admin'
                    ? 'bg-white border-slate-300 text-slate-800 font-extrabold shadow-2xs'
                    : 'bg-transparent border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                超级管理员
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('developer');
                  setPassword('dev2026');
                  setErrorMsg('');
                }}
                className={`px-2 py-0.5 rounded-md border text-[10px] transition-all cursor-pointer ${
                  username === 'developer'
                    ? 'bg-white border-slate-300 text-slate-800 font-extrabold shadow-2xs'
                    : 'bg-transparent border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                开发工程师
              </button>
            </div>
          </div>

          {/* Keep logged status toggler */}
          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                defaultChecked
                className="rounded border-slate-200 text-indigo-600 focus:ring-indigo-550/20 w-3.5 h-3.5"
              />
              <span className="text-[11px] text-slate-400 select-none group-hover:text-slate-600 transition-colors">
                30 天内保持登录状态
              </span>
            </label>
          </div>

          {/* Core action CTA */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-4 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-xs transition-all shadow-[0_2px_10px_rgba(99,102,241,0.15)] hover:shadow-[0_4px_16px_rgba(99,102,241,0.2)] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>进入控制台</span>
              </>
            )}
          </button>
        </form>

        {/* Aesthetic watermark footer */}
        <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-[9px] text-slate-400 font-mono tracking-tight">
          <span>CONSOLE SYSTEM v2.0</span>
          <span>SECURED TRANSIT</span>
        </div>
      </motion.div>
    </div>
  );
}
