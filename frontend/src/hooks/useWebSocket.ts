import { useEffect, useRef, useState, useCallback } from "react";

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error"
  | "taken_over";

interface WebSocketState {
  status: ConnectionStatus;
  sessionId: string | null;
  lastMessage: Record<string, unknown> | null;
}

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

function getBackoffDelay(attempt: number): number {
  const exponential = Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
  const jitter = Math.random() * 1000;
  return exponential + jitter;
}

export function useWebSocket() {
  const [state, setState] = useState<WebSocketState>({
    status: "connecting",
    sessionId: null,
    lastMessage: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const takenOverRef = useRef(false);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current || takenOverRef.current) return;

    // Build WebSocket URL: use relative /ws path (Vite proxy handles routing)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    setState((prev) => ({
      ...prev,
      status: retryCountRef.current > 0 ? "reconnecting" : "connecting",
    }));

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      retryCountRef.current = 0;
      setState((prev) => ({ ...prev, status: "connected" }));
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;

      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "connected":
            setState((prev) => ({
              ...prev,
              status: "connected",
              sessionId: data.session_id ?? prev.sessionId,
            }));
            break;

          case "ping":
            ws.send(JSON.stringify({ type: "pong" }));
            break;

          case "session_takeover":
            takenOverRef.current = true;
            setState((prev) => ({
              ...prev,
              status: "taken_over",
              lastMessage: data,
            }));
            break;

          case "idle_warning":
            setState((prev) => ({ ...prev, lastMessage: data }));
            break;

          case "session_expired":
            setState((prev) => ({
              ...prev,
              status: "disconnected",
              lastMessage: data,
            }));
            break;

          default:
            setState((prev) => ({ ...prev, lastMessage: data }));
            break;
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      wsRef.current = null;

      // Code 4000 = session takeover -- do NOT reconnect
      if (event.code === 4000) {
        takenOverRef.current = true;
        setState((prev) => ({ ...prev, status: "taken_over" }));
        return;
      }

      // Don't reconnect if taken over via message
      if (takenOverRef.current) return;

      // Attempt reconnect with exponential backoff
      if (retryCountRef.current < MAX_RETRIES) {
        const delay = getBackoffDelay(retryCountRef.current);
        setState((prev) => ({ ...prev, status: "reconnecting" }));
        retryCountRef.current++;

        retryTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current && !takenOverRef.current) {
            connect();
          }
        }, delay);
      } else {
        setState((prev) => ({ ...prev, status: "error" }));
      }
    };

    ws.onerror = () => {
      // Close the socket -- onclose will handle reconnect logic
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, []);

  const retry = useCallback(() => {
    takenOverRef.current = false;
    retryCountRef.current = 0;
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    status: state.status,
    sessionId: state.sessionId,
    lastMessage: state.lastMessage,
    retry,
    retryCount: retryCountRef.current,
  };
}
