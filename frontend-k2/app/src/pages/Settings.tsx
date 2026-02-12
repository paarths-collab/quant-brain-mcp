import { Card } from '@/components/ui/card';
import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">Settings</h1>
        <p className="text-white/60 mt-1">Configure your preferences</p>
      </div>

      <Card className="bg-white/5 border-white/10 p-12 text-center">
        <SettingsIcon className="w-16 h-16 mx-auto mb-4 text-purple" />
        <h2 className="text-xl font-semibold text-white mb-2">Settings Coming Soon</h2>
        <p className="text-white/60 max-w-md mx-auto">
          Customize your trading platform experience.
        </p>
      </Card>
    </div>
  );
}
