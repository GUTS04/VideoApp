export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-slate-800/80 bg-surface-900/50">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-6 text-center text-sm text-slate-400 sm:flex-row sm:px-6 lg:px-8">
        <p>&copy; {year} VideoApp. All rights reserved.</p>
        <p className="text-slate-500">Built with React, Vite &amp; Tailwind CSS</p>
      </div>
    </footer>
  );
}
