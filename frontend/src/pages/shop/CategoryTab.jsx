import React, { useState, useEffect, useMemo } from 'react';
import { CategorySidebar } from '../../components/shop/CategorySidebar';
import { ProductGrid } from '../../components/shop/ProductGrid';
import { SearchAndFilters } from '../../components/shop/SearchAndFilters';
import { sampleProducts } from '../../data/sampleProducts';

// Define subcategories for each category (must match CategorySidebar)
const CATEGORY_SUBCATEGORIES = {
  fashion: ['Fashion-Men', 'Fashion-Women', 'Fashion-Kids'],
  electronics: ['Electronics-Laptops', 'Electronics-Desktops', 'Electronics-Smartphones', 'Electronics-Tablets', 'Electronics-Screens', 'Electronics-Keyboards', 'Electronics-Mice', 'Electronics-Chargers', 'Electronics-Storage', 'Electronics-Servers', 'Electronics-TV', 'Electronics-Media', 'Electronics-Supplies', 'Electronics-Other'],
  baby: ['Baby-Feeding', 'Baby-Toys', 'Baby-Clothes', 'Baby-Furniture']
};

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
  const [isSearchResults, setIsSearchResults] = useState(false); // Track if showing search results

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://192.168.1.128:8002';

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
    setIsSearchResults(false); // Reset search results flag when changing category
  }, [category]);

  // Apply filters
  const filteredProducts = useMemo(() => {
    let filtered = [...products];

    // If showing search results from API, don't apply text search filter
    // The API already handled the search relevance
    if (activeSearchQuery && !isSearchResults) {
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(activeSearchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(activeSearchQuery.toLowerCase())
      );
    }

    // Don't apply subcategory filter when showing search results
    // The search API already filtered by category
    if (selectedSubcategories.length > 0 && !isSearchResults) {
      filtered = filtered.filter(p => selectedSubcategories.includes(p.metadata?.subcategory));
    }

    // These filters can still be applied to search results if needed
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

    if (showDiscountOnly) {
      filtered = filtered.filter(p => p.has_discount);
    }

    return filtered;
  }, [products, activeSearchQuery, priceRange, selectedGender, selectedCondition, selectedBrand, showDiscountOnly, selectedSubcategories, isSearchResults]);

  const handleSearchSubmit = async () => {
    setActiveSearchQuery(searchQuery);
    setCurrentPage(1);
    
    if (searchQuery) {
      try {
        // Prepare filters - if no subcategories selected, use all subcategories for this category
        // Convert subcategory names to "Category-Subcategory" format
        const categoryPrefix = category.charAt(0).toUpperCase() + category.slice(1);
        const subcategoriesToSend = selectedSubcategories.length > 0 
          ? selectedSubcategories.map(sub => `${categoryPrefix}-${sub}`)
          : CATEGORY_SUBCATEGORIES[category] || [];
        
        const filters = {
          category: subcategoriesToSend,
          ...(priceRange.min && { min_price: parseFloat(priceRange.min) }),
          ...(priceRange.max && { max_price: parseFloat(priceRange.max) })
        };

        // Send search request
        const searchRequest = {
          user_id: user._id || 'anonymous',
          query_text: searchQuery,
          filters: filters,
          limit: 20
        };
        console.log("aaaaaa",searchRequest)
        const response = await fetch(`${API_URL}/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(searchRequest)
        });
        if (response.ok) {
          const data = await response.json();
          console.log('Search results:', data);
          
          // Transform search results to match product structure
          if (data.results && Array.isArray(data.results)) {
            const transformedProducts = data.results.map(result => ({
              _id: result.product_id,
              product_id: result.product_id,
              name: result.name,
              price: result.price,
              image_url: result.image_url,
              description: result.payload?.metadata?.description || '',
              category: result.payload?.metadata?.category || category,
              brand: result.payload?.metadata?.brand || '',
              has_discount: result.payload?.metadata?.is_discounted || false,
              discount_amount: result.payload?.metadata?.discount_amount || 0,
              original_price: result.payload?.metadata?.original_price || result.price,
              match_reason: result.match_reason, // Add match reason for display
              metadata: result.payload?.metadata || {}
            }));
            setProducts(transformedProducts);
            setIsSearchResults(true); // Mark as search results
            console.log('Transformed products:', transformedProducts);
          }
        }
      } catch (err) {
        console.error('Search failed:', err);
      }
      
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
