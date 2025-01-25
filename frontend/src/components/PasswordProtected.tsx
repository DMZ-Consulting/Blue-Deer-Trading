'use client'

import { useState, useEffect } from 'react'

interface PasswordProtectedProps {
  children: React.ReactNode;
}

export function PasswordProtected({ children }: PasswordProtectedProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const correctPassword = process.env.NEXT_PUBLIC_SITE_PASSWORD || 'bluedeer';

  useEffect(() => {
    // Check if already authenticated in this session
    const auth = sessionStorage.getItem('isAuthenticated');
    if (auth === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === correctPassword) {
      setIsAuthenticated(true);
      sessionStorage.setItem('isAuthenticated', 'true');
    } else {
      alert('Incorrect password');
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <form onSubmit={handleSubmit} className="p-8 space-y-4 bg-card rounded-lg shadow-lg">
          <h1 className="text-2xl font-bold text-center mb-6">Blue Deer Trading</h1>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-2">
              Enter Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 border rounded-md bg-background"
              autoFocus
            />
          </div>
          <button
            type="submit"
            className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Enter
          </button>
        </form>
      </div>
    );
  }

  return children;
} 