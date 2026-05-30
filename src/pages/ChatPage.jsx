import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import VideoGrid from '../components/chat/VideoGrid';
import { MATCH_POOL } from '../constants/matchPool';

const CONNECT_DELAY_MS = 800;
const NEXT_DELAY_MS = 600;

function pickRandomMatch(excludeIndex) {
  const pool = MATCH_POOL.filter((_, i) => i !== excludeIndex);
  const index = Math.floor(Math.random() * pool.length);
  const match = pool[index];
  const originalIndex = MATCH_POOL.indexOf(match);
  return { match, index: originalIndex };
}

export default function ChatPage() {
  const [matchIndex, setMatchIndex] = useState(0);
  const [localStatus, setLocalStatus] = useState('connecting');
  const [remoteStatus, setRemoteStatus] = useState('waiting');
  const [sessionKey, setSessionKey] = useState(0);

  const participants = {
    local: 'You',
    remote: MATCH_POOL[matchIndex].name,
  };

  const connectSession = useCallback(() => {
    setLocalStatus('connecting');
    setRemoteStatus('waiting');

    const localTimer = setTimeout(() => setLocalStatus('live'), CONNECT_DELAY_MS);
    const remoteTimer = setTimeout(
      () => setRemoteStatus('live'),
      CONNECT_DELAY_MS + 400,
    );

    return () => {
      clearTimeout(localTimer);
      clearTimeout(remoteTimer);
    };
  }, []);

  useEffect(() => {
    return connectSession();
  }, [connectSession, sessionKey]);

  const handleNext = () => {
    setRemoteStatus('connecting');
    setTimeout(() => {
      const { index } = pickRandomMatch(matchIndex);
      setMatchIndex(index);
      setSessionKey((k) => k + 1);
    }, NEXT_DELAY_MS);
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white sm:text-3xl">
            Video chat
          </h1>
          <p className="mt-1 text-slate-400">
            Session with{' '}
            <span className="font-medium text-slate-200">
              {participants.remote}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link to="/">
            <Button variant="ghost" size="sm">
              Back home
            </Button>
          </Link>
          <Button size="md" onClick={handleNext}>
            Next
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
              />
            </svg>
          </Button>
        </div>
      </div>

      <VideoGrid
        participants={participants}
        localStatus={localStatus}
        remoteStatus={remoteStatus}
      />

      <p className="mt-6 text-center text-sm text-slate-500">
        Camera and microphone integration can be wired here. UI is ready for
        WebRTC streams inside each video container.
      </p>
    </div>
  );
}
