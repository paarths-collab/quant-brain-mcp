import { useState } from 'react';
import { 
  CreditCard, Plus, Send, Download, MoreHorizontal,
  ArrowUpRight, ArrowDownRight, Eye, EyeOff
} from 'lucide-react';
import './Payment.css';

const mockCards = [
  { id: 1, type: 'Mastercard', last4: '4532', balance: '$12,485.00', color: 'purple' },
  { id: 2, type: 'Visa', last4: '8821', balance: '$8,250.00', color: 'cyan' },
];

const mockTransactions = [
  { id: 1, name: 'Netflix', type: 'Subscription', amount: -15.99, date: 'Today' },
  { id: 2, name: 'Salary Deposit', type: 'Income', amount: 4500.00, date: 'Yesterday' },
  { id: 3, name: 'Amazon', type: 'Shopping', amount: -89.99, date: 'Jan 28' },
  { id: 4, name: 'Freelance Work', type: 'Income', amount: 850.00, date: 'Jan 27' },
];

function Payment() {
  const [showBalance, setShowBalance] = useState(true);

  return (
    <div className="payment-page">
      <h1 className="page-title">My Wallet</h1>

      <div className="payment-grid">
        {/* Cards Section */}
        <div className="cards-section">
          <div className="section-header">
            <h2>My Cards</h2>
            <button className="add-btn"><Plus size={16} /> Add Card</button>
          </div>
          <div className="cards-list">
            {mockCards.map((card) => (
              <div key={card.id} className={`credit-card ${card.color}`}>
                <div className="card-top">
                  <CreditCard size={24} />
                  <button className="card-menu"><MoreHorizontal size={18} /></button>
                </div>
                <div className="card-number">**** **** **** {card.last4}</div>
                <div className="card-bottom">
                  <div className="card-info">
                    <span className="card-label">Balance</span>
                    <span className="card-balance">{card.balance}</span>
                  </div>
                  <span className="card-type">{card.type}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="actions-section glass-card">
          <h2>Quick Actions</h2>
          <div className="actions-grid">
            <button className="quick-action">
              <div className="action-icon send"><Send size={20} /></div>
              <span>Send</span>
            </button>
            <button className="quick-action">
              <div className="action-icon receive"><Download size={20} /></div>
              <span>Receive</span>
            </button>
            <button className="quick-action">
              <div className="action-icon topup"><Plus size={20} /></div>
              <span>Top Up</span>
            </button>
          </div>
        </div>

        {/* Transactions */}
        <div className="transactions-section glass-card">
          <div className="section-header">
            <h2>Recent Transactions</h2>
            <button className="see-all">See All</button>
          </div>
          <div className="transactions-list">
            {mockTransactions.map((tx) => (
              <div key={tx.id} className="transaction-item">
                <div className={`tx-icon ${tx.amount > 0 ? 'income' : 'expense'}`}>
                  {tx.amount > 0 ? <ArrowDownRight size={18} /> : <ArrowUpRight size={18} />}
                </div>
                <div className="tx-info">
                  <span className="tx-name">{tx.name}</span>
                  <span className="tx-type">{tx.type}</span>
                </div>
                <div className="tx-right">
                  <span className={`tx-amount ${tx.amount > 0 ? 'positive' : 'negative'}`}>
                    {tx.amount > 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                  </span>
                  <span className="tx-date">{tx.date}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Balance Overview */}
        <div className="balance-overview glass-card">
          <div className="balance-top">
            <h2>Total Balance</h2>
            <button onClick={() => setShowBalance(!showBalance)}>
              {showBalance ? <Eye size={18} /> : <EyeOff size={18} />}
            </button>
          </div>
          <div className="total-balance">
            {showBalance ? '$20,735.00' : '••••••'}
          </div>
          <div className="balance-change positive">+12.5% from last month</div>
        </div>
      </div>
    </div>
  );
}

export default Payment;
