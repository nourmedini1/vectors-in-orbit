import React, { useContext } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { ShoppingBag, Search, Sparkles } from 'lucide-react';
import { StoreContext } from '../context/StoreContext';
import { motion } from 'framer-motion';
import { Button } from './ui/Button';

export const Navbar = ({ variant = 'authenticated' }) => {
  const { cart, userRole, setUserRole } = useContext(StoreContext);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    setUserRole(null);
    navigate('/');
  };

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      const offset = 80; // Account for fixed navbar
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  // Landing/Login variant - for unauthenticated users
  if (variant === 'landing') {
    return (
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center text-white font-bold">
              N
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">Nexus<span className="text-emerald-600">AI</span></span>
          </button>
          
          <div className="hidden md:flex items-center gap-8">
            <button onClick={() => navigate('/shop')} className="text-slate-600 hover:text-slate-900 transition-colors font-medium">
              Products
            </button>
            <button className="text-slate-600 hover:text-slate-900 transition-colors font-medium">
              Features
            </button>
            <button className="text-slate-600 hover:text-slate-900 transition-colors font-medium">
              About
            </button>
          </div>

          <div className="flex items-center gap-3">
            <Button 
              onClick={() => navigate('/login')} 
              variant="outline"
              className="!border-slate-300 !text-slate-700 hover:!bg-slate-50"
            >
              Sign In
            </Button>
            <Button 
              onClick={() => navigate('/login')} 
              variant="primary"
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>
    );
  }

  // Authenticated variant - for logged in users
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
        
        {/* Logo */}
        <Link to={userRole === 'vendor' ? '/vendor' : '/shop'} className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg shadow-emerald-200 transition-transform group-hover:rotate-3">N</div>
          <span className="text-xl font-bold tracking-tight text-slate-900">Nexus<span className="text-emerald-600">AI</span></span>
        </Link>

        {/* Center Nav (Shopper Only) */}
        {location.pathname === '/shop' && (
          <div className="hidden md:flex items-center gap-6">
            <button onClick={() => scrollToSection('hot-deals')} className="text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              Hot Deals
            </button>
            <button onClick={() => scrollToSection('new-arrivals')} className="text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              New Arrivals
            </button>
            <button onClick={() => scrollToSection('trending')} className="text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              Trending
            </button>
            <button onClick={() => scrollToSection('all-products')} className="text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              All Products
            </button>
            <NavLink to="/wishlist" active={location.pathname === '/wishlist'}>
              <span className="flex items-center gap-1"><Sparkles size={14} className="text-emerald-500" /> AI Requests</span>
            </NavLink>
          </div>
        )}
        
        {userRole === 'shopper' && location.pathname !== '/shop' && (
          <div className="hidden md:flex items-center gap-8">
            <NavLink to="/shop" active={location.pathname === '/shop'}>Discover</NavLink>
            <NavLink to="/wishlist" active={location.pathname === '/wishlist'}>
              <span className="flex items-center gap-1"><Sparkles size={14} className="text-emerald-500" /> AI Requests</span>
            </NavLink>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-4">
          {userRole === 'shopper' && (
            <>
              <div className="hidden lg:flex relative w-64">
                <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                <input 
                  type="text" 
                  placeholder="Search products..." 
                  className="w-full bg-slate-100 border-none rounded-full py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-emerald-500 transition-all"
                />
              </div>
              <Link to="/cart" className="relative p-2 hover:bg-slate-100 rounded-full transition-colors">
                <ShoppingBag size={20} className="text-slate-700" />
                {cart.length > 0 && (
                  <motion.span 
                    initial={{ scale: 0 }} animate={{ scale: 1 }}
                    className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center"
                  >
                    {cart.length}
                  </motion.span>
                )}
              </Link>
            </>
          )}
          
          <div className="h-6 w-px bg-slate-200 mx-2"></div>
          
          <button onClick={handleLogout} className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors">
            Log Out
          </button>
        </div>
      </div>
    </nav>
  );
};

const NavLink = ({ to, children, active }) => (
  <Link to={to} className={`text-sm font-medium transition-colors ${active ? 'text-emerald-600' : 'text-slate-500 hover:text-slate-900'}`}>
    {children}
  </Link>
);