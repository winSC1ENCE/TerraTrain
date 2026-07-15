import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ size = 20, className }: { size?: number; className?: string }) {
  return (
    <Loader2
      className={cn("animate-spin text-text-muted", className)}
      style={{ width: size, height: size }}
    />
  );
}

export function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner size={28} />
    </div>
  );
}
