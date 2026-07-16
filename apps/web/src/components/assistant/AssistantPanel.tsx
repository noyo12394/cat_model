"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, CheckCircle2, Database, Send, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { AssistantAnswer } from "@/lib/types";
import { ConfidencePill } from "@/components/common/Badges";

type ChatMessage =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "assistant"; text: string; result: AssistantAnswer };

/** Ask EarthPulse is an evidence-grounded tool navigator. Groq can improve
 * phrasing server-side, but the visible tool trace and platform facts are
 * computed before a language model is called. */
export function AssistantPanel({ question }: { question: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const askedInitial = useRef("");
  const nextId = useRef(1);

  const mutation = useMutation({
    mutationFn: (prompt: string) => api.queryAssistant(prompt),
    onSuccess: (result) => {
      setMessages((current) => [...current, { id: nextId.current++, role: "assistant", text: result.answer, result }]);
    },
  });

  const ask = (prompt: string) => {
    const clean = prompt.trim();
    if (!clean || mutation.isPending) return;
    setMessages((current) => [...current, { id: nextId.current++, role: "user", text: clean }]);
    setInput("");
    mutation.mutate(clean);
  };

  useEffect(() => {
    if (!question.trim() || askedInitial.current === question) return;
    askedInitial.current = question;
    ask(question);
    // `ask` intentionally runs only when a new panel question arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question]);

  const latest = [...messages].reverse().find((message): message is Extract<ChatMessage, { role: "assistant" }> => message.role === "assistant");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask(input);
  };

  return (
    <div className="agent-panel">
      <header className="agent-header">
        <span className="agent-avatar" aria-hidden><Bot size={18} /></span>
        <div>
          <strong>Ask EarthPulse</strong>
          <span>Grounded compound-hazard navigator</span>
        </div>
        <span className={`agent-provider ${latest?.result.prose_source === "groq-grounded" ? "is-live" : ""}`}>
          {latest?.result.prose_source === "groq-grounded" ? "Groq active" : "Grounded mode"}
        </span>
      </header>

      <div className="agent-guardrail">
        <ShieldCheck size={14} aria-hidden />
        <span>Tools calculate first. AI explains second. No invented hazard values.</span>
      </div>

      <div className="agent-thread" aria-live="polite">
        {messages.map((message) => message.role === "user" ? (
          <article className="agent-message agent-message-user" key={message.id}>
            <span>You</span><p>{message.text}</p>
          </article>
        ) : (
          <article className="agent-message agent-message-ai" key={message.id}>
            <span>Navigator</span>
            <p>{message.text}</p>
            <div className="agent-meta">
              <ConfidencePill value={message.result.confidence} />
              <span>{message.result.time_range.label}</span>
              {message.result.location_label && <span>{message.result.location_label}</span>}
            </div>

            {message.result.tool_trace.length > 0 && (
              <details className="agent-trace" open>
                <summary><Sparkles size={13} /> Tool trace</summary>
                {message.result.tool_trace.map((call) => (
                  <div className="agent-tool" key={`${message.id}-${call.tool}`}>
                    {call.status === "complete" ? <CheckCircle2 size={13} /> : <Database size={13} />}
                    <span><strong>{call.tool.replaceAll("_", " ")}</strong>{call.summary}</span>
                  </div>
                ))}
              </details>
            )}

            <details className="agent-evidence">
              <summary>Evidence &amp; limits</summary>
              {message.result.observed_vs_inferred.map((item) => <p key={item}>{item}</p>)}
              {message.result.sources.map((source) => <p key={source.label}>Source: {source.label}</p>)}
              {message.result.limitations.map((item) => <p key={item}>Limit: {item}</p>)}
            </details>
          </article>
        ))}
        {mutation.isPending && <div className="agent-thinking"><span /><span /><span /> Checking EarthPulse tools…</div>}
        {mutation.isError && <p className="agent-error">The agent could not reach the evidence service. Try again.</p>}
      </div>

      <div className="agent-suggestions" aria-label="Suggested questions">
        {(latest?.result.suggested_questions ?? ["Show the compound event", "What should we check next?"]).slice(0, 3).map((suggestion) => (
          <button type="button" key={suggestion} onClick={() => ask(suggestion)} disabled={mutation.isPending}>{suggestion}</button>
        ))}
      </div>

      <form className="agent-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="earthpulse-agent-input">Ask EarthPulse</label>
        <input id="earthpulse-agent-input" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask about evidence, routes, or possible futures…" maxLength={500} />
        <button type="submit" disabled={!input.trim() || mutation.isPending} aria-label="Send question"><Send size={16} /></button>
      </form>
    </div>
  );
}
