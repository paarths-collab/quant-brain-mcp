import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Twitter,
  Youtube,
  Linkedin,
  Instagram,
  Menu,
  X,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

// Navigation Component
const Navigation = () => {
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = ['HOW IT WORKS', 'ABOUT US'];

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
      isScrolled ? 'bg-black/80 backdrop-blur-md border-b border-white/5' : ''
    }`}>
      <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-12">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
              <span className="text-black font-display font-bold text-xl">B</span>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-8">
            {navItems.map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                className="text-white/70 hover:text-white text-xs tracking-wider transition-colors duration-300"
              >
                {item}
              </a>
            ))}
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="hidden sm:block text-white/70 hover:text-white text-sm transition-colors"
            >
              LOG IN
            </button>
            <Button 
              onClick={() => navigate('/dashboard')}
              className="hidden sm:flex bg-transparent border border-white/30 text-white hover:bg-white hover:text-black transition-all duration-300 rounded-full px-6"
            >
              GET STARTED
            </Button>
            
            {/* Mobile Menu Button */}
            <button
              className="lg:hidden text-white"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-black/95 backdrop-blur-md border-t border-white/10">
          <div className="px-4 py-6 space-y-4">
            {navItems.map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                className="block text-white/70 hover:text-white text-sm tracking-wider py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                {item}
              </a>
            ))}
            <div className="pt-4 border-t border-white/10 space-y-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="block text-white/70 hover:text-white text-sm w-full text-left"
              >
                LOG IN
              </button>
              <Button
                onClick={() => navigate('/dashboard')}
                className="w-full bg-white text-black hover:bg-white/90 rounded-full"
              >
                GET STARTED
              </Button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

// Hero Section
const HeroSection = () => {
  const candlesticks = [
    { src: '/images/candlestick-1.png', className: 'left-[8%] top-[15%] w-24 md:w-32 lg:w-40', delay: 0 },
    { src: '/images/candlestick-2.png', className: 'left-[18%] top-[35%] w-20 md:w-28 lg:w-36', delay: 0.5 },
    { src: '/images/candlestick-3.png', className: 'left-[28%] top-[10%] w-28 md:w-36 lg:w-44', delay: 1 },
    { src: '/images/candlestick-4.png', className: 'left-[40%] top-[25%] w-22 md:w-30 lg:w-38', delay: 1.5 },
    { src: '/images/candlestick-5.png', className: 'left-[52%] top-[12%] w-26 md:w-34 lg:w-42', delay: 0.3 },
    { src: '/images/candlestick-6.png', className: 'left-[62%] top-[30%] w-20 md:w-28 lg:w-36', delay: 0.8 },
    { src: '/images/candlestick-7.png', className: 'left-[72%] top-[18%] w-24 md:w-32 lg:w-40', delay: 1.2 },
  ];

  return (
    <section className="relative min-h-screen w-full bg-black overflow-hidden bg-grid">
      {/* Animated background gradient */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute inset-0" style={{
          background: 'radial-gradient(ellipse at 50% 50%, rgba(108, 99, 255, 0.15) 0%, transparent 50%)',
        }} />
      </div>

      {/* Floating Candlesticks */}
      <div className="absolute inset-0">
        {candlesticks.map((candle, index) => (
          <div
            key={index}
            className={`absolute ${candle.className}`}
            style={{
              animation: `float ${4 + (index % 7) * 0.28}s ease-in-out infinite`,
              animationDelay: `${candle.delay}s`,
            }}
          >
            <img
              src={candle.src}
              alt={`Candlestick ${index + 1}`}
              className="w-full h-full object-contain opacity-60 hover:opacity-100 transition-opacity"
              style={{
                filter: 'drop-shadow(0 0 20px rgba(108, 99, 255, 0.3))',
              }}
            />
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col justify-end pb-16 md:pb-24 px-6 md:px-12 lg:px-24">
        <div className="max-w-4xl">
          <h1 className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-tight tracking-tight">
            BREAKING BARRIERS
            <br />
            <span className="text-gradient">REDEFINING EQUITY</span>
            <br />
            AND F&O TRADING!
          </h1>
          <p className="text-white/60 text-lg mt-6 max-w-2xl">
            UNLOCK THE POTENTIAL OF MARKET SIMULATION, READY-MADE STRATEGIES, AND MUCH MORE WITH OUR NETWORK OF FINANCIAL SERVICES
          </p>
          <div className="mt-8 flex gap-4">
            <Button 
              onClick={() => window.location.href = '/dashboard'}
              className="bg-purple hover:bg-purple/90 text-white rounded-full px-8 py-6"
            >
              <Download className="mr-2" size={20} />
              Get Started
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
    </section>
  );
};


// Footer
const Footer = () => {
  return (
    <footer className="relative bg-black border-t border-white/10">
      <div className="w-full px-6 md:px-12 lg:px-24 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                <span className="text-black font-display font-bold text-xl">B</span>
              </div>
              <span className="font-display font-bold text-xl text-white">Bloomberg</span>
            </div>
            <p className="text-white/50 text-sm max-w-xs mb-6">
              Breaking barriers and redefining equity and F&O trading with cutting-edge technology.
            </p>
            <div className="flex gap-3">
              {[Twitter, Youtube, Linkedin, Instagram].map((Icon, index) => (
                <a
                  key={index}
                  href="#"
                  className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-white/50 hover:text-white hover:bg-white/10 transition-all"
                >
                  <Icon size={16} />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-white/40 text-sm">
            © 2026 Bloomberg. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};

// Main Landing Component
export default function Landing() {
  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      <Navigation />
      <main>
        <HeroSection />
      </main>
      <Footer />
    </div>
  );
}
