import { useState, useRef, useEffect } from 'react';
import { Play, Square, Pause, RotateCcw } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createRun } from '@/lib/api';
import { Run } from '@/types/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useBackendHealth } from '@/hooks/useBackendHealth';
import { useToaster } from '@/components/ui/toaster';

interface NewApplicationProps {
  onRunStatusChange?: () => void;
}

export function NewApplication({ onRunStatusChange }: NewApplicationProps = {}) {
  const [url, setUrl] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRunState] = useState<Run | null>(null);
  
  // Custom setter with comprehensive logging
  const setCurrentRun = (newRun: Run | null, reason: string) => {
    console.log('🔧 [DEBUG] setCurrentRun called:', {
      reason,
      oldRun: currentRun ? { id: currentRun.id, status: currentRun.result_status } : null,
      newRun: newRun ? { id: newRun.id, status: newRun.result_status } : null,
      timestamp: new Date().toISOString()
    });
    setCurrentRunState(newRun);
  };
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { addToast } = useToaster();
  const { isHealthy, isChecking } = useBackendHealth();
  
  // WebSocket integration
  const {
    isConnected,
    events,
    screencastFrame,
    consoleLogs,
    runError,
    sendControlCommand,
    clearEvents,
  } = useWebSocket(currentRun?.id);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Track component mount and initial state
  useEffect(() => {
    console.log('🔧 [DEBUG] NewApplication component mounted with initial state:', {
      currentRun: currentRun ? { id: currentRun.id, status: currentRun.result_status } : null,
      isRunning,
      isConnected,
      isHealthy,
      isChecking
    });
  }, []); // Empty dependency array - only run on mount

  useEffect(() => {
    console.log('🔧 [DEBUG] Events or consoleLogs changed:', { eventsCount: events.length, consoleLogsCount: consoleLogs.length });
    scrollToBottom();
  }, [events, consoleLogs]);

  // Track screencast frame changes
  useEffect(() => {
    console.log('🔧 [DEBUG] Screencast frame changed:', { length: screencastFrame?.length || 0 });
  }, [screencastFrame]);

  // Track currentRun changes
  useEffect(() => {
    console.log('🔧 [DEBUG] currentRun changed:', currentRun ? { id: currentRun.id, status: currentRun.result_status } : null);
    console.log('🔧 [DEBUG] Current state summary:', {
      currentRun: currentRun ? { id: currentRun.id, status: currentRun.result_status } : null,
      isRunning,
      isConnected,
      eventsCount: events.length,
      consoleLogsCount: consoleLogs.length,
      screencastFrameLength: screencastFrame?.length || 0,
      runError: runError ? { status: runError.status, error: runError.error } : null
    });
  }, [currentRun, isRunning, isConnected, events.length, consoleLogs.length, screencastFrame?.length, runError]);

  // Track isRunning changes
  useEffect(() => {
    console.log('🔧 [DEBUG] isRunning changed:', isRunning);
  }, [isRunning]);

  // Track WebSocket connection status
  useEffect(() => {
    console.log('🔧 [DEBUG] WebSocket connection status changed:', { isConnected, isHealthy });
  }, [isConnected, isHealthy]);

  // Handle run errors from WebSocket
  useEffect(() => {
    if (runError) {
      console.error('❌ Run error received:', runError);
      const errorMessage = runError.error?.error || runError.error || 'An error occurred during automation';
      
      // Only clear events and stop if this is an actual error, not just termination
      if (runError.status !== 'TERMINATED') {
        addToast({
          title: 'Automation Error',
          description: errorMessage,
          variant: 'destructive',
          duration: 10000,
        });
        addToast({
          title: 'Run Status',
          description: 'The automation run has been marked as failed and stopped.',
          variant: 'warning',
          duration: 8000,
        });
        clearEvents();
        setIsRunning(false);
        setCurrentRun(null, 'runError: actual error occurred');
        
        // Notify parent component that run status changed
        onRunStatusChange?.();
      } else {
        // For termination, show different toasts
        addToast({
          title: 'Run Terminated',
          description: 'The browser automation was terminated (likely by closing the browser window).',
          variant: 'warning',
          duration: 8000,
        });
        addToast({
          title: 'Run Status',
          description: 'The run has been marked as terminated in the database.',
          variant: 'default',
          duration: 6000,
        });
        // For termination, just clear the error state but keep the run info
        console.log('🔧 [DEBUG] Setting isRunning to false and currentRun to null (termination)');
        setIsRunning(false);
        setCurrentRun(null, 'runError: run was terminated by user');
        
        // Notify parent component that run status changed
        onRunStatusChange?.();
      }
    }
  }, [runError, addToast, clearEvents]);

  const handleStartRun = async () => {
    if (!url.trim()) {
      addToast({
        title: 'Invalid Input',
        description: 'Please enter a URL',
        variant: 'warning',
      });
      return;
    }

    console.log('🚀 Starting new run with URL:', url);
    try {
      console.log('🔧 [DEBUG] Setting isRunning to true');
      setIsRunning(true);
      console.log('🔧 [DEBUG] Clearing events');
      clearEvents();
      
      console.log('📡 Creating run via API...');
      console.log('🔧 [DEBUG] API call parameters:', { initial_url: url, headless: false });
      console.log('🔧 [DEBUG] About to call createRun API...');
      const run = await createRun({
        initial_url: url,
        headless: false, // We want to see the browser
      });
      console.log('🔧 [DEBUG] createRun API call completed, result:', run);
      console.log('✅ Run created successfully:', run);
      console.log('🔧 [DEBUG] Run object details:', {
        id: run?.id,
        initial_url: run?.initial_url,
        result_status: run?.result_status,
        started_at: run?.started_at,
        runType: typeof run,
        runKeys: run ? Object.keys(run) : 'null'
      });
      console.log('🔧 [DEBUG] Setting currentRun to:', run);
      setCurrentRun(run, 'handleStartRun: new run created successfully');
      
      addToast({
        title: 'Run Started',
        description: `Successfully started automation for ${url}`,
        variant: 'success',
      });
      
      // Notify parent component that run status changed
      onRunStatusChange?.();
      
    } catch (error) {
      console.error('❌ Failed to start run:', error);
      console.log('🔧 [DEBUG] Error details:', {
        errorType: typeof error,
        errorMessage: error instanceof Error ? error.message : 'Unknown error',
        errorStack: error instanceof Error ? error.stack : 'No stack trace',
        errorName: error instanceof Error ? error.name : 'Unknown error type'
      });
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Show multiple toasts for different error scenarios
      if (errorMessage.includes('CONNECTION_ERROR')) {
        addToast({
          title: 'Backend Connection Error',
          description: 'Unable to connect to the backend server. Please check if the server is running.',
          variant: 'destructive',
          duration: 10000,
        });
        addToast({
          title: 'Troubleshooting',
          description: 'Make sure the backend server is running on port 8000 and try again.',
          variant: 'warning',
          duration: 8000,
        });
      } else if (errorMessage.includes('Failed to start automation')) {
        addToast({
          title: 'Automation Startup Failed',
          description: 'The browser automation could not be started. This may be due to browser or system issues.',
          variant: 'destructive',
          duration: 8000,
        });
        addToast({
          title: 'Browser Issue',
          description: 'Try restarting the application or check if Chrome/Chromium is properly installed.',
          variant: 'warning',
          duration: 6000,
        });
      } else if (errorMessage.includes('Invalid URL')) {
        addToast({
          title: 'Invalid URL',
          description: 'The provided URL is not valid. Please check the format and try again.',
          variant: 'warning',
          duration: 6000,
        });
      } else {
        addToast({
          title: 'Failed to Start Run',
          description: errorMessage,
          variant: 'destructive',
          duration: 8000,
        });
        addToast({
          title: 'Error Details',
          description: 'Check the console for more detailed error information.',
          variant: 'warning',
          duration: 6000,
        });
      }
      
      console.log('🔧 [DEBUG] Setting isRunning to false due to error');
      setIsRunning(false);
      
      // Notify parent component that run status changed (even on error)
      onRunStatusChange?.();
    }
  };

  const handleStopRun = () => {
    if (currentRun) {
      sendControlCommand('stop');
    }
    console.log('🔧 [DEBUG] Setting isRunning to false and currentRun to null (stop)');
    setIsRunning(false);
    setCurrentRun(null, 'handleStopRun: user clicked stop button');
  };

  const handlePauseRun = () => {
    if (currentRun) {
      sendControlCommand('pause');
    }
  };

  const handleResumeRun = () => {
    if (currentRun) {
      sendControlCommand('resume');
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-600';
      case 'WARNING': return 'text-yellow-600';
      case 'INFO': return 'text-blue-600';
      case 'DEBUG': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>New Application</CardTitle>
          <CardDescription>
            Enter a job posting URL to start the automated application process
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex space-x-2 flex-1">
              <Input
                placeholder="https://example.com/job-posting"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isRunning}
              />
              <Button
                onClick={handleStartRun}
                disabled={isRunning || !url.trim() || !isHealthy}
                className="min-w-[100px]"
              >
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
              {isRunning && (
                <Button
                  variant="outline"
                  onClick={handleStopRun}
                  className="min-w-[100px]"
                >
                  <Square className="h-4 w-4 mr-2" />
                  Stop
                </Button>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  isHealthy === null ? 'bg-yellow-500' : 
                  isHealthy ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span className="text-sm text-gray-600">
                  {isChecking ? 'Checking Backend...' : 
                   isHealthy ? 'Backend Online' : 'Backend Offline'}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">
                  {isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {isRunning && currentRun && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Embedded Browser */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Browser View
                <div className="flex space-x-2">
                  <Button variant="outline" size="sm" onClick={handlePauseRun}>
                    <Pause className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleResumeRun}>
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg h-96 bg-gray-100 flex items-center justify-center">
                {screencastFrame ? (
                  <img src={`data:image/png;base64,${screencastFrame}`} alt="Browser view" className="max-w-full max-h-full" />
                ) : (
                  <div className="text-gray-500">
                    Browser view will appear here when the automation starts
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Live Logs */}
          <Card>
            <CardHeader>
              <CardTitle>Live Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96 overflow-y-auto bg-black text-green-400 p-4 font-mono text-sm rounded">
                {events.length === 0 && consoleLogs.length === 0 ? (
                  <div className="text-gray-500">Waiting for logs...</div>
                ) : (
                  <>
                    {events.map((event, index) => (
                      <div key={`event-${index}`} className="mb-1">
                        <span className="text-gray-500">[{new Date(event.ts).toLocaleTimeString()}]</span>
                        <span className={`ml-2 ${getLogLevelColor(event.level)}`}>
                          [{event.level}]
                        </span>
                        <span className="ml-2">{event.message}</span>
                      </div>
                    ))}
                    {consoleLogs.map((log, index) => (
                      <div key={`console-${index}`} className="mb-1">
                        <span className="text-gray-500">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                        <span className={`ml-2 ${getLogLevelColor(log.level.toUpperCase())}`}>
                          [{log.level.toUpperCase()}]
                        </span>
                        <span className="ml-2">{log.message}</span>
                      </div>
                    ))}
                  </>
                )}
                <div ref={logsEndRef} />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {currentRun && (
        <Card>
          <CardHeader>
            <CardTitle>Run Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Run ID:</span> {currentRun.id}
              </div>
              <div>
                <span className="font-medium">Status:</span> {currentRun.result_status}
              </div>
              <div>
                <span className="font-medium">Started:</span> {new Date(currentRun.started_at).toLocaleString()}
              </div>
              <div>
                <span className="font-medium">URL:</span> {currentRun.initial_url}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* DEBUG BLOCK */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>🔍 Debug State</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-gray-100 text-gray-900 p-4 rounded overflow-auto" style={{ color: '#111827' }}>
            {JSON.stringify({
              url,
              isRunning,
              currentRun: currentRun ? {
                id: currentRun.id,
                status: currentRun.result_status,
                url: currentRun.initial_url
              } : null,
              isConnected,
              eventsCount: events.length,
              consoleLogsCount: consoleLogs.length,
              screencastFrameLength: screencastFrame?.length || 0,
              runError: runError ? {
                error: runError.error,
                status: runError.status
              } : null,
              isHealthy,
              isChecking
            }, null, 2)}
          </pre>
        </CardContent>
      </Card>
      
    </div>
  );
}
