import React, { useState, useEffect } from 'react';
import { Tag, Package, Star } from 'lucide-react';
import { FeaturedCarousel } from '../../components/shop/FeaturedCarousel';
import { ProductSection } from '../../components/shop/ProductSection';
import { ProductGrid } from '../../components/shop/ProductGrid';
import { sampleProducts } from '../../data/sampleProducts';

export const ShopTab = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [products, setProducts] = useState([]);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://localhost:8000';

  // TODO: Replace with API call
  useEffect(() => {
    // For now, use sample products
    // Later: fetch(`${API_URL}/api/products/for-you?user_id=${user._id}`)
    const parseProductCategory = (product) => {
      const metadata = product.metadata || {};
      let category = metadata.category || '';
      let subcategory = metadata.subcategory || null;
      
      if (category.includes('-')) {
        const parts = category.split('-');
        category = parts[0];
        subcategory = parts[1] || subcategory;
      }
      
      return {
        ...product,
        metadata: { ...metadata, category, subcategory },
        category,
        name: metadata.name,
        description: metadata.description,
        price: metadata.price,
        image_url: metadata.image_url,
        has_discount: metadata.is_discounted,
        brand: metadata.brand,
        _id: product.product_id
      };
    };

    setProducts(sampleProducts.map(parseProductCategory));
  }, []);

  // Get featured products for carousel
  const featuredProducts = products.filter(p => p.has_discount).slice(0, 5).length > 0
    ? products.filter(p => p.has_discount).slice(0, 5)
    : products.slice(0, 5);

  // Auto-advance carousel
  useEffect(() => {
    if (featuredProducts.length === 0) return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % featuredProducts.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [featuredProducts.length]);

  // Get different product categories
  const trendingProducts = products.slice(0, 8);
  const discountedProducts = products.filter(p => p.has_discount).slice(0, 4);
  const newArrivals = products.slice(0, 4);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const nextSlide = () => setCurrentSlide((prev) => (prev + 1) % featuredProducts.length);
  const prevSlide = () => setCurrentSlide((prev) => (prev - 1 + featuredProducts.length) % featuredProducts.length);

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;

  return (
    <>
      <FeaturedCarousel
        featuredProducts={featuredProducts}
        currentSlide={currentSlide}
        nextSlide={nextSlide}
        prevSlide={prevSlide}
      />

      {/* Hot Deals Section */}
      {discountedProducts.length > 0 && (
        <div id="hot-deals" className="py-16">
          <ProductSection
            products={discountedProducts}
            title="Hot Deals"
            description="Limited time offers you don't want to miss"
            icon={Tag}
            source="hot-deals"
          />
        </div>
      )}

      {/* New Arrivals Section */}
      <div id="new-arrivals" className="bg-white py-16">
        <ProductSection
          products={newArrivals}
          title="New Arrivals"
          description="Fresh products just added to our collection"
          icon={Package}
          source="new-arrivals"
        />
      </div>

      {/* Trending Now Section */}
      <div id="trending" className="py-16">
        <ProductSection
          products={trendingProducts}
          title="Trending Now"
          description="Most popular items loved by our customers"
          icon={Star}
          source="trending"
        />
      </div>

    </>
  );
};
