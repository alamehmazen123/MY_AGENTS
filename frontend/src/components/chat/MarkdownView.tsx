import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github-dark.css'

function FencedCode({ inline, className, children }: any) {
  const text = String(children).replace(/\n$/, '')

  // Inline `code` — small monospace, no box.
  if (inline) {
    return (
      <code className="px-1 py-0.5 rounded bg-gray-100 text-pink-700 font-mono text-[0.85em]">
        {text}
      </code>
    )
  }

  const lang = (className || '').replace(/^language-/, '') || ''
  let html: string
  try {
    html =
      lang && hljs.getLanguage(lang)
        ? hljs.highlight(text, { language: lang, ignoreIllegals: true }).value
        : hljs.highlightAuto(text).value
  } catch {
    html = text.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] || c))
  }

  return <CodeBlockBox text={text} lang={lang || 'code'} html={html} />
}

function CodeBlockBox({ text, lang, html }: { text: string; lang: string; html: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* ignore */
    }
  }
  return (
    <div className="my-2 rounded-md border border-gray-700 bg-[#0d1117] overflow-hidden text-xs">
      <div className="flex items-center justify-between px-2 py-1 bg-gray-900/80 text-gray-400 border-b border-gray-700">
        <span className="font-mono">{lang}</span>
        <button
          onClick={copy}
          className="px-2 py-0.5 rounded hover:bg-gray-800 hover:text-white transition-colors"
          title="Copy this code block"
        >
          {copied ? '✓ Copied' : '📋 Copy code'}
        </button>
      </div>
      <pre className="p-3 overflow-auto m-0">
        <code className="hljs" dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    </div>
  )
}

// Compact, readable typography for chat bubbles (no @tailwindcss/typography dep).
const COMPONENTS = {
  code: FencedCode as any,
  h1: (p: any) => <h2 className="text-base font-bold mt-2 mb-1" {...p} />,
  h2: (p: any) => <h3 className="text-sm font-bold mt-2 mb-1" {...p} />,
  h3: (p: any) => <h4 className="text-sm font-semibold mt-1 mb-1" {...p} />,
  ul: (p: any) => <ul className="list-disc pl-5 my-1 space-y-0.5" {...p} />,
  ol: (p: any) => <ol className="list-decimal pl-5 my-1 space-y-0.5" {...p} />,
  li: (p: any) => <li className="text-sm" {...p} />,
  p: (p: any) => <p className="my-1 text-sm leading-snug" {...p} />,
  a: (p: any) => <a className="text-blue-600 underline" target="_blank" rel="noreferrer" {...p} />,
  strong: (p: any) => <strong className="font-semibold" {...p} />,
  em: (p: any) => <em className="italic" {...p} />,
  blockquote: (p: any) => (
    <blockquote className="border-l-2 border-gray-400 pl-2 italic my-1 text-gray-700" {...p} />
  ),
  hr: () => <hr className="my-2 border-gray-300" />,
  table: (p: any) => <table className="border-collapse my-2 text-xs" {...p} />,
  th: (p: any) => <th className="border border-gray-300 px-2 py-1 bg-gray-100" {...p} />,
  td: (p: any) => <td className="border border-gray-300 px-2 py-1" {...p} />,
}

export function MarkdownView({ text }: { text: string }) {
  return <ReactMarkdown components={COMPONENTS}>{text}</ReactMarkdown>
}
