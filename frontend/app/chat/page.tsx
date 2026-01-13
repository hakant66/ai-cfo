const messages = [
  {
    role: "assistant",
    content: "Cash position is $42,000 as of today. Expected net inflow next 7 days: $6,000.",
  },
];

export default function ChatPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Ask CFO</h1>
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div key={index} className="rounded bg-slate-100 px-3 py-2 text-sm">
              {message.content}
            </div>
          ))}
        </div>
        <div className="mt-4 flex gap-2">
          <input className="flex-1 rounded border px-3 py-2" placeholder="Ask about cash runway..." />
          <button className="rounded bg-slate-900 px-4 py-2 text-white">Send</button>
        </div>
      </div>
    </section>
  );
}
