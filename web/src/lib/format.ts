// Number formatting for Brazilian Portuguese readers.
const percent = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatPercent(value: number): string {
  return percent.format(value);
}

export function formatDecimal(value: number, digits: number): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

// 95% interval as "90,4% a 98,0%"; the point value is shown separately.
export function formatRange(interval: { low: number; high: number }): string {
  return `${formatPercent(interval.low)} a ${formatPercent(interval.high)}`;
}

// "Ureia\n\n Adubo  \n" -> ["Ureia", "Adubo"]: one description per non-empty line.
export function splitLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}
