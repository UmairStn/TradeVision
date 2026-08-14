import React, { useState } from 'react';
import { useLocation, useSearchParams, Link } from 'react-router-dom';
import { MessageCircle, X, Maximize2, Bot } from 'lucide-react';
import { ChatPanel } from './ChatPanel';
import { useChat } from '../context/ChatContext';

/**
 * Floating chat, available on every page except /chat itself.
 *
 * The symbol context is read from the URL rather than from StockContext, because
 * the URL is where the analyzer actually keeps the selected ticker
 * (`/analyzer?ticker=JKH.N0000`). Reading it here means "should I buy this?"
 * resolves to the stock on screen, and resolves to nothing when there isn't one —
 * which is the honest answer on the home page.
 */
export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { messages, isAvailable } = useChat();

  // Two chats on one screen would share state and fight over scroll position.
  if (location.pathname === '/chat') return null;

  const symbol =
    location.pathname === '/analyzer' ? searchParams.get('ticker') ?? undefined : undefined;

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        title="Ask TradeVision AI"
        aria-label="Open AI chat"
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-2xl bg-accent-green text-white shadow-lg shadow-accent-green/30 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
      >
        <MessageCircle className="w-6 h-6" />
        {/* Unread-ish marker: the conversation is still there after closing, so
            hint that reopening resumes rather than starts over. */}
        {messages.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-text-primary text-primary text-[11px] font-bold flex items-center justify-center">
            {messages.length > 9 ? '9+' : messages.length}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[calc(100vw-3rem)] sm:w-96 h-[32rem] max-h-[calc(100vh-6rem)] flex flex-col bg-primary border border-border rounded-2xl shadow-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/50">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-accent-green/10 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-accent-green" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-text-primary leading-tight">TradeVision AI</p>
            <p className="text-xs text-text-secondary truncate">
              {!isAvailable ? 'Unavailable' : symbol ? `Context: ${symbol}` : 'Live CSE data'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {/* The thread lives in ChatContext, so the full page picks it up mid-
              conversation instead of starting a second one. */}
          <Link
            to="/chat"
            onClick={() => setIsOpen(false)}
            title="Open full page"
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-secondary transition-colors"
          >
            <Maximize2 className="w-4 h-4" />
          </Link>
          <button
            onClick={() => setIsOpen(false)}
            title="Close"
            aria-label="Close AI chat"
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-secondary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <ChatPanel variant="widget" symbol={symbol} />
      </div>
    </div>
  );
};
