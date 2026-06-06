import type { PropsWithChildren } from 'react';
import NavSidebar from './NavSidebar';

export default function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <NavSidebar />
      <main className="app-main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Mock-first readiness console</p>
            <h1>GeneTrader Bollinger Dashboard</h1>
          </div>
          <span className="runtime-pill">offline mode</span>
        </header>
        {children}
      </main>
    </div>
  );
}
