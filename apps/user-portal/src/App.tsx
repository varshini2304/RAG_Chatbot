import { useEffect, useState } from 'react';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { authService } from './services/authService';
import './styles/base.css';
import './styles/login.css';
import './styles/dashboard.css';
import './styles/chat.css';
import './styles/industrial-theme.css';

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('user');
  const [isInitializing, setIsInitializing] = useState(true);

  // Restore authenticated session on mount if token is present
  useEffect(() => {
    const checkAuth = async () => {
      if (authService.hasToken()) {
        try {
          const res = await authService.me();
          if (res.success && res.username) {
            setUsername(res.username);
            setIsAuthenticated(true);
          } else {
            authService.logout();
            setIsAuthenticated(false);
          }
        } catch {
          authService.logout();
          setIsAuthenticated(false);
        }
      }
      setIsInitializing(false);
    };
    checkAuth();
  }, []);

  const handleLoginSuccess = (user: string) => {
    setUsername(user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
  };

  if (isInitializing) {
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#090a11', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b8ea9', fontSize: '0.88rem' }}>
        Loading session...
      </div>
    );
  }

  return (
    <>
      {!isAuthenticated ? (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      ) : (
        <DashboardPage username={username} onLogout={handleLogout} />
      )}
    </>
  );
}

export default App;
