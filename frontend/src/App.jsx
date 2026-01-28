import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { StoreProvider } from './context/StoreContext';
import { CartProvider } from './context/CartContext';
import { OrderProvider } from './context/OrderContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import ShopHome from './pages/shop/ShopHome';
import ProductDetail from './pages/shop/ProductDetail';
import Cart from './pages/shop/Cart';
import CartPage from './pages/shop/CartPage';
import CheckoutPage from './pages/shop/CheckoutPage';
import OrdersPage from './pages/shop/OrdersPage';
import PurchaseHistory from './pages/shop/PurchaseHistory';
import SmartWishlist from './pages/shop/SmartWishlist';
import VendorDashboard from './pages/vendor/VendorDashboard';

function App() {
  return (
    <StoreProvider>
      <CartProvider>
        <OrderProvider>
          <Router>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/shop" element={<ShopHome />} />
              <Route path="/product/:id" element={<ProductDetail />} />
              <Route path="/wishlist" element={<SmartWishlist />} /> 
              <Route path="/cart" element={<Cart />} />
              <Route path="/cart-new" element={<CartPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/purchases" element={<PurchaseHistory />} />
              <Route path="/vendor" element={<VendorDashboard />} />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Router>
        </OrderProvider>
      </CartProvider>
    </StoreProvider>
  );
}

export default App;