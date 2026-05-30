import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';

const features = [
  {
    title: 'Instant matching',
    description: 'Jump into a session with one tap and connect in seconds.',
  },
  {
    title: 'HD video containers',
    description: 'Clear local and remote video panels that scale on any screen.',
  },
  {
    title: 'Skip & continue',
    description: 'Use Next when you want to meet someone new.',
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col">
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--color-brand-600)_0%,_transparent_55%)] opacity-20"
          aria-hidden
        />

        <div className="relative mx-auto flex max-w-7xl flex-col items-center px-4 py-16 text-center sm:px-6 sm:py-24 lg:px-8 lg:py-32">
          <p className="mb-4 inline-flex rounded-full border border-brand-500/30 bg-brand-600/10 px-4 py-1.5 text-sm font-medium text-brand-300">
            Live video chat
          </p>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
            Meet new people through{' '}
            <span className="bg-gradient-to-r from-brand-300 to-brand-500 bg-clip-text text-transparent">
              video
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg text-slate-400 sm:text-xl">
            VideoApp pairs you for real-time conversations. Start a chat, see
            both video panels, and tap Next whenever you are ready for someone
            new.
          </p>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
            <Link to="/chat">
              <Button size="lg">Start Chat</Button>
            </Link>
            <a href="#features">
              <Button variant="secondary" size="lg">
                Learn more
              </Button>
            </a>
          </div>
        </div>
      </section>

      <section
        id="features"
        className="border-t border-slate-800/80 bg-surface-800/30 py-16 sm:py-20"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            Everything you need
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-slate-400">
            A focused flow: land on home, start chat, view videos, go next.
          </p>

          <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <li
                key={feature.title}
                className="rounded-2xl border border-slate-700/60 bg-surface-800/50 p-6 shadow-lg"
              >
                <h3 className="text-lg font-semibold text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 text-slate-400">{feature.description}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
