import React from 'react';
import { Bot, User, AlertCircle, Wrench } from 'lucide-react';
import type { ChatMessage as ChatMessageData } from '../types/stock';

/**
 * One chat bubble.
 *
 * WHY THERE IS A HAND-ROLLED FORMATTER HERE
 * Gemini writes in markdown — `**bold**` for figures, `*` bullets for lists — and
 * raw asterisks on screen look like a bug. Pulling in react-markdown for two
 * constructs would add a parser and a sanitiser to the bundle for no other
 * benefit, so bold and bullets are handled below and everything else renders as
 * plain text. Nothing here uses dangerouslySetInnerHTML: model output is
 * untrusted input, and it is only ever turned into React nodes.
 */

/** `**19.90**` -> a <strong> node. Leaves everything else alone. */
const renderInline = (text: string): React.ReactNode[] =>
  text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.length > 4 && part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i} className="font-semibold text-text-primary">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    )
  );

const BULLET = /^\s*[*-]\s+/;

/** Paragraphs and bullet lists. Blank lines separate blocks. */
const renderBlocks = (content: string): React.ReactNode[] => {
  const blocks: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flushBullets = () => {
    if (!bullets.length) return;
    blocks.push(
      <ul key={`ul${blocks.length}`} className="list-disc pl-5 space-y-1 my-2">
        {bullets.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    bullets = [];
  };

  for (const line of content.split('\n')) {
    if (BULLET.test(line)) {
      bullets.push(line.replace(BULLET, ''));
      continue;
    }
    flushBullets();
    if (line.trim()) {
      blocks.push(
        <p key={`p${blocks.length}`} className="my-1">
          {renderInline(line)}
        </p>
      );
    }
  }
  flushBullets();

  return blocks;
};

export const ChatMessage: React.FC<{ message: ChatMessageData }> = ({ message }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-2">
        <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-sm bg-accent-green text-white text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <div className="shrink-0 w-8 h-8 rounded-full bg-secondary border border-border flex items-center justify-center">
          <User className="w-4 h-4 text-text-secondary" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2">
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          message.isError ? 'bg-accent-red/10' : 'bg-accent-green/10'
        }`}
      >
        {message.isError ? (
          <AlertCircle className="w-4 h-4 text-accent-red" />
        ) : (
          <Bot className="w-4 h-4 text-accent-green" />
        )}
      </div>

      <div className="max-w-[85%] space-y-2">
        <div
          className={`px-4 py-2.5 rounded-2xl rounded-bl-sm text-sm leading-relaxed break-words ${
            message.isError
              ? 'bg-accent-red/10 border border-accent-red/20 text-accent-red'
              : 'bg-secondary border border-border text-text-secondary'
          }`}
        >
          {message.isError ? message.content : renderBlocks(message.content)}
        </div>

        {/* The assistant may not state a figure it did not fetch, so show what it
            fetched. This is the user's check on the answer, not decoration. */}
        {message.toolsUsed && message.toolsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.toolsUsed.map((tool, i) => (
              <span
                key={`${tool}-${i}`}
                title="Live data this answer was built from"
                className="inline-flex items-center max-w-full px-2 py-0.5 rounded-md bg-primary border border-border text-[11px] font-mono text-text-secondary"
              >
                <Wrench className="w-3 h-3 mr-1 shrink-0" />
                <span className="truncate">{tool}</span>
              </span>
            ))}
          </div>
        )}

        {message.warnings && message.warnings.length > 0 && (
          <div className="space-y-1">
            {message.warnings.map((warning, i) => (
              <p
                key={`${warning}-${i}`}
                className="flex items-start text-[11px] text-yellow-600 dark:text-yellow-500"
              >
                <AlertCircle className="w-3 h-3 mr-1 mt-0.5 shrink-0" />
                <span>{warning}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
