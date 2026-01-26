import React, { useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Plus, Clock, DollarSign, Image as ImageIcon, X } from 'lucide-react';
import { StoreContext } from '../../context/StoreContext';
import { Navbar } from '../../components/Navbar';
import { Button } from '../../components/ui/Button';

const SmartWishlist = () => {
  const { wishes, createWish } = useContext(StoreContext);
  const [isFormOpen, setIsFormOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    description: '',
    minBudget: '',
    maxBudget: '',
    urgency: '7',
    imageUrl: '',
    notes: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    createWish(formData);
    setIsFormOpen(false);
    setFormData({ description: '', minBudget: '', maxBudget: '', urgency: '7', imageUrl: '', notes: '' });
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <Navbar />

      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2 flex items-center gap-2">
              <Sparkles className="text-emerald-500" /> AI Request Center
            </h1>
            <p className="text-slate-500 max-w-2xl">
              Don't browse endlessly. Tell our AI Agent exactly what you want, your budget, and timeline. 
              We'll scan the market and notify you when we find the perfect match.
            </p>
          </div>
          <Button onClick={() => setIsFormOpen(true)} className="shrink-0">
            <Plus size={18} /> Create New Request
          </Button>
        </div>

        {/* Active Wishes Grid */}
        {wishes.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-16 text-center">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
              <Sparkles size={24} />
            </div>
            <h3 className="text-lg font-bold text-slate-900">No active requests</h3>
            <p className="text-slate-500 mb-6">Start by telling the AI what you are looking for.</p>
            <Button variant="secondary" onClick={() => setIsFormOpen(true)}>Create Request</Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {wishes.map((wish) => (
                <WishCard key={wish.id} wish={wish} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Modal Form */}
      <AnimatePresence>
        {isFormOpen && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsFormOpen(false)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" 
            />
            <motion.div 
              initial={{ scale: 0.95, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-white w-full max-w-lg rounded-2xl shadow-2xl relative z-10 overflow-hidden"
            >
              <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                <h3 className="text-lg font-bold text-slate-900">New Purchase Request</h3>
                <button onClick={() => setIsFormOpen(false)} className="text-slate-400 hover:text-slate-700"><X size={20}/></button>
              </div>
              
              <form onSubmit={handleSubmit} className="p-6 space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">What are you looking for?</label>
                  <input 
                    required
                    placeholder="e.g. Red Gaming Laptop with RTX 4060"
                    className="w-full px-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 outline-none transition-all"
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Min Budget (TND)</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-3 text-slate-400" />
                      <input 
                        type="number" required placeholder="1000"
                        className="w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 outline-none"
                        value={formData.minBudget}
                        onChange={e => setFormData({...formData, minBudget: e.target.value})}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Max Budget (TND)</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-3 text-slate-400" />
                      <input 
                        type="number" required placeholder="3000"
                        className="w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 outline-none"
                        value={formData.maxBudget}
                        onChange={e => setFormData({...formData, maxBudget: e.target.value})}
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Urgency (Days)</label>
                    <div className="relative">
                      <Clock size={14} className="absolute left-3 top-3 text-slate-400" />
                      <select 
                        className="w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 outline-none bg-white"
                        value={formData.urgency}
                        onChange={e => setFormData({...formData, urgency: e.target.value})}
                      >
                        <option value="1">ASAP (1 Day)</option>
                        <option value="3">This Week (3 Days)</option>
                        <option value="7">Standard (7 Days)</option>
                        <option value="30">Browsing (30 Days)</option>
                      </select>
                    </div>
                  </div>
                  <div>
                     <label className="block text-sm font-semibold text-slate-700 mb-1">Reference Image URL</label>
                     <div className="relative">
                      <ImageIcon size={14} className="absolute left-3 top-3 text-slate-400" />
                      <input 
                        placeholder="https://..."
                        className="w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 outline-none"
                        value={formData.imageUrl}
                        onChange={e => setFormData({...formData, imageUrl: e.target.value})}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Additional Notes</label>
                  <textarea 
                    placeholder="Specific brands, colors, or features to avoid..."
                    className="w-full px-4 py-2.5 rounded-lg border border-slate-200 focus:border-emerald-500 outline-none h-24 resize-none"
                    value={formData.notes}
                    onChange={e => setFormData({...formData, notes: e.target.value})}
                  />
                </div>

                <div className="pt-2">
                  <Button className="w-full justify-center">Submit Request to Agent</Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

const WishCard = ({ wish }) => (
  <motion.div 
    layout
    initial={{ opacity: 0, scale: 0.9 }} 
    animate={{ opacity: 1, scale: 1 }}
    className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow"
  >
    <div className="p-5">
      <div className="flex justify-between items-start mb-4">
        <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2 py-1 rounded-full border border-emerald-200">
          Active Request
        </span>
        <span className="text-xs text-slate-400 font-mono">ID: {wish.id.toString().slice(-4)}</span>
      </div>

      <div className="flex gap-4">
        {wish.imageUrl ? (
          <img src={wish.imageUrl} alt="Ref" className="w-16 h-16 rounded-lg object-cover bg-slate-100 border border-slate-100" />
        ) : (
          <div className="w-16 h-16 rounded-lg bg-slate-50 flex items-center justify-center text-slate-300 border border-slate-100">
            <Sparkles size={20} />
          </div>
        )}
        <div>
          <h4 className="font-bold text-slate-900 leading-tight mb-1">{wish.description}</h4>
          <div className="text-sm text-slate-500 flex items-center gap-2">
            <Clock size={12} /> Ends in {wish.urgency} days
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-center">
        <div className="text-sm">
          <span className="text-slate-400">Budget: </span>
          <span className="font-semibold text-slate-700">{wish.minBudget} - {wish.maxBudget} TND</span>
        </div>
        <button className="text-xs font-medium text-red-500 hover:text-red-600">Cancel</button>
      </div>
    </div>
  </motion.div>
);

export default SmartWishlist;