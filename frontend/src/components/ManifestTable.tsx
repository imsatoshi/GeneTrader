import type { InventoryFile } from '../types/offlineData';

export default function ManifestTable({ files }: { files: InventoryFile[] }) {
  return (
    <div className="panel">
      <h3>Manifest datasets</h3>
      <div className="manifest-list">
        {files.map((file) => (
          <div key={file.path} className="manifest-row">
            <span>{file.pair ?? 'unknown'}</span>
            <span>{file.timeframe ?? 'unknown'}</span>
            <code>{file.format}</code>
          </div>
        ))}
      </div>
    </div>
  );
}
