import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Frontend route protection is a UX convenience only — every one of these
// roles is re-checked server-side by the backend on every request.
export default function ProtectedRoute({ roles, children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return <div className="p-12 text-center text-gray-500">Loading...</div>;
    }

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (roles && !roles.includes(user.role)) {
        return (
            <div className="max-w-lg mx-auto mt-16 text-center bg-white p-8 rounded-xl shadow border border-gray-100">
                <h2 className="text-xl font-bold text-gray-900 mb-2">Not authorized</h2>
                <p className="text-gray-600">Your account ({user.role}) doesn't have access to this page.</p>
            </div>
        );
    }

    return children;
}
