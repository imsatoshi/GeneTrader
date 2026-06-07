import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Overview' },
  { to: '/offline-data', label: 'Offline Data' },
  { to: '/requirements', label: 'Requirements' },
  { to: '/mock-dashboard', label: 'Mock Dashboard' },
  { to: '/mock-batch-dashboard', label: 'Batch Dashboard' },
  { to: '/ga-runs', label: 'GA Runs' },
  { to: '/run-explorer', label: 'Run Explorer' },
  { to: '/custom-run-explorer', label: 'Custom Runs' },
  { to: '/run-comparison', label: 'Run Compare' },
  { to: '/risk-dashboard', label: 'Risk Dashboard' },
  { to: '/results', label: 'Results' },
  { to: '/charts', label: 'Charts' },
  { to: '/settings', label: 'Settings' },
];

export default function NavSidebar() {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <span className="brand-mark">GT</span>
        <div>
          <strong>Bollinger Evolver</strong>
          <small>readiness dashboard</small>
        </div>
      </div>
      <nav aria-label="Primary navigation">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'} className="nav-link">
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
