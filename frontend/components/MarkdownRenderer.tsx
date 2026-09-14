"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-content text-xs leading-relaxed text-slate-200">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-white mt-3 mb-2 tracking-tight">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-white mt-3 mb-1.5 tracking-tight border-b border-slate-800 pb-1">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mt-2 mb-1.5 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 inline-block" />
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="mb-2 leading-relaxed text-slate-300">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white bg-slate-800/40 px-1 py-0.5 rounded text-[11px] border border-slate-700/50">
              {children}
            </strong>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 my-2 text-slate-300 pl-1">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="space-y-2 my-2 text-slate-300 counter-reset-item">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-1">
              {children}
            </li>
          ),
          code: ({ children }) => (
            <code className="font-mono text-[11px] bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-indigo-300">
              {children}
            </code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-indigo-500 pl-3 my-2 text-slate-400 italic">
              {children}
            </blockquote>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
