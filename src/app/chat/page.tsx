"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

interface Message {
  role: "user" | "model";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("playerprincipal");
  const [apiUrl, setApiUrl] = useState("http://127.0.0.1:8000");
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const stored = localStorage.getItem("chess_trainer_username");
    if (stored) setUsername(stored);
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim() || !username) return;
    
    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/chat/${username}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages })
      });
      const data = await res.json();
      
      if (data.status === "success") {
        setMessages([...newMessages, { role: "model", content: data.reply }]);
      } else {
        setMessages([...newMessages, { role: "model", content: "Error: " + data.message }]);
      }
    } catch (e) {
      setMessages([...newMessages, { role: "model", content: "Failed to connect to AI Coach." }]);
    }
    
    setLoading(false);
  };

  const handleQuickAction = (action: string) => {
    sendMessage(action);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-zinc-950 font-[family-name:var(--font-geist-sans)]">
      <header className="p-4 bg-white dark:bg-black border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm font-medium hover:text-blue-600 transition">
            &larr; Dashboard
          </Link>
          <h1 className="text-xl font-bold">AI Chat Coach</h1>
        </div>
        <div className="text-sm text-gray-500">
          Coaching: <span className="font-semibold text-gray-900 dark:text-gray-100">{username}</span>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 max-w-3xl w-full mx-auto flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
            <h2 className="text-2xl font-semibold mb-2">Welcome to your AI Coach</h2>
            <p className="text-gray-500 max-w-md mb-8">
              I am grounded in your exact game telemetry, weaknesses, and blunder history. Ask me anything or use a quick action below.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              <button onClick={() => handleQuickAction("What should I work on today based on my plan?")} className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 px-4 py-2 rounded-full text-sm hover:bg-gray-50 dark:hover:bg-zinc-800 transition shadow-sm">
                What should I work on today?
              </button>
              <button onClick={() => handleQuickAction("Review my last 3 blunders using your tools.")} className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 px-4 py-2 rounded-full text-sm hover:bg-gray-50 dark:hover:bg-zinc-800 transition shadow-sm">
                Review my recent blunders
              </button>
              <button onClick={() => handleQuickAction("What is my performance in the Caro-Kann Defense as Black?")} className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 px-4 py-2 rounded-full text-sm hover:bg-gray-50 dark:hover:bg-zinc-800 transition shadow-sm">
                How is my Caro-Kann?
              </button>
              <button onClick={() => handleQuickAction("Explain my biggest weakness in plain terms.")} className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 px-4 py-2 rounded-full text-sm hover:bg-gray-50 dark:hover:bg-zinc-800 transition shadow-sm">
                Explain my biggest weakness
              </button>
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl p-4 whitespace-pre-wrap ${m.role === "user" ? "bg-blue-600 text-white" : "bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 shadow-sm"}`}>
                {m.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 dark:bg-zinc-800 animate-pulse rounded-2xl p-4 w-24">
              <span className="opacity-0">...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="p-4 bg-white dark:bg-black border-t border-gray-200 dark:border-zinc-800">
        <form 
          className="max-w-3xl mx-auto relative"
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
        >
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask your coach..."
            className="w-full bg-gray-100 dark:bg-zinc-900 border border-transparent focus:border-blue-500 focus:bg-white dark:focus:bg-zinc-950 rounded-full py-4 pl-6 pr-16 outline-none transition disabled:opacity-50"
          />
          <button 
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full px-4 font-medium transition disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
