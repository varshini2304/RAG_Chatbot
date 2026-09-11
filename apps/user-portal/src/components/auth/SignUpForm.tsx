import React, { useState } from 'react';

interface SignUpFormProps {
  onSubmit: (username: string, pass: string, confirm: string) => void;
  errorMessage?: string;
  successMessage?: string;
  isLoading?: boolean;
}

export const SignUpForm: React.FC<SignUpFormProps> = ({
  onSubmit,
  errorMessage,
  successMessage,
  isLoading,
}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    onSubmit(username, password, confirmPassword);
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <p style={{ color: '#94a3b8', fontSize: '0.78rem', lineHeight: '1.45', margin: '0 0 0.4rem 0' }}>
        Create a local account to save your chat sessions and review custom document sets.
      </p>

      {errorMessage && (
        <div className="login-alert error">{errorMessage}</div>
      )}
      {successMessage && (
        <div className="login-alert success">{successMessage}</div>
      )}

      <div className="form-group">
        <label className="form-label">New Username</label>
        <input
          type="text"
          className="form-input"
          placeholder="Choose a username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <div className="form-group">
        <label className="form-label">Choose Password</label>
        <input
          type="password"
          className="form-input"
          placeholder="Choose a password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <div className="form-group">
        <label className="form-label">Confirm Password</label>
        <input
          type="password"
          className="form-input"
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          disabled={isLoading}
        />
      </div>
      <button type="submit" className="login-submit-btn" disabled={isLoading}>
        {isLoading ? 'Creating Account...' : 'Create Account →'}
      </button>
    </form>
  );
};
