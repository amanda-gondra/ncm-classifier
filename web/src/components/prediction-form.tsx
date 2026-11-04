"use client";

// Form for one description or a batch (one per line), with the API limits checked
// before sending and clickable examples to try the model quickly.
import { FileText, List, LoaderCircle, Sparkles } from "lucide-react";
import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { EXAMPLES, MAX_BATCH_SIZE, MAX_TEXT_LENGTH } from "@/lib/config";
import { splitLines } from "@/lib/format";
import { textLength, validateDescriptions, type InputMode } from "@/lib/validation";

type Props = {
  onSubmit: (descriptions: string[]) => void;
  pending: boolean;
  disabled: boolean;
};

const FIELDS: Record<InputMode, { label: string; placeholder: string }> = {
  single: {
    label: "Descrição do produto",
    placeholder: "Ex.: Ureia agrícola, pacote 1 kg",
  },
  batch: {
    label: `Descrições, uma por linha (até ${MAX_BATCH_SIZE})`,
    placeholder: "Ureia agrícola, pacote 1 kg\nSal mineral para bovinos 25 kg",
  },
};

function isInputMode(value: unknown): value is InputMode {
  return value === "single" || value === "batch";
}

export function PredictionForm({ onSubmit, pending, disabled }: Props) {
  const id = useId();
  const [mode, setMode] = useState<InputMode>("single");
  const [texts, setTexts] = useState<Record<InputMode, string>>({ single: "", batch: "" });
  const [error, setError] = useState<string | null>(null);
  const text = texts[mode];

  const setText = (value: string) => {
    setTexts((current) => ({ ...current, [mode]: value }));
    setError(null);
  };

  // In single mode an example replaces the text; in batch mode it becomes a new line.
  const addExample = (example: string) => {
    if (mode === "single") setText(example);
    else setText(text.trim() ? `${text.trimEnd()}\n${example}` : example);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = validateDescriptions(mode, text);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    onSubmit(result.descriptions);
  };

  const counter =
    mode === "single"
      ? `${textLength(text)}/${MAX_TEXT_LENGTH} caracteres`
      : `${splitLines(text).length}/${MAX_BATCH_SIZE} descrições`;

  const field = (fieldMode: InputMode) => {
    const fieldId = `${id}-${fieldMode}`;
    const hintId = `${fieldId}-hint`;
    const errorId = `${fieldId}-error`;
    const showError = fieldMode === mode && error !== null;
    return (
      <div className="flex flex-col gap-2">
        <Label htmlFor={fieldId}>{FIELDS[fieldMode].label}</Label>
        <Textarea
          id={fieldId}
          value={texts[fieldMode]}
          onChange={(event) => setText(event.target.value)}
          placeholder={FIELDS[fieldMode].placeholder}
          rows={fieldMode === "single" ? 3 : 6}
          aria-invalid={showError || undefined}
          aria-describedby={showError ? `${hintId} ${errorId}` : hintId}
        />
        <p id={hintId} className="text-xs text-muted-foreground tabular-nums">
          {counter}
        </p>
        {showError && (
          <p id={errorId} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    );
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Tabs
        value={mode}
        onValueChange={(value) => {
          if (isInputMode(value)) {
            setMode(value);
            setError(null);
          }
        }}
      >
        <TabsList aria-label="Modo de entrada" variant="line" className="mb-2">
          <TabsTrigger value="single" className="px-3 data-active:text-primary">
            <FileText aria-hidden className="hidden sm:block" />
            Uma descrição
          </TabsTrigger>
          <TabsTrigger value="batch" className="px-3 data-active:text-primary">
            <List aria-hidden className="hidden sm:block" />
            Várias descrições
          </TabsTrigger>
        </TabsList>
        <TabsContent value="single">{field("single")}</TabsContent>
        <TabsContent value="batch">{field("batch")}</TabsContent>
      </Tabs>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <Button type="submit" size="lg" disabled={disabled || pending} className="h-11 px-6 text-base">
          {pending ? (
            <LoaderCircle data-icon="inline-start" className="animate-spin" aria-hidden />
          ) : (
            <Sparkles data-icon="inline-start" aria-hidden />
          )}
          {pending ? "Classificando…" : "Classificar"}
        </Button>
        {disabled && !pending && (
          <p className="text-xs text-muted-foreground">Aguarde a API ficar pronta.</p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs text-muted-foreground">Exemplos para testar:</p>
        <ul className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <Button type="button" size="sm" variant="outline" onClick={() => addExample(example)}>
                {example}
              </Button>
            </li>
          ))}
        </ul>
      </div>
    </form>
  );
}
