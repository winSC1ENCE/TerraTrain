import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("bg-surface border border-border rounded-card", className)}>
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("px-5 pt-5 pb-3 flex items-start justify-between", className)}>
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
  sub,
}: {
  className?: string;
  children: React.ReactNode;
  sub?: string;
}) {
  return (
    <div>
      <h2 className={cn("text-sm font-semibold text-text", className)}>{children}</h2>
      {sub && <p className="text-xs text-text-muted mt-0.5">{sub}</p>}
    </div>
  );
}

export function CardBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={cn("px-5 pb-5", className)}>{children}</div>;
}
