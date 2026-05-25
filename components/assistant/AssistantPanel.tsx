"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Bot, User, Send, Loader2, TreePine,
  BarChart3, HelpCircle, Leaf, X, MessageCircle,
} from "lucide-react";
import { useMapStore } from "@/lib/store/mapStore";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const QUICK_PROMPTS = [
  { icon: BarChart3, label: "Объясни результаты",     text: "Объясни результаты последнего анализа" },
  { icon: TreePine,  label: "Что такое confidence?",  text: "Что означает уверенность модели и как её интерпретировать?" },
  { icon: Leaf,      label: "Как работает детекция?", text: "Как платформа обнаруживает деревья на снимках?" },
  { icon: HelpCircle,label: "Ограничения модели",     text: "Какие у модели ограничения и насколько точны результаты?" },
];

export function AssistantPanel() {
  const { treeCount, canopyCoverage, jobStatus } = useMapStore();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Привет! Я AI-ассистент HowTree. Могу объяснить результаты анализа или ответить на вопросы об экологии и озеленении.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [messages, isOpen]);

  const analysisContext =
    jobStatus?.status === "completed" && treeCount > 0
      ? { tree_count: treeCount, status: jobStatus.status }
      : null;

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      const updatedMessages = [...messages, userMsg];
      setMessages(updatedMessages);
      setInput("");
      setIsLoading(true);

      try {
        const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const res = await fetch(`${BASE}/api/v1/assistant/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: updatedMessages.map(({ role, content }) => ({ role, content })),
            analysis_context: analysisContext,
          }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: { content: string; action: string | null } = await res.json();
        setMessages((prev) => [...prev, { role: "assistant", content: data.content }]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Ошибка соединения с бэкендом." },
        ]);
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [messages, isLoading, analysisContext],
  );

  return (
    <>
      {/* Floating button — левый нижний угол, с отступом от сайдбара */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="fixed bottom-6 left-[336px] z-50 w-12 h-12 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg flex items-center justify-center transition-all duration-200"
        aria-label="AI-ассистент"
      >
        {isOpen ? <X className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
      </button>

      {/* Chat window — над кнопкой, слева */}
      <div
        className={`fixed bottom-20 left-[336px] z-50 w-96 bg-card border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 origin-bottom-left ${
          isOpen
            ? "opacity-100 scale-100 pointer-events-auto"
            : "opacity-0 scale-95 pointer-events-none"
        }`}
        style={{ height: "520px" }}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-border shrink-0 flex items-center gap-2.5 bg-card">
          <div className="w-7 h-7 rounded-md bg-emerald-600 flex items-center justify-center shrink-0">
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold leading-none text-foreground">AI-ассистент</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Claude Haiku · HowTree</p>
          </div>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
        </div>

        {/* Context badge */}
        {analysisContext && (
          <div className="mx-3 mt-2 px-3 py-1.5 rounded border border-emerald-800/60 bg-emerald-950/40 shrink-0">
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-emerald-300">
              <span>🌳 {treeCount.toLocaleString()} деревьев</span>
              <span>🌿 {canopyCoverage}% покрытие</span>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center shrink-0 mt-0.5 ${
                  msg.role === "user" ? "bg-primary/80" : "bg-emerald-700"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="w-3 h-3 text-white" />
                ) : (
                  <Bot className="w-3 h-3 text-white" />
                )}
              </div>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap break-words ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-secondary text-foreground rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2">
              <div className="w-5 h-5 rounded bg-emerald-700 flex items-center justify-center shrink-0">
                <Bot className="w-3 h-3 text-white" />
              </div>
              <div className="bg-secondary rounded-xl rounded-tl-sm px-3 py-2.5 flex items-center gap-1">
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick prompts */}
        {messages.length === 1 && (
          <div className="px-3 pb-2 shrink-0">
            <p className="text-[10px] text-muted-foreground mb-1.5">Быстрые вопросы:</p>
            <div className="grid grid-cols-2 gap-1">
              {QUICK_PROMPTS.map(({ icon: Icon, label, text }) => (
                <button
                  key={label}
                  onClick={() => sendMessage(text)}
                  className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-secondary hover:bg-secondary/80 text-[11px] text-muted-foreground text-left transition-colors"
                >
                  <Icon className="w-3 h-3 text-emerald-500 shrink-0" />
                  <span className="truncate">{label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="px-3 pb-3 pt-2 border-t border-border shrink-0">
          <div className="flex gap-1.5">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              placeholder="Спросите что-нибудь..."
              disabled={isLoading}
              className="flex-1 min-w-0 bg-secondary border border-border rounded-lg px-3 py-1.5 text-[12px] text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-8 h-8 bg-primary hover:bg-primary/90 disabled:bg-secondary disabled:text-muted-foreground text-primary-foreground rounded-lg flex items-center justify-center transition-colors shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}