'use client';

import { useState, FormEvent } from 'react';
import { apiClient } from '@/lib/api-client';
import { HelioLogo } from '@/components/helio-mark';

type DemoPersona = {
  id: string;
  name: string;
  role: string;
  tenant: 'Northstar';
  section: 'employees' | 'it_support';
  department?: string;
};

const DEMO_PERSONAS: DemoPersona[] = [
  { id: 'NS-001', name: 'Asha Rao', role: 'Employee', tenant: 'Northstar', section: 'employees', department: 'Engineering' },
  { id: 'NS-005', name: 'Kiran Desai', role: 'Employee', tenant: 'Northstar', section: 'employees', department: 'Finance' },
  { id: 'NS-006', name: 'Leena Joseph', role: 'Employee', tenant: 'Northstar', section: 'employees', department: 'Marketing' },
  { id: 'NS-002', name: 'Rahul Sharma', role: 'IT Engineer', tenant: 'Northstar', section: 'it_support', department: 'IT Support' },
  { id: 'NS-003', name: 'Priya Menon', role: 'IT Manager', tenant: 'Northstar', section: 'it_support', department: 'IT Operations' },
  { id: 'NS-004', name: 'Vikram Rao', role: 'Tenant Admin', tenant: 'Northstar', section: 'it_support', department: 'IT Security' },
];

const SECTIONS = [
  { id: 'employees' as const, title: 'Employees', blurb: 'End users requesting IT help.' },
  { id: 'it_support' as const, title: 'IT Support staff', blurb: 'Engineers and admins handling tickets and approvals.' },
];

export default function LoginPage() {
  const [selectedPersona, setSelectedPersona] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedPersona) {
      setError('Please select a persona');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await apiClient.demoLogin({ user_id: selectedPersona });
      window.location.href = '/helpdesk';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      <div className="lg:w-[52%] px-8 py-12 lg:px-14 flex flex-col justify-between text-white bg-brand-gradient">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-white/15 p-1.5">
            <HelioLogo size={32} />
          </span>
          <span className="text-lg sm:text-xl font-semibold tracking-tight leading-tight">
            CloudiQS Demo agent
          </span>
        </div>
        <div className="mt-12 lg:mt-0 max-w-lg">
          <h1 className="text-4xl lg:text-5xl font-semibold tracking-tight leading-tight">
            Clarity, when work gets complicated.
          </h1>
          <p className="mt-5 text-white/85 text-[15px] leading-relaxed">
            Guided IT helpdesk demo with simulated enterprise systems.
          </p>
        </div>
        <div className="mt-10 text-xs text-white/90 border border-white/25 rounded-full px-3 py-1.5 w-fit bg-white/10">
          Demo environment · Simulated enterprise data
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-5 py-10">
        <form onSubmit={handleLogin} className="w-full max-w-[460px]">
          <p className="text-[11px] font-medium uppercase tracking-widest" style={{ color: 'var(--ink-tertiary)' }}>
            Enter workspace
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Choose a demo persona</h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--ink-secondary)' }}>
            Select a Northstar demo user to enter the guided helpdesk.
          </p>

          <div className="mt-5 space-y-5 max-h-[min(420px,50vh)] overflow-y-auto pr-1">
            {SECTIONS.map((section) => {
              const people = DEMO_PERSONAS.filter((p) => p.section === section.id);
              if (!people.length) return null;
              return (
                <div key={section.id}>
                  <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--signal)' }}>
                    {section.title}
                  </p>
                  <p className="text-xs mt-0.5 mb-2" style={{ color: 'var(--ink-tertiary)' }}>
                    {section.blurb}
                  </p>
                  <div className="space-y-2">
                    {people.map((p) => {
                      const active = selectedPersona === p.id;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => setSelectedPersona(p.id)}
                          className="w-full text-left rounded-2xl border px-3.5 py-3.5 transition-all"
                          style={{
                            borderColor: active ? 'var(--signal)' : 'var(--stroke)',
                            background: active ? 'var(--signal-soft)' : 'var(--surface)',
                          }}
                        >
                          <div className="text-sm font-medium">{p.name}</div>
                          <div className="text-xs mt-0.5" style={{ color: 'var(--ink-secondary)' }}>
                            {[p.role, p.department].filter(Boolean).join(' · ')} · {p.id}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {error && (
            <p className="mt-3 text-sm" style={{ color: 'var(--danger)' }}>
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary w-full mt-6" disabled={loading || !selectedPersona}>
            {loading ? 'Signing in…' : 'Enter demo workspace'}
          </button>
        </form>
      </div>
    </div>
  );
}
