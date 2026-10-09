import { useCallback, useEffect, useRef, useState } from 'react';
import { getWebSocketUrl } from '../config/env';

/**
 * @typedef {'idle' | 'connecting' | 'connected' | 'queued' | 'matched' | 'error'} SocketStatus
 * @typedef {{ matchId: string, partner: { user_id: string, username: string, gender?: string } }} MatchInfo
 */

/**
 * Authenticated WebSocket for matchmaking + signaling transport.
 * @param {string | null} accessToken
 * @param {{ onMessage?: (msg: Record<string, unknown>) => void }} options
 */
export function useMatchmakingSocket(accessToken, { onMessage } = {}) {
  const wsRef = useRef(null);
  const socketSeqRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  const [status, setStatus] = useState(/** @type {SocketStatus} */ ('idle'));
  const [match, setMatch] = useState(/** @type {MatchInfo | null} */ (null));
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [queueInfo, setQueueInfo] = useState(null);

  onMessageRef.current = onMessage;

  const send = useCallback((payload) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] SEND_SKIPPED socket_not_open', {
        type: payload?.type,
        readyState: ws?.readyState,
      });
      return false;
    }
    console.info('[WS] SEND', { type: payload?.type });
    ws.send(JSON.stringify(payload));
    return true;
  }, []);

  const joinQueue = useCallback(() => {
    setError(null);
    send({ type: 'join_queue' });
  }, [send]);

  const leaveQueue = useCallback(() => {
    send({ type: 'leave_queue' });
    setMatch(null);
    setQueueInfo(null);
    setStatus('connected');
  }, [send]);

  const nextPartner = useCallback(() => {
    setMatch(null);
    setQueueInfo(null);
    send({ type: 'next_partner' });
  }, [send]);

  const handleServerMessage = useCallback((msg) => {
    onMessageRef.current?.(msg);

    switch (msg.type) {
      case 'connected':
      case 'presence':
        setStatus((s) => (s === 'connecting' ? 'connected' : s));
        break;
      case 'queue_joined':
        setStatus('queued');
        setQueueInfo({ position: msg.position, queueSize: msg.queue_size });
        setMatch(null);
        break;
      case 'queue_left':
        setStatus('connected');
        setQueueInfo(null);
        break;
      case 'match_found':
        setStatus('matched');
        setQueueInfo(null);
        setMatch({
          matchId: msg.match_id,
          partner: msg.partner,
        });
        break;
      case 'partner_disconnected':
        setMatch(null);
        setStatus('connected');
        setQueueInfo(null);
        break;
      case 'error':
        setError(msg.message ?? 'Unknown error');
        if (msg.code === 'not_in_match') {
          /* signaling-only */
        }
        break;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    if (!accessToken) {
      setStatus('idle');
      return undefined;
    }

    setStatus('connecting');
    setError(null);
    const socketSeq = ++socketSeqRef.current;
    const ws = new WebSocket(getWebSocketUrl(accessToken));
    wsRef.current = ws;
    console.info('[WS] CONNECTING', { socketSeq });

    ws.onopen = () => {
      if (wsRef.current !== ws) {
        console.debug('[WS] IGNORE_STALE_OPEN', { socketSeq });
        return;
      }
      console.info('[WS] OPEN', { socketSeq });
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      if (wsRef.current !== ws) {
        console.debug('[WS] IGNORE_STALE_MESSAGE', { socketSeq });
        return;
      }
      try {
        const msg = JSON.parse(event.data);
        console.info('[WS] RECEIVED', { socketSeq, type: msg?.type });
        handleServerMessage(msg);
      } catch {
        setError('Invalid message from server');
      }
    };

    ws.onerror = () => {
      if (wsRef.current !== ws) {
        console.debug('[WS] IGNORE_STALE_ERROR', { socketSeq });
        return;
      }
      console.error('[WS] ERROR', { socketSeq });
      setError('WebSocket connection error');
      setStatus('error');
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) {
        console.debug('[WS] IGNORE_STALE_CLOSE', { socketSeq });
        return;
      }
      console.info('[WS] CLOSED', { socketSeq, code: ws.code, reason: ws.reason });
      setStatus('idle');
      setMatch(null);
      wsRef.current = null;
    };

    return () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
        console.info('[WS] CLOSING_ON_CLEANUP', { socketSeq, readyState: ws.readyState });
        ws.close();
      }
    };
  }, [accessToken, handleServerMessage]);

  return {
    status,
    match,
    error,
    queueInfo,
    send,
    joinQueue,
    leaveQueue,
    nextPartner,
  };
}
