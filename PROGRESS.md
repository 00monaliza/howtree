# Tree Detection Platform — Progress

## Completed Tasks

### [1/7] Next.js init + shadcn setup + folder structure ✅
- Next.js 16.2.6 (Turbopack) with TypeScript + Tailwind
- shadcn/ui components: button, card, badge, separator, progress, skeleton, table, tabs, select, scroll-area, tooltip
- Dependencies: mapbox-gl, @mapbox/mapbox-gl-draw, recharts, zustand, @tanstack/react-query, @turf/turf, @react-pdf/renderer
- Dark navy palette (#0f1923) with accent green (#22c55e) configured in globals.css
- Folder structure: app/{dashboard,analytics,reports}, components/{map,panels,charts,layout,reports}, lib/{api,hooks,store}, types

### [2/7] MapContainer with Mapbox satellite + bbox draw tool ✅
- components/map/MapContainer.tsx — Mapbox satellite-streets-v12 style
- MapboxDraw rectangle selection → bbox stored in Zustand
- Module-level map registry for external GeoJSON updates

### [3/7] AnalysisPanel + API integration + WebSocket progress ✅
- components/panels/AnalysisPanel.tsx
- POST /analyze → job_id → WebSocket /ws/jobs/{job_id}
- Live progress bar with streaming messages
- Results: tree count, density, canopy coverage

### [4/7] Tree points GeoJSON layer + heatmap toggle ✅
- Circle layer: color-coded by confidence score (green=high, red=low)
- Heatmap layer with confidence-weighted density
- Layer toggle panel (components/panels/LayerToggle.tsx)

### [5/7] /analytics page with Recharts ✅
- District bar chart (DistrictBarChart)
- Density over time line chart (DensityLineChart)
- Top-10 zones sortable table
- CSV export button

### [6/7] PDF report generation ✅
- @react-pdf/renderer government-format document
- Executive summary, satellite map placeholder, sub-zone table, confidence distribution bar
- Dynamic import (ssr: false) to avoid SSR issues with browser-only PDF APIs

### [7/7] Mobile responsive + dark mode polish ✅
- Collapsible sidebar on mobile (translate-x slide-in)
- Backdrop overlay when sidebar open
- Dark mode locked via `dark` class on `<html>`

## Next Steps
- [ ] Deploy to Vercel (Task 10)
- [ ] Add Mapbox token to Vercel environment variables
- [ ] Wire real backend at http://localhost:8000
- [ ] Replace mock data in /analytics and /reports with live API calls

## Config Required
Set `NEXT_PUBLIC_MAPBOX_TOKEN` in `.env.local`
