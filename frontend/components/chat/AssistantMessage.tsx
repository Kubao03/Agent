"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Step } from "@/types/chat";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { ThinkingPanel } from "./ThinkingPanel";

type AssistantMessageProps = {
  content:      string;
  steps?:       Step[];
  isStreaming?: boolean;
};

export function AssistantMessage({ content, steps, isStreaming }: AssistantMessageProps) {
  return (
    <div>
      <ThinkingPanel steps={steps ?? []} isStreaming={!!isStreaming} />

      {!content && isStreaming && (
        <span className="inline-block w-2 h-5 bg-gray-400 animate-pulse rounded" />
      )}

      {content && (
        <div className="prose prose-sm max-w-none
          prose-p:text-gray-900 prose-p:leading-7 prose-p:my-3 prose-p:text-[15px]
          prose-headings:font-semibold prose-headings:text-gray-900 prose-headings:mt-5 prose-headings:mb-2
          prose-strong:text-gray-900 prose-strong:font-semibold
          prose-ul:my-3 prose-ol:my-3 prose-li:my-1 prose-li:text-gray-900 prose-li:text-[15px]
          prose-code:text-[#e06c75] prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono prose-code:before:content-[''] prose-code:after:content-['']
          prose-pre:p-0 prose-pre:bg-transparent prose-pre:my-0 prose-pre:border-none
          prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:text-gray-600 prose-blockquote:italic
          prose-hr:border-gray-200
          prose-table:text-sm prose-th:text-gray-900 prose-td:text-gray-700"
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              code({ inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                const code  = String(children).replace(/\n$/, "");
                return !inline && match ? (
                  <CodeBlock language={match[1]} code={code} />
                ) : (
                  <code
                    className="text-[#e06c75] bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono"
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              pre({ children }) {
                return <>{children}</>;
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
