// Side panel of the demonstration: whether the API can classify now, the model version and
// its headline result, and the fiscal notice in one line.
import { CircleCheck, Info, LoaderCircle, Package, RotateCw, Target, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { ApiStatus } from "@/hooks/use-api-status";
import { formatPercent } from "@/lib/format";
import { PUBLISHED_TEST } from "@/lib/project-facts";

type Props = {
  status: ApiStatus;
  modelVersion: string | null;
  onRetry: () => void;
};

const STATES: Record<ApiStatus, { title: string; text: string }> = {
  checking: { title: "Verificando a API…", text: "Um instante." },
  waking: {
    title: "Acordando o servidor…",
    text: "No plano gratuito ele dorme sem uso e leva até um minuto para voltar.",
  },
  ready: { title: "API operacional", text: "Pronta para classificar." },
  unavailable: { title: "A API não respondeu", text: "Tente de novo em alguns instantes." },
};

function StatusIcon({ status }: { status: ApiStatus }) {
  if (status === "ready") {
    return (
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <CircleCheck aria-hidden className="size-5" />
      </span>
    );
  }
  if (status === "unavailable") {
    return <TriangleAlert aria-hidden className="size-10 shrink-0 p-2 text-destructive" />;
  }
  return <LoaderCircle aria-hidden className="size-10 shrink-0 animate-spin p-2 text-primary" />;
}

export function StatusPanel({ status, modelVersion, onRetry }: Props) {
  const state = STATES[status];
  return (
    <aside className="flex flex-col gap-5 rounded-xl border bg-secondary/50 p-5" aria-label="Estado da API">
      <div role="status" className="flex gap-3">
        <StatusIcon status={status} />
        <div className="flex flex-col gap-0.5">
          <p className="font-heading text-lg font-semibold">{state.title}</p>
          <p className="text-sm text-muted-foreground">{state.text}</p>
          {status === "unavailable" && (
            <Button size="sm" variant="outline" className="mt-2 w-fit" onClick={onRetry}>
              <RotateCw data-icon="inline-start" aria-hidden />
              Tentar de novo
            </Button>
          )}
        </div>
      </div>

      <Separator />

      <div className="flex flex-col gap-3">
        <p className="text-sm font-semibold">Sobre o modelo</p>
        <dl className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2">
            <Package aria-hidden className="size-5 text-primary" />
            <div className="flex flex-col">
              <dt className="order-2 text-xs text-muted-foreground">Versão</dt>
              <dd className="order-1 font-semibold">{modelVersion ?? "—"}</dd>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Target aria-hidden className="size-5 text-primary" />
            <div className="flex flex-col">
              <dt className="order-2 text-xs text-muted-foreground">Acerto top-1</dt>
              <dd className="order-1 font-semibold">{formatPercent(PUBLISHED_TEST.top1)}</dd>
            </div>
          </div>
        </dl>
      </div>

      <Separator />

      <p className="flex gap-2 text-xs text-muted-foreground">
        <Info aria-hidden className="size-4 shrink-0" />
        A classificação é uma sugestão e não substitui a análise fiscal.
      </p>
    </aside>
  );
}
