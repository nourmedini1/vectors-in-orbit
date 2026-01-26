import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, ShoppingCart, Package, Star, Truck } from 'lucide-react';
import { Navbar } from '../../components/Navbar';
import { useCart } from '../../context/CartContext';

const ProductDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { addToCart } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [addedToCart, setAddedToCart] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewData, setReviewData] = useState({ rating: 5, comment: '' });

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://localhost:8000';

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/products/${id}`);
      if (!response.ok) throw new Error('Product not found');
      const data = await response.json();
      setProduct(data);
      
      // Track product view event (non-blocking)
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (user._id) {
        // Get source from navigation state, default to 'direct' if not provided
        const source = location.state?.source || 'direct';
        const params = new URLSearchParams({
          product_id: id,
          user_id: user._id,
          source: source,
          timestamp: new Date().toISOString(),
          session_id: `session_${user._id}`
        });
        fetch(`http://localhost:8000/events/product-view?${params}`)
          .catch(err => console.log('Event tracking failed:', err));
      }
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async () => {
    try {
      await addToCart(product._id, quantity);
      setAddedToCart(true);
      setTimeout(() => setAddedToCart(false), 2000);
    } catch (error) {
      alert(error.message);
    }
  };

  const handleReviewSubmit = (e) => {
    e.preventDefault();
    
    if (!user._id) {
      alert('Please login to submit a review');
      return;
    }

    const params = new URLSearchParams({
      product_id: product._id,
      user_id: user._id,
      rating: reviewData.rating.toString(),
      timestamp: new Date().toISOString(),
      session_id: `session_${user._id}`
    });

    if (reviewData.comment) {
      params.append('comment', reviewData.comment);
    }

    // Track review event (non-blocking)
    fetch(`${API_URL}/events/review-submit?${params}`)
      .then(() => {
        alert('Review submitted successfully!');
        setShowReviewForm(false);
        setReviewData({ rating: 5, comment: '' });
      })
      .catch(err => {
        console.log('Event tracking failed:', err);
        alert('Failed to submit review');
      });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-6 py-20 text-center">
          <Package className="mx-auto h-16 w-16 text-gray-400 mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Product Not Found</h2>
          <button
            onClick={() => navigate('/shop')}
            className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700"
          >
            <ArrowLeft className="mr-2" size={20} />
            Back to Shop
          </button>
        </div>
      </div>
    );
  }

  const imageUrl = product.image_url && product.image_url !== 'nan' && product.image_url !== '' 
    ? product.image_url 
    : 'https://placehold.co/600x600/e2e8f0/64748b?text=No+Image+Available';

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Back Button */}
        <button
          onClick={() => navigate('/shop')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="mr-2" size={20} />
          Back to Shop
        </button>

        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 p-8">
            {/* Product Image */}
            <div className="relative flex items-center justify-center bg-gray-50 rounded-lg p-8">
              <img
                src={imageUrl}
                alt={product.name}
                className="max-w-full max-h-96 object-contain"
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = 'https://placehold.co/600x600/e2e8f0/64748b?text=Image+Not+Available';
                }}
              />
              {product.has_discount && product.discount_amount && (
                <div className="absolute top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg text-lg font-bold shadow-lg">
                  SAVE {product.discount_amount.toFixed(3)} DT
                </div>
              )}
            </div>

            {/* Product Info */}
            <div className="flex flex-col">
              {/* Category & Brand */}
              <div className="flex items-center gap-3 mb-4">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-semibold rounded-full">
                  {product.category}
                </span>
                {product.brand && (
                  <span className="px-3 py-1 bg-gray-100 text-gray-700 text-sm font-medium rounded-full">
                    {product.brand}
                  </span>
                )}
              </div>

              {/* Product Name */}
              <h1 className="text-3xl font-bold text-gray-900 mb-4">
                {product.name}
              </h1>

              {/* Price */}
              <div className="mb-6">
                {product.has_discount ? (
                  <div>
                    <div className="flex items-baseline gap-3 mb-2">
                      <span className="text-4xl font-bold text-emerald-600">
                        {product.price.toFixed(3)} DT
                      </span>
                      <span className="text-2xl text-gray-400 line-through">
                        {product.original_price.toFixed(3)} DT
                      </span>
                    </div>
                    <div className="inline-block px-3 py-1 bg-red-100 text-red-700 text-sm font-bold rounded-full">
                      You save {(product.original_price - product.price).toFixed(3)} DT!
                    </div>
                  </div>
                ) : (
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold text-gray-900">
                      {product.price.toFixed(3)} DT
                    </span>
                  </div>
                )}
              </div>

              {/* Stock Status */}
              <div className="mb-6">
                {product.stock > 0 ? (
                  <div className="flex items-center text-green-600">
                    <Package className="mr-2" size={20} />
                    <span className="font-medium">In Stock ({product.stock} available)</span>
                  </div>
                ) : (
                  <div className="flex items-center text-red-600">
                    <Package className="mr-2" size={20} />
                    <span className="font-medium">Out of Stock</span>
                  </div>
                )}
              </div>

              {/* Description */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
                <p className="text-gray-600 leading-relaxed">
                  {product.description || 'No description available.'}
                </p>
              </div>

              {/* Quantity Selector */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    -
                  </button>
                  <span className="px-6 py-2 border border-gray-300 rounded-md font-medium">
                    {quantity}
                  </span>
                  <button
                    onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}
                    className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                    disabled={quantity >= product.stock}
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Add to Cart Button */}
              <button
                onClick={handleAddToCart}
                disabled={product.stock === 0 || addedToCart}
                className={`w-full py-4 rounded-lg font-semibold text-white flex items-center justify-center gap-2 transition-colors ${
                  addedToCart
                    ? 'bg-green-600 hover:bg-green-700'
                    : product.stock === 0
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <ShoppingCart size={20} />
                {addedToCart ? 'Added to Cart!' : product.stock === 0 ? 'Out of Stock' : 'Add to Cart'}
              </button>

              {/* Additional Info */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center text-gray-600 mb-3">
                  <Truck className="mr-3" size={20} />
                  <span>Free shipping on orders over $50</span>
                </div>
                <div className="flex items-center text-gray-600">
                  <Star className="mr-3" size={20} />
                  <span>Sold by {product.vendor.toUpperCase()}</span>
                </div>
              </div>

              {/* Review Section */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                {!showReviewForm ? (
                  <button
                    onClick={() => setShowReviewForm(true)}
                    className="w-full py-3 border-2 border-blue-600 text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
                  >
                    Write a Review
                  </button>
                ) : (
                  <form onSubmit={handleReviewSubmit} className="space-y-4">
                    <h3 className="text-lg font-bold text-gray-900">Write a Review</h3>
                    
                    {/* Rating */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Rating
                      </label>
                      <div className="flex gap-2">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => setReviewData({ ...reviewData, rating: star })}
                            className={`text-2xl ${
                              star <= reviewData.rating ? 'text-yellow-400' : 'text-gray-300'
                            }`}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Comment */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Comment (optional)
                      </label>
                      <textarea
                        value={reviewData.comment}
                        onChange={(e) => setReviewData({ ...reviewData, comment: e.target.value })}
                        rows="4"
                        placeholder="Share your thoughts about this product..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-3">
                      <button
                        type="submit"
                        className="flex-1 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700"
                      >
                        Submit Review
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowReviewForm(false);
                          setReviewData({ rating: 5, comment: '' });
                        }}
                        className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
