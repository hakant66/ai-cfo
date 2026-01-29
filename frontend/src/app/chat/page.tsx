"use client";

import { useState } from "react";
import { postAuthed } from "@/hooks/useApi";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const ask = async () => {
    if (!question) return;
    const newMessages: Message[] = [...messages, { role: "user", content: question }];
    setMessages(newMessages);
    setLoading(true);
    setQuestion("");
    try {
      const response = await postAuthed<{ answer: string }>("/chat/ask", { question });
      setMessages([...newMessages, { role: "assistant", content: response.answer }]);
    } catch (err) {
      setMessages([
        ...newMessages,
        { role: "assistant", content: "Unable to answer. Please verify your data sources." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-ink/60">Ask CFO</p>
        <h1 className="text-3xl font-semibold">Natural language finance analysis</h1>
      </div>

      <Card className="grid gap-4">
        <div className="grid gap-3">
          {messages.length === 0 && <p className="text-sm text-ink/70">Ask about cash runway, inventory risk, or payables timing.</p>}
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.role === "user" ? "text-right" : "text-left"}>
              <div className={msg.role === "user" ? "inline-block rounded-lg bg-ink px-4 py-2 text-white" : "inline-block rounded-lg bg-fog px-4 py-2 text-ink"}>
                {msg.content}
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <Input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What is our cash outlook for 14 days?" />
          <Button onClick={ask} disabled={loading}>
            {loading ? "Thinking" : "Ask"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
