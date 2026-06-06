interface StatusCardProps {
  label: string;
  value: string | number;
  tone?: 'success' | 'warning' | 'danger' | 'neutral';
  detail?: string;
}

export default function StatusCard({ label, value, tone = 'neutral', detail }: StatusCardProps) {
  return (
    <article className={`status-card status-card-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}
