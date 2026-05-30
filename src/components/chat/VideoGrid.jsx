import VideoContainer from '../ui/VideoContainer';

export default function VideoGrid({ participants, localStatus, remoteStatus }) {
  return (
    <div className="grid w-full gap-4 sm:gap-6 md:grid-cols-2">
      <VideoContainer
        label={participants.local}
        isLocal
        status={localStatus}
      />
      <VideoContainer
        label={participants.remote}
        status={remoteStatus}
      />
    </div>
  );
}
