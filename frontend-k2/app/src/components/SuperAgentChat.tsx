import React, { useState, useRef, useEffect } from 'react';
import {
    Send,
    Bot,
    User,
    Loader2,
    Terminal,
    ChevronRight,
    ChevronDown,
    LayoutDashboard,
    Brain,
    Play,
    X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// You might need to add this endpoint to your API client or use fetch directly
const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001').replace(/\/$/, '');
const AGENT_API_URL = `${API_BASE}/api/super-agent`;

interface Step {
    tool: string;
    args: any;
    description: string;
}

interface Plan {
    thought: string;
    steps: Step[];
}

interface ExecutionLog {
    step: string;
    tool: string;
    result: string;
}

interface Message {
    role: 'user' | 'agent' | 'assistant';
    content?: string;
    plan?: Plan;
    execution_log?: ExecutionLog[];
    isThinking?: boolean;
    status?: 'awaiting_confirmation' | 'approved' | 'success' | 'error';
}

export const SuperAgentChat = () => {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'agent',
            content: "I'm the **Super Agent**. I can plan tasks, research the web, and even inspect my own codebase. How can I help?"
        }
    ]);
    // const [isTyping, setIsTyping] = useState(false); // Removed unused
    const [isLoading, setIsLoading] = useState(false);
    const [expandedPlan, setExpandedPlan] = useState<Plan | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // ... (rest of the component)

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const [showHistory, setShowHistory] = useState(false);

    // Toggle history when sending or manually
    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMsg: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        setShowHistory(true); // Show dropdown
        setExpandedPlan(null);

        try {
            const response = await fetch(AGENT_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: userMsg.content,
                    ticker: "AAPL",
                    market: "us"
                }),
            });

            const data = await response.json();

            if (data.status === 'awaiting_confirmation') {
                const planMsg: Message = {
                    role: 'assistant',
                    content: "I've created a plan. Please review and approve it to proceed.",
                    plan: data.plan,
                    status: 'awaiting_confirmation'
                };
                setMessages(prev => [...prev, planMsg]);
                setExpandedPlan(data.plan);
            } else {
                const botMsg: Message = {
                    role: 'assistant',
                    content: data.report || data.response,
                    plan: data.plan,
                    execution_log: data.execution_log
                };
                setMessages(prev => [...prev, botMsg]);
            }
        } catch (error) {
            console.error('Error:', error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleApprovePlan = async (plan: Plan, originalQuery: string) => {
        setIsLoading(true);
        try {
            const response = await fetch(AGENT_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: originalQuery, // Backend expects 'query', not 'message'
                    ticker: "AAPL", // Default or context-aware
                    market: "us",
                    session_id: "default"
                    // approved_plan: plan // Backend might not handling this yet, but sending query triggers execution
                }),
            });

            const data = await response.json();

            const botMsg: Message = {
                role: 'assistant',
                content: typeof data === 'string' ? data : data.response || JSON.stringify(data),
                execution_log: data.execution_log
            };

            setMessages(prev => {
                const updated = [...prev];
                // Update status of the plan message
                let lastIdx = -1;
                for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].status === 'awaiting_confirmation') {
                        lastIdx = i;
                        break;
                    }
                }

                if (lastIdx !== -1) {
                    updated[lastIdx] = { ...updated[lastIdx], status: 'approved' };
                }
                return [...updated, botMsg];
            });

        } catch (error) {
            console.error('Error executing plan:', error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error executing plan.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative w-full max-w-2xl mx-auto z-50">
            {/* Input Area - The 'Small Box' */}
            <form
                onSubmit={handleSendMessage}
                className={`
                    relative z-50 bg-black border border-white/10 rounded-2xl shadow-xl transition-all duration-200
                    ${showHistory ? 'rounded-b-none border-b-0' : 'hover:border-white/20 hover:shadow-2xl hover:shadow-indigo-500/10'}
                `}
            >
                <div className="flex items-center p-2">
                    <div className="pl-4 text-indigo-400">
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bot className="w-5 h-5" />}
                    </div>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onFocus={() => { if (messages.length > 1) setShowHistory(true); }}
                        placeholder="Ask Super Agent (e.g., 'Analyze TSLA')..."
                        className="flex-1 bg-transparent px-4 py-3 text-white placeholder:text-white/30 focus:outline-none text-sm font-medium"
                        disabled={isLoading || (messages.length > 0 && messages[messages.length - 1].status === 'awaiting_confirmation')}
                    />
                    <div className="flex gap-2 pr-2">
                        {messages.length > 1 && (
                            <button
                                type="button"
                                onClick={() => setShowHistory(!showHistory)}
                                className={`p-2 rounded-xl transition-colors ${showHistory ? 'bg-white/10 text-white' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}
                            >
                                {showHistory ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </button>
                        )}
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-xl transition-colors"
                        >
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            </form>

            {/* Popover History */}
            {showHistory && messages.length > 0 && (
                <div className="absolute top-full left-0 right-0 bg-[#0a0a0a]/95 backdrop-blur-xl border border-white/10 border-t-0 rounded-b-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200 max-h-[600px] flex flex-col">
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                        {messages.slice(1).map((msg, idx) => ( // Skip initial greeting in popover
                            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'assistant' ? 'bg-indigo-500/20' : 'bg-white/10'}`}>
                                    {msg.role === 'assistant' ? <Bot className="w-3 h-3 text-indigo-400" /> : <User className="w-3 h-3 text-white" />}
                                </div>
                                <div className={`flex flex-col gap-2 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                    {msg.content && (
                                        <div className={`px-4 py-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-white/5 text-slate-200 border border-white/5'}`}>
                                            <div className="prose prose-invert prose-xs max-w-none">
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                        </div>
                                    )}
                                    {msg.plan && (
                                        <div className="w-full text-xs">
                                            <button
                                                onClick={() => setExpandedPlan(expandedPlan === msg.plan ? null : (msg.plan ?? null))}
                                                className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 transition-colors mb-1.5"
                                            >
                                                {expandedPlan === msg.plan ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                                {msg.status === 'awaiting_confirmation' ? 'REVIEW PLAN' : 'VIEW REASONING'}
                                            </button>
                                            {expandedPlan === msg.plan && (
                                                <div className="bg-black/40 rounded-lg border border-indigo-500/20 p-3 space-y-3">
                                                    <div className="text-slate-400 italic">"{msg.plan.thought}"</div>
                                                    <div className="space-y-2">
                                                        {msg.plan.steps.map((step, i) => (
                                                            <div key={i} className="flex gap-2 items-start">
                                                                <span className="text-indigo-500 font-bold">{i + 1}.</span>
                                                                <div>
                                                                    <div className="text-slate-300">{step.description}</div>
                                                                    <div className="text-[10px] text-white/30 font-mono mt-0.5">Using: {step.tool}</div>
                                                                    {msg.execution_log?.[i] && (
                                                                        <div className="mt-1 bg-black/50 p-1.5 rounded text-green-300 font-mono text-[10px] break-all border-l-2 border-green-500">
                                                                            {'>'} {msg.execution_log[i].result.slice(0, 100)}...
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {msg.status === 'awaiting_confirmation' && (
                                                        <div className="flex gap-2 pt-2">
                                                            <button onClick={() => handleApprovePlan(msg.plan!, messages[messages.length - 2]?.content || "retry")} className="flex-1 bg-green-600 hover:bg-green-500 text-white py-1.5 rounded flex items-center justify-center gap-2 text-xs font-bold"><Play size={12} /> Approve</button>
                                                            <button
                                                                onClick={() => {
                                                                    setMessages(p => [...p, { role: 'assistant', content: 'Cancelled.' }]);
                                                                    setExpandedPlan(null);
                                                                }}
                                                                className="flex-1 bg-white/10 hover:bg-white/20 text-white py-1.5 rounded text-xs"
                                                            >
                                                                Cancel
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                </div>
            )}
        </div>
    );
};


