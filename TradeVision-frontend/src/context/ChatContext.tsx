import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/stock';
import { sendChatMessage, fetchChatStatus } from '../services/api';

/**
 * One conversation, shared by the floating widget and the /chat page.
 *
 * The state lives up here rather than inside either component so a user can open
 * the widget, ask two questions, then click through to the full page and find the
 * thread intact. The backend is stateless — it gets the whole history on every
 * turn — so this provider is the only place the conversation exists.
 */

interface ChatContextType {
  messages: ChatMessage[];
  /** True while awaiting a reply. Turns can be slow: tool calls, sometimes a scrape. */
  isSending: boolean;
  error: string | null;
  /** False when the server has no GEMINI_API_KEY, so the UI can say so up front. */
  isAvailable: boolean;
  unavailableReason: string | null;
  sendMessage: (text: string, symbol?: string) => Promise<void>;
  clearChat: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

/** Monotonic ids, so two identical questions still get distinct React keys. */
let messageSeq = 0;
const nextId = () => `m${++messageSeq}`;

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAvailable, setIsAvailable] = useState(true);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);

  // Read in sendMessage without making it depend on `messages`, which would
  // rebuild the callback on every turn and re-render both chat surfaces.
  const messagesRef = useRef<ChatMessage[]>(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    let stale = false;
    void fetchChatStatus().then((status) => {
      if (stale) return;
      setIsAvailable(status.available);
      setUnavailableReason(status.available ? null : status.detail);
    });
    return () => { stale = true; };
  }, []);

  const sendMessage = useCallback(async (text: string, symbol?: string) => {
    const content = text.trim();
    if (!content || isSending) return;

    const userMessage: ChatMessage = { id: nextId(), role: 'user', content };
    // Show the user's own message immediately; the reply can take a while.
    const history = [...messagesRef.current, userMessage];
    setMessages(history);
    setIsSending(true);
    setError(null);

    try {
      const reply = await sendChatMessage(history, symbol);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          content: reply.reply,
          toolsUsed: reply.toolsUsed,
          warnings: reply.warnings,
        },
      ]);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'The assistant could not reply.';
      setError(message);
      // Also record it in the thread. Without this the conversation reads as if
      // the question was never asked, and the user's own message is still there.
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', content: message, isError: true },
      ]);
    } finally {
      setIsSending(false);
    }
  }, [isSending]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        messages, isSending, error, isAvailable, unavailableReason, sendMessage, clearChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

// Hook is co-located with its provider by design; the rule only affects the
// granularity of dev-server fast refresh, not runtime behaviour.
// eslint-disable-next-line react-refresh/only-export-components
export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
