import React, { useState, useEffect, useMemo } from 'react';
import { CategorySidebar } from '../../components/shop/CategorySidebar';
import { ProductGrid } from '../../components/shop/ProductGrid';
import { SearchAndFilters } from '../../components/shop/SearchAndFilters';
import { sampleProducts } from '../../data/sampleProducts';

export const CategoryTab = ({ category }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearchQuery, setActiveSearchQuery] = useState('');
  const [priceRange, setPriceRange] = useState({ min: '', max: '' });
  const [selectedGender, setSelectedGender] = useState('');
  const [selectedCondition, setSelectedCondition] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [showDiscountOnly, setShowDiscountOnly] = useState(false);
  const [selectedSubcategories, setSelectedSubcategories] = useState([]);
  const [products, setProducts] = useState([]);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://localhost:8000';

  // TODO: Replace with API call based on category
  useEffect(() => {
    // For now, use sample products filtered by category
    // Later: fetch(`${API_URL}/api/products/${category}`)
    const parseProductCategory = (product) => {
      const metadata = product.metadata || {};
      let cat = metadata.category || '';
      let subcategory = metadata.subcategory || null;
      
      if (cat.includes('-')) {
        const parts = cat.split('-');
        cat = parts[0];
        subcategory = parts[1] || subcategory;
      }
      
      return {
        ...product,
        metadata: { ...metadata, category: cat, subcategory },
        category: cat,
        name: metadata.name,
        description: metadata.description,
        price: metadata.price,
        image_url: metadata.image_url,
        has_discount: metadata.is_discounted,
        brand: metadata.brand,
        _id: product.product_id
      };
    };

    const categoryName = category.charAt(0).toUpperCase() + category.slice(1);
    const filtered = sampleProducts
      .map(parseProductCategory)
      .filter(p => p.metadata.category === categoryName);
    
    setProducts(filtered);
    setSelectedSubcategories([]);
    setSearchQuery('');
    setActiveSearchQuery('');
  }, [category]);

  // Apply filters
  const filteredProducts = useMemo(() => {
    let filtered = [...products];

    if (activeSearchQuery) {
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(activeSearchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(activeSearchQuery.toLowerCase())
      );
    }

    if (priceRange.min) {
      filtered = filtered.filter(p => p.price >= parseFloat(priceRange.min));
    }
    if (priceRange.max) {
      filtered = filtered.filter(p => p.price <= parseFloat(priceRange.max));
    }

    if (selectedGender) {
      filtered = filtered.filter(p => p.metadata?.gender === selectedGender);
    }

    if (selectedCondition) {
      filtered = filtered.filter(p => p.metadata?.condition === selectedCondition);
    }

    if (selectedBrand) {
      filtered = filtered.filter(p => p.metadata?.brand === selectedBrand);
    }

    if (selectedSubcategories.length > 0) {
      filtered = filtered.filter(p => selectedSubcategories.includes(p.metadata?.subcategory));
    }

    if (showDiscountOnly) {
      filtered = filtered.filter(p => p.has_discount);
    }

    return filtered;
  }, [products, activeSearchQuery, priceRange, selectedGender, selectedCondition, selectedBrand, showDiscountOnly, selectedSubcategories]);

  const handleSearchSubmit = () => {
    setActiveSearchQuery(searchQuery);
    setCurrentPage(1);
    
    if (searchQuery) {
      const params = new URLSearchParams({
        query: searchQuery,
        user_id: user._id || 'anonymous',
        category: category,
        timestamp: new Date().toISOString(),
        session_id: `session_${user._id || 'anonymous'}`
      });
      fetch(`${API_URL}/events/search?${params}`)
        .catch(err => console.log('Event tracking failed:', err));
    }
  };

  const handleFilterApply = () => {
    setCurrentPage(1);
  };

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 100, behavior: 'smooth' });
  };

  const brands = [...new Set(products.map(p => p.metadata?.brand).filter(Boolean))];
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;

  const categoryTitles = {
    fashion: 'Fashion Products',
    electronics: 'Electronics Products',
    baby: 'Baby Products'
  };

  return (
    <>
      {/* Search and Filter Bar */}
      <SearchAndFilters
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        activeSearchQuery={activeSearchQuery}
        setActiveSearchQuery={setActiveSearchQuery}
        selectedCategory=""
        setSelectedCategory={() => {}}
        selectedGender={selectedGender}
        setSelectedGender={setSelectedGender}
        selectedCondition={selectedCondition}
        setSelectedCondition={setSelectedCondition}
        selectedBrand={selectedBrand}
        setSelectedBrand={setSelectedBrand}
        showDiscountOnly={showDiscountOnly}
        setShowDiscountOnly={setShowDiscountOnly}
        priceRange={priceRange}
        setPriceRange={setPriceRange}
        selectedSubcategories={selectedSubcategories}
        setSelectedSubcategories={setSelectedSubcategories}
        activeTab={category}
        categories={[]}
        brands={brands}
        filteredCount={filteredProducts.length}
        onSearch={handleSearchSubmit}
        onFilterApply={handleFilterApply}
      />

      {/* Category Products Section */}
      <div className="bg-slate-100 py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-6">
            {/* Category Sidebar */}
            <CategorySidebar
              activeTab={category}
              selectedSubcategories={selectedSubcategories}
              setSelectedSubcategories={setSelectedSubcategories}
            />

            {/* Products Grid */}
            <div className="flex-1">
              <ProductGrid
                products={filteredProducts}
                currentPage={currentPage}
                itemsPerPage={itemsPerPage}
                onPageChange={handlePageChange}
                source={`${category}-tab`}
                title={categoryTitles[category] || 'Products'}
                description={`Showing ${indexOfFirstItem + 1}-${Math.min(indexOfLastItem, filteredProducts.length)} of ${filteredProducts.length} products`}
                layout="horizontal"
              />
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
