import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export interface WebSocketEvent {
  type: 'run_event' | 'run_status' | 'screencast_frame' | 'console_log';
  data: any;
  timestamp?: number;
}

export interface RunEvent {
  id: number;
  run_id: number;
  ts: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  category: 'BROWSER' | 'FORM' | 'NETWORK' | 'SYSTEM';
  message: string;
  code: string | null;
  data: any | null;
  created_at: string;
}

export interface RunStatus {
  run_id: number;
  status: 'IN_PROGRESS' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
  message?: string;
  timestamp: number;
}

export interface ScreencastFrame {
  run_id: number;
  frame: string; // Base64 encoded image
  timestamp: number;
}

export interface ConsoleLog {
  run_id: number;
  level: 'log' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: number;
}

export function useWebSocket(runId?: number) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [screencastFrame, setScreencastFrame] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Connect to WebSocket server
    const newSocket = io('http://localhost:8000', {
      transports: ['websocket', 'polling'],
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    newSocket.on('run_event', (data: RunEvent) => {
      console.log('Received run event:', data);
      setEvents(prev => [...prev, data]);
    });

    newSocket.on('run_status', (data: RunStatus) => {
      console.log('Received run status:', data);
      setStatus(data);
    });

    newSocket.on('screencast_frame', (data: ScreencastFrame) => {
      console.log('Received screencast frame');
      setScreencastFrame(data.frame);
    });

    newSocket.on('console_log', (data: ConsoleLog) => {
      console.log('Received console log:', data);
      setConsoleLogs(prev => [...prev, data]);
    });

    socketRef.current = newSocket;
    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  useEffect(() => {
    if (socket && runId) {
      // Join the run room
      socket.emit('join_run', { run_id: runId });
      console.log(`Joined run room: ${runId}`);

      return () => {
        // Leave the run room
        socket.emit('leave_run', { run_id: runId });
        console.log(`Left run room: ${runId}`);
      };
    }
  }, [socket, runId]);

  const sendControlCommand = (command: 'pause' | 'resume' | 'stop') => {
    if (socket && runId) {
      socket.emit('control_run', { run_id: runId, command });
    }
  };

  const clearEvents = () => {
    setEvents([]);
    setConsoleLogs([]);
  };

  return {
    socket,
    isConnected,
    events,
    status,
    screencastFrame,
    consoleLogs,
    sendControlCommand,
    clearEvents,
  };
}
