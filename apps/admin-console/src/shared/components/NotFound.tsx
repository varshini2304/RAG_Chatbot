import React from 'react';
import { Link } from 'react-router-dom';

export const NotFound: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4">
      <h1 className="text-6xl font-extrabold text-indigo-500 font-outfit">404</h1>
      <h2 className="text-xl font-bold text-white">Page Not Found</h2>
      <p className="text-sm text-muted max-w-sm">The page you are looking for does not exist or has been relocated.</p>
      <Link to="/dashboard" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-lg transition-all">
        Go Back Home
      </Link>
    </div>
  );
};
