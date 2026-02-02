# Adventure Works Analytics - Frontend

A modern React-based chat interface for the Adventure Works Analytics System.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Component library
- **React Query** - Server state management
- **Plotly.js** - Interactive visualizations

## Getting Started

### Prerequisites

- Node.js 18+ (recommended: use [nvm](https://github.com/nvm-sh/nvm))
- npm or bun

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

## Project Structure

```
src/
├── components/
│   ├── chat/           # Chat interface components
│   │   ├── ChatHeader.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── PlotlyVisualization.tsx
│   │   ├── SessionSidebar.tsx
│   │   └── ToolCallDisplay.tsx
│   └── ui/             # shadcn/ui components
├── services/
│   └── api.ts          # Backend API client
├── types/
│   └── chat.ts         # TypeScript interfaces
├── pages/
│   └── Index.tsx       # Main chat page
└── App.tsx             # Root component
```

## Configuration

The frontend connects to the backend API. Configure the API URL in `src/services/api.ts` if needed.

Default: `http://localhost:8000`

## Features

- Real-time streaming responses
- Session management (create, switch, delete sessions)
- Interactive Plotly visualizations
- Code syntax highlighting
- Tool call expansion/collapse
- Responsive design
