# WebBot Frontend

A React-based frontend for the WebBot job application automation system.

## Features

- **Applications Table**: View all automated job application runs with sorting and filtering
- **New Application**: Start new automation runs with URL input and live monitoring
- **Embedded Browser**: Real-time browser view during automation (planned)
- **Live Logs**: Streaming console output during runs
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Development

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React hooks
- **API**: REST API client for backend communication

## API Integration

The frontend communicates with the Flask backend running on port 8000. API calls are proxied through Vite's development server.

## Components

- `App.tsx` - Main application with navigation
- `RunTable.tsx` - Table displaying all application runs
- `NewApplication.tsx` - Form for starting new automation runs
- `ui/` - Reusable shadcn/ui components

## Future Enhancements

- WebSocket integration for real-time updates
- Embedded browser view using Playwright
- User profile management
- Advanced filtering and search
- Dark mode support
