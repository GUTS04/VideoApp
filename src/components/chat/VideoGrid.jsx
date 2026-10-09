import VideoContainer from '../ui/VideoContainer';

export default function VideoGrid({
  participants,
  localStatus,
  remoteStatus,
  localStream = null,
  remoteStream = null,
}) {
  return (
    <div className="grid w-full gap-4 sm:gap-6 md:grid-cols-2">
      <VideoContainer
        label={participants.local}
        isLocal
        status={localStatus}
        stream={localStream}
      />
      <VideoContainer
        label={participants.remote}
        status={remoteStatus}
        stream={remoteStream}
      />
    </div>
  );
}
