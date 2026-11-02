'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DemoModeBanner from '@/components/DemoModeBanner';
import SidePanel from '@/components/SidePanel';
import { apiClient } from '@/lib/api-client';
import type { ConversationResponse, Option } from '@/lib/types';
import {
  ArrowLeft,
  RotateCcw,
  MessageCircle,
  HelpCircle,
  Send,
  CheckCircle,
  Clock,
  Ticket as TicketIcon,
} from 'lucide-react';

const TICKET_OPTION_IDS = new Set([
  'open_ticket',
  'confirm_raise_ticket',
  'still_failing',
]);

function optionLooksLikeTicket(option: Option): boolean {
  const id = (option.id || '').toLowerCase();
  const label = (option.label || '').toLowerCase();
  if (TICKET_OPTION_IDS.has(id)) return true;
  if (label.includes('raise') && label.includes('ticket')) return true;
  if (label.includes('open') && label.includes('ticket')) return true;
  return false;
}

function optionsOfferTicket(options: Option[] | undefined | null): boolean {
  return (options || []).some(optionLooksLikeTicket);
}

function optionIsOthers(option: Option): boolean {
  const id = (option.id || '').toLowerCase();
  const label = (option.label || '').trim().toLowerCase();
  const type = (option.type || '').toLowerCase();
  if (id === 'cant_find' || id === 'others') return true;
  if (label === 'others') return true;
  if (type === 'fallback' && label.includes('other')) return true;
  return false;
}

export default function HelpdeskPage() {
  const router = useRouter();
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [freeText, setFreeText] = useState('');
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState<'helpdesk' | 'tickets'>('helpdesk');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    initConversation();
  }, []);

  // Clear pending selection whenever the assistant presents a new step
  useEffect(() => {
    setSelectedIds([]);
    setFreeText('');
  }, [conversation?.state, conversation?.assistant_message, conversation?.conversation_id]);

  const initConversation = async () => {
    try {
      const data = await apiClient.createConversation();
      setConversation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start conversation');
      if (err instanceof Error && err.message.includes('401')) {
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const selectionMode: 'single' | 'multiple' =
    conversation?.selection_mode === 'multiple' ? 'multiple' : 'single';

  const toggleOption = (optionId: string) => {
    setSelectedIds((prev) => {
      const next =
        selectionMode === 'single'
          ? prev.includes(optionId)
            ? []
            : [optionId]
          : prev.includes(optionId)
            ? prev.filter((id) => id !== optionId)
            : [...prev, optionId];
      const stillOthers = (conversation?.options || []).some(
        (o) => next.includes(o.id) && optionIsOthers(o)
      );
      if (!stillOthers) setFreeText('');
      return next;
    });
  };

  const confirmSelection = async () => {
    if (!conversation || selectedIds.length === 0) return;

    const selectedOpts = (conversation.options || []).filter((o) =>
      selectedIds.includes(o.id)
    );
    const complaint = freeText.trim();
    const othersSelected = selectedOpts.some(optionIsOthers);
    if (othersSelected && !complaint) return;
    const attachComplaint =
      (Boolean(complaint) && selectedOpts.some(optionLooksLikeTicket)) ||
      othersSelected;

    setSending(true);
    setError('');

    try {
      const response = await apiClient.sendTurn(conversation.conversation_id, {
        option_id: selectedIds[0],
        option_ids: selectedIds,
        ...(attachComplaint ? { free_text: complaint } : {}),
      });
      setConversation(response);
      setFreeText('');
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm selection');
    } finally {
      setSending(false);
    }
  };

  const sendFreeText = async () => {
    if (!conversation || !freeText.trim()) return;

    setSending(true);
    setError('');

    try {
      const response = await apiClient.sendTurn(conversation.conversation_id, {
        free_text: freeText.trim(),
      });
      setConversation(response);
      setFreeText('');
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const sendControl = async (control: string) => {
    if (!conversation) return;

    setSending(true);
    setError('');

    try {
      const response = await apiClient.sendTurn(conversation.conversation_id, {
        control,
      });
      setConversation(response);
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send control');
    } finally {
      setSending(false);
    }
  };

  const handleNavigate = (page: 'helpdesk' | 'tickets') => {
    setCurrentPage(page);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading helpdesk...</p>
        </div>
      </div>
    );
  }

  if (currentPage === 'tickets') {
    return <MyTicketsView onBack={() => setCurrentPage('helpdesk')} />;
  }

  const sessionLocked =
    Boolean(conversation?.session_locked) || conversation?.state === 'CLOSED';
  const options = sessionLocked ? [] : conversation?.options || [];
  const selectedOpts = options.filter((o) => selectedIds.includes(o.id));
  const othersSelected = selectedOpts.some(optionIsOthers);
  const allowFreeText =
    !sessionLocked &&
    (Boolean(conversation?.allow_free_text) ||
      conversation?.state === 'DESCRIBING_OTHER' ||
      conversation?.state === 'AWAITING_TICKET_DETAILS' ||
      conversation?.state === 'AWAITING_UNKNOWN_TICKET_CONFIRM' ||
      optionsOfferTicket(options));
  const hasOptions = options.length > 0;
  const confirmDisabled =
    sending ||
    selectedIds.length === 0 ||
    (othersSelected && !freeText.trim());

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--canvas)' }}>
      <DemoModeBanner />

      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        <div className="flex-1 overflow-y-auto min-h-0 order-1">
          <div className="max-w-4xl mx-auto p-4 sm:p-8 space-y-5 sm:space-y-6 pb-8">
            <div className="rounded-2xl bg-brand-gradient text-white px-5 py-5 shadow-soft">
              <p className="text-[11px] font-medium uppercase tracking-widest text-white/75">
                Get help
              </p>
              <h1 className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight">
                CloudiQS Demo agent
              </h1>
              <p className="mt-2 text-sm text-white/85">
                Guided catalogue: select options, then Confirm.
              </p>
            </div>

            {conversation?.breadcrumb && conversation.breadcrumb.length > 0 && (
              <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--ink-tertiary)' }}>
                {conversation.breadcrumb.map((crumb, idx) => (
                  <span key={idx} className="flex items-center gap-2">
                    {idx > 0 && <span>›</span>}
                    <span>{crumb}</span>
                  </span>
                ))}
              </div>
            )}

            {conversation?.assistant_message && (
              <div className="card" style={{ background: 'var(--surface)', borderColor: 'var(--stroke)' }}>
                <div className="flex gap-3">
                  <MessageCircle className="w-6 h-6 flex-shrink-0 mt-1" style={{ color: 'var(--signal)' }} />
                  <div className="flex-1">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--ink)' }}>
                      {conversation.assistant_message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {allowFreeText && !hasOptions && (
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendFreeText()}
                  placeholder={
                    conversation?.free_text_hint || 'Enter your complaint…'
                  }
                  disabled={sending}
                  aria-label={
                    conversation?.free_text_hint || 'Enter your complaint…'
                  }
                  className="input flex-1 h-9 py-1.5 text-sm"
                />
                <button
                  onClick={sendFreeText}
                  disabled={sending || !freeText.trim()}
                  className="btn-primary flex items-center gap-2 h-9 px-3 text-sm"
                >
                  <Send className="w-3.5 h-3.5" />
                  {conversation?.free_text_submit_label ||
                    (conversation?.state === 'DESCRIBING_OTHER' ? 'Send' : 'Raise ticket')}
                </button>
              </div>
            )}

            {hasOptions && (
              <div className="card">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">
                      {selectionMode === 'multiple'
                        ? 'Multiple choice: select all that apply'
                        : 'Single choice: select one option'}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {conversation?.selection_hint ||
                        (selectionMode === 'multiple'
                          ? 'Select all that apply, then Confirm.'
                          : 'Select one option, then Confirm.')}
                    </p>
                  </div>
                  <span
                    className="text-xs font-medium px-2 py-1 rounded-lg uppercase tracking-wide"
                    style={{ background: 'var(--signal-soft)', color: 'var(--signal)' }}
                  >
                    {selectionMode}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
                  {options.map((option: Option) => {
                    const checked = selectedIds.includes(option.id);
                    return (
                      <label
                        key={option.id}
                        className={`flex items-start gap-3 p-3.5 sm:p-4 min-h-[52px] rounded-2xl border cursor-pointer transition-all ${
                          checked ? '' : ''
                        } ${sending ? 'opacity-50 pointer-events-none' : ''}`}
                        style={{
                          borderColor: checked ? 'var(--signal)' : 'var(--stroke)',
                          background: checked ? 'var(--signal-soft)' : 'var(--surface)',
                        }}
                      >
                        <input
                          type={selectionMode === 'multiple' ? 'checkbox' : 'radio'}
                          name="helpdesk-option"
                          className="mt-1"
                          checked={checked}
                          disabled={sending}
                          onChange={() => toggleOption(option.id)}
                        />
                        <span className="flex-1">
                          <span className="block font-medium text-gray-900">{option.label}</span>
                          {option.description && (
                            <span className="block text-sm text-gray-600 mt-1">
                              {option.description}
                            </span>
                          )}
                        </span>
                      </label>
                    );
                  })}
                </div>

                {allowFreeText && !othersSelected && (
                  <div className="mt-3 flex gap-2 items-center">
                    <input
                      type="text"
                      value={freeText}
                      onChange={(e) => setFreeText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendFreeText()}
                      placeholder={
                        conversation?.free_text_hint || 'Enter your complaint…'
                      }
                      disabled={sending}
                      aria-label={
                        conversation?.free_text_hint || 'Enter your complaint…'
                      }
                      className="input flex-1 h-9 py-1.5 text-sm"
                    />
                    <button
                      onClick={sendFreeText}
                      disabled={sending || !freeText.trim()}
                      className="btn-primary flex items-center gap-2 h-9 px-3 text-sm"
                    >
                      <Send className="w-3.5 h-3.5" />
                      {conversation?.free_text_submit_label ||
                        (conversation?.state === 'DESCRIBING_OTHER' ? 'Send' : 'Raise ticket')}
                    </button>
                  </div>
                )}

                {othersSelected && (
                  <div className="mt-3 space-y-1.5">
                    <label
                      htmlFor="others-problem-description"
                      className="text-xs font-medium text-gray-600"
                    >
                      Describe your problem
                    </label>
                    <textarea
                      id="others-problem-description"
                      value={freeText}
                      onChange={(e) => setFreeText(e.target.value)}
                      placeholder="Describe your problem…"
                      disabled={sending}
                      rows={3}
                      aria-label="Describe your problem"
                      className="input w-full text-sm min-h-[72px] resize-y"
                    />
                  </div>
                )}

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={confirmSelection}
                    disabled={confirmDisabled}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {conversation?.confirm_label || 'Confirm selection'}
                    {selectedIds.length > 0 ? ` (${selectedIds.length})` : ''}
                  </button>
                  {selectedIds.length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedIds([]);
                        setFreeText('');
                      }}
                      disabled={sending}
                      className="btn-secondary text-sm"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            )}

            {conversation?.finding && (
              <div className="card bg-amber-50 border-amber-300">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 mb-2">Note:</h3>
                  {conversation.finding.hypothesis && (
                    <p className="text-gray-800 mb-3">{conversation.finding.hypothesis}</p>
                  )}
                  {conversation.finding.observations?.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-gray-700">Evidence:</p>
                      {conversation.finding.observations.map((obs, idx) => (
                        <div key={idx} className="text-sm text-gray-600 pl-3">
                          <span className="font-mono">{obs.field}:</span> {obs.value}
                          <span className="text-gray-500 ml-2">({obs.source})</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {conversation?.action_proposal && (
              <div className="card bg-green-50 border-green-300">
                <div className="flex gap-3">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-2">Note: Proposed Action</h3>
                    <p className="text-gray-800 mb-2">
                      {conversation.action_proposal.description ||
                        conversation.action_proposal.action_code}
                    </p>
                    {conversation.action_proposal.impact && (
                      <p className="text-sm text-gray-600 mb-3">
                        <span className="font-medium">Impact:</span>{' '}
                        {conversation.action_proposal.impact}
                      </p>
                    )}
                    {conversation.action_proposal.requires_approval ? (
                      <div className="flex items-center gap-2 text-amber-700">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          Requires IT approval: select an option above and Confirm
                        </span>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-600">
                        Select an action option above and press Confirm to proceed.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {conversation?.ticket && (
              <div className="card bg-purple-50 border-purple-300">
                <div className="flex gap-3">
                  <TicketIcon className="w-6 h-6 text-purple-600 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-2">
                      Ticket Created: {conversation.ticket.ticket_id}
                    </h3>
                    {conversation.ticket.summary && (
                      <p className="text-gray-800 mb-1">
                        <span className="font-medium">Summary:</span> {conversation.ticket.summary}
                      </p>
                    )}
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Status:</span> {conversation.ticket.status}
                      {conversation.ticket.assigned_team && (
                        <>
                          {' '}
                          • <span className="font-medium">Team:</span>{' '}
                          {conversation.ticket.assigned_team}
                        </>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {sessionLocked && (
              <div className="card text-sm text-gray-600">
                This chat is closed. Press <span className="font-medium text-gray-900">Start over</span>{' '}
                for a new request.
              </div>
            )}

            {conversation?.controls && conversation.controls.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {(sessionLocked
                  ? conversation.controls.filter((c) => c === 'start_over')
                  : conversation.controls
                ).map((control) => (
                  <button
                    key={control}
                    onClick={() => sendControl(control)}
                    disabled={sending}
                    className={`${
                      sessionLocked ? 'btn-primary' : 'btn-secondary'
                    } text-sm flex items-center gap-1`}
                  >
                    {control === 'back' && <ArrowLeft className="w-4 h-4" />}
                    {control === 'start_over' && <RotateCcw className="w-4 h-4" />}
                    {control === 'something_else' && <HelpCircle className="w-4 h-4" />}
                    {control.replace(/_/g, ' ').toUpperCase()}
                  </button>
                ))}
              </div>
            )}

            {error && (
              <div className="card bg-red-50 border-red-200">
                <p className="text-red-700">{error}</p>
              </div>
            )}
          </div>
        </div>

        <div className="order-2 shrink-0">
          <SidePanel onNavigate={handleNavigate} currentPage={currentPage} />
        </div>
      </div>
    </div>
  );
}

function MyTicketsView({ onBack }: { onBack: () => void }) {
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTickets();
  }, []);

  const loadTickets = async () => {
    try {
      const data = await apiClient.getMyTickets();
      setTickets(data.tickets || []);
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-6">
          <button onClick={onBack} className="btn-secondary text-sm mb-4">
            <ArrowLeft className="w-4 h-4 inline mr-1" />
            Back to Helpdesk
          </button>
          <h1 className="text-3xl font-bold text-gray-900">My Tickets</h1>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          </div>
        ) : tickets.length === 0 ? (
          <div className="card text-center py-12">
            <TicketIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No tickets found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {tickets.map((ticket) => (
              <div key={ticket.ticket_id} className="card hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-lg text-gray-900">{ticket.ticket_id}</h3>
                    <p className="text-gray-800">{ticket.summary}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      ticket.status === 'open'
                        ? 'bg-blue-100 text-blue-800'
                        : ticket.status === 'resolved'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {ticket.status}
                  </span>
                </div>
                <div className="flex gap-4 text-sm text-gray-600 mt-3">
                  <span>Priority: {ticket.priority || 'Normal'}</span>
                  {ticket.assigned_team && <span>Team: {ticket.assigned_team}</span>}
                  {ticket.created_at && (
                    <span>
                      Created:{" "}
                      {new Date(ticket.created_at).toLocaleString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
