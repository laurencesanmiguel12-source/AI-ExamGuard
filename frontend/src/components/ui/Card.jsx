export default function Card({ children, className = "" }) {
  return (
    <div className={`bg-card border border-border rounded-xl shadow-sm ${className}`}>
      {children}
    </div>
  );
}
