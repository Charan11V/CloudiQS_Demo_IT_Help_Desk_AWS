'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DemoModeBanner from '@/components/DemoModeBanner';
import { apiClient } from '@/lib/api-client';
import type { Approval, MeResponse } from '@/lib/types';
import {
  CheckCircle,
  XCircle,
  Clock,
  User,
  AlertCircle,
  ArrowLeft,
  LogOut,
} from 'lucide-react';

export default function ITQueuePage() {
  const router = useRouter();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [meData, setMeData] = useState<MeResponse | null>(null);
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [decisionReason, setDecisionReason] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [approvalsData, userData] = await Promise.all([
        apiClient.getPendingApprovals(),
        apiClient.getMe(),
      ]);

      // Check if user has IT role
      if (!['it_engineer', 'it_manager', 'tenant_admin'].includes(userData.user.role)) {
        router.push('/helpdesk');
        return;
      }

      setApprovals(approvalsData.approvals || []);
      setMeData(userData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals');
      if (err instanceof Error && err.message.includes('401')) {
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (approvalId: string, approved: boolean) => {
    setProcessing(approvalId);
    setError('');

    try {
      await apiClient.decideApproval(approvalId, {
        approved,
        reason: decisionReason.trim() || undefined,
      });

      // Refresh approvals list
      await loadData();
      setSelectedApproval(null);
      setDecisionReason('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process decision');
    } finally {
      setProcessing(null);
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.logout();
      window.location.href = '/';
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--canvas)' }}>
      <DemoModeBanner />

      <div
        className="border-b px-6 py-5"
        style={{ background: 'var(--surface)', borderColor: 'var(--stroke)' }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <button
              type="button"
              onClick={() => router.push('/helpdesk')}
              className="btn-secondary text-sm"
            >
              <ArrowLeft className="w-4 h-4 inline mr-1" />
              Back
            </button>
            <div className="min-w-0">
              <p className="text-[11px] font-medium uppercase tracking-widest" style={{ color: 'var(--ink-tertiary)' }}>
                Operations
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
              {meData && (
                <p className="text-sm truncate" style={{ color: 'var(--ink-secondary)' }}>
                  {meData.user.full_name} · {meData.user.role.replace('_', ' ')}
                  {approvals.length ? ` · ${approvals.length} pending` : ''}
                </p>
              )}
            </div>
          </div>
          <button type="button" onClick={handleLogout} className="btn-secondary flex items-center gap-2">
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {approvals.length === 0 ? (
            <div className="card text-center py-12">
              <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                No Pending Approvals
              </h2>
              <p className="text-gray-600">All caught up! No actions awaiting your review.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {approvals.map((approval) => (
                <div
                  key={approval.approval_id}
                  className="card hover:shadow-lg transition-shadow"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertCircle className="w-5 h-5 text-amber-600" />
                        <h3 className="font-semibold text-lg text-gray-900">
                          Approval Request
                        </h3>
                        <span className="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded">
                          {approval.approval_id}
                        </span>
                      </div>
                      <p className="text-gray-800 mb-2">{approval.description}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                    <div>
                      <span className="text-gray-600">Requested by:</span>
                      <div className="flex items-center gap-2 mt-1">
                        <User className="w-4 h-4 text-gray-500" />
                        <span className="font-medium text-gray-900">
                          {approval.requester_name}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600">Action:</span>
                      <p className="font-mono text-xs text-gray-900 mt-1">
                        {approval.action_code}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Target:</span>
                      <p className="font-medium text-gray-900 mt-1">
                        {approval.target_resource}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Expires:</span>
                      <p className="font-medium text-gray-900 mt-1">
                        {new Date(approval.expires_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">Impact:</span> {approval.impact}
                    </p>
                  </div>

                  {selectedApproval?.approval_id === approval.approval_id ? (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Decision Reason (optional):
                        </label>
                        <textarea
                          value={decisionReason}
                          onChange={(e) => setDecisionReason(e.target.value)}
                          placeholder="Add notes about your decision..."
                          className="input min-h-[80px]"
                        />
                      </div>
                      <div className="flex gap-3">
                        <button
                          onClick={() =>
                            handleDecision(approval.approval_id, true)
                          }
                          disabled={processing === approval.approval_id}
                          className="btn-primary flex items-center gap-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          {processing === approval.approval_id
                            ? 'Processing...'
                            : 'Approve & Execute'}
                        </button>
                        <button
                          onClick={() =>
                            handleDecision(approval.approval_id, false)
                          }
                          disabled={processing === approval.approval_id}
                          className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          <XCircle className="w-4 h-4" />
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            setSelectedApproval(null);
                            setDecisionReason('');
                          }}
                          className="btn-secondary"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex gap-3">
                      <button
                        onClick={() => setSelectedApproval(approval)}
                        className="btn-primary flex items-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Review & Decide
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
