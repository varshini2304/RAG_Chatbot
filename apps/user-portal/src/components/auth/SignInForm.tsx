import React, { useState } from 'react';

interface SignInFormProps {
  onSubmit: (username: string, pass: string) => void;
  errorMessage?: string;
  isLoading?: boolean;
}

export const SignInForm: React.FC<SignInFormProps> = ({ onSubmit, errorMessage, isLoading }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    onSubmit(username, password);
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      {errorMessage && (
        <div className="login-alert error">{errorMessage}</div>
      )}
      <div className="form-group">
        <label className="form-label">Username</label>
        <input
          type="text"
          className="form-input"
          placeholder="Enter your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <div className="form-group">
        <label className="form-label">Password</label>
        <input
          type="password"
          className="form-input"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <button type="submit" className="login-submit-btn" disabled={isLoading}>
        {isLoading ? 'Signing In...' : 'Sign In →'}
      </button>
    </form>
  );
};
