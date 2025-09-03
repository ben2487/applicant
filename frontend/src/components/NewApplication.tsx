import { useState, useRef, useEffect } from 'react';
import { Play, Square, Pause, RotateCcw } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createRun, getRunEvents } from '@/lib/api';
import { Run, RunEvent } from '@/types/api';

export function NewApplication() {
  const [url, setUrl] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<Run | null>(null);
  const [logs, setLogs] = useState<RunEvent[]>([]);
  const [browserFrame] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    if (!currentRun) return;

    const pollEvents = async () => {
      try {
        const response = await getRunEvents(currentRun.id);
        setLogs(response.events);
      } catch (error) {
        console.error('Failed to fetch events:', error);
      }
    };

    const interval = setInterval(pollEvents, 1000);
    return () => clearInterval(interval);
  }, [currentRun]);

  const handleStartRun = async () => {
    if (!url.trim()) {
      alert('Please enter a URL');
      return;
    }

    try {
      setIsRunning(true);
      setLogs([]);
      
      const run = await createRun({
        initial_url: url,
        headless: false, // We want to see the browser
      });
      
      setCurrentRun(run);
      
      // In a real implementation, this would connect to WebSocket for real-time updates
      // For now, we'll simulate with polling
      
    } catch (error) {
      console.error('Failed to start run:', error);
      alert('Failed to start run');
      setIsRunning(false);
    }
  };

  const handleStopRun = () => {
    setIsRunning(false);
    setCurrentRun(null);
    // In a real implementation, this would send a stop signal to the backend
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
          <div className="flex space-x-2">
            <Input
              placeholder="https://example.com/job-posting"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isRunning}
            />
            <Button
              onClick={handleStartRun}
              disabled={isRunning || !url.trim()}
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
                  <Button variant="outline" size="sm">
                    <Pause className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm">
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg h-96 bg-gray-100 flex items-center justify-center">
                {browserFrame ? (
                  <img src={browserFrame} alt="Browser view" className="max-w-full max-h-full" />
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
                {logs.length === 0 ? (
                  <div className="text-gray-500">Waiting for logs...</div>
                ) : (
                  logs.map((event, index) => (
                    <div key={index} className="mb-1">
                      <span className="text-gray-500">[{new Date(event.ts).toLocaleTimeString()}]</span>
                      <span className={`ml-2 ${getLogLevelColor(event.level)}`}>
                        [{event.level}]
                      </span>
                      <span className="ml-2">{event.message}</span>
                    </div>
                  ))
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
