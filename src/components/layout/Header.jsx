import { Link, NavLink } from 'react-router-dom';

const navLinkClass = ({ isActive }) =>
  [
    'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-brand-600/20 text-brand-300'
      : 'text-slate-300 hover:bg-surface-700 hover:text-white',
  ].join(' ');

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-surface-900/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="flex items-center gap-2 text-lg font-semibold tracking-tight text-white"
        >
          <span
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold shadow-lg shadow-brand-600/30"
            aria-hidden
          >
            V
          </span>
          <span className="hidden sm:inline">VideoApp</span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Main">
          <NavLink to="/" end className={navLinkClass}>
            Home
          </NavLink>
          <NavLink to="/chat" className={navLinkClass}>
            Chat
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
