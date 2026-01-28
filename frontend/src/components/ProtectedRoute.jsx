import { Navigate } from 'react-router-dom';
import { useContext } from 'react';
import { StoreContext } from '../context/StoreContext';

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useContext(StoreContext);
  
  // Check localStorage as backup
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const hasValidUser = !!(user._id && user.user_type);
  
  if (!isAuthenticated && !hasValidUser) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};
