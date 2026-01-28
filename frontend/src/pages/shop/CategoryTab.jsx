import React, { useState, useEffect, useMemo } from 'react';
import { CategorySidebar } from '../../components/shop/CategorySidebar';
import { ProductGrid } from '../../components/shop/ProductGrid';
import { ProductSection } from '../../components/shop/ProductSection';
import { SearchAndFilters } from '../../components/shop/SearchAndFilters';

// Define subcategories for each category (must match CategorySidebar)
const CATEGORY_SUBCATEGORIES = {
  fashion: ['Fashion-Men', 'Fashion-Women', 'Fashion-Kids'],
  electronics: ['Electronics-Laptops', 'Electronics-Desktops', 'Electronics-Smartphones', 'Electronics-Tablets', 'Electronics-Screens', 'Electronics-Keyboards', 'Electronics-Mice', 'Electronics-Chargers', 'Electronics-Storage', 'Electronics-Servers', 'Electronics-TV', 'Electronics-Media', 'Electronics-Supplies', 'Electronics-Other'],
  baby: ['Baby-Feeding', 'Baby-Toys', 'Baby-Clothes', 'Baby-Furniture']
};

const SUBCATEGORY_LABELS = {
  'Fashion-Men': 'Men\'s Fashion',
  'Fashion-Women': 'Women\'s Fashion',
  'Fashion-Kids': 'Kids Fashion',
  'Electronics-Laptops': 'Laptops',
  'Electronics-Desktops': 'Desktop Computers',
  'Electronics-Smartphones': 'Smartphones',
  'Electronics-Tablets': 'Tablets',
  'Electronics-Screens': 'Monitors & Screens',
  'Electronics-Keyboards': 'Keyboards',
  'Electronics-Mice': 'Mice & Pointing Devices',
  'Electronics-Chargers': 'Chargers & Cables',
  'Electronics-Storage': 'Storage Devices',
  'Electronics-Servers': 'Servers',
  'Electronics-TV': 'TVs & Home Entertainment',
  'Electronics-Media': 'Media Devices',
  'Electronics-Supplies': 'Office Supplies',
  'Electronics-Other': 'Other Electronics',
  'Baby-Feeding': 'Feeding & Nursing',
  'Baby-Toys': 'Toys & Play',
  'Baby-Clothes': 'Baby Clothing',
  'Baby-Furniture': 'Nursery Furniture'
};

export const CategoryTab = ({ category }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearchQuery, setActiveSearchQuery] = useState('');
    // Restore search state from sessionStorage on mount
    // Only restore search state, do not re-trigger search API
    React.useEffect(() => {
      const saved = sessionStorage.getItem(`searchState-${category}`);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed && parsed.searchQuery) setSearchQuery(parsed.searchQuery);
          if (parsed && parsed.activeSearchQuery) setActiveSearchQuery(parsed.activeSearchQuery);
          if (parsed && Array.isArray(parsed.products)) {
            setProducts(parsed.products);
            setIsSearchResults(true);
          }
        } catch {}
      } else {
        setIsSearchResults(false);
        setActiveSearchQuery('');
      }
    }, [category]);
  const [priceRange, setPriceRange] = useState({ min: '', max: '' });
  const [selectedGender, setSelectedGender] = useState('');
  const [selectedCondition, setSelectedCondition] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [showDiscountOnly, setShowDiscountOnly] = useState(false);
  const [selectedSubcategories, setSelectedSubcategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [productsBySubcategory, setProductsBySubcategory] = useState({});
  const [loading, setLoading] = useState(false);
  const [isSearchResults, setIsSearchResults] = useState(false); // Track if showing search results

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const API_URL = 'http://192.168.1.128:8002';

  // Fetch products for each subcategory when not searching
  useEffect(() => {
    const fetchCategoryProducts = async () => {
      setLoading(true);
      const subcategories = CATEGORY_SUBCATEGORIES[category] || [];
      const productsBySubcat = {};

      try {
        // Fetch products for each subcategory
        for (const subcategory of subcategories) {
          const response = await fetch(`http://192.168.1.128:8000/products/${subcategory}`);
          if (response.ok) {
            const data = await response.json();
            // Transform products
            console.log("data",data)
            const transformedProducts = (data.products || []).map(p => {
              const isDiscounted = p.metadata.is_discounted || false;
              const discountAmount = p.metadata.discount_percentage || p.metadata.discount_amount || (isDiscounted ? 15 : 0);
              return {
                _id: p.id || p.product_id || p._id,
                product_id: p.id || p.product_id || p._id,
                name: p.metadata.name,
                price: p.metadata.price,
                image_url: p.image || p.metadata.image_url,
                description: p.metadata.description || '',
                category: p.metadata.category,
                brand: p.metadata.brand || '',
                has_discount: isDiscounted,
                discount_amount: discountAmount,
                stock_quantity: p.metadata.stock_quantity || 0,
                vendor: p.metadata.brand || 'Unknown',
                metadata: p
              };
            });
            productsBySubcat[subcategory] = transformedProducts;
          }
        }
        setProductsBySubcategory(productsBySubcat);
        // Flatten all products for filtering
        const allProducts = Object.values(productsBySubcat).flat();
        setProducts(allProducts);
      } catch (error) {
        console.error('Failed to fetch category products:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCategoryProducts();
    setSelectedSubcategories([]);
    // Don't reset search state - preserve when navigating back from product detail
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
        const response = await fetch(`${API_URL}/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(searchRequest)
        });
        if (response.ok) {
          const data = await response.json();
          // Transform search results to match product structure
          if (data.results && Array.isArray(data.results)) {
            const transformedProducts = data.results.map(result => {
              const isDiscounted = result.payload?.metadata?.is_discounted || false;
              const discountAmount = result.payload?.metadata?.discount_percentage || 
                                    result.payload?.metadata?.discount_amount || 
                                    (isDiscounted ? 15 : 0);
              return {
                _id: result.product_id,
                product_id: result.product_id,
                name: result.name,
                price: result.price,
                image_url: result.image_url,
                description: result.payload?.metadata?.description || '',
                category: result.payload?.metadata?.category || category,
                brand: result.payload?.metadata?.brand || '',
                has_discount: isDiscounted,
                discount_amount: discountAmount,
                stock_quantity: result.payload?.metadata?.stock_quantity || 0,
                vendor: result.payload?.metadata?.brand || 'Unknown',
                match_reason: result.match_reason,
                metadata: result.payload?.metadata || {}
              };
            });
            setProducts(transformedProducts);
            setIsSearchResults(true); // Mark as search results
            // Save search state to sessionStorage
            sessionStorage.setItem(`searchState-${category}`, JSON.stringify({
              searchQuery,
              activeSearchQuery: searchQuery,
              products: transformedProducts,
              isSearchResults: true
            }));
          }
        }
      } catch (err) {
        console.error('Search failed:', err);
      }
    }
  };

  const handleFilterApply = () => {
      // Clear search state from sessionStorage when not searching
      useEffect(() => {
        if (!isSearchResults && !activeSearchQuery) {
          sessionStorage.removeItem(`searchState-${category}`);
        }
      }, [isSearchResults, activeSearchQuery, category]);
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

            {/* Products Display */}
            <div className="flex-1">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
                </div>
              ) : isSearchResults || activeSearchQuery ? (
                /* Search Results - Grid View */
                <ProductGrid
                  products={filteredProducts}
                  currentPage={currentPage}
                  itemsPerPage={itemsPerPage}
                  onPageChange={handlePageChange}
                  source={`${category}-tab`}
                  description={`Showing ${indexOfFirstItem + 1}-${Math.min(indexOfLastItem, filteredProducts.length)} of ${filteredProducts.length} products`}
                  layout="horizontal"
                />
              ) : (
                /* Category Browse - Subcategory Sections */
                <div className="space-y-12">
                  {Object.entries(productsBySubcategory).map(([subcategory, products], index) => {
                    if (products.length === 0) return null;
                    
                    return (
                      <div 
                        key={subcategory}
                        className={'bg-white p-8 rounded-lg'}
                      >
                        <ProductSection
                          products={products.slice(0, 8)}
                          title={SUBCATEGORY_LABELS[subcategory] || subcategory}
                          source={subcategory}
                          layout="horizontal"
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
