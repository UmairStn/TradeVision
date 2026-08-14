import React from 'react';
import { Bot, TrendingUp, Newspaper, Search } from 'lucide-react';
import { ChatPanel } from '../components/ChatPanel';
import { useChat } from '../context/ChatContext';

/**
 * Full-page chat. Same conversation as the floating widget — both read
 * ChatContext — so switching between them mid-thread loses nothing.
 */

const CAPABILITIES = [
  {
    icon: TrendingUp,
    title: 'Live market data',
    body: "Prices, gainers, losers and the ASPI, read from the CSE's own API when you ask.",
  },
  {
    icon: Bot,
    title: 'Model predictions',
    body: 'Next-day direction from the XGBoost model, with its probability and the date it was computed for.',
  },
  {
    icon: Newspaper,
    title: 'News sentiment',
    body: 'FinBERT over recent headlines — requested only when you ask about news, since scraping is slow.',
  },
  {
    icon: Search,
    title: 'Company lookup',
    body: 'Name a company and it finds the ticker across all listed CSE securities.',
  },
];

export const Chat: React.FC = () => {
  const { isAvailable } = useChat();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-text-primary flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-accent-green/10 flex items-center justify-center">
            <Bot className="w-6 h-6 text-accent-green" />
          </span>
          TradeVision AI
        </h1>
        <p className="text-text-secondary mt-2">
          Ask about any stock on the Colombo Stock Exchange. Answers are built from live
          data fetched during the conversation, not from the model's training set.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Conversation. Fixed height so the message list scrolls internally and
            the composer stays reachable without scrolling the page. */}
        <div className="lg:col-span-2 h-[calc(100vh-19rem)] min-h-[28rem] border border-border rounded-2xl overflow-hidden shadow-sm">
          <ChatPanel variant="page" />
        </div>

        {/* Capability list. Deliberately concrete: a chat box with no stated
            limits invites questions it cannot answer, like intraday history or
            anything outside the CSE. */}
        <aside className="space-y-4">
          <div className="bg-primary border border-border rounded-2xl p-5 shadow-sm">
            <h2 className="font-bold text-text-primary mb-4">What it can reach</h2>
            <ul className="space-y-4">
              {CAPABILITIES.map((item) => (
                <li key={item.title} className="flex gap-3">
                  <span className="shrink-0 w-8 h-8 rounded-lg bg-secondary border border-border flex items-center justify-center">
                    <item.icon className="w-4 h-4 text-accent-green" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{item.title}</p>
                    <p className="text-xs text-text-secondary mt-0.5">{item.body}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-secondary border border-border rounded-2xl p-5">
            <h2 className="font-bold text-text-primary mb-2 text-sm">Worth knowing</h2>
            <ul className="space-y-2 text-xs text-text-secondary list-disc pl-4">
              <li>
                Live prices come from the CSE. Predictions are computed from Yahoo history,
                which has stopped updating for many CSE symbols — so a prediction can be
                months old while the price beside it is current. The assistant reports the
                date; take it seriously.
              </li>
              <li>
                A question about news triggers a live scrape plus FinBERT and can take up
                to a minute the first time.
              </li>
              <li>Nothing here is financial advice.</li>
              {!isAvailable && (
                <li className="text-yellow-600 dark:text-yellow-500">
                  Chat is currently unconfigured on the server, so the composer is disabled.
                </li>
              )}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
};
