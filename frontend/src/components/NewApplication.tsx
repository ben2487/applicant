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

export function NewApplication() {
  const [url, setUrl] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<Run | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { addToast } = useToaster();
  const { isHealthy, isChecking } = useBackendHealth();
  
  // WebSocket integration
  const {
    isConnected,
    events,
    screencastFrame,
    consoleLogs,
    sendControlCommand,
    clearEvents,
  } = useWebSocket(currentRun?.id);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [events, consoleLogs]);

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
      setIsRunning(true);
      clearEvents();
      
      console.log('📡 Creating run via API...');
      const run = await createRun({
        initial_url: url,
        headless: false, // We want to see the browser
      });
      
      console.log('✅ Run created successfully:', run);
      setCurrentRun(run);
      
      addToast({
        title: 'Run Started',
        description: `Successfully started automation for ${url}`,
        variant: 'success',
      });
      
    } catch (error) {
      console.error('❌ Failed to start run:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      if (errorMessage.includes('CONNECTION_ERROR')) {
        addToast({
          title: 'Backend Connection Error',
          description: 'Unable to connect to the backend server. Please check if the server is running.',
          variant: 'destructive',
          duration: 10000,
        });
      } else {
        addToast({
          title: 'Failed to Start Run',
          description: errorMessage,
          variant: 'destructive',
        });
      }
      
      setIsRunning(false);
    }
  };

  const handleStopRun = () => {
    if (currentRun) {
      sendControlCommand('stop');
    }
    setIsRunning(false);
    setCurrentRun(null);
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
    </div>
  );
}
