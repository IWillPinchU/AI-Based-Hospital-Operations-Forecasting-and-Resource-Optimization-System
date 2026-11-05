"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { getWebSocketUrl } from "./api";

export type WebSocketStatus = "connected" | "connecting" | "disconnected";

interface UseTelemetryWebSocketOptions {
  onDataUpdated?: (payload: unknown) => void;
  enabled?: boolean;
}

export function useTelemetryWebSocket({
  onDataUpdated,
  enabled = true,
}: UseTelemetryWebSocketOptions = {}) {
  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const isUnmountedRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (!enabled || isUnmountedRef.current) return;

    try {
      const url = getWebSocketUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close();
          return;
        }
        setStatus("connected");
        retryCountRef.current = 0;

        // Periodic heartbeat ping to keep connection alive
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.event === "data_updated") {
            onDataUpdated?.(data);
          }
        } catch {
          // Plain text response (e.g., 'pong')
        }
      };

      ws.onclose = () => {
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        if (isUnmountedRef.current) return;

        setStatus("disconnected");
        // Exponential backoff reconnect: 1.5s, 3s, 6s, max 12s
        const backoffMs = Math.min(1500 * Math.pow(1.8, retryCountRef.current), 12000);
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connectRef.current();
        }, backoffMs);
      };

      ws.onerror = () => {
        setStatus("disconnected");
        ws.close();
      };
    } catch {
      // Socket initialization error
    }
  }, [enabled, onDataUpdated]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status };
}
