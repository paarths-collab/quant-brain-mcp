# Finverse Wealth Pipeline — Dynamic Input Architecture (v3)

**Zero Templates. Pure Intelligence. Multi-Channel Ready.**

This architecture enables **natural language input** from any source (chat, email, voice, WhatsApp, Slack) without rigid templates or forms.

---

## 🎯 Core Philosophy

**Before (Rigid):**
```python
# User MUST provide structured data
{
  "age": 35,
  "income": 100000,
  "risk_tolerance": "moderate",
  "time_horizon": 10
}
```

**After (Dynamic):**
```text
"Hey, I'm 35, make about 8-10 lakhs a year, 
don't want to lose money but okay with some risk. 
Looking to invest for my daughter's college in 10 years."

OR

"Subject: Investment advice needed
I have 50k to invest, moderate risk, 5 year horizon"

OR

"[Voice message transcribed]
So basically I got this bonus..."
```

The system **intelligently extracts** what it needs and **asks clarifying questions** when needed.

---

## 🏗️ Framework Stack (Best-of-Breed)

| Component | Framework | Why |
|-----------|-----------|-----|
| **Workflow Orchestration** | LangGraph | Stateful, streaming, debuggable |
| **LLM Routing** | LangChain | Mature ecosystem, tool calling |
| **Structured Extraction** | Instructor + Pydantic | Type-safe LLM outputs |
| **Multi-Agent Coordination** | AutoGen (optional) | When agents need to negotiate |
| **Prompt Optimization** | DSPy (future) | Auto-optimize prompts with data |
| **Memory & Context** | LangChain Memory | Conversation history |
| **Tool Calling** | OpenAI Function Calling | Native integration |

---

## 📊 Dynamic State (No Templates)

```python
from pydantic import BaseModel, Field
from typing import Optional, Any

class DynamicWealthState(BaseModel):
    """State evolves as information is gathered"""
    
    # Raw input (any format)
    raw_input: str
    input_channel: str  # "chat" | "email" | "voice" | "whatsapp"
    
    # Extracted information (filled progressively)
    user_context: dict[str, Any] = Field(default_factory=dict)
    # Examples: age, income, occupation, dependents, current_investments
    
    investment_intent: dict[str, Any] = Field(default_factory=dict)
    # Examples: goal, amount, time_horizon, risk_preference
    
    # Confidence scores (what we know vs. what we need)
    extraction_confidence: dict[str, float] = Field(default_factory=dict)
    missing_critical_info: list[str] = Field(default_factory=list)
    
    # Market intelligence (same as before)
    market_data: dict = Field(default_factory=dict)
    news_context: dict = Field(default_factory=dict)
    
    # Recommendations (progressive build)
    discovered_sectors: list[str] = Field(default_factory=list)
    selected_stocks: list[dict] = Field(default_factory=list)
    allocation_strategy: dict = Field(default_factory=dict)
    
    # Communication
    clarification_questions: list[str] = Field(default_factory=list)
    investment_report: str = ""
    
    # Execution trace
    execution_log: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
```

---

## 🧠 Dynamic Agent Architecture

### 1. **IntelligentIntakeAgent** (NEW)
*Replaces rigid InputStructurerAgent*

**Framework:** Instructor + OpenAI Function Calling

**Job:**
- Parse ANY input format (prose, bullet points, email, voice transcription)
- Extract entities using LLM
- Assess confidence in extracted data
- Generate smart follow-up questions

```python
from instructor import from_openai
from openai import OpenAI
from pydantic import BaseModel

class ExtractedUserProfile(BaseModel):
    age: Optional[int] = None
    income_range: Optional[str] = None  # "50k-1L", "1L-5L", etc.
    risk_appetite: Optional[str] = None  # "conservative", "moderate", "aggressive"
    time_horizon_years: Optional[int] = None
    investment_amount: Optional[str] = None
    primary_goal: Optional[str] = None
    confidence: float  # 0-1 score

class IntelligentIntakeAgent:
    def __init__(self):
        self.client = from_openai(OpenAI())
    
    def extract(self, raw_input: str, channel: str) -> ExtractedUserProfile:
        """Use LLM to extract structured data from unstructured input"""
        
        prompt = f"""
        Extract investment profile from this {channel} message.
        Be conservative with confidence scores.
        
        User input: {raw_input}
        """
        
        return self.client.chat.completions.create(
            model="gpt-4",
            response_model=ExtractedUserProfile,
            messages=[{"role": "user", "content": prompt}]
        )
    
    def generate_clarifications(self, profile: ExtractedUserProfile) -> list[str]:
        """Ask questions for low-confidence or missing critical fields"""
        questions = []
        
        if profile.confidence < 0.7:
            if not profile.age or profile.age == 0:
                questions.append("What's your age? This helps us plan your investment horizon.")
            
            if not profile.investment_amount:
                questions.append("How much are you looking to invest?")
            
            if not profile.time_horizon_years:
                questions.append("What's your investment timeframe? (e.g., 1 year, 5 years, 10+ years)")
            
            if not profile.risk_appetite:
                questions.append(
                    "How comfortable are you with market fluctuations?\n"
                    "• Conservative (preserve capital)\n"
                    "• Moderate (balanced growth)\n"
                    "• Aggressive (maximize returns)"
                )
        
        return questions
```

---

### 2. **AdaptiveRiskProfiler** (Enhanced)

**Framework:** LangChain + Custom Logic

**Job:**
- Convert fuzzy risk descriptions → numeric score
- Handle cultural context ("I'm risk-averse" vs "I can handle volatility")
- Use conversational history for context

```python
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class AdaptiveRiskProfiler:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    def calculate_risk_score(self, state: DynamicWealthState) -> int:
        """Convert natural language → risk score (1-10)"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a risk profiling expert.
            
            Convert user's risk tolerance description to a score (1-10):
            1-3: Conservative (capital preservation, minimal volatility)
            4-6: Moderate (balanced, some volatility okay)
            7-10: Aggressive (growth-focused, high volatility acceptable)
            
            Consider:
            - Explicit risk statements
            - Age and time horizon
            - Financial situation
            - Cultural context
            
            Return ONLY the numeric score."""),
            ("user", """
            User profile: {profile}
            Time horizon: {horizon} years
            
            Calculate risk score:
            """)
        ])
        
        response = self.llm.invoke(
            prompt.format(
                profile=state.user_context,
                horizon=state.investment_intent.get("time_horizon_years", 5)
            )
        )
        
        return int(response.content.strip())
```

---

### 3. **ConversationalMarketDataAgent** (Enhanced)

**Framework:** LangChain Tools + Custom APIs

**Job:**
- Fetch data based on **extracted context** (not predefined queries)
- Adapt search queries to user's language/location

```python
from langchain.agents import Tool
from langchain.agents import initialize_agent, AgentType
from duckduckgo_search import DDGS

class ConversationalMarketDataAgent:
    def __init__(self):
        self.ddg = DDGS()
        self.tools = self._setup_tools()
        self.agent = initialize_agent(
            self.tools,
            ChatOpenAI(model="gpt-4"),
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True
        )
    
    def _setup_tools(self):
        return [
            Tool(
                name="search_market_news",
                func=self._search_news,
                description="Search for current market news and sentiment"
            ),
            Tool(
                name="fetch_stock_data",
                func=self._fetch_yahoo_finance,
                description="Get stock fundamentals and price data"
            )
        ]
    
    def run(self, state: DynamicWealthState) -> DynamicWealthState:
        """Dynamically determine what data to fetch"""
        
        # LLM decides what data is needed based on context
        query = f"""
        User wants to invest in: {state.investment_intent}
        Current sectors discovered: {state.discovered_sectors}
        
        What market data should we fetch? Generate search queries.
        """
        
        result = self.agent.run(query)
        
        state.market_data = result
        state.execution_log.append("Market data fetched dynamically")
        return state
    
    def _search_news(self, query: str) -> str:
        results = self.ddg.text(query, max_results=5)
        return str(results)
    
    def _fetch_yahoo_finance(self, symbols: str) -> dict:
        # Implementation here
        pass
```

---

### 4. **ContextAwareSectorDiscovery**

**Framework:** LangChain + RAG (optional)

**Job:**
- Recommend sectors based on:
  - User's risk profile
  - Current market regime
  - News sentiment
  - User's stated preferences (if any)

```python
class ContextAwareSectorDiscovery:
    def discover(self, state: DynamicWealthState) -> list[str]:
        """Use LLM reasoning to discover sectors"""
        
        prompt = f"""
        Based on this investor profile:
        {state.user_context}
        
        Risk score: {state.user_context.get('risk_score')}
        Time horizon: {state.investment_intent.get('time_horizon_years')} years
        
        Current market conditions:
        {state.news_context.get('macro_news', 'Not available')}
        
        Recommend 3-5 sectors suitable for this investor.
        Consider: risk alignment, market outlook, diversification.
        
        Return as JSON array of sector names.
        """
        
        # Use Instructor for structured output
        # Returns: ["Technology", "Healthcare", "Financial Services"]
```

---

### 5. **Multi-Channel Response Generator**

**Framework:** LangChain + Template Engine

**Job:**
- Generate responses adapted to input channel
- Email → formal report
- Chat → conversational bullets
- WhatsApp → concise summaries

```python
class MultiChannelResponseGenerator:
    def generate(self, state: DynamicWealthState) -> str:
        channel = state.input_channel
        
        if channel == "email":
            return self._generate_email_report(state)
        elif channel == "chat":
            return self._generate_chat_response(state)
        elif channel == "whatsapp":
            return self._generate_whatsapp_summary(state)
        else:
            return self._generate_default_report(state)
    
    def _generate_email_report(self, state: DynamicWealthState) -> str:
        """Formal, detailed report with sections"""
        prompt = f"""
        Write a professional investment report email.
        
        Allocation: {state.allocation_strategy}
        Stocks: {state.selected_stocks}
        Rationale: Based on risk score {state.user_context.get('risk_score')}
        
        Structure:
        - Executive Summary
        - Recommended Allocation
        - Stock Details with rationale
        - Risk Disclaimer
        - Next Steps
        """
        # Generate using LLM
    
    def _generate_chat_response(self, state: DynamicWealthState) -> str:
        """Conversational, friendly tone"""
        prompt = f"""
        Respond conversationally about these recommendations:
        {state.allocation_strategy}
        
        Keep it friendly, use emojis if appropriate, bullet points for clarity.
        """
        # Generate using LLM
    
    def _generate_whatsapp_summary(self, state: DynamicWealthState) -> str:
        """Ultra-concise, mobile-friendly"""
        prompt = """
        Create a WhatsApp-style summary (max 3 paragraphs):
        - Top 3 stocks
        - Why they fit
        - Next step
        
        Keep it casual and brief.
        """
        # Generate using LLM
```

---

## 🔄 LangGraph Flow (Dynamic)

```python
from langgraph.graph import StateGraph, END

def build_dynamic_wealth_graph():
    graph = StateGraph(DynamicWealthState)
    
    # Dynamic intake
    graph.add_node("intake", intelligent_intake_agent)
    graph.add_node("clarify", clarification_handler)
    graph.add_node("risk_profile", adaptive_risk_profiler)
    
    # Data gathering
    graph.add_node("fetch_market_data", conversational_market_agent)
    
    # Analysis
    graph.add_node("discover_sectors", context_aware_sector_discovery)
    graph.add_node("select_stocks", stock_selection_agent)
    graph.add_node("allocate", allocation_agent)
    
    # Validation
    graph.add_node("critic", critic_agent)
    
    # Response generation
    graph.add_node("generate_response", multi_channel_response_generator)
    
    # Conditional edges
    def should_clarify(state):
        return "clarify" if state.clarification_questions else "risk_profile"
    
    def should_retry(state):
        return "fetch_market_data" if state.errors else "generate_response"
    
    graph.add_edge("intake", should_clarify)
    graph.add_edge("clarify", "risk_profile")
    graph.add_edge("risk_profile", "fetch_market_data")
    graph.add_edge("fetch_market_data", "discover_sectors")
    graph.add_edge("discover_sectors", "select_stocks")
    graph.add_edge("select_stocks", "allocate")
    graph.add_edge("allocate", "critic")
    graph.add_edge("critic", should_retry)
    graph.add_edge("generate_response", END)
    
    graph.set_entry_point("intake")
    
    return graph.compile()
```

---

## 🎨 Usage Examples

### Example 1: Casual Chat
```python
result = wealth_pipeline.run({
    "raw_input": "yo I got 50k lying around, what should I do with it? 
                  don't wanna lose it but also don't want it sitting idle",
    "input_channel": "chat"
})

# System:
# 1. Extracts: amount=50k, risk=moderate, goal=growth
# 2. Asks: "What's your time horizon?" (low confidence)
# 3. User: "maybe 3-4 years"
# 4. Proceeds with recommendations
```

### Example 2: Email
```python
result = wealth_pipeline.run({
    "raw_input": """
    Subject: Investment advice for daughter's education
    
    Hi, I'm 38 years old, software engineer earning 25L/year.
    I want to invest 5L for my daughter's college fund (she's 8 now).
    I can tolerate some risk but not comfortable with very volatile instruments.
    """,
    "input_channel": "email"
})

# System auto-extracts:
# - age: 38
# - income: 25L
# - amount: 5L
# - goal: education
# - time_horizon: ~10 years
# - risk: moderate
# No clarification needed, proceeds directly
```

### Example 3: Voice Transcription
```python
result = wealth_pipeline.run({
    "raw_input": """
    [Transcribed voice note]
    Um, so I just got my annual bonus, it's around 3 lakhs,
    and I'm thinking instead of just putting it in savings,
    maybe I should invest? I'm 29, work in marketing,
    pretty stable job. Not sure about stocks though,
    seems risky. Maybe mutual funds? What do you think?
    """,
    "input_channel": "voice"
})

# System handles:
# - Filler words ("um", "maybe")
# - Uncertainty ("not sure", "what do you think")
# - Implicit risk preference (concerned about risk)
# - Generates conversational response
```

---

## 🚀 Implementation Priorities

### Phase 1: Core Dynamic Intake
1. ✅ Implement IntelligentIntakeAgent with Instructor
2. ✅ Add confidence scoring
3. ✅ Build clarification question generator
4. ✅ Test with 20+ varied inputs

### Phase 2: Channel Adaptation
1. ✅ Multi-channel response templates
2. ✅ Tone/style adaptation
3. ✅ Format handling (markdown, plain text, HTML)

### Phase 3: Advanced Intelligence
1. ✅ Memory integration (remember user across sessions)
2. ✅ Context carryover (reference previous conversations)
3. ✅ Auto-refinement based on user feedback

---

## 🎯 Framework Decision Matrix

| Use Case | Recommended Framework | Alternative |
|----------|----------------------|-------------|
| Workflow orchestration | **LangGraph** | Temporal, Prefect |
| Structured LLM outputs | **Instructor** | Guardrails, Marvin |
| Tool/function calling | **LangChain Tools** | Native OpenAI |
| Multi-agent debates | **AutoGen** | CrewAI |
| Prompt optimization | **DSPy** | Manual A/B testing |
| Memory management | **LangChain Memory** | Redis + custom |
| Observability | **LangSmith** | Helicone, Phoenix |

---

## 📝 Key Principles

1. **No Templates**: System adapts to user's communication style
2. **Progressive Extraction**: Gather information conversationally
3. **Confidence-Aware**: Know what you know, ask about what you don't
4. **Channel-Adaptive**: Email ≠ Chat ≠ Voice
5. **Fail Gracefully**: Handle ambiguity, don't force structure

---

## 🔧 Next Steps

1. Would you like me to **implement the IntelligentIntakeAgent** with actual code?
2. Should I create a **comparison of agentic frameworks** (LangGraph vs AutoGen vs CrewAI)?
3. Want a **demo notebook** showing dynamic input handling?
4. Need **API specifications** for multi-channel endpoints?

Let me know what to build next!
