import { useState } from 'react';
import ChatAuthPanel from '../components/chat/ChatAuthPanel';
import VideoChat from '../components/chat/VideoChat';
import Button from '../components/ui/Button';
import { logoutUser } from '../api/auth';
import { clearAuth, getAccessToken, getRefreshToken, getStoredUser } from '../utils/authStorage';

export default function ChatPage() {
  const [accessToken, setAccessToken] = useState(() => getAccessToken());
  const [user, setUser] = useState(() => getStoredUser());

  const handleAuthenticated = ({ accessToken: token, user: nextUser }) => {
    setAccessToken(token);
    setUser(nextUser);
  };

  const handleSignOut = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await logoutUser(refreshToken);
      } catch {
        /* ignore logout errors */
      }
    }
    clearAuth();
    setAccessToken(null);
    setUser(null);
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 sm:px-6 lg:px-8">
      {!accessToken ? (
        <ChatAuthPanel onAuthenticated={handleAuthenticated} />
      ) : (
        <>
          <div className="mb-4 flex justify-end">
            <Button variant="ghost" size="sm" onClick={handleSignOut}>
              Sign out ({user?.username})
            </Button>
          </div>
          <VideoChat accessToken={accessToken} user={user} />
        </>
      )}
    </div>
  );
}
