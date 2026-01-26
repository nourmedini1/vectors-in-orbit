import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

export const StoreContext = createContext();

const API_URL = "http://localhost:8000";

const getUserId = () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  return user._id || null;
};

export const StoreProvider = ({ children }) => {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [wishes, setWishes] = useState([]); 
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    fetchProducts();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.user_type) {
      // Map customer to shopper for frontend
      setUserRole(user.user_type === 'customer' ? 'shopper' : user.user_type);
      if (user._id) {
        fetchCart(user._id);
      }
    }
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/products`);
      setProducts(res.data);
    } catch (err) { console.error("API Error", err); }
  };

  const fetchCart = async (userId) => {
    try {
      const res = await axios.get(`${API_URL}/api/cart/${userId}`);
      setCart(res.data.items || []);
    } catch (err) { 
      console.error("Cart fetch error", err);
      setCart([]);
    }
  };



  const addToCart = async (product) => {
    const userId = getUserId();
    if (!userId) {
      alert('Please login to add items to cart');
      return;
    }

    try {
      await axios.post(`${API_URL}/api/cart/add`, {
        user_id: userId,
        product_id: product._id || product.product_id,
        quantity: 1
      });
      await fetchCart(userId);
      console.log('✅ Added to cart');
    } catch (err) {
      console.error('Add to cart error:', err);
      alert('Failed to add item to cart');
    }
  };

  const removeFromCart = async (index, product) => {
    const userId = getUserId();
    if (!userId) return;

    try {
      await axios.post(`${API_URL}/api/cart/remove`, {
        user_id: userId,
        product_id: product.product_id || product._id
      });
      await fetchCart(userId);
      console.log('✅ Removed from cart');
    } catch (err) {
      console.error('Remove from cart error:', err);
      // Fallback to local removal
      const newCart = [...cart];
      newCart.splice(index, 1);
      setCart(newCart);
    }
  };

  // NEW: Create a Wish Intent
  const createWish = (wishData) => {
    const newWish = { id: Date.now(), ...wishData };
    setWishes([newWish, ...wishes]);
    
    // Track wishlist event (non-blocking)
    const userId = getUserId();
    if (userId) {
      const params = new URLSearchParams({
        user_id: userId,
        product_id: wishData.productId || 'custom',
        timestamp: new Date().toISOString(),
        session_id: `session_${userId}`
      });
      fetch(`${API_URL}/events/wishlist-add?${params}`, { method: 'POST' })
        .catch(err => console.log('Event tracking failed:', err));
    }
  };

  return (
    <StoreContext.Provider value={{ 
      products, cart, wishes, userRole, 
      setWishes, setUserRole, addToCart, removeFromCart, createWish,
      fetchProducts, API_URL 
    }}>
      {children}
    </StoreContext.Provider>
  );
};