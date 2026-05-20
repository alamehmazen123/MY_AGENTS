export function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  return (
    <div className="bg-gray-950 rounded my-2 overflow-hidden text-xs">
      <div className="flex justify-between px-2 py-1 bg-gray-900 text-gray-400">
        <span>{lang || 'code'}</span>
        <button className="hover:text-white">Copy</button>
      </div>
      <pre className="p-3 overflow-auto">
        <code>{code}</code>
      </pre>
    </div>
  )
}
