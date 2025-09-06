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
  const [runError, setRunError] = useState<any>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    console.log('🔌 Initializing WebSocket connection...');
    // Connect to WebSocket server
    const newSocket = io('http://localhost:8000', {
      transports: ['websocket', 'polling'],
      timeout: 5000,
      forceNew: true,
    });

    newSocket.on('connect', () => {
      console.log('✅ WebSocket connected successfully');
      setIsConnected(true);
    });

    newSocket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason);
      setIsConnected(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('❌ WebSocket connection error:', error);
      setIsConnected(false);
    });

    newSocket.on('run_event', (data: RunEvent) => {
      console.log('📝 Received run event:', data);
      setEvents(prev => [...prev, data]);
    });

    newSocket.on('run_status', (data: RunStatus) => {
      console.log('📊 Received run status:', data);
      setStatus(data);
    });

    newSocket.on('screencast_frame', (data: ScreencastFrame) => {
      console.log('🖼️ [VERBOSE] Received screencast frame, size:', data.frame?.length || 0);
      console.log('🖼️ [VERBOSE] Screencast frame data:', {
        run_id: data.run_id,
        timestamp: data.timestamp,
        frameLength: data.frame?.length || 0
      });
      setScreencastFrame(data.frame);
      console.log('✅ [VERBOSE] Screencast frame state updated');
    });

    newSocket.on('console_log', (data: ConsoleLog) => {
      console.log('💬 Received console log:', data);
      setConsoleLogs(prev => [...prev, data]);
    });

    newSocket.on('control_acknowledged', (data) => {
      console.log('✅ Control command acknowledged:', data);
    });

    newSocket.on('error', (error) => {
      console.error('❌ WebSocket error:', error);
    });

    newSocket.on('run_error', (data) => {
      console.error('❌ Run error received:', data);
      setRunError(data);
    });

    socketRef.current = newSocket;
    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  useEffect(() => {
    if (socket && runId) {
      console.log(`🚪 [VERBOSE] Joining run room: ${runId}`);
      console.log(`🔍 [VERBOSE] Socket connection state:`, socket.connected);
      // Join the run room
      socket.emit('join_run', { run_id: runId });
      console.log(`✅ [VERBOSE] Join run request sent for run ${runId}`);

      return () => {
        console.log(`🚪 [VERBOSE] Leaving run room: ${runId}`);
        // Leave the run room
        socket.emit('leave_run', { run_id: runId });
        console.log(`✅ [VERBOSE] Leave run request sent for run ${runId}`);
      };
    }
  }, [socket, runId]);

  const sendControlCommand = (command: 'pause' | 'resume' | 'stop') => {
    if (socket && runId) {
      console.log(`🎮 Sending control command: ${command} for run ${runId}`);
      socket.emit('control_run', { run_id: runId, command });
    } else {
      console.warn('⚠️ Cannot send control command: socket or runId not available');
    }
  };

  const clearEvents = () => {
    setEvents([]);
    setConsoleLogs([]);
    setRunError(null);
  };

  return {
    socket,
    isConnected,
    events,
    status,
    screencastFrame,
    consoleLogs,
    runError,
    sendControlCommand,
    clearEvents,
  };
}
