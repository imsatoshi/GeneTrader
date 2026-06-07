import { lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

const ChartsPage = lazy(() => import('./pages/ChartsPage'));
const GaRunsPage = lazy(() => import('./pages/GaRunsPage'));
const MockBatchDashboardPage = lazy(() => import('./pages/MockBatchDashboardPage'));
const MockDashboardPage = lazy(() => import('./pages/MockDashboardPage'));
const OfflineDataPage = lazy(() => import('./pages/OfflineDataPage'));
const OverviewPage = lazy(() => import('./pages/OverviewPage'));
const RequirementsPage = lazy(() => import('./pages/RequirementsPage'));
const ResultsPage = lazy(() => import('./pages/ResultsPage'));
const RiskDashboardPage = lazy(() => import('./pages/RiskDashboardPage'));
const RunComparisonPage = lazy(() => import('./pages/RunComparisonPage'));
const RunExplorerPage = lazy(() => import('./pages/RunExplorerPage'));
const RunExplorerCustomPage = lazy(() => import('./pages/RunExplorerCustomPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<OverviewPage />} />
      <Route path="/offline-data" element={<OfflineDataPage />} />
      <Route path="/requirements" element={<RequirementsPage />} />
      <Route path="/mock-dashboard" element={<MockDashboardPage />} />
      <Route path="/mock-batch-dashboard" element={<MockBatchDashboardPage />} />
      <Route path="/ga-runs" element={<GaRunsPage />} />
      <Route path="/run-explorer" element={<RunExplorerPage />} />
      <Route path="/custom-run-explorer" element={<RunExplorerCustomPage />} />
      <Route path="/run-comparison" element={<RunComparisonPage />} />
      <Route path="/risk-dashboard" element={<RiskDashboardPage />} />
      <Route path="/results" element={<ResultsPage />} />
      <Route path="/charts" element={<ChartsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
