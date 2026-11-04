// Shared heading of the content sections: a small label, the title and a short intro.
// `titleId` lets the section point to it with aria-labelledby.
import type { ReactNode } from "react";

type Props = {
  titleId: string;
  eyebrow: string;
  title: string;
  children?: ReactNode;
};

export function SectionHeading({ titleId, eyebrow, title, children }: Props) {
  return (
    <div className="flex max-w-3xl flex-col gap-3">
      <p className="text-sm font-semibold tracking-wide text-primary uppercase">{eyebrow}</p>
      <h2 id={titleId} className="font-heading text-2xl font-bold tracking-tight text-balance sm:text-3xl">
        {title}
      </h2>
      {children && <div className="text-pretty text-muted-foreground">{children}</div>}
    </div>
  );
}
