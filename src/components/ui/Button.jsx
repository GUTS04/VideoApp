const variants = {
  primary:
    'bg-brand-600 text-white shadow-lg shadow-brand-600/25 hover:bg-brand-500 focus-visible:ring-brand-400',
  secondary:
    'border border-slate-600 bg-surface-800 text-slate-100 hover:border-slate-500 hover:bg-surface-700 focus-visible:ring-slate-400',
  ghost:
    'bg-transparent text-slate-200 hover:bg-surface-700 focus-visible:ring-slate-400',
};

const sizes = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-2.5 text-sm sm:text-base',
  lg: 'px-8 py-3 text-base sm:text-lg',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900',
        'disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </button>
  );
}
