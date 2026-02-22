// Minimal test component to debug
import { useState } from 'react';

export default function AIChat() {
  const [test] = useState('Hello');
  
  return (
    <div className="h-screen flex items-center justify-center bg-zinc-900">
      <div className="text-white text-2xl">
        AI Chat Page Test - {test}
      </div>
    </div>
  );
}
