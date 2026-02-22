# Boomerang Trading Terminal - Architecture Guide

> **Complete Guide to Understanding Backend, Frontend, and React Development**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [React Fundamentals](#react-fundamentals)
5. [Data Flow](#data-flow)
6. [WebSocket Communication](#websocket-communication)
7. [File Connections Map](#file-connections-map)
8. [How to Add New Features](#how-to-add-new-features)

---

## System Overview

### High-Level Architecture

```
┌─────────────────┐         HTTP/WebSocket          ┌──────────────────┐
│                 │ ◄────────────────────────────► │                  │
│  Frontend       │         API Calls              │   Backend        │
│  (React + TS)   │         Real-time Data         │   (FastAPI)      │
│                 │                                │                  │
└─────────────────┘                                └──────────────────┘
        │                                                    │
        │                                                    │
        ▼                                                    ▼
┌─────────────────┐                                ┌──────────────────┐
│  UI Components  │                                │   Services       │
│  - AIChat.tsx   │                                │   - backtest     │
│  - QuantLab.tsx │                                │   - monte_carlo  │
└─────────────────┘                                └──────────────────┘
```

### Technology Stack

**Backend:**
- **FastAPI**: Modern Python web framework for building APIs
- **WebSocket**: Real-time bidirectional communication
- **Pandas/NumPy**: Data analysis and numerical computing
- **YFinance**: Stock market data fetching

**Frontend:**
- **React 18**: UI library for building component-based interfaces
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Recharts**: Data visualization library
- **TailwindCSS**: Utility-first CSS framework

---

## Backend Architecture

### Directory Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── routes/
│   ├── backtest.py           # Backtest endpoints (HTTP + WebSocket)
│   ├── live_feed.py          # Live market data WebSocket
│   └── super_agent.py        # AI agent endpoints
├── services/
│   ├── backtest_service.py   # Core backtesting logic
│   ├── monte_carlo.py        # Monte Carlo simulations
│   └── risk_metrics.py       # Risk calculations
└── finverse_integration/
    └── strategies/           # Trading strategies
        ├── momentum.py
        ├── mean_reversion.py
        └── ema_crossover.py
```

### How Backend Works

#### 1. **Entry Point: main.py**

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import backtest, live_feed, super_agent

app = FastAPI()

# Enable CORS so frontend can communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(backtest.router, prefix="/api/backtest")
app.include_router(live_feed.router, prefix="/ws")
app.include_router(super_agent.router, prefix="/api")
```

**Key Concepts:**
- `FastAPI()`: Creates the main application
- `CORSMiddleware`: Allows frontend (different port) to make requests
- `include_router()`: Connects route files to main app

#### 2. **Routes: backtest.py**

```python
# routes/backtest.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.backtest_service import run_backtest_service

router = APIRouter()

# HTTP Endpoint
@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Traditional HTTP endpoint - returns all data at once"""
    result = run_backtest_service(
        ticker=request.ticker,
        strategy=request.strategy
    )
    return {"status": "ok", "data": result}

# WebSocket Endpoint
@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    """Real-time streaming endpoint - sends progress updates"""
    await websocket.accept()
    
    try:
        # Receive request from frontend
        data = await websocket.receive_json()
        ticker = data.get("ticker")
        strategy = data.get("strategy")
        
        # Send progress updates
        await websocket.send_json({"status": "starting"})
        await websocket.send_json({"status": "fetching"})
        
        # Run backtest (in thread to avoid blocking)
        result = await asyncio.to_thread(
            run_backtest_service, ticker, strategy
        )
        
        # Send final result
        await websocket.send_json({
            "status": "complete",
            "data": result
        })
    except WebSocketDisconnect:
        print("Client disconnected")
```

**Key Concepts:**
- `APIRouter()`: Groups related endpoints
- `@router.post()`: HTTP POST endpoint decorator
- `@router.websocket()`: WebSocket endpoint decorator
- `async/await`: Asynchronous programming for non-blocking operations
- `asyncio.to_thread()`: Runs blocking code in separate thread

#### 3. **Services: backtest_service.py**

```python
# services/backtest_service.py
import yfinance as yf
import pandas as pd
from .monte_carlo import run_monte_carlo_simulation
from ..finverse_integration.strategies.momentum import momentum_strategy

def run_backtest_service(ticker: str, strategy: str):
    """
    Core backtesting logic
    
    Flow:
    1. Fetch historical price data
    2. Apply trading strategy
    3. Calculate performance metrics
    4. Run Monte Carlo simulations
    5. Return comprehensive results
    """
    
    # Step 1: Fetch data from Yahoo Finance
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y")  # 2 years of data
    
    # Step 2: Apply strategy
    if strategy == "momentum":
        signals = momentum_strategy(df)
    
    # Step 3: Calculate returns
    equity_curve = calculate_equity_curve(df, signals)
    
    # Step 4: Run Monte Carlo (1000 simulations)
    monte_carlo_results = run_monte_carlo_simulation(
        equity_curve, simulations=1000
    )
    
    # Step 5: Calculate risk metrics
    var_95 = calculate_var(equity_curve, confidence=0.95)
    
    # Return everything
    return {
        "ticker": ticker,
        "strategy": {
            "best_strategy": {
                "strategy": strategy,
                "return": total_return,
                "win_rate": win_rate,
                "equity_curve": equity_curve.to_dict(),
                "trades": trade_list,
                "monteCarlo": monte_carlo_results
            }
        },
        "risk_engine": {
            "VaR": var_95,
            "CVaR": cvar_95
        }
    }
```

**Key Concepts:**
- Functions are the work units
- Data flows through transformations
- Returns dictionary that becomes JSON for frontend

---

## Frontend Architecture

### Directory Structure

```
frontend-k2/app/src/
├── main.tsx                  # React app entry point
├── App.tsx                   # Root component with routing
├── pages/
│   ├── AIChat.tsx           # Main chat interface (1780+ lines)
│   ├── QuantLab.tsx         # Quant lab interface
│   └── Dashboard.tsx        # Portfolio dashboard
├── components/
│   └── LightweightChart.tsx # Reusable chart component
└── api/
    └── index.ts             # API client functions
```

### How Frontend Works

#### 1. **Entry Point: main.tsx**

```tsx
// main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Render the entire React app into the HTML element with id="root"
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**What happens:**
1. `ReactDOM.createRoot()` finds `<div id="root"></div>` in HTML
2. Renders `<App />` component inside it
3. React takes over and manages all UI updates

#### 2. **Root Component: App.tsx**

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AIChat from './pages/AIChat'
import QuantLab from './pages/QuantLab'
import Dashboard from './pages/Dashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AIChat />} />
        <Route path="/quant-lab" element={<QuantLab />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

**Key Concepts:**
- `BrowserRouter`: Enables client-side routing (URL changes without page reload)
- `Routes`: Container for all routes
- `Route`: Maps URL path to component
- `/` → Shows AIChat component
- `/quant-lab` → Shows QuantLab component

#### 3. **Main Page: AIChat.tsx**

This is the most complex file. Let's break it down:

```tsx
// AIChat.tsx - Simplified structure
import { useState, useRef, useEffect } from 'react'
import { Send, Terminal } from 'lucide-react'

// ========================================
// CONSTANTS & CONFIG
// ========================================
const API_BASE = 'http://127.0.0.1:8001'
const WS_URL = 'ws://127.0.0.1:8001/ws/live'
const BACKTEST_WS_URL = 'ws://127.0.0.1:8001/api/backtest/ws'

// ========================================
// TYPE DEFINITIONS
// ========================================
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  agentData?: AgentResponse
}

interface AgentResponse {
  financial?: { ticker: string; price: number }
  strategy?: {
    best_strategy?: {
      strategy: string
      return: number
      equity_curve?: Array<{time: string; value: number}>
      monteCarlo?: MonteCarloResult
    }
  }
}

// ========================================
// HELPER COMPONENTS
// ========================================
function MessageBubble({ message }: { message: Message }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded bg-orange-500">
        <Terminal size={16} />
      </div>
      <div className="flex-1">
        {message.content}
      </div>
    </div>
  )
}

function AnalyticsDashboard({ 
  agentData, 
  ticker 
}: { 
  agentData?: AgentResponse
  ticker?: string 
}) {
  return (
    <div>
      <h2>Analytics Terminal</h2>
      {/* Display charts, metrics, etc */}
      {agentData?.strategy?.best_strategy && (
        <div>
          Return: {agentData.strategy.best_strategy.return}%
        </div>
      )}
    </div>
  )
}

// ========================================
// MAIN COMPONENT
// ========================================
export default function AIChat() {
  // STATE: Data that changes and triggers re-renders
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [latestAgentData, setLatestAgentData] = useState<AgentResponse>()
  
  // REFS: Persistent values that don't trigger re-renders
  const wsRef = useRef<WebSocket | null>(null)
  const backtestWsRef = useRef<WebSocket | null>(null)
  
  // EFFECTS: Side effects that run when dependencies change
  useEffect(() => {
    // Connect to WebSocket when component mounts
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setLatestAgentData(data)
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.report,
        timestamp: new Date(),
        agentData: data
      }])
    }
    
    // Cleanup when component unmounts
    return () => ws.close()
  }, []) // Empty array = run once on mount
  
  // EVENT HANDLERS
  const sendMessage = async () => {
    if (!input.trim()) return
    
    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }])
    
    // Send to backend
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ query: input }))
    } else {
      // Fallback to HTTP
      const response = await fetch(`${API_BASE}/api/super-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })
      })
      const data = await response.json()
      setLatestAgentData(data)
    }
    
    setInput('')
  }
  
  const runBacktest = (ticker: string, strategy: string) => {
    const ws = new WebSocket(BACKTEST_WS_URL)
    backtestWsRef.current = ws
    
    ws.onopen = () => {
      ws.send(JSON.stringify({ ticker, strategy }))
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.status === 'complete') {
        setLatestAgentData(data.data)
      }
    }
  }
  
  // RENDER: JSX that defines UI
  return (
    <div className="flex gap-4 h-screen p-4">
      {/* Left Panel - Chat */}
      <div className="flex-1 flex flex-col">
        <h1>Command Interface</h1>
        
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
        
        {/* Input Area */}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Enter command..."
          />
          <button onClick={sendMessage}>
            <Send size={20} />
          </button>
        </div>
      </div>
      
      {/* Right Panel - Analytics */}
      <div className="w-[45%]">
        <AnalyticsDashboard 
          agentData={latestAgentData}
          ticker={latestAgentData?.financial?.ticker}
        />
      </div>
    </div>
  )
}
```

---

## React Fundamentals

### 1. **Components**

Components are reusable UI pieces. Think of them as functions that return HTML-like code (JSX).

```tsx
// Simple component (no logic)
function Button() {
  return <button>Click me</button>
}

// Component with props (inputs)
function Button({ text, onClick }: { text: string; onClick: () => void }) {
  return <button onClick={onClick}>{text}</button>
}

// Using the component
<Button text="Submit" onClick={() => console.log('Clicked!')} />
```

### 2. **State (useState)**

State is data that can change and triggers re-rendering.

```tsx
const [count, setCount] = useState(0)
//     ↑       ↑                    ↑
//   value  updater           initial value

// Reading state
console.log(count) // 0

// Updating state
setCount(1)              // Set to 1
setCount(count + 1)      // Increment (⚠️ may be stale)
setCount(prev => prev + 1) // Increment (✅ always correct)
```

**When to use:**
- Form inputs: `const [email, setEmail] = useState('')`
- Loading states: `const [loading, setLoading] = useState(false)`
- Fetched data: `const [users, setUsers] = useState([])`

### 3. **Effects (useEffect)**

Effects run code when component mounts or when dependencies change.

```tsx
// Run once on mount
useEffect(() => {
  console.log('Component mounted')
}, [])

// Run when 'count' changes
useEffect(() => {
  console.log(`Count changed to ${count}`)
}, [count])

// Cleanup function
useEffect(() => {
  const ws = new WebSocket('ws://...')
  
  return () => {
    // This runs when component unmounts
    ws.close()
  }
}, [])
```

**Common use cases:**
- Fetch data when component loads
- Set up WebSocket connections
- Subscribe to events
- Clean up resources

### 4. **Refs (useRef)**

Refs store values that persist between renders but DON'T trigger re-renders.

```tsx
const inputRef = useRef<HTMLInputElement>(null)
const wsRef = useRef<WebSocket | null>(null)

// Access DOM element
const focusInput = () => {
  inputRef.current?.focus()
}

// Store WebSocket without triggering re-render
useEffect(() => {
  wsRef.current = new WebSocket('ws://...')
}, [])

// Use in JSX
<input ref={inputRef} />
```

**State vs Ref:**
- State: Changes trigger re-render (UI updates)
- Ref: Changes don't trigger re-render (background data)

### 5. **Props**

Props pass data from parent to child components.

```tsx
// Parent component
function Parent() {
  const [name, setName] = useState('John')
  
  return <Child name={name} age={25} />
}

// Child component
function Child({ name, age }: { name: string; age: number }) {
  return <div>{name} is {age} years old</div>
}
```

**Props flow one way:** Parent → Child (not the other way)

### 6. **Conditional Rendering**

Show/hide UI based on conditions.

```tsx
// Method 1: && operator
{isLoading && <Spinner />}

// Method 2: Ternary
{isLoggedIn ? <Dashboard /> : <Login />}

// Method 3: Early return
if (!data) return <Loading />
return <Content data={data} />
```

### 7. **Lists**

Render arrays of data.

```tsx
const users = ['Alice', 'Bob', 'Charlie']

return (
  <ul>
    {users.map((user, index) => (
      <li key={index}>{user}</li>
    ))}
  </ul>
)
```

**Always provide `key` prop for list items!**

---

## Data Flow

### Frontend → Backend Flow

```
┌──────────────┐
│ User Action  │  (Click button, type input)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Event Handler│  (onClick, onChange)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  HTTP/WS     │  (fetch, WebSocket.send)
│  Request     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Backend    │
│   Endpoint   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Service    │  (Business logic)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Response   │  (JSON data)
└──────────────┘
```

### Backend → Frontend Flow

```
┌──────────────┐
│  Backend     │
│  Sends Data  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Frontend    │
│  Receives    │  (ws.onmessage, fetch response)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Update State│  (setState, setData)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  React       │
│  Re-renders  │  (Automatic!)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  UI Updates  │  (User sees new data)
└──────────────┘
```

### Example: Complete Flow

**Scenario:** User clicks "WS BACKTEST" button

```tsx
// 1. USER CLICKS BUTTON
<button onClick={() => runBacktestViaWebSocket('AAPL', 'momentum')}>
  WS BACKTEST
</button>

// 2. EVENT HANDLER RUNS
const runBacktestViaWebSocket = (ticker: string, strategy: string) => {
  // 3. OPEN WEBSOCKET
  const ws = new WebSocket(BACKTEST_WS_URL)
  
  ws.onopen = () => {
    // 4. SEND REQUEST TO BACKEND
    ws.send(JSON.stringify({ ticker, strategy }))
  }
  
  ws.onmessage = (event) => {
    // 8. RECEIVE RESPONSE FROM BACKEND
    const data = JSON.parse(event.data)
    
    if (data.status === 'complete') {
      // 9. UPDATE STATE
      setLatestAgentData(data.data)
      // 10. REACT RE-RENDERS (automatic)
      // 11. UI SHOWS NEW CHARTS
    }
  }
}

// Meanwhile on backend...
// 5. BACKEND RECEIVES REQUEST
@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    
    # 6. RUN BACKTEST SERVICE
    result = await asyncio.to_thread(
        run_backtest_service,
        ticker=data['ticker'],
        strategy=data['strategy']
    )
    
    # 7. SEND RESPONSE
    await websocket.send_json({
        "status": "complete",
        "data": result
    })
```

---

## WebSocket Communication

### Why WebSockets?

**HTTP:** Request → Wait → Response (one-way, single exchange)

**WebSocket:** Persistent connection, both sides can send anytime (two-way, ongoing)

### Backend WebSocket Setup

```python
# routes/backtest.py
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    # 1. Accept connection
    await websocket.accept()
    
    try:
        # 2. Receive data (wait for client to send)
        data = await websocket.receive_json()
        
        # 3. Send updates (can send multiple times!)
        await websocket.send_json({"status": "starting"})
        await websocket.send_json({"status": "processing"})
        
        # 4. Do work
        result = await asyncio.to_thread(run_backtest, data)
        
        # 5. Send final result
        await websocket.send_json({"status": "complete", "data": result})
        
    except WebSocketDisconnect:
        print("Client disconnected")
```

### Frontend WebSocket Setup

```tsx
// Create connection
const ws = new WebSocket('ws://127.0.0.1:8001/api/backtest/ws')

// Connection opened
ws.onopen = () => {
  console.log('Connected!')
  ws.send(JSON.stringify({ ticker: 'AAPL', strategy: 'momentum' }))
}

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  if (data.status === 'starting') {
    console.log('Backtest starting...')
  } else if (data.status === 'complete') {
    console.log('Done!', data.data)
  }
}

// Connection closed
ws.onclose = () => {
  console.log('Disconnected')
}

// Error handling
ws.onerror = (error) => {
  console.error('WebSocket error:', error)
}

// Close connection manually
ws.close()
```

---

## File Connections Map

### How AIChat.tsx Connects Everything

```
AIChat.tsx (Main Component)
│
├─ Imports Components
│  ├─ LightweightChart.tsx ────► Candlestick charts
│  └─ Local components (MessageBubble, AnalyticsDashboard)
│
├─ Uses API Client
│  └─ api/index.ts ────► investorProfileAPI.load()
│
├─ Connects to Backend
│  ├─ WebSocket: ws://127.0.0.1:8001/ws/live
│  │  └─► backend/routes/live_feed.py
│  │
│  ├─ WebSocket: ws://127.0.0.1:8001/api/backtest/ws
│  │  └─► backend/routes/backtest.py @router.websocket("/ws")
│  │       └─► services/backtest_service.py run_backtest_service()
│  │            ├─► services/monte_carlo.py
│  │            └─► strategies/momentum.py
│  │
│  └─ HTTP POST: /api/super-agent
│     └─► backend/routes/super_agent.py
│
└─ State Flow
   ├─ User types in input → setInput()
   ├─ User sends message → sendMessage()
   ├─ Backend responds → setLatestAgentData()
   └─ React re-renders with new data
```

### Backend Service Connections

```
routes/backtest.py
│
├─ Calls ────► services/backtest_service.py
│              │
│              ├─ Uses ────► yfinance (fetch data)
│              │
│              ├─ Calls ────► strategies/momentum.py
│              │              └─ Returns: buy/sell signals
│              │
│              ├─ Calls ────► services/monte_carlo.py
│              │              └─ Returns: simulation results
│              │
│              └─ Calls ────► services/risk_metrics.py
│                             └─ Returns: VaR, CVaR, drawdown
│
└─ Returns JSON to frontend
```

---

## How to Add New Features

### Example: Add a New Chart

**Step 1: Add data to backend response**

```python
# services/backtest_service.py
def run_backtest_service(ticker, strategy):
    # ... existing code ...
    
    # NEW: Calculate moving averages
    df['MA_20'] = df['Close'].rolling(20).mean()
    df['MA_50'] = df['Close'].rolling(50).mean()
    
    return {
        # ... existing return data ...
        "strategy": {
            "best_strategy": {
                # ... existing fields ...
                "moving_averages": {  # NEW FIELD
                    "ma20": df['MA_20'].tolist(),
                    "ma50": df['MA_50'].tolist()
                }
            }
        }
    }
```

**Step 2: Update TypeScript interface**

```tsx
// AIChat.tsx
interface StrategyData {
  best_strategy?: {
    strategy: string
    return: number
    equity_curve?: Array<{time: string; value: number}>
    moving_averages?: {  // NEW FIELD
      ma20: number[]
      ma50: number[]
    }
  }
}
```

**Step 3: Create chart component**

```tsx
// AIChat.tsx
function MovingAveragesChart({ data }: { data: {ma20: number[]; ma50: number[]} }) {
  const chartData = data.ma20.map((val, i) => ({
    index: i,
    ma20: val,
    ma50: data.ma50[i]
  }))
  
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData}>
        <XAxis dataKey="index" />
        <YAxis />
        <Line type="monotone" dataKey="ma20" stroke="#ff6b35" />
        <Line type="monotone" dataKey="ma50" stroke="#3b82f6" />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

**Step 4: Add to AnalyticsDashboard**

```tsx
// AIChat.tsx - Inside AnalyticsDashboard component
{agentData?.strategy?.best_strategy?.moving_averages && (
  <div className="terminal-border border-2 rounded-lg p-4">
    <h3>Moving Averages</h3>
    <MovingAveragesChart 
      data={agentData.strategy.best_strategy.moving_averages}
    />
  </div>
)}
```

**Done!** The new chart appears when backend sends the data.

### Example: Add a New WebSocket Endpoint

**Step 1: Create backend endpoint**

```python
# routes/new_feature.py
from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/new-feature")
async def new_feature_websocket(websocket: WebSocket):
    await websocket.accept()
    
    data = await websocket.receive_json()
    
    # Do something
    result = process_data(data)
    
    await websocket.send_json({"result": result})
```

**Step 2: Register in main.py**

```python
# main.py
from routes import new_feature

app.include_router(new_feature.router, prefix="/api")
```

**Step 3: Connect from frontend**

```tsx
// AIChat.tsx
const NEW_FEATURE_WS = 'ws://127.0.0.1:8001/api/ws/new-feature'

const callNewFeature = () => {
  const ws = new WebSocket(NEW_FEATURE_WS)
  
  ws.onopen = () => {
    ws.send(JSON.stringify({ param: 'value' }))
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    console.log('Received:', data)
  }
}
```

---

## Common Patterns & Best Practices

### 1. **State Management**

```tsx
// ❌ BAD: Multiple related states
const [firstName, setFirstName] = useState('')
const [lastName, setLastName] = useState('')
const [email, setEmail] = useState('')

// ✅ GOOD: Single object state
const [user, setUser] = useState({
  firstName: '',
  lastName: '',
  email: ''
})

// Update single field
setUser(prev => ({ ...prev, firstName: 'John' }))
```

### 2. **Conditional Data Access**

```tsx
// ❌ BAD: Can cause errors if data is undefined
const return = agentData.strategy.best_strategy.return

// ✅ GOOD: Optional chaining
const return = agentData?.strategy?.best_strategy?.return

// ✅ BETTER: With default value
const return = agentData?.strategy?.best_strategy?.return ?? 0

// ✅ BEST: Type guard
if (agentData?.strategy?.best_strategy) {
  const return = agentData.strategy.best_strategy.return
}
```

### 3. **Event Handlers**

```tsx
// ❌ BAD: Creating new function on every render
<button onClick={() => handleClick(param)}>Click</button>

// ✅ GOOD: Use useCallback for performance
const handleClick = useCallback((param: string) => {
  console.log(param)
}, []) // Dependencies array

<button onClick={() => handleClick('test')}>Click</button>
```

### 4. **Fetching Data**

```tsx
// Standard pattern
useEffect(() => {
  let cancelled = false
  
  const fetchData = async () => {
    try {
      const response = await fetch('/api/data')
      const data = await response.json()
      
      if (!cancelled) {
        setData(data)
      }
    } catch (error) {
      console.error('Error:', error)
    }
  }
  
  fetchData()
  
  return () => {
    cancelled = true // Prevent state update if unmounted
  }
}, [])
```

### 5. **Component Organization**

```tsx
// Order your component code consistently:

function MyComponent() {
  // 1. State hooks
  const [state, setState] = useState()
  
  // 2. Ref hooks
  const ref = useRef()
  
  // 3. Effect hooks
  useEffect(() => {}, [])
  
  // 4. Event handlers
  const handleClick = () => {}
  
  // 5. Helper functions
  const formatData = () => {}
  
  // 6. Return JSX
  return <div>...</div>
}
```

---

## Debugging Tips

### Backend Debugging

```python
# Add print statements
print(f"Received ticker: {ticker}")
print(f"Data shape: {df.shape}")

# Use pdb debugger
import pdb; pdb.set_trace()

# Check FastAPI docs (automatic!)
# Visit: http://127.0.0.1:8001/docs
```

### Frontend Debugging

```tsx
// Console logging
console.log('State:', state)
console.log('Data:', agentData)

// React DevTools (browser extension)
// - View component tree
// - Inspect props and state
// - Track re-renders

// Network tab
// - See all HTTP/WebSocket requests
// - Check request/response data

// Add error boundaries
try {
  // Risky code
} catch (error) {
  console.error('Error:', error)
}
```

---

## Quick Reference Card

### React Hooks Cheat Sheet

```tsx
// State
const [value, setValue] = useState(initialValue)

// Effect (runs on mount)
useEffect(() => { /* code */ }, [])

// Effect (runs when dep changes)
useEffect(() => { /* code */ }, [dependency])

// Ref
const ref = useRef(initialValue)

// Callback (memoized function)
const fn = useCallback(() => { /* code */ }, [deps])
```

### FastAPI Cheat Sheet

```python
# HTTP Endpoint
@router.post("/path")
async def endpoint(data: RequestModel):
    return {"result": data}

# WebSocket Endpoint
@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    await websocket.send_json({"result": data})
```

### Common TypeScript Types

```tsx
// Basic types
string, number, boolean, null, undefined

// Arrays
string[], Array<string>

// Objects
{ key: string; value: number }

// Optional properties
{ key?: string }

// Union types
string | number

// Function types
(param: string) => void
```

---

## Next Steps

1. **Read the actual code:** Start with `AIChat.tsx` and follow the connections
2. **Experiment:** Change colors, text, layouts - see what happens
3. **Add console.logs:** Track data flow through the application
4. **Build something:** Add a simple new feature end-to-end
5. **Use the docs:**
   - React: https://react.dev
   - FastAPI: https://fastapi.tiangolo.com
   - TypeScript: https://www.typescriptlang.org/docs

---

## Summary

**Backend = Python Functions** that:
- Receive requests (HTTP/WebSocket)
- Process data (fetch, calculate, analyze)
- Send responses (JSON)

**Frontend = React Components** that:
- Display UI (HTML + CSS)
- Manage state (data that changes)
- Handle events (clicks, inputs)
- Communicate with backend (fetch, WebSocket)

**Connection:**
```
User Action → Frontend Handler → Backend Endpoint → Service Logic
→ Backend Response → Frontend State Update → React Re-render → UI Update
```

**Key Insight:** The entire app is just data flowing through functions!

