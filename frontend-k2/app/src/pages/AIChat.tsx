import { Card } from '@/components/ui/card';
import { MessageSquare } from 'lucide-react';

export default function AIChat() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">AI Chat</h1>
        <p className="text-white/60 mt-1">Chat with AI about stocks and investments</p>
      </div>

      <Card className="bg-white/5 border-white/10 p-12 text-center">
        <MessageSquare className="w-16 h-16 mx-auto mb-4 text-purple" />
        <h2 className="text-xl font-semibold text-white mb-2">AI Chat Coming Soon</h2>
        <p className="text-white/60 max-w-md mx-auto">
          Have intelligent conversations about your investment strategy.
        </p>
      </Card>
    </div>
  );
}
