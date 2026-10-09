import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Button from '../ui/Button';
import VideoGrid from './VideoGrid';
import { blockUser, reportUser } from '../../api/blocks';
import { fetchCoinBalance } from '../../api/coins';
import { useMatchmakingSocket } from '../../hooks/useMatchmakingSocket';
import { useWebRTC } from '../../hooks/useWebRTC';

function mapVideoStatus(callStatus, hasStream) {
  if (callStatus === 'connected' && hasStream) return 'live';
  if (callStatus === 'starting' || callStatus === 'negotiating') return 'connecting';
  if (callStatus === 'disconnected' || callStatus === 'error') return 'connecting';
  return 'waiting';
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function VideoChat({ accessToken, user }) {
  const signalHandlerRef = useRef(/** @type {(msg: Record<string, unknown>) => void} */ (() => {}));
  const joinedRef = useRef(false);
  const [coinBalance, setCoinBalance] = useState(null);
  const [callDuration, setCallDuration] = useState(0);
  const [billingMessage, setBillingMessage] = useState(null);

  const onSocketMessage = useCallback((msg) => {
    if (
      msg.type === 'webrtc_offer' ||
      msg.type === 'webrtc_answer' ||
      msg.type === 'ice_candidate'
    ) {
      signalHandlerRef.current(msg);
    }
    if (msg.type === 'call_billing_update') {
      setCoinBalance(msg.coin_balance);
      setCallDuration(msg.call_duration_seconds ?? 0);
    }
    if (msg.type === 'call_terminated') {
      setBillingMessage(msg.message ?? 'Call ended');
    }
    if (msg.type === 'partner_disconnected') {
      setBillingMessage(msg.message ?? 'Partner disconnected');
    }
  }, []);

  const {
    status: socketStatus,
    match,
    error: socketError,
    queueInfo,
    send,
    joinQueue,
    leaveQueue,
    nextPartner,
  } = useMatchmakingSocket(accessToken, { onMessage: onSocketMessage });

  const partnerUserId = match?.partner?.user_id ?? null;
  const localUserId = user?.id != null ? String(user.id) : null;

  const {
    localStream,
    remoteStream,
    callStatus,
    callError,
    isCameraEnabled,
    isMicEnabled,
    callStartedAt,
    teardown,
    endCall,
    toggleCamera,
    toggleMic,
    handleSignal,
  } = useWebRTC({
    enabled: Boolean(match?.matchId),
    matchId: match?.matchId ?? null,
    partnerUserId,
    localUserId,
    send,
  });

  signalHandlerRef.current = handleSignal;

  useEffect(() => {
    if (!accessToken) return;
    fetchCoinBalance(accessToken)
      .then((data) => setCoinBalance(data.balance))
      .catch(() => {});
  }, [accessToken]);

  useEffect(() => {
    if (socketStatus === 'connected' && !match && !joinedRef.current) {
      joinedRef.current = true;
      joinQueue();
    }
    if (socketStatus === 'queued' || socketStatus === 'matched') {
      joinedRef.current = true;
    }
    if (socketStatus === 'idle') {
      joinedRef.current = false;
    }
  }, [socketStatus, match, joinQueue]);

  useEffect(() => {
    return () => {
      leaveQueue();
    };
  }, [leaveQueue]);

  useEffect(() => {
    if (!callStartedAt || callStatus !== 'connected') return undefined;
    const interval = setInterval(() => {
      setCallDuration(Math.floor((Date.now() - callStartedAt) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [callStartedAt, callStatus]);

  const handleNext = useCallback(() => {
    teardown();
    setBillingMessage(null);
    nextPartner();
  }, [teardown, nextPartner]);

  const handleEndCall = useCallback(() => {
    endCall();
    leaveQueue();
    setBillingMessage('Call ended');
  }, [endCall, leaveQueue]);

  const handleBlock = useCallback(async () => {
    if (!partnerUserId || !accessToken) return;
    try {
      await blockUser(accessToken, partnerUserId);
      setBillingMessage('User blocked');
      handleEndCall();
    } catch (err) {
      setBillingMessage(err instanceof Error ? err.message : 'Block failed');
    }
  }, [partnerUserId, accessToken, handleEndCall]);

  const handleReport = useCallback(async () => {
    if (!partnerUserId || !accessToken) return;
    try {
      await reportUser(accessToken, {
        reported_user_id: partnerUserId,
        reason: 'inappropriate_content',
        description: 'Reported from video chat',
      });
      setBillingMessage('Report submitted');
    } catch (err) {
      setBillingMessage(err instanceof Error ? err.message : 'Report failed');
    }
  }, [partnerUserId, accessToken]);

  const localVideoStatus = mapVideoStatus(callStatus, Boolean(localStream));
  const remoteVideoStatus = mapVideoStatus(callStatus, Boolean(remoteStream));

  const participants = {
    local: user?.username ?? 'You',
    remote: match?.partner?.username ?? 'Waiting for partner…',
  };

  const statusLine = (() => {
    if (billingMessage) return billingMessage;
    if (socketError) return socketError;
    if (callError) return callError;
    if (socketStatus === 'connecting') return 'Connecting to server…';
    if (socketStatus === 'queued') {
      const size = queueInfo?.queueSize;
      return size != null ? `In queue (${size} waiting)` : 'Looking for a partner…';
    }
    if (callStatus === 'negotiating') return 'Setting up video…';
    if (callStatus === 'connected') return `Connected with ${participants.remote}`;
    if (callStatus === 'disconnected') return 'Connection interrupted…';
    if (callStatus === 'error') return 'Video connection failed';
    if (socketStatus === 'connected' && !match) return 'Ready — joining match queue…';
    return 'Preparing session…';
  })();

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-4 text-sm text-slate-300">
          <span>
            Coins:{' '}
            <strong className="text-brand-300">{coinBalance ?? '…'}</strong>
          </span>
          {callStatus === 'connected' && (
            <span>
              Timer: <strong className="text-white">{formatDuration(callDuration)}</strong>
            </span>
          )}
        </div>
      </div>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white sm:text-3xl">Video chat</h1>
          <p className="mt-1 text-slate-400">{statusLine}</p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link to="/">
            <Button variant="ghost" size="sm">
              Back home
            </Button>
          </Link>
          {match && (
            <>
              <Button variant="ghost" size="sm" onClick={toggleCamera}>
                {isCameraEnabled ? 'Camera off' : 'Camera on'}
              </Button>
              <Button variant="ghost" size="sm" onClick={toggleMic}>
                {isMicEnabled ? 'Mute' : 'Unmute'}
              </Button>
              <Button variant="ghost" size="sm" onClick={handleBlock}>
                Block
              </Button>
              <Button variant="ghost" size="sm" onClick={handleReport}>
                Report
              </Button>
              <Button variant="secondary" size="sm" onClick={handleEndCall}>
                End call
              </Button>
            </>
          )}
          <Button
            size="md"
            onClick={handleNext}
            disabled={socketStatus !== 'matched' && socketStatus !== 'queued'}
          >
            Next
          </Button>
        </div>
      </div>

      <VideoGrid
        participants={participants}
        localStatus={localVideoStatus}
        remoteStatus={remoteVideoStatus}
        localStream={localStream}
        remoteStream={remoteStream}
      />

      <p className="mt-6 text-center text-sm text-slate-500">
        {match?.matchId
          ? `100 coins ≈ 35 min · Match ${match.matchId.slice(0, 8)}…`
          : 'Allow camera and microphone when prompted.'}
      </p>
    </>
  );
}
