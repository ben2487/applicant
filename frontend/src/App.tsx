import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Plus, User } from 'lucide-react';

import { RunTable } from '@/components/RunTable';
import { NewApplication } from '@/components/NewApplication';

function App() {
  const [activeTab, setActiveTab] = useState('applications');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                WebBot - Job Application Automation
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveTab('new')}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Application
              </Button>
              <Button variant="outline" size="sm">
                <User className="h-4 w-4 mr-2" />
                Profile
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="applications">Applications</TabsTrigger>
            <TabsTrigger value="new">New Application</TabsTrigger>
          </TabsList>

          <TabsContent value="applications" className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Applications</h2>
                <p className="text-gray-600">View and manage your automated job applications</p>
              </div>
              <Button
                onClick={() => setActiveTab('new')}
                className="flex items-center"
              >
                <Plus className="h-4 w-4 mr-2" />
                New Application
              </Button>
            </div>
            <RunTable />
          </TabsContent>

          <TabsContent value="new" className="space-y-6">
            <NewApplication />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;
