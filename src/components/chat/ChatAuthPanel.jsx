import { useState } from 'react';
import Button from '../ui/Button';
import { loginUser, registerUser } from '../../api/auth';
import { saveAuth } from '../../utils/authStorage';

export default function ChatAuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [gender, setGender] = useState('male');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response =
        mode === 'register'
          ? await registerUser({ email, username, password, gender })
          : await loginUser({ email, password });

      const accessToken = response.tokens.access_token;
      const refreshToken = response.tokens.refresh_token;
      saveAuth({ accessToken, refreshToken, user: response.user });
      onAuthenticated({ accessToken, refreshToken, user: response.user });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto mb-8 max-w-md rounded-2xl border border-slate-700/80 bg-surface-800 p-6 shadow-xl">
      <h2 className="text-lg font-semibold text-white">
        {mode === 'login' ? 'Sign in to chat' : 'Create an account'}
      </h2>
      <p className="mt-1 text-sm text-slate-400">
        Matchmaking pairs male with female accounts. Use two browsers with opposite genders to test.
      </p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm text-slate-300">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-surface-900 px-3 py-2 text-white"
          />
        </label>

        {mode === 'register' && (
          <>
            <label className="block text-sm text-slate-300">
              Username
              <input
                type="text"
                required
                minLength={3}
                pattern="^[a-zA-Z0-9_]+$"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-600 bg-surface-900 px-3 py-2 text-white"
              />
            </label>
            <label className="block text-sm text-slate-300">
              Gender
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-600 bg-surface-900 px-3 py-2 text-white"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </label>
          </>
        )}

        <label className="block text-sm text-slate-300">
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-surface-900 px-3 py-2 text-white"
          />
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Register'}
        </Button>
      </form>

      <button
        type="button"
        className="mt-4 w-full text-center text-sm text-brand-300 hover:text-brand-200"
        onClick={() => {
          setMode(mode === 'login' ? 'register' : 'login');
          setError(null);
        }}
      >
        {mode === 'login' ? 'Need an account? Register' : 'Already have an account? Sign in'}
      </button>
    </div>
  );
}
