'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import type { MeResponse } from '@/lib/types';
import { User as UserIcon, Laptop, LogOut, Ticket, LifeBuoy } from 'lucide-react';
import { HelioLogo } from '@/components/helio-mark';

interface SidePanelProps {
  onNavigate: (page: 'helpdesk' | 'tickets') => void;
  currentPage: string;
}

export default function SidePanel({ onNavigate, currentPage }: SidePanelProps) {
  const [meData, setMeData] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadUserInfo();
  }, []);

  const loadUserInfo = async () => {
    try {
      const data = await apiClient.getMe();
      setMeData(data);
    } catch (err) {
      console.error('Failed to load user info:', err);
    } finally {
      setLoading(false);
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
      <div className="hidden md:block w-72 border-l p-4" style={{ background: 'var(--surface)', borderColor: 'var(--stroke)' }}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 rounded w-3/4" style={{ background: 'var(--surface-soft)' }} />
          <div className="h-4 rounded w-1/2" style={{ background: 'var(--surface-soft)' }} />
        </div>
      </div>
    );
  }

  if (!meData) return null;

  const navBtn = (active: boolean) => ({
    background: active ? 'var(--signal-soft)' : 'transparent',
    color: active ? 'var(--signal)' : 'var(--ink-secondary)',
  });

  return (
    <div
      className="w-full md:w-72 flex flex-col border-t md:border-t-0 md:border-l max-h-[40vh] md:max-h-none overflow-y-auto"
      style={{ background: 'var(--surface)', borderColor: 'var(--stroke)' }}
    >
      <div className="p-4 border-b flex items-center gap-2" style={{ borderColor: 'var(--stroke)' }}>
        <span style={{ color: 'var(--signal)' }}>
          <HelioLogo size={22} />
        </span>
        <div>
          <div className="text-sm font-semibold tracking-tight leading-tight">
            CloudiQS Demo agent
          </div>
          <div className="text-[11px]" style={{ color: 'var(--ink-tertiary)' }}>
            Guided helpdesk
          </div>
        </div>
      </div>

      <div className="p-4 border-b" style={{ borderColor: 'var(--stroke)' }}>
        <div className="flex items-start gap-3">
          <div
            className="w-11 h-11 rounded-full flex items-center justify-center shrink-0 text-white bg-brand-gradient"
          >
            <UserIcon className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold truncate text-sm">{meData.user.full_name}</h3>
            <p className="text-xs capitalize" style={{ color: 'var(--ink-secondary)' }}>
              {meData.user.role.replace('_', ' ')}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--ink-tertiary)' }}>
              {meData.tenant_name}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <h4
            className="text-[10px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--ink-tertiary)' }}
          >
            Navigation
          </h4>
          <nav className="space-y-1">
            <button
              type="button"
              onClick={() => onNavigate('helpdesk')}
              className="w-full text-left px-3 py-2.5 rounded-xl text-sm flex items-center gap-2 transition-colors"
              style={navBtn(currentPage === 'helpdesk')}
            >
              <LifeBuoy className="w-4 h-4" />
              Get help
            </button>
            <button
              type="button"
              onClick={() => onNavigate('tickets')}
              className="w-full text-left px-3 py-2.5 rounded-xl text-sm flex items-center gap-2 transition-colors"
              style={navBtn(currentPage === 'tickets')}
            >
              <Ticket className="w-4 h-4" />
              My tickets
            </button>
            <a
              href="/it"
              className="w-full text-left px-3 py-2.5 rounded-xl text-sm flex items-center gap-2"
              style={{ color: 'var(--ink-secondary)' }}
            >
              Approvals workbench
            </a>
          </nav>
        </div>

        {meData.devices && meData.devices.length > 0 && (
          <div>
            <h4
              className="text-[10px] font-semibold uppercase tracking-widest mb-2"
              style={{ color: 'var(--ink-tertiary)' }}
            >
              Devices
            </h4>
            <ul className="space-y-2">
              {meData.devices.slice(0, 3).map((d) => (
                <li
                  key={d.device_id}
                  className="flex items-center gap-2 text-sm px-2 py-2 rounded-xl"
                  style={{ background: 'var(--surface-soft)' }}
                >
                  <Laptop className="w-4 h-4 shrink-0" style={{ color: 'var(--ink-tertiary)' }} />
                  <span className="truncate">{d.device_name || d.device_id}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div
          className="text-[11px] rounded-xl px-3 py-2"
          style={{ background: 'var(--signal-soft)', color: 'var(--ink-secondary)' }}
        >
          Demo environment · Simulated enterprise data
        </div>
      </div>

      <div className="p-4 border-t" style={{ borderColor: 'var(--stroke)' }}>
        <button type="button" onClick={handleLogout} className="btn-secondary w-full text-sm">
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </div>
  );
}
