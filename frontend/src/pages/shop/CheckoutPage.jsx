import { useState, useEffect, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { StoreContext } from '../../context/StoreContext';
import { useOrder } from '../../context/OrderContext';
import { ProgressSteps } from '../../components/checkout/ProgressSteps';
import { ShippingForm } from '../../components/checkout/ShippingForm';
import { PaymentForm } from '../../components/checkout/PaymentForm';
import { OrderConfirmation } from '../../components/checkout/OrderConfirmation';

const CheckoutPage = () => {
  const { cart, fetchCart } = useContext(StoreContext);
  const { createOrder } = useOrder();
  const navigate = useNavigate();
  const location = useLocation();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [items, setItems] = useState([]);

  const [shippingInfo, setShippingInfo] = useState({
    street: '',
    city: '',
    state: '',
    postal_code: '',
    country: ''
  });

  const [paymentMethod, setPaymentMethod] = useState('credit_card');

  // Handle cart validation and items from navigation state
  useEffect(() => {
    // Check if items passed via navigation state (for buy now feature)
    if (location.state?.items) {
      setItems(location.state.items);
    } else if (cart?.items?.length > 0) {
      setItems(cart.items);
    } else {
      // No items to checkout, redirect to cart
      navigate('/cart', { replace: true });
    }
  }, [cart, location.state, navigate]);

  const handleShippingSubmit = (e) => {
    e.preventDefault();
    setStep(2);
  };

  const handlePaymentSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const user = JSON.parse(localStorage.getItem('user'));
      
      // Create order payload
      // If items came from navigation state (Buy Now), include product_ids
      // If checking out full cart, don't include product_ids (buys all cart items)
      const orderPayload = {
        user_id: user._id,
        shipping_address: shippingInfo,
        payment_method: paymentMethod
      };

      // Only add product_ids if this is a "Buy Now" checkout (from navigation state)
      if (location.state?.items) {
        orderPayload.product_ids = items.map(item => item.product_id);
      }

      const orderResponse = await fetch('http://localhost:8000/api/orders/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderPayload)
      });

      if (!orderResponse.ok) {
        const errorData = await orderResponse.json();
        throw new Error(errorData.detail || 'Failed to create order');
      }

      const order = await orderResponse.json();
      
      // Then create purchase records for each item
      const purchasePromises = items.map(item => 
        fetch('http://localhost:8000/api/purchases', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: user._id,
            order_id: order._id,
            product_id: item.product_id,
            product_name: item.product_name || item.name,
            quantity: item.quantity || 1,
            price: item.price,
            discount_applied: 0,
            payment_method: paymentMethod,
            is_from_wishlist: item.is_from_wishlist || false,
            is_from_search: item.is_from_search || false
          })
        })
      );
      
      await Promise.all(purchasePromises);
      
      setOrderId(order._id);
      setStep(3);
      
      // Refetch cart from server to get updated state
      if (user._id) {
        await fetchCart(user._id);
      }
    } catch (error) {
      console.error('Payment error:', error);
      alert(error.message || 'Failed to process payment');
    } finally {
      setLoading(false);
    }
  };

  // Don't render checkout if no items
  if (items.length === 0) {
    return null;
  }

  // Calculate total for display
  const totalAmount = items.reduce((sum, item) => sum + (item.price * (item.quantity || 1)), 0);
  const cartData = { items, total_amount: totalAmount };

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <ProgressSteps currentStep={step} />

        {step === 1 && (
          <ShippingForm
            shippingInfo={shippingInfo}
            setShippingInfo={setShippingInfo}
            onSubmit={handleShippingSubmit}
            onBack={() => navigate('/cart')}
          />
        )}

        {step === 2 && (
          <PaymentForm
            paymentMethod={paymentMethod}
            setPaymentMethod={setPaymentMethod}
            cart={cartData}
            onSubmit={handlePaymentSubmit}
            onBack={() => setStep(1)}
            loading={loading}
          />
        )}

        {step === 3 && (
          <OrderConfirmation
            orderId={orderId}
            onViewPurchases={() => navigate('/purchases')}
            onContinueShopping={() => navigate('/shop')}
          />
        )}
      </div>
    </div>
  );
};

export default CheckoutPage;
