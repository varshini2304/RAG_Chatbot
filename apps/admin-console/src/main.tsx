import React from 'react';
import { createRoot } from 'react-dom/client';
import { AppRouter } from './app/router';
import { ThemeProvider } from './app/providers/ThemeProvider';
import { ErrorBoundary } from './shared/components/ErrorBoundary';
import './styles/index.css';

console.log('Mounting AppRouter...');

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <ThemeProvider>
          <AppRouter />
        </ThemeProvider>
      </ErrorBoundary>
    </React.StrictMode>
  );
}

