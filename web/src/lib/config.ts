// Address of the NCM Classifier API. NEXT_PUBLIC_ variables are inlined at build time,
// so the published site always calls the API it was built for.
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "https://ncm-classifier-api.onrender.com"
).replace(/\/+$/, "");

// The same limits the API enforces (MAX_TEXT_LENGTH and MAX_BATCH_SIZE). The interface
// checks them first to give immediate feedback; the API still validates every request.
export const MAX_TEXT_LENGTH = 500;
export const MAX_BATCH_SIZE = 20;

// Public address of this site (GitHub Pages), used for canonical and share-image URLs.
// The base path (/ncm-classifier) is added by Next from PAGES_BASE_PATH at build time.
export const SITE_ORIGIN = "https://amanda-gondra.github.io";

export const LINKS = {
  github: "https://github.com/amanda-gondra/ncm-classifier",
  model: "https://huggingface.co/AmandaGondra/ncm-classifier",
  dataset: "https://huggingface.co/datasets/AmandaGondra/ncm-classifier-dataset",
  apiDocs: `${API_URL}/docs`,
} as const;

export const EXAMPLES = [
  "Ureia agrícola, pacote 1 kg",
  "Adubo NPK 20-05-20 saco 50kg",
  "Arame farpado galvanizado rolo 500 m",
  "Sal mineral para bovinos 25 kg",
  "Semente de milho híbrido saco 20 kg",
  "Chocadeira automática 120 ovos",
] as const;
