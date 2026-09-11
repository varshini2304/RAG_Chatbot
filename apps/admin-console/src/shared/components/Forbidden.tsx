import React from 'react';
import { Link } from 'react-router-dom';

export const Forbidden: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
      <h1 className="text-6xl font-extrabold text-red-500 font-outfit">403</h1>
      <h2 className="text-xl font-bold text-white">Access Forbidden</h2>
      <p className="text-sm text-muted max-w-sm">You do not have the required administrative permissions to access this page.</p>
      <Link to="/dashboard" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-lg transition-all">
        Go Back Home
      </Link>
    </div>
  );
};
