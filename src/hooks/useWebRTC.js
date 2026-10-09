import { useCallback, useEffect, useRef, useState } from 'react';
import { getIceServers } from '../config/ice';

/**
 * @typedef {'idle' | 'starting' | 'negotiating' | 'connected' | 'ended' | 'error' | 'disconnected'} CallStatus
 */

/**
 * @param {{
 *   enabled: boolean,
 *   matchId: string | null,
 *   partnerUserId: string | null,
 *   localUserId: string | null,
 *   send: (payload: Record<string, unknown>) => boolean,
 * }} options
 */
export function useWebRTC({ enabled, matchId, partnerUserId, localUserId, send }) {
  const pcRef = useRef(/** @type {RTCPeerConnection | null} */ (null));
  const localStreamRef = useRef(/** @type {MediaStream | null} */ (null));
  const pendingCandidatesRef = useRef(/** @type {RTCIceCandidateInit[]} */ ([]));
  const makingOfferRef = useRef(false);
  const connectedNotifiedRef = useRef(false);
  const sessionMatchIdRef = useRef(/** @type {string | null} */ (null));
  const iceServersRef = useRef(/** @type {RTCIceServer[] | null} */ (null));

  const [localStream, setLocalStream] = useState(/** @type {MediaStream | null} */ (null));
  const [remoteStream, setRemoteStream] = useState(/** @type {MediaStream | null} */ (null));
  const [callStatus, setCallStatus] = useState(/** @type {CallStatus} */ ('idle'));
  const [callError, setCallError] = useState(/** @type {string | null} */ (null));
  const [isCameraEnabled, setIsCameraEnabled] = useState(true);
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [callStartedAt, setCallStartedAt] = useState(/** @type {number | null} */ (null));

  const isOfferer =
    Boolean(localUserId && partnerUserId) && String(localUserId) < String(partnerUserId);

  useEffect(() => {
    getIceServers().then((servers) => {
      iceServersRef.current = servers;
    });
  }, []);

  const flushPendingCandidates = useCallback(async (pc) => {
    const pending = pendingCandidatesRef.current;
    pendingCandidatesRef.current = [];
    for (const init of pending) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(init));
      } catch (err) {
        console.warn('ICE candidate error', err);
      }
    }
  }, []);

  const sendIceCandidate = useCallback(
    (candidate) => {
      if (!candidate?.candidate) return;
      send({
        type: 'ice_candidate',
        match_id: matchId ?? undefined,
        candidate: {
          candidate: candidate.candidate,
          sdpMid: candidate.sdpMid,
          sdpMLineIndex: candidate.sdpMLineIndex,
        },
      });
    },
    [matchId, send],
  );

  const notifyCallEnded = useCallback(() => {
    const mid = sessionMatchIdRef.current;
    if (mid && connectedNotifiedRef.current) {
      send({ type: 'call_ended', match_id: mid });
    }
    connectedNotifiedRef.current = false;
    sessionMatchIdRef.current = null;
  }, [send]);

  const teardown = useCallback(() => {
    notifyCallEnded();
    makingOfferRef.current = false;
    pendingCandidatesRef.current = [];

    if (pcRef.current) {
      pcRef.current.onicecandidate = null;
      pcRef.current.ontrack = null;
      pcRef.current.onconnectionstatechange = null;
      pcRef.current.close();
      pcRef.current = null;
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }

    setLocalStream(null);
    setRemoteStream(null);
    setCallStartedAt(null);
    setIsCameraEnabled(true);
    setIsMicEnabled(true);
    setCallStatus('ended');
  }, [notifyCallEnded]);

  const createPeerConnection = useCallback(
    (stream) => {
      const iceServers = iceServersRef.current ?? [{ urls: 'stun:stun.l.google.com:19302' }];
      const pc = new RTCPeerConnection({ iceServers });
      pcRef.current = pc;

      stream.getTracks().forEach((track) => {
        pc.addTrack(track, stream);
      });

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          sendIceCandidate(event.candidate);
        }
      };

      pc.ontrack = (event) => {
        const [remote] = event.streams;
        if (remote) {
          setRemoteStream(remote);
        }
      };

      pc.onconnectionstatechange = () => {
        const state = pc.connectionState;
        if (state === 'connected') {
          setCallStatus('connected');
          setCallStartedAt(Date.now());
          if (!connectedNotifiedRef.current && matchId) {
            connectedNotifiedRef.current = true;
            send({ type: 'call_connected', match_id: matchId });
          }
        } else if (state === 'failed') {
          setCallError('Connection failed');
          setCallStatus('error');
        } else if (state === 'disconnected') {
          setCallStatus('disconnected');
        } else if (state === 'closed') {
          setCallStatus('ended');
        }
      };

      return pc;
    },
    [matchId, send, sendIceCandidate],
  );

  const startCall = useCallback(async () => {
    if (!enabled || !matchId || !partnerUserId) return;
    if (pcRef.current) return;

    sessionMatchIdRef.current = matchId;
    setCallError(null);
    setCallStatus('starting');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: true,
      });
      localStreamRef.current = stream;
      setLocalStream(stream);

      const pc = createPeerConnection(stream);

      if (isOfferer) {
        setCallStatus('negotiating');
        makingOfferRef.current = true;
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        send({
          type: 'webrtc_offer',
          match_id: matchId,
          sdp: { type: offer.type, sdp: offer.sdp },
        });
        makingOfferRef.current = false;
      } else {
        setCallStatus('negotiating');
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Could not access camera or microphone';
      setCallError(message);
      setCallStatus('error');
      teardown();
    }
  }, [enabled, matchId, partnerUserId, isOfferer, createPeerConnection, send, teardown]);

  const handleSignal = useCallback(
    async (msg) => {
      const pc = pcRef.current;
      if (!pc || !matchId) return;
      if (msg.match_id && msg.match_id !== matchId) return;

      try {
        if (msg.type === 'webrtc_offer' && msg.sdp) {
          await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
          await flushPendingCandidates(pc);
          if (!isOfferer) {
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            send({
              type: 'webrtc_answer',
              match_id: matchId,
              sdp: { type: answer.type, sdp: answer.sdp },
            });
          }
        } else if (msg.type === 'webrtc_answer' && msg.sdp) {
          if (makingOfferRef.current) return;
          await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
          await flushPendingCandidates(pc);
        } else if (msg.type === 'ice_candidate' && msg.candidate) {
          const init = {
            candidate: msg.candidate.candidate,
            sdpMid: msg.candidate.sdpMid ?? msg.candidate.sdp_mid ?? null,
            sdpMLineIndex:
              msg.candidate.sdpMLineIndex ?? msg.candidate.sdp_m_line_index ?? null,
          };
          if (!pc.remoteDescription) {
            pendingCandidatesRef.current.push(init);
          } else {
            await pc.addIceCandidate(new RTCIceCandidate(init));
          }
        }
      } catch (err) {
        console.error('Signaling handler error', err);
        setCallError(err instanceof Error ? err.message : 'Signaling failed');
        setCallStatus('error');
      }
    },
    [matchId, isOfferer, send, flushPendingCandidates],
  );

  const toggleCamera = useCallback(() => {
    const stream = localStreamRef.current;
    if (!stream) return;
    stream.getVideoTracks().forEach((track) => {
      track.enabled = !track.enabled;
      setIsCameraEnabled(track.enabled);
    });
  }, []);

  const toggleMic = useCallback(() => {
    const stream = localStreamRef.current;
    if (!stream) return;
    stream.getAudioTracks().forEach((track) => {
      track.enabled = !track.enabled;
      setIsMicEnabled(track.enabled);
    });
  }, []);

  const endCall = useCallback(() => {
    teardown();
  }, [teardown]);

  useEffect(() => {
    if (!enabled || !matchId || !partnerUserId) {
      teardown();
      if (!enabled) {
        setCallStatus('idle');
      }
      return undefined;
    }

    let cancelled = false;
    (async () => {
      await startCall();
      if (cancelled) {
        teardown();
      }
    })();

    const onPageHide = () => {
      if (sessionMatchIdRef.current) {
        send({ type: 'call_ended', match_id: sessionMatchIdRef.current });
      }
    };
    window.addEventListener('pagehide', onPageHide);

    return () => {
      cancelled = true;
      window.removeEventListener('pagehide', onPageHide);
      teardown();
    };
  }, [enabled, matchId, partnerUserId, startCall, teardown, send]);

  return {
    localStream,
    remoteStream,
    callStatus,
    callError,
    isOfferer,
    isCameraEnabled,
    isMicEnabled,
    callStartedAt,
    startCall,
    teardown,
    endCall,
    toggleCamera,
    toggleMic,
    handleSignal,
  };
}
