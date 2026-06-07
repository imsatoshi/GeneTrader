import { Suspense } from 'react';
import AppLayout from './components/AppLayout';
import { AppRoutes } from './routes';

export default function App() {
  return (
    <AppLayout>
      <Suspense fallback={<div role="status">Loading dashboard view</div>}>
        <AppRoutes />
      </Suspense>
    </AppLayout>
  );
}
