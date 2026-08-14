import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Send, Loader2, Trash2, AlertCircle, Sparkles } from 'lucide-react';
import { useChat } from '../context/ChatContext';
import { ChatMessage } from './ChatMessage';

/**
 * The conversation body, shared by the floating widget and the /chat page.
 *
 * `variant` controls sizing only — both surfaces read the same messages from
 * ChatContext, so a thread started in the widget continues on the page.
 */

interface ChatPanelProps {
  variant?: 'widget' | 'page';
  /** Ticker the user is looking at, forwarded so "this stock" resolves. */
  symbol?: string;
}

const STARTERS = [
  "Who are today's top gainers?",
  'How is the market doing?',
  'What is JKH trading at?',
  'Give me the outlook for COMB.N0000',
];

export const ChatPanel: React.FC<ChatPanelProps> = ({ variant = 'page', symbol }) => {
  const { messages, isSending, error, isAvailable, unavailableReason, sendMessage, clearChat } =
    useChat();
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  // Follow the conversation as it grows, including while a reply is pending so
  // the typing indicator stays visible.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  const submit = useCallback(
    (text: string) => {
      if (!text.trim() || isSending) return;
      setDraft('');
      void sendMessage(text, symbol);
    },
    [isSending, sendMessage, symbol]
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter newlines — the convention every chat UI uses.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(draft);
    }
  };

  const isPage = variant === 'page';

  return (
    <div className="flex flex-col h-full min-h-0 bg-primary">
      {/* Messages */}
      <div className={`flex-1 min-h-0 overflow-y-auto space-y-4 ${isPage ? 'p-6' : 'p-4'}`}>
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-2">
            <div className="w-12 h-12 rounded-2xl bg-accent-green/10 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6 text-accent-green" />
            </div>
            <h3 className="font-bold text-text-primary mb-2">Ask about the CSE</h3>
            <p className="text-sm text-text-secondary max-w-sm mb-6">
              Every figure comes from live Colombo Stock Exchange data or the
              TradeVision model — never from the assistant's memory.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {STARTERS.map((starter) => (
                <button
                  key={starter}
                  onClick={() => submit(starter)}
                  disabled={!isAvailable || isSending}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary border border-border text-text-secondary hover:border-accent-green hover:text-accent-green disabled:opacity-50 disabled:hover:border-border disabled:hover:text-text-secondary transition-colors"
                >
                  {starter}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}

        {isSending && (
          <div className="flex items-center gap-2 text-sm text-text-secondary pl-10">
            <Loader2 className="w-4 h-4 animate-spin text-accent-green" />
            {/* A question about news triggers a scrape plus FinBERT, which is
                genuinely slow. Say so rather than let it look frozen. */}
            <span>Checking live market data…</span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Composer */}
      <div className={`border-t border-border bg-primary ${isPage ? 'p-4' : 'p-3'}`}>
        {!isAvailable && (
          <div className="mb-3 flex items-start px-3 py-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-xs text-yellow-600 dark:text-yellow-500">
            <AlertCircle className="w-3.5 h-3.5 mr-2 mt-0.5 shrink-0" />
            <span>{unavailableReason ?? 'AI chat is not available right now.'}</span>
          </div>
        )}

        {/* The failed turn is already in the thread as an error bubble; this is
            the banner for the composer, so only show it when it adds something. */}
        {error && isAvailable && (
          <div className="mb-3 flex items-start px-3 py-2 rounded-lg bg-accent-red/10 border border-accent-red/20 text-xs text-accent-red">
            <AlertCircle className="w-3.5 h-3.5 mr-2 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={!isAvailable}
            rows={1}
            placeholder={
              isAvailable
                ? symbol
                  ? `Ask about ${symbol}…`
                  : 'Ask about any CSE stock…'
                : 'AI chat is unavailable'
            }
            className="flex-1 resize-none px-3 py-2.5 max-h-32 bg-secondary border border-border rounded-xl text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent-green focus:border-transparent disabled:opacity-60 transition-all"
          />

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              title="Clear conversation"
              className="p-2.5 rounded-xl border border-border text-text-secondary hover:text-accent-red hover:border-accent-red/40 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={() => submit(draft)}
            disabled={!draft.trim() || isSending || !isAvailable}
            title="Send"
            className="p-2.5 rounded-xl bg-accent-green text-white hover:bg-accent-green/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>

        <p className="mt-2 text-[11px] text-text-secondary">
          Model output, not financial advice. Predictions can be based on older price
          data — check the date the assistant quotes.
        </p>
      </div>
    </div>
  );
};
