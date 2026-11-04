// Project mark: a sprout in a green square, the same one used in the icon and share image.
import { Sprout } from "lucide-react";

import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground",
        className,
      )}
    >
      <Sprout className="size-5" />
    </span>
  );
}
