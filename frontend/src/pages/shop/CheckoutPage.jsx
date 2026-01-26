import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { useOrder } from '../../context/OrderContext';
import { CheckCircle, CreditCard, Truck } from 'lucide-react';

const CheckoutPage = () => {
  const { cart, clearCart } = useCart();
  const { createOrder } = useOrder();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState(null);

  const [shippingInfo, setShippingInfo] = useState({
    street: '',
    city: '',
    state: '',
    postal_code: '',
    country: ''
  });

  const [paymentMethod, setPaymentMethod] = useState('credit_card');

  const handleShippingSubmit = (e) => {
    e.preventDefault();
    setStep(2);
  };

  const handlePaymentSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const order = await createOrder(shippingInfo, paymentMethod);
      setOrderId(order._id);
      setStep(3);
    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!cart || cart.items.length === 0) {
    navigate('/cart');
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-center">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    step >= s
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  {s}
                </div>
                {s < 3 && (
                  <div
                    className={`w-24 h-1 mx-2 ${
                      step > s ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 px-12">
            <span className="text-sm">Shipping</span>
            <span className="text-sm">Payment</span>
            <span className="text-sm">Confirmation</span>
          </div>
        </div>

        {/* Step 1: Shipping Information */}
        {step === 1 && (
          <div className="bg-white rounded-lg shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Truck className="text-blue-600" size={24} />
              <h2 className="text-2xl font-bold">Shipping Information</h2>
            </div>

            <form onSubmit={handleShippingSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Street Address
                </label>
                <input
                  type="text"
                  required
                  value={shippingInfo.street}
                  onChange={(e) => setShippingInfo({ ...shippingInfo, street: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    required
                    value={shippingInfo.city}
                    onChange={(e) => setShippingInfo({ ...shippingInfo, city: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    State/Province
                  </label>
                  <input
                    type="text"
                    required
                    value={shippingInfo.state}
                    onChange={(e) => setShippingInfo({ ...shippingInfo, state: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    required
                    value={shippingInfo.postal_code}
                    onChange={(e) => setShippingInfo({ ...shippingInfo, postal_code: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    required
                    value={shippingInfo.country}
                    onChange={(e) => setShippingInfo({ ...shippingInfo, country: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => navigate('/cart')}
                  className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-md hover:bg-gray-200 font-medium"
                >
                  Back to Cart
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 font-medium"
                >
                  Continue to Payment
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Step 2: Payment */}
        {step === 2 && (
          <div className="bg-white rounded-lg shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <CreditCard className="text-blue-600" size={24} />
              <h2 className="text-2xl font-bold">Payment Method</h2>
            </div>

            <form onSubmit={handlePaymentSubmit} className="space-y-4">
              <div className="space-y-3">
                <label className="flex items-center p-4 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    name="payment"
                    value="credit_card"
                    checked={paymentMethod === 'credit_card'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">Credit Card</div>
                    <div className="text-sm text-gray-600">Pay with credit or debit card</div>
                  </div>
                </label>

                <label className="flex items-center p-4 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    name="payment"
                    value="paypal"
                    checked={paymentMethod === 'paypal'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">PayPal</div>
                    <div className="text-sm text-gray-600">Pay with your PayPal account</div>
                  </div>
                </label>

                <label className="flex items-center p-4 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    name="payment"
                    value="cash_on_delivery"
                    checked={paymentMethod === 'cash_on_delivery'}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">Cash on Delivery</div>
                    <div className="text-sm text-gray-600">Pay when you receive the order</div>
                  </div>
                </label>
              </div>

              {/* Order Summary */}
              <div className="border-t border-gray-200 pt-6 mt-6">
                <h3 className="font-semibold mb-4">Order Summary</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Subtotal</span>
                    <span>${cart.total_amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Shipping</span>
                    <span>Free</span>
                  </div>
                  <div className="border-t pt-2 flex justify-between font-bold text-base">
                    <span>Total</span>
                    <span>${cart.total_amount.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-md hover:bg-gray-200 font-medium"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 font-medium disabled:bg-gray-400"
                >
                  {loading ? 'Processing...' : 'Place Order'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Step 3: Confirmation */}
        {step === 3 && (
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
            <CheckCircle className="mx-auto text-green-600 mb-4" size={64} />
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Order Confirmed!</h2>
            <p className="text-gray-600 mb-6">
              Thank you for your purchase. Your order has been successfully placed.
            </p>
            
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <p className="text-sm text-gray-600 mb-1">Order Number</p>
              <p className="text-xl font-mono font-bold">{orderId}</p>
            </div>

            <p className="text-sm text-gray-600 mb-6">
              A confirmation email has been sent to your email address with order details.
            </p>

            <div className="flex gap-4 justify-center">
              <button
                onClick={() => navigate('/orders')}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
              >
                View Orders
              </button>
              <button
                onClick={() => navigate('/shop')}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 font-medium"
              >
                Continue Shopping
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CheckoutPage;
