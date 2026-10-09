import { useEffect, useRef } from 'react';

export default function VideoContainer({
  label,
  status = 'waiting',
  isLocal = false,
  stream = null,
  className = '',
}) {
  const videoRef = useRef(null);

  useEffect(() => {
    const el = videoRef.current;
    if (!el) return undefined;
    el.srcObject = stream;
    return () => {
      if (el.srcObject === stream) {
        el.srcObject = null;
      }
    };
  }, [stream]);

  const statusLabel =
    status === 'live' ? 'Live' : status === 'connecting' ? 'Connecting…' : 'Waiting';

  const hasVideo = Boolean(stream);

  return (
    <article
      className={[
        'group relative flex aspect-video w-full flex-col overflow-hidden rounded-2xl',
        'border border-slate-700/80 bg-surface-800 shadow-xl shadow-black/20',
        'ring-1 ring-white/5 transition-shadow hover:shadow-2xl hover:shadow-black/30',
        className,
      ].join(' ')}
    >
      <div
        className="absolute inset-0 bg-gradient-to-br from-surface-700 via-surface-800 to-surface-900"
        aria-hidden
      />

      {hasVideo ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isLocal}
          className={[
            'absolute inset-0 h-full w-full object-cover',
            isLocal && 'scale-x-[-1]',
          ].join(' ')}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className={[
              'flex h-16 w-16 items-center justify-center rounded-full sm:h-20 sm:w-20',
              isLocal ? 'bg-brand-600/30' : 'bg-slate-600/30',
            ].join(' ')}
          >
            <svg
              className="h-8 w-8 text-slate-400 sm:h-10 sm:w-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
              />
            </svg>
          </div>
        </div>
      )}

      <div className="relative z-10 mt-auto flex items-end justify-between gap-2 p-3 sm:p-4">
        <div>
          <p className="text-sm font-semibold text-white sm:text-base">{label}</p>
          {isLocal && (
            <p className="text-xs text-slate-400">Your camera</p>
          )}
        </div>
        <span
          className={[
            'rounded-full px-2.5 py-1 text-xs font-medium',
            status === 'live' && 'bg-emerald-500/20 text-emerald-300',
            status === 'connecting' && 'bg-amber-500/20 text-amber-300',
            status === 'waiting' && 'bg-slate-500/20 text-slate-300',
          ].join(' ')}
        >
          {statusLabel}
        </span>
      </div>
    </article>
  );
}
