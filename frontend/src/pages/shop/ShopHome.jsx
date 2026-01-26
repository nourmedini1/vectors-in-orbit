import React, { useContext, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingCart, ChevronLeft, ChevronRight, Tag, Package, Star, Search, X, Filter, DollarSign } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { StoreContext } from '../../context/StoreContext';
import { Navbar } from '../../components/Navbar';
import { Button } from '../../components/ui/Button';

const ProductCard = ({ product, source = 'all-products', position }) => {
  const { addToCart } = useContext(StoreContext);
  const navigate = useNavigate();

  // Handle image_url field and fallback for missing images
  const imageUrl = (product.image_url && product.image_url !== 'nan' && product.image_url !== '') 
    ? product.image_url 
    : (product.image || 'https://placehold.co/300x300/e2e8f0/64748b?text=No+Image');

  const handleProductClick = () => {
    // Track product click event (non-blocking)
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user._id) {
      const params = new URLSearchParams({
        product_id: product._id || product.product_id,
        user_id: user._id,
        source: source,
        timestamp: new Date().toISOString(),
        session_id: `session_${user._id}`
      });
      if (position !== undefined) params.append('position', position);
      
      fetch(`http://localhost:8000/events/product-click?${params}`)
        .catch(err => console.log('Event tracking failed:', err));
    }
    // Navigate with source info for ProductViewedEvent
    navigate(`/product/${product._id || product.product_id}`, { state: { source } });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      whileHover={{ y: -5 }}
      className="bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 flex flex-col h-full cursor-pointer"
      onClick={handleProductClick}
    >
      <div className="relative h-56 overflow-hidden rounded-t-xl bg-slate-50">
        <img 
          src={imageUrl} 
          alt={product.name} 
          className="w-full h-full object-cover mix-blend-multiply" 
          onError={(e) => {
            e.target.onerror = null;
            e.target.src = 'https://placehold.co/300x300/e2e8f0/64748b?text=No+Image';
          }}
        />
        {product.has_discount && product.discount_amount && (
          <div className="absolute top-3 right-3 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg">
            SAVE {product.discount_amount.toFixed(3)} DT
          </div>
        )}
      </div>
      
      <div className="p-5 flex-1 flex flex-col">
        <div className="text-xs font-bold text-emerald-600 uppercase tracking-wide mb-2">{product.category}</div>
        <h3 className="text-lg font-bold text-slate-900 mb-2 leading-tight">{product.name}</h3>
        <p className="text-slate-500 text-sm mb-4 line-clamp-2 flex-1">{product.description}</p>
        
        <div className="flex items-center justify-between pt-4 border-t border-slate-50 mt-auto">
          <div>
            <span className="text-xs text-slate-400 block">Price</span>
            {product.has_discount ? (
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-emerald-600">{product.price?.toFixed(3)} DT</span>
                <span className="text-sm text-slate-400 line-through">{product.original_price?.toFixed(3)} DT</span>
              </div>
            ) : (
              <span className="text-lg font-bold text-slate-900">{product.price?.toFixed(3)} DT</span>
            )}
          </div>
          <Button 
            onClick={(e) => {
              e.stopPropagation();
              addToCart(product);
            }} 
            variant="dark" 
            className="!px-4 !py-2"
          >
            <ShoppingCart size={16} /> Buy
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

const ShopHome = () => {
  const { products, addToCart } = useContext(StoreContext);
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearchQuery, setActiveSearchQuery] = useState(''); // Submitted search query
  const [selectedCategory, setSelectedCategory] = useState('');
  const [priceRange, setPriceRange] = useState({ min: '', max: '' });
  const [filteredProducts, setFilteredProducts] = useState(products);
  const [appliedFilters, setAppliedFilters] = useState({ category: '', priceMin: '', priceMax: '' }); // Track when filters are actually applied

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://localhost:8000';

  // Helper to get event metadata
  const getEventMetadata = () => ({
    timestamp: new Date().toISOString(),
    session_id: `session_${user._id || 'anonymous'}_${Date.now()}`
  });

  // Filter products based on search and filters
  useEffect(() => {
    let filtered = [...products];

    // Search filter - only use activeSearchQuery (submitted search)
    if (activeSearchQuery) {
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(activeSearchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(activeSearchQuery.toLowerCase())
      );
    }

    // Category filter
    if (selectedCategory) {
      filtered = filtered.filter(p => p.category === selectedCategory);
    }

    // Price filter
    if (priceRange.min) {
      filtered = filtered.filter(p => p.price >= parseFloat(priceRange.min));
    }
    if (priceRange.max) {
      filtered = filtered.filter(p => p.price <= parseFloat(priceRange.max));
    }

    setFilteredProducts(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  }, [products, activeSearchQuery, selectedCategory, priceRange]);

  const handleSearchSubmit = () => {
    // Set the active search query to trigger filtering
    setActiveSearchQuery(searchQuery);
    
    // Track search event (non-blocking) only when user submits
    if (searchQuery) {
      const params = new URLSearchParams({
        query: searchQuery,
        user_id: user._id || 'anonymous',
        timestamp: new Date().toISOString(),
        session_id: `session_${user._id || 'anonymous'}`
      });
      fetch(`${API_URL}/events/search?${params}`)
        .catch(err => console.log('Event tracking failed:', err));
    }
  };

  const handleFilterApply = () => {
    // Send filter event when filters are applied
    if (selectedCategory || priceRange.min || priceRange.max) {
      // Check if filters actually changed
      if (selectedCategory !== appliedFilters.category || 
          priceRange.min !== appliedFilters.priceMin || 
          priceRange.max !== appliedFilters.priceMax) {
        
        const params = new URLSearchParams({
          user_id: user._id || 'anonymous',
          timestamp: new Date().toISOString(),
          session_id: `session_${user._id || 'anonymous'}`
        });
        
        if (selectedCategory) params.append('category', selectedCategory);
        if (priceRange.min) params.append('price_min', priceRange.min);
        if (priceRange.max) params.append('price_max', priceRange.max);
        
        fetch(`${API_URL}/events/filter-apply?${params}`)
          .catch(err => console.log('Event tracking failed:', err));
        
        // Update applied filters
        setAppliedFilters({
          category: selectedCategory,
          priceMin: priceRange.min,
          priceMax: priceRange.max
        });
      }
    }
  };

  // Get featured products for carousel (products with discounts or first 5)
  const featuredProducts = products.filter(p => p.has_discount).slice(0, 5).length > 0
    ? products.filter(p => p.has_discount).slice(0, 5)
    : products.slice(0, 5);

  // Auto-advance carousel
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % featuredProducts.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [featuredProducts.length]);

  // Get different product categories
  const trendingProducts = filteredProducts.slice(0, 8);
  const discountedProducts = filteredProducts.filter(p => p.has_discount).slice(0, 4);
  const newArrivals = filteredProducts.slice(0, 4);

  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentProducts = filteredProducts.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredProducts.length / itemsPerPage);

  // Get unique categories
  const categories = [...new Set(products.map(p => p.category))].filter(Boolean);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    const element = document.getElementById('all-products');
    if (element) {
      const offset = 80;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % featuredProducts.length);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + featuredProducts.length) % featuredProducts.length);
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <Navbar />
      
      {/* Search and Filter Bar */}
      <div className="bg-white  pt-20">
        <div className="max-w-7xl mx-auto px-6 py-6">
          {/* Main Search Bar */}
          <div className="relative mb-4">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                <input
                  type="text"
                  placeholder="Search products..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSearchSubmit();
                    }
                  }}
                  className="w-full pl-12 pr-10 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>
              <button
                onClick={handleSearchSubmit}
                className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium"
              >
                Search
              </button>
            </div>
          </div>

          {/* Filters Row */}
          <div className="flex flex-wrap gap-3 items-center">
            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                // Auto-apply after a short delay to batch changes
                setTimeout(() => handleFilterApply(), 300);
              }}
              className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none bg-white"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>

            {/* Price Range */}
            <div className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg">
              <span className="text-sm text-slate-600">Price:</span>
              <input
                type="number"
                placeholder="Min"
                value={priceRange.min}
                onChange={(e) => setPriceRange({ ...priceRange, min: e.target.value })}
                onBlur={handleFilterApply}
                className="w-20 text-sm outline-none"
              />
              <span className="text-slate-400">-</span>
              <input
                type="number"
                placeholder="Max"
                value={priceRange.max}
                onChange={(e) => setPriceRange({ ...priceRange, max: e.target.value })}
                onBlur={handleFilterApply}
                className="w-20 text-sm outline-none"
              />
              <span className="text-sm text-slate-600">DT</span>
            </div>

            {/* Apply Filters Button - Remove it since filters auto-apply now */}

            {/* Results Count */}
            <div className="ml-auto">
              <span className="text-sm text-slate-600">
                {filteredProducts.length} products
              </span>
            </div>
          </div>
          
          {/* Active Filters Display */}
          {(activeSearchQuery || selectedCategory || priceRange.min || priceRange.max) && (
            <div className="mt-3 flex gap-2 flex-wrap items-center">
              {activeSearchQuery && (
                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-md text-sm flex items-center gap-2">
                  {activeSearchQuery}
                  <button onClick={() => { setActiveSearchQuery(''); setSearchQuery(''); }} className="hover:text-slate-900">
                    <X size={14} />
                  </button>
                </span>
              )}
              {selectedCategory && (
                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-md text-sm flex items-center gap-2">
                  {selectedCategory}
                  <button onClick={() => setSelectedCategory('')} className="hover:text-slate-900">
                    <X size={14} />
                  </button>
                </span>
              )}
              {(priceRange.min || priceRange.max) && (
                <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-md text-sm flex items-center gap-2">
                  {priceRange.min || '0'} - {priceRange.max || '∞'} DT
                  <button onClick={() => setPriceRange({ min: '', max: '' })} className="hover:text-slate-900">
                    <X size={14} />
                  </button>
                </span>
              )}
              <button
                onClick={() => {
                  setSearchQuery('');
                  setActiveSearchQuery('');
                  setSelectedCategory('');
                  setPriceRange({ min: '', max: '' });
                }}
                className="px-3 py-1 text-sm text-slate-600 hover:text-slate-900 underline"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Check if any filter is active */}
      {!(activeSearchQuery || selectedCategory || priceRange.min || priceRange.max) && (
        <>
          {/* Hero Carousel */}
          <div className="bg-gradient-to-br from-emerald-50 to-teal-50">
            <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="relative rounded-2xl overflow-hidden bg-white shadow-2xl">
            <AnimatePresence mode="wait">
              {featuredProducts.map((product, index) => {
                if (index !== currentSlide) return null;
                
                const imageUrl = (product.image_url && product.image_url !== 'nan' && product.image_url !== '') 
                  ? product.image_url 
                  : (product.image || 'https://placehold.co/600x600/e2e8f0/64748b?text=No+Image');

                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.5 }}
                    className="grid md:grid-cols-2 gap-6 items-center p-6 md:p-10 min-h-[350px] md:min-h-[400px]"
                  >
                    {/* Left - Product Info */}
                    <div className="space-y-3 ms-10 md:space-y-4 flex flex-col justify-center">
                      <div className="inline-block">
                        <span className="px-3 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">
                          Featured Product
                        </span>
                      </div>
                      <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold text-slate-900 leading-tight">
                        {product.name}
                      </h1>
                      <p className="text-sm md:text-base text-slate-600 leading-relaxed line-clamp-2">
                        {product.description}
                      </p>
                      <div className="flex items-center gap-3">
                        {product.has_discount ? (
                          <div className="flex items-baseline gap-2">
                            <span className="text-2xl md:text-3xl font-bold text-emerald-600">{product.price?.toFixed(3)} DT</span>
                            <span className="text-base md:text-lg text-slate-400 line-through">{product.original_price?.toFixed(3)} DT</span>
                          </div>
                        ) : (
                          <span className="text-2xl md:text-3xl font-bold text-slate-900">{product.price?.toFixed(3)} DT</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 md:gap-3 flex-wrap">
                        <Button 
                          onClick={() => {
                            const user = JSON.parse(localStorage.getItem('user') || '{}');
                            if (user._id) {
                              const params = new URLSearchParams({
                                product_id: product._id || product.product_id,
                                user_id: user._id,
                                source: 'carousel',
                                position: index.toString(),
                                timestamp: new Date().toISOString(),
                                session_id: `session_${user._id}`
                              });
                              fetch(`http://localhost:8000/events/product-click?${params}`)
                                .catch(err => console.log('Event tracking failed:', err));
                            }
                            navigate(`/product/${product._id || product.product_id}`, { state: { source: 'carousel' } });
                          }}
                          variant="primary"
                          className="!px-4 md:!px-6 !py-2 md:!py-2.5 !text-sm md:!text-base"
                        >
                          View Details
                        </Button>
                        <Button 
                          onClick={(e) => {
                            e.stopPropagation();
                            addToCart(product);
                          }}
                          variant="outline"
                          className="!px-4 md:!px-6 !py-2 md:!py-2.5 !text-sm md:!text-base"
                        >
                          <ShoppingCart size={16} /> Add to Cart
                        </Button>
                      </div>
                    </div>

                    {/* Right - Product Image */}
                    <div className="relative flex items-center justify-center p-4 md:p-8">
                      <div className="absolute inset-0 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-2xl opacity-20"></div>
                      <div className="relative">
                        <img 
                          src={imageUrl}
                          alt={product.name}
                          className="relative z-10 w-full max-w-xs h-auto max-h-[200px] md:max-h-[280px] object-contain drop-shadow-2xl"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = 'https://placehold.co/600x600/e2e8f0/64748b?text=No+Image';
                          }}
                        />
                        {product.has_discount && product.discount_amount && (
                          <div className="absolute -top-2 -right-2 md:top-0 md:right-0 bg-red-500 text-white px-3 py-1.5 md:px-4 md:py-2 rounded-xl text-xs md:text-sm font-bold shadow-xl z-20">
                            SAVE {product.discount_amount.toFixed(3)} DT
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {/* Carousel Controls */}
            <button
              onClick={prevSlide}
              className="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 z-30 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white p-2.5 rounded-full shadow-xl transition-all hover:scale-110"
            >
              <ChevronLeft size={20} strokeWidth={3} />
            </button>
            <button
              onClick={nextSlide}
              className="absolute right-2 md:right-4 top-1/2 -translate-y-1/2 z-30 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white p-2.5 rounded-full shadow-xl transition-all hover:scale-110"
            >
              <ChevronRight size={20} strokeWidth={3} />
            </button>

            {/* Carousel Indicators */}
            <div className="absolute bottom-3 md:bottom-4 left-1/2 -translate-x-1/2 flex gap-2 z-20">
              {featuredProducts.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentSlide(index)}
                  className={`h-1.5 rounded-full transition-all ${
                    index === currentSlide ? 'w-6 bg-emerald-600' : 'w-1.5 bg-slate-300'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Hot Deals Section */}
      {discountedProducts.length > 0 && (
        <div id="hot-deals" className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex items-center gap-3 mb-8">
            <Tag className="text-red-500" size={32} />
            <div>
              <h2 className="text-3xl font-bold text-slate-900">Hot Deals</h2>
              <p className="text-slate-600 mt-1">Limited time offers you don't want to miss</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {discountedProducts.map((p, idx) => <ProductCard key={p._id || p.product_id || idx} product={p} source="hot-deals" position={idx} />)}
          </div>
        </div>
      )}

      {/* New Arrivals Section */}
      <div id="new-arrivals" className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center gap-3 mb-8">
            <Package className="text-emerald-600" size={32} />
            <div>
              <h2 className="text-3xl font-bold text-slate-900">New Arrivals</h2>
              <p className="text-slate-600 mt-1">Fresh products just added to our collection</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {newArrivals.map((p, idx) => <ProductCard key={p._id || p.product_id || idx} product={p} source="new-arrivals" position={idx} />)}
          </div>
        </div>
      </div>

      {/* Trending Now Section */}
      <div id="trending" className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex items-center gap-3 mb-8">
          <Star className="text-blue-600" size={32} />
          <div>
            <h2 className="text-3xl font-bold text-slate-900">Trending Now</h2>
            <p className="text-slate-600 mt-1">Most popular items loved by our customers</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {trendingProducts.map((p, idx) => <ProductCard key={p._id || p.product_id || idx} product={p} source="trending" position={idx} />)}
        </div>
      </div>
        </>
      )}

      {/* All Products Section - Always visible but shows filtered results when filters are active */}
      <div id="all-products" className="bg-slate-100 py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-slate-900">
                {(activeSearchQuery || selectedCategory || priceRange.min || priceRange.max) ? 'Search Results' : 'All Products'}
              </h2>
              <p className="text-slate-600 mt-1">Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredProducts.length)} of {filteredProducts.length} products</p>
            </div>
          </div>
          
          {currentProducts.length === 0 ? (
            <div className="text-center py-20">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-2xl font-bold text-slate-900 mb-2">No products found</h3>
              <p className="text-slate-600 mb-6">Try adjusting your search or filters</p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setActiveSearchQuery('');
                  setSelectedCategory('');
                  setPriceRange({ min: '', max: '' });
                }}
                className="px-6 py-3 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 transition-colors"
              >
                Clear All Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {currentProducts.map((p, idx) => (
                <ProductCard 
                  key={p._id || p.product_id || idx} 
                  product={p} 
                  source={(activeSearchQuery || selectedCategory || priceRange.min || priceRange.max) ? 'search-results' : 'all-products'}
                  position={indexOfFirstItem + idx}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-12">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-slate-200 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed bg-white"
              >
                <ChevronLeft size={20} />
              </button>

              {[...Array(totalPages)].map((_, index) => {
                const pageNumber = index + 1;
                if (
                  pageNumber === 1 ||
                  pageNumber === totalPages ||
                  (pageNumber >= currentPage - 1 && pageNumber <= currentPage + 1)
                ) {
                  return (
                    <button
                      key={pageNumber}
                      onClick={() => handlePageChange(pageNumber)}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        currentPage === pageNumber
                          ? 'bg-emerald-600 text-white'
                          : 'border border-slate-200 hover:bg-white text-slate-700 bg-white'
                      }`}
                    >
                      {pageNumber}
                    </button>
                  );
                } else if (
                  pageNumber === currentPage - 2 ||
                  pageNumber === currentPage + 2
                ) {
                  return <span key={pageNumber} className="px-2">...</span>;
                }
                return null;
              })}

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-slate-200 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed bg-white"
              >
                <ChevronRight size={20} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShopHome;