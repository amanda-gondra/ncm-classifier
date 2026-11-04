// Shared heading of the content sections: a small label, the title and an optional one-line
// intro. `titleId` lets the section point to it with aria-labelledby.
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Props = {
  titleId: string;
  eyebrow: string;
  title: string;
  centered?: boolean;
  children?: ReactNode;
};

export function SectionHeading({ titleId, eyebrow, title, centered = false, children }: Props) {
  return (
    <div className={cn("flex max-w-2xl flex-col gap-3", centered && "items-center text-center")}>
      <p className="w-fit rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
        {eyebrow}
      </p>
      <h2 id={titleId} className="font-heading text-2xl font-bold tracking-tight text-balance sm:text-3xl">
        {title}
      </h2>
      {children && <div className="text-pretty text-muted-foreground">{children}</div>}
    </div>
  );
}
