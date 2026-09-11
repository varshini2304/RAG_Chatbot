import React, { useState } from 'react';
import { SignInForm } from '../components/auth/SignInForm';
import { SignUpForm } from '../components/auth/SignUpForm';
import { authService } from '../services/authService';
import { ApiError } from '../services/api';

interface LoginPageProps {
  onLoginSuccess: (username: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async (uname: string, pass: string) => {
    setErrorMsg('');
    if (!uname.trim() || !pass.trim()) {
      setErrorMsg('Username and password are required.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.login(uname.trim(), pass.trim());
      onLoginSuccess(res.username);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg('Sign in failed. Please check your network connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (uname: string, pass: string, confirm: string) => {
    setErrorMsg('');
    setSuccessMsg('');
    if (!uname.trim()) {
      setErrorMsg('Username cannot be empty.');
      return;
    }
    if (!pass.trim()) {
      setErrorMsg('Password cannot be empty.');
      return;
    }
    if (pass !== confirm) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.register(uname.trim(), pass.trim(), confirm.trim());
      setSuccessMsg(res.message || 'Account created successfully!');
      setTimeout(() => {
        onLoginSuccess(res.username);
      }, 600);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg('Registration failed. Please check your network connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-logo">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: '1.6rem', height: '1.6rem' }}
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <h1 className="login-title">Document RAG Portal</h1>
        <p className="login-subtitle">
          Sign in to access the document grounding engine.
        </p>

        <div className="login-warning-banner">
          ⚠️ Prototype Warning: This portal uses prototype-level local file authentication. Do not use production secrets.
        </div>

        <div className="login-tabs">
          <button
            type="button"
            className={`login-tab-btn ${activeTab === 'signin' ? 'active' : 'inactive'}`}
            onClick={() => {
              setActiveTab('signin');
              setErrorMsg('');
              setSuccessMsg('');
            }}
            disabled={isLoading}
          >
            👤 Sign In
          </button>
          <button
            type="button"
            className={`login-tab-btn ${activeTab === 'signup' ? 'active' : 'inactive'}`}
            onClick={() => {
              setActiveTab('signup');
              setErrorMsg('');
              setSuccessMsg('');
            }}
            disabled={isLoading}
          >
            👤+ Sign Up
          </button>
        </div>

        {activeTab === 'signin' ? (
          <SignInForm onSubmit={handleSignIn} errorMessage={errorMsg} isLoading={isLoading} />
        ) : (
          <SignUpForm
            onSubmit={handleSignUp}
            errorMessage={errorMsg}
            successMessage={successMsg}
            isLoading={isLoading}
          />
        )}

        <div className="login-footer-text">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: '0.9rem', height: '0.9rem' }}
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span>
            Your data is secure and private. Document extraction, chunking, and database storage are performed locally, while retrieved text is sent to external API providers (Gemini/Groq) for answer generation.
          </span>
        </div>
      </div>
    </div>
  );
};
