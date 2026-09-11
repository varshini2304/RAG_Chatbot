import React, { useEffect } from 'react';
import { useThemeStore } from '../../store/themeStore';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { theme } = useThemeStore();

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return <div className="min-h-screen bg-background text-slate-100 antialiased">{children}</div>;
};
