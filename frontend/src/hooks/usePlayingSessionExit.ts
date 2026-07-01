import { useEffect, type RefObject } from "react";
import { useBlocker } from "react-router-dom";
import type { GameSession } from "../types/game";
import {
  finalizePlayingSession,
  isPlayingSession,
  sendFinalizeBeacon,
} from "../services/sessionFinalize";

type UsePlayingSessionExitOptions = {
  enabled: boolean;
  session: GameSession | null;
  skipFinalizeRef: RefObject<boolean>;
};

export function usePlayingSessionExit({
  enabled,
  session,
  skipFinalizeRef,
}: UsePlayingSessionExitOptions): void {
  const shouldGuard =
    enabled && isPlayingSession(session) && session !== null;

  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    if (!shouldGuard || skipFinalizeRef.current) {
      return false;
    }
    if (currentLocation.pathname !== "/game") {
      return false;
    }
    if (nextLocation.pathname.startsWith("/result")) {
      return false;
    }
    return currentLocation.pathname !== nextLocation.pathname;
  });

  useEffect(() => {
    if (!shouldGuard || blocker.state !== "blocked" || !session) {
      return;
    }

    let cancelled = false;

    void (async () => {
      try {
        await finalizePlayingSession(session.sessionId, "voluntary_exit");
      } finally {
        if (!cancelled) {
          blocker.proceed();
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [blocker, session, shouldGuard]);

  useEffect(() => {
    if (!shouldGuard || !session) {
      return;
    }

    const handlePageHide = () => {
      if (skipFinalizeRef.current) {
        return;
      }
      sendFinalizeBeacon(session.sessionId, "tab_closed");
    };

    window.addEventListener("pagehide", handlePageHide);
    return () => window.removeEventListener("pagehide", handlePageHide);
  }, [shouldGuard, session, skipFinalizeRef]);
}
