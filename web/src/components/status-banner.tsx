// Tells the person whether the API is ready, waking up or out of reach.
import { CircleCheck, LoaderCircle, RotateCw, TriangleAlert } from "lucide-react";

import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ApiStatus } from "@/hooks/use-api-status";

type Props = {
  status: ApiStatus;
  onRetry: () => void;
};

export function StatusBanner({ status, onRetry }: Props) {
  if (status === "unavailable") {
    return (
      <Alert variant="destructive">
        <TriangleAlert aria-hidden />
        <AlertTitle>A API não respondeu</AlertTitle>
        <AlertDescription>
          O servidor pode estar fora do ar ou sem conexão. Tente de novo em alguns instantes.
        </AlertDescription>
        <AlertAction>
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RotateCw data-icon="inline-start" aria-hidden />
            Tentar de novo
          </Button>
        </AlertAction>
      </Alert>
    );
  }

  if (status === "ready") {
    return (
      <Alert role="status">
        <CircleCheck aria-hidden className="text-emerald-600" />
        <AlertTitle>API pronta</AlertTitle>
        <AlertDescription>O modelo está carregado e pode classificar.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert role="status">
      <LoaderCircle aria-hidden className="animate-spin" />
      <AlertTitle>{status === "checking" ? "Verificando a API…" : "A API está acordando…"}</AlertTitle>
      <AlertDescription>
        No plano gratuito o servidor dorme após 15 minutos sem uso e leva cerca de um minuto
        para voltar. Esta página avisa quando ele estiver pronto.
      </AlertDescription>
    </Alert>
  );
}
