# Review Pro Frontend

Modern React frontend for the Review Pro security analysis platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **TanStack Query** - Data fetching and state management
- **React Router** - Client-side routing
- **Recharts** - Data visualization
- **Lucide React** - Icon library
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env
```

### Development

```bash
# Start dev server (http://localhost:3000)
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/       # Reusable UI components
│   ├── ui/          # Base UI components (Card, Button, Badge, etc.)
│   └── Layout.tsx   # App layout with navigation
├── pages/           # Page components
│   ├── Dashboard.tsx
│   ├── Scans.tsx
│   ├── ScanDetail.tsx
│   ├── Findings.tsx
│   ├── FindingDetail.tsx
│   ├── Clusters.tsx
│   ├── ClusterDetail.tsx
│   └── Patterns.tsx
├── services/        # API client and services
│   └── api.ts
├── hooks/           # Custom React hooks
│   └── useApi.ts    # TanStack Query hooks
├── types/           # TypeScript type definitions
│   └── index.ts
├── App.tsx          # Root component with routing
├── main.tsx         # Application entry point
└── index.css        # Global styles
```

## Features

### Dashboard
- Overview statistics (total scans, findings, etc.)
- Recent scans list
- Findings by severity and tool charts
- Top vulnerabilities

### Scans
- List all security scans with filtering
- Detailed scan view with findings breakdown
- Trigger re-scans, LLM adjudication, and clustering

### Findings
- Browse and filter security findings
- Detailed finding view with code snippets
- LLM verdict analysis
- Update finding status

### Clusters
- View semantically similar findings grouped together
- Distance to centroid visualization
- Cluster statistics and quality metrics

### Pattern Comparison
- Compare three LLM agent patterns:
  - Post-Processing Filter (fast, cheap)
  - Interactive Retrieval (balanced)
  - Multi-Agent Collaboration (thorough, expensive)
- Performance metrics and cost analysis
- Visual comparison charts

## API Integration

The frontend communicates with the Django backend through a REST API:

- Base URL: `/api` (proxied through Vite dev server)
- All endpoints return JSON
- Uses TanStack Query for caching and optimistic updates

## Environment Variables

- `VITE_API_BASE_URL` - Backend API base URL (default: `/api`)

## Development Notes

- All API calls are type-safe using TypeScript interfaces
- TanStack Query handles caching, refetching, and loading states
- Responsive design works on desktop and mobile
- Charts are interactive using Recharts library
