import { Navigate, Route, Routes } from 'react-router-dom';
import ChartsPage from './pages/ChartsPage';
import GaRunsPage from './pages/GaRunsPage';
import MockBatchDashboardPage from './pages/MockBatchDashboardPage';
import MockDashboardPage from './pages/MockDashboardPage';
import OfflineDataPage from './pages/OfflineDataPage';
import OverviewPage from './pages/OverviewPage';
import RequirementsPage from './pages/RequirementsPage';
import ResultsPage from './pages/ResultsPage';
import RunExplorerPage from './pages/RunExplorerPage';
import RunExplorerCustomPage from './pages/RunExplorerCustomPage';
import SettingsPage from './pages/SettingsPage';

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
      <Route path="/results" element={<ResultsPage />} />
      <Route path="/charts" element={<ChartsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
