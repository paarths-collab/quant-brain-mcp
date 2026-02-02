import { useState, useEffect, useRef } from 'react';
import {
  Sparkles, Send, Bot, User, TrendingUp, TrendingDown,
  BarChart3, PieChart, Target, Shield, Zap, Brain,
  RefreshCw, Copy, Check, Lightbulb, AlertTriangle, DollarSign
} from 'lucide-react';
import { sentimentAPI, wealthAPI } from '../api';
import './InvestmentAI.css';

const sampleQueries = [
  "Analyze AAPL stock for investment",
  "What's the sentiment for NVDA?",
  "Analyze RELIANCE.NS for long-term investment",
  "Should I buy TCS.NS stock?",
  "Risk assessment for TSLA at current valuations",
  "Analyze MSFT stock outlook",
];

const aiCapabilities = [
  { icon: Target, title: 'Portfolio Optimization', desc: 'AI-driven asset allocation' },
  { icon: Brain, title: 'Stock Analysis', desc: 'Deep fundamental & technical analysis' },
  { icon: Shield, title: 'Risk Assessment', desc: 'Comprehensive risk profiling' },
  { icon: BarChart3, title: 'Market Insights', desc: 'Real-time market intelligence' },
];

// Extract stock symbol from query
const extractSymbol = (query) => {
  // Common patterns: "analyze AAPL", "NVDA stock", "what about RELIANCE.NS"
  const patterns = [
    /analyze\s+([A-Z]{1,5}(?:\.[A-Z]{1,2})?)/i,
    /([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\s+stock/i,
    /sentiment\s+for\s+([A-Z]{1,5}(?:\.[A-Z]{1,2})?)/i,
    /buy\s+([A-Z]{1,5}(?:\.[A-Z]{1,2})?)/i,
    /\b([A-Z]{2,5}(?:\.[A-Z]{1,2})?)\b/,
  ];

  for (const pattern of patterns) {
    const match = query.match(pattern);
    if (match) return match[1].toUpperCase();
  }
  return null;
};

// Format sentiment API response to markdown
const formatSentimentResponse = (data, symbol) => {
  const sentiment = data.sentiment || 'Neutral';
  const outlook = data.outlook || 'Mixed outlook based on current market conditions.';
  const recommendation = data.recommendation || 'Hold';
  const targetPrice = data.targetPrice || data.target_price || 'N/A';
  const risks = data.risks || [];
  const catalysts = data.catalysts || [];
  const metrics = data.metrics || {};

  let response = `## 📊 ${symbol} Stock Analysis\n\n`;
  response += `### Current Assessment: ${sentiment} ${sentiment === 'Bullish' ? '🟢' : sentiment === 'Bearish' ? '🔴' : '⚪'}\n\n`;
  response += `**AI Recommendation:** ${recommendation}\n`;
  response += `**Target Price:** ${targetPrice}\n\n`;
  response += `### 📈 Outlook\n${outlook}\n\n`;

  if (Object.keys(metrics).length > 0) {
    response += `### 📊 Key Metrics\n`;
    response += `| Metric | Value |\n|--------|-------|\n`;
    Object.entries(metrics).forEach(([key, value]) => {
      response += `| ${key} | ${value} |\n`;
    });
    response += '\n';
  }

  if (risks.length > 0) {
    response += `### ⚠️ Key Risks\n`;
    risks.forEach(risk => {
      response += `- ${risk}\n`;
    });
    response += '\n';
  }

  if (catalysts.length > 0) {
    response += `### ✅ Potential Catalysts\n`;
    catalysts.forEach(catalyst => {
      response += `- ${catalyst}\n`;
    });
    response += '\n';
  }

  if (data.reddit_posts_count) {
    response += `\n*Analysis based on ${data.reddit_posts_count} Reddit discussions and market data.*\n`;
  }

  response += '\n*This is AI-generated analysis. Please consult a financial advisor before investing.*';

  return response;
};

function InvestmentAI() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copied, setCopied] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    const query = input;
    setInput('');
    setIsTyping(true);

    try {
      // Try to extract a stock symbol from the query
      const symbol = extractSymbol(query);

      if (symbol) {
        // Determine market based on symbol
        const isIndian = symbol.endsWith('.NS') || symbol.endsWith('.BO');
        const market = isIndian ? 'india' : 'us';

        // Call sentiment API
        const response = await sentimentAPI.analyze(symbol, market);

        if (response.data && !response.data.error) {
          const formattedResponse = formatSentimentResponse(response.data, symbol);
          const aiMessage = { role: 'assistant', content: formattedResponse };
          setMessages(prev => [...prev, aiMessage]);
        } else {
          throw new Error(response.data?.error || 'Analysis failed');
        }
      } else {
        // Generic response for non-stock queries
        const genericResponse = `## 🤖 AI Investment Assistant

Thank you for your query: "${query}"

I specialize in analyzing individual stocks. To get detailed analysis, try asking about a specific stock like:

- "Analyze AAPL stock"
- "What's the sentiment for NVDA?"
- "Should I buy RELIANCE.NS?"
- "Risk assessment for TSLA"

I'll provide:
- 📊 Fundamental analysis
- 📈 Technical indicators
- 💬 Social sentiment from Reddit
- ⚠️ Risk assessment
- ✅ Investment catalysts

*Powered by real-time market data and AI analysis.*`;

        const aiMessage = { role: 'assistant', content: genericResponse };
        setMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error('AI analysis error:', error);
      const errorResponse = `## ⚠️ Analysis Error

I encountered an issue while analyzing your request. This could be due to:
- Invalid stock symbol
- Network connectivity issues
- Market data unavailable

Please try again with a valid stock symbol like:
- US Stocks: AAPL, MSFT, GOOGL, NVDA
- Indian Stocks: RELIANCE.NS, TCS.NS, HDFCBANK.NS

*If the issue persists, the backend service may be unavailable.*`;

      const aiMessage = { role: 'assistant', content: errorResponse };
      setMessages(prev => [...prev, aiMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSampleQuery = (query) => {
    setInput(query);
    inputRef.current?.focus();
  };

  const handleCopy = (content, idx) => {
    navigator.clipboard.writeText(content);
    setCopied(idx);
    setTimeout(() => setCopied(null), 2000);
  };

  const clearChat = () => {
    setMessages([]);
  };

  const formatMessage = (content) => {
    // Simple markdown-like formatting
    return content
      .replace(/## (.*)/g, '<h2>$1</h2>')
      .replace(/### (.*)/g, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/✅/g, '<span class="icon-check">✅</span>')
      .replace(/⚠️/g, '<span class="icon-warn">⚠️</span>')
      .replace(/❌/g, '<span class="icon-x">❌</span>')
      .replace(/🚀/g, '<span class="icon">🚀</span>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="ai-page">
      {/* Header */}
      <div className="ai-header">
        <div className="ai-title">
          <div className="ai-logo">
            <Sparkles size={28} />
          </div>
          <div>
            <h1>Ultimate Investment AI</h1>
            <p>Your AI-powered investment advisor • Powered by advanced LLM</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button className="clear-btn" onClick={clearChat}>
            <RefreshCw size={16} />
            New Chat
          </button>
        )}
      </div>

      {/* Main Content */}
      <div className="ai-content">
        {messages.length === 0 ? (
          /* Empty State */
          <div className="ai-empty">
            <div className="ai-hero">
              <div className="hero-icon">
                <Brain size={48} />
              </div>
              <h2>How can I help you invest smarter?</h2>
              <p>
                I can analyze stocks, optimize portfolios, assess risks, and provide
                market insights for both Indian and US markets.
              </p>
            </div>

            {/* Capabilities */}
            <div className="capabilities-grid">
              {aiCapabilities.map((cap, i) => (
                <div key={i} className="capability-card">
                  <cap.icon size={22} />
                  <h3>{cap.title}</h3>
                  <p>{cap.desc}</p>
                </div>
              ))}
            </div>

            {/* Sample Queries */}
            <div className="sample-queries">
              <h3><Lightbulb size={18} /> Try asking:</h3>
              <div className="queries-grid">
                {sampleQueries.map((query, i) => (
                  <button
                    key={i}
                    className="query-chip"
                    onClick={() => handleSampleQuery(query)}
                  >
                    {query}
                  </button>
                ))}
              </div>
            </div>

            {/* Disclaimer */}
            <div className="ai-disclaimer">
              <AlertTriangle size={16} />
              <span>
                AI-generated insights are for educational purposes only.
                Always consult a SEBI-registered advisor before making investment decisions.
              </span>
            </div>
          </div>
        ) : (
          /* Chat Messages */
          <div className="chat-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                </div>
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <>
                      <div
                        className="message-text"
                        dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
                      />
                      <button
                        className="copy-btn"
                        onClick={() => handleCopy(msg.content, idx)}
                      >
                        {copied === idx ? <Check size={14} /> : <Copy size={14} />}
                        {copied === idx ? 'Copied!' : 'Copy'}
                      </button>
                    </>
                  ) : (
                    <div className="message-text">{msg.content}</div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="message assistant">
                <div className="message-avatar">
                  <Bot size={18} />
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="ai-input-area">
        <div className="input-container">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about stocks, portfolios, market trends..."
            rows={1}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
          >
            <Send size={18} />
          </button>
        </div>
        <p className="input-hint">
          <Zap size={12} /> Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

export default InvestmentAI;
