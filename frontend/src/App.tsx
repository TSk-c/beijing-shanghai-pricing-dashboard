import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';
import { Layout } from './components/Layout';

const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })));
const DataPanoramaPage = lazy(() => import('./pages/DataPanoramaPage').then((m) => ({ default: m.DataPanoramaPage })));
const PriceDistributionPage = lazy(() => import('./pages/PriceDistributionPage').then((m) => ({ default: m.PriceDistributionPage })));
const AdvanceBookingPage = lazy(() => import('./pages/AdvanceBookingPage').then((m) => ({ default: m.AdvanceBookingPage })));
const AirlineHeatmapPage = lazy(() => import('./pages/AirlineHeatmapPage').then((m) => ({ default: m.AirlineHeatmapPage })));
const RpaAnalysisPage = lazy(() => import('./pages/RpaAnalysisPage').then((m) => ({ default: m.RpaAnalysisPage })));
const AirHsrComparisonPage = lazy(() => import('./pages/AirHsrComparisonPage').then((m) => ({ default: m.AirHsrComparisonPage })));
const HolidayExpoPage = lazy(() => import('./pages/HolidayExpoPage').then((m) => ({ default: m.HolidayExpoPage })));
const ModelComparisonPage = lazy(() => import('./pages/ModelComparisonPage').then((m) => ({ default: m.ModelComparisonPage })));
const ModelPerformancePage = lazy(() => import('./pages/ModelPerformancePage').then((m) => ({ default: m.ModelPerformancePage })));
const SingleFlightPage = lazy(() => import('./pages/SingleFlightPage').then((m) => ({ default: m.SingleFlightPage })));

function PageSpinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
      <Spin size="large" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/data-overview" element={<DataPanoramaPage />} />
          <Route path="/price-analysis/distribution" element={<PriceDistributionPage />} />
          <Route path="/price-analysis/advance-booking" element={<AdvanceBookingPage />} />
          <Route path="/price-analysis/airline-heatmap" element={<AirlineHeatmapPage />} />
          <Route path="/rail-air-competition/rpa-analysis" element={<RpaAnalysisPage />} />
          <Route path="/rail-air-competition/air-hsr-comparison" element={<AirHsrComparisonPage />} />
          <Route path="/rail-air-competition/holiday-expo" element={<HolidayExpoPage />} />
          <Route path="/model-insights/comparison" element={<ModelComparisonPage />} />
          <Route path="/model-insights/performance" element={<ModelPerformancePage />} />
          <Route path="/pricing-system/single-flight" element={<SingleFlightPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
