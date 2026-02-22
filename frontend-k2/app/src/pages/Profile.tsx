
import { useState, useEffect } from 'react';
import { Save, User, DollarSign, Target, Briefcase, TrendingUp } from 'lucide-react';
import { investorProfileAPI } from '../api';

export default function Profile() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const [formData, setFormData] = useState({
        user_id: 'default',
        name: '',
        age: '',
        monthly_income: '',
        monthly_savings: '',
        risk_tolerance: 'moderate',
        horizon_years: '5',
        primary_goal: '',
        existing_investments: '',
        market: 'US',
    });

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        try {
            const { data } = await investorProfileAPI.load();
            if (data.status === 'ok' && data.profile) {
                setFormData((prev) => ({
                    ...prev,
                    ...data.profile,
                    // Ensure numbers are converted to strings for inputs
                    age: data.profile.age?.toString() || '',
                    monthly_income: data.profile.monthly_income?.toString() || '',
                    monthly_savings: data.profile.monthly_savings?.toString() || '',
                    horizon_years: data.profile.horizon_years?.toString() || '5',
                }));
            }
        } catch (error) {
            console.error('Failed to load profile', error);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            // Convert strings back to numbers
            const payload = {
                ...formData,
                age: formData.age ? parseInt(formData.age) : null,
                monthly_income: formData.monthly_income ? parseFloat(formData.monthly_income) : null,
                monthly_savings: formData.monthly_savings ? parseFloat(formData.monthly_savings) : null,
                horizon_years: formData.horizon_years ? parseInt(formData.horizon_years) : 5,
            };

            await investorProfileAPI.save(payload);
            setMessage({ type: 'success', text: 'Profile saved successfully!' });

            // Clear success message after 3s
            setTimeout(() => setMessage(null), 3000);
        } catch (error) {
            console.error('Failed to save profile', error);
            setMessage({ type: 'error', text: 'Failed to save profile. Please try again.' });
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-black text-white flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-t-2 border-orange-500 rounded-full"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-black text-slate-200 p-8 font-manrope">
            <div className="max-w-2xl mx-auto">
                <header className="mb-10 pb-6 border-b border-white/10">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-orange-500/10 rounded-lg">
                            <User className="text-orange-500" size={24} />
                        </div>
                        <h1 className="text-3xl font-bold text-white font-fraunces">Investor Profile</h1>
                    </div>
                    <p className="text-white/60">
                        Tell us about your financial goals and risk appetite. This information powers the
                        AI recommendations in your dashboard.
                    </p>
                </header>

                <form onSubmit={handleSubmit} className="space-y-8">
                    {/* Personal Details */}
                    <section className="space-y-4">
                        <h2 className="text-lg font-semibold text-white/90 flex items-center gap-2">
                            <Briefcase size={18} className="text-orange-500" /> Personal Details
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Full Name</label>
                                <input
                                    type="text"
                                    name="name"
                                    value={formData.name}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="Enter your name"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Age</label>
                                <input
                                    type="number"
                                    name="age"
                                    value={formData.age}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="e.g. 30"
                                />
                            </div>
                        </div>
                    </section>

                    {/* Financials */}
                    <section className="space-y-4">
                        <h2 className="text-lg font-semibold text-white/90 flex items-center gap-2">
                            <DollarSign size={18} className="text-green-500" /> Financials
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Monthly Income ($)</label>
                                <input
                                    type="number"
                                    name="monthly_income"
                                    value={formData.monthly_income}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="e.g. 5000"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Monthly Savings ($)</label>
                                <input
                                    type="number"
                                    name="monthly_savings"
                                    value={formData.monthly_savings}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="e.g. 1000"
                                />
                            </div>
                        </div>
                    </section>

                    {/* Goals & Risk */}
                    <section className="space-y-4">
                        <h2 className="text-lg font-semibold text-white/90 flex items-center gap-2">
                            <Target size={18} className="text-blue-500" /> Goals & Risk
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Risk Tolerance</label>
                                <select
                                    name="risk_tolerance"
                                    value={formData.risk_tolerance}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all text-white/90"
                                >
                                    <option value="low">Low (Conservative)</option>
                                    <option value="moderate">Moderate (Balanced)</option>
                                    <option value="high">High (Aggressive)</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Time Horizon (Years)</label>
                                <input
                                    type="number"
                                    name="horizon_years"
                                    value={formData.horizon_years}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="e.g. 10"
                                />
                            </div>
                            <div className="md:col-span-2 space-y-1">
                                <label className="text-xs uppercase tracking-wider text-white/50">Primary Goal</label>
                                <input
                                    type="text"
                                    name="primary_goal"
                                    value={formData.primary_goal}
                                    onChange={handleChange}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all"
                                    placeholder="e.g. Retirement, Buying a House, Wealth Growth"
                                />
                            </div>
                        </div>
                    </section>

                    {/* Existing Investments */}
                    <section className="space-y-4">
                        <h2 className="text-lg font-semibold text-white/90 flex items-center gap-2">
                            <TrendingUp size={18} className="text-purple-500" /> Existing Portfolio
                        </h2>
                        <div className="space-y-1">
                            <label className="text-xs uppercase tracking-wider text-white/50">Current Holdings (Optional)</label>
                            <textarea
                                name="existing_investments"
                                value={formData.existing_investments}
                                onChange={handleChange}
                                rows={3}
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all resize-none"
                                placeholder="e.g. $10k in AAPL, $5k in SPY..."
                            />
                        </div>
                    </section>

                    {/* Market Preference */}
                    <section className="space-y-4">
                        <div className="space-y-1">
                            <label className="text-xs uppercase tracking-wider text-white/50">Preferred Market</label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="market"
                                        value="US"
                                        checked={formData.market === 'US'}
                                        onChange={handleChange}
                                        className="accent-orange-500"
                                    />
                                    <span>United States (US)</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="market"
                                        value="IN"
                                        checked={formData.market === 'IN'}
                                        onChange={handleChange}
                                        className="accent-orange-500"
                                    />
                                    <span>India (IN)</span>
                                </label>
                            </div>
                        </div>
                    </section>

                    <footer className="pt-6 border-t border-white/10 flex items-center justify-between">
                        {message && (
                            <div className={`text-sm ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                                {message.text}
                            </div>
                        )}
                        {!message && <div></div>} {/* Spacer */}

                        <button
                            type="submit"
                            disabled={saving}
                            className="bg-orange-600 hover:bg-orange-500 text-white px-8 py-3 rounded-full font-semibold transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {saving ? (
                                <>Saving...</>
                            ) : (
                                <>
                                    <Save size={18} /> Save Profile
                                </>
                            )}
                        </button>
                    </footer>
                </form>
            </div>
        </div>
    );
}
