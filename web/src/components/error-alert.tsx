// A failed classification, with the API message, when to retry and the request id.
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { ApiError } from "@/lib/api/client";

export function ErrorAlert({ error }: { error: ApiError }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Não foi possível classificar</AlertTitle>
      <AlertDescription>
        <p>
          {error.message}
          {error.retryAfterSeconds !== null &&
            ` Tente de novo em ${error.retryAfterSeconds} segundo(s).`}
        </p>
        {error.requestId && (
          <p className="text-xs">
            Código da requisição: <code>{error.requestId}</code>
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}
