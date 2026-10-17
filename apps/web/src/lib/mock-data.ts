/** Invented editorial fixtures only. Replace this module with the API client later. */
export type Fragrance = {
  slug: string;
  name: string;
  brand: string;
  concentration: string;
  family: string;
  year: number;
  color: string;
  accent: string;
  description: string;
  notes: { top: string[]; heart: string[]; base: string[] };
};
export const fragrances: readonly Fragrance[] = [
  {
    slug: "santal-no-04",
    name: "Santal No. 04",
    brand: "Maison Aube",
    concentration: "Eau de Parfum",
    family: "Woody",
    year: 2024,
    color: "#d3b994",
    accent: "#695039",
    description:
      "An imagined study in warm woods. Creamy sandalwood meets a dry whisper of cardamom, settling into a quiet amber trail.",
    notes: {
      top: ["Cardamom", "Bergamot"],
      heart: ["Iris", "Cedar"],
      base: ["Sandalwood", "Amber"],
    },
  },
  {
    slug: "figue-sauvage",
    name: "Figue Sauvage",
    brand: "Atelier Vert",
    concentration: "Eau de Toilette",
    family: "Green",
    year: 2023,
    color: "#bac4a4",
    accent: "#4e6343",
    description:
      "A fictional afternoon beneath a fig tree: green leaves, milky fruit and sun-warmed wood.",
    notes: {
      top: ["Fig leaf", "Lemon"],
      heart: ["Fig", "Neroli"],
      base: ["Cedar", "Musk"],
    },
  },
  {
    slug: "rose-de-minuit",
    name: "Rose de Minuit",
    brand: "Maison Aube",
    concentration: "Extrait de Parfum",
    family: "Floral",
    year: 2025,
    color: "#c9a8ac",
    accent: "#794e5a",
    description:
      "An invented nocturnal rose, softened by violet and grounded in a velvet patchouli accord.",
    notes: {
      top: ["Pink pepper"],
      heart: ["Rose", "Violet"],
      base: ["Patchouli", "Musk"],
    },
  },
  {
    slug: "sel-et-soleil",
    name: "Sel & Soleil",
    brand: "Studio Marée",
    concentration: "Eau de Parfum",
    family: "Fresh",
    year: 2024,
    color: "#a8c0c5",
    accent: "#41616e",
    description:
      "A synthetic coastal composition of citrus, salt air and pale driftwood.",
    notes: {
      top: ["Mandarin", "Sea salt"],
      heart: ["Neroli"],
      base: ["Driftwood", "Musk"],
    },
  },
  {
    slug: "ambre-lent",
    name: "Ambre Lent",
    brand: "Atelier Vert",
    concentration: "Extrait de Parfum",
    family: "Amber",
    year: 2025,
    color: "#c5a179",
    accent: "#76512d",
    description:
      "An imaginary amber wrapped in soft vanilla and a trace of incense.",
    notes: { top: ["Orange"], heart: ["Incense"], base: ["Amber", "Vanilla"] },
  },
  {
    slug: "iris-papier",
    name: "Iris Papier",
    brand: "Studio Marée",
    concentration: "Eau de Toilette",
    family: "Powdery",
    year: 2023,
    color: "#b9b4c5",
    accent: "#605673",
    description:
      "A fictional portrait of powdery iris, clean paper and airy white musk.",
    notes: {
      top: ["Aldehydes"],
      heart: ["Iris"],
      base: ["White musk", "Cedar"],
    },
  },
];
export const brands = [...new Set(fragrances.map((f) => f.brand))];
export const concentrations = [
  ...new Set(fragrances.map((f) => f.concentration)),
];
export function filterFragrances(
  query: string,
  brand: string,
  concentration: string,
) {
  const term = query.trim().toLocaleLowerCase();
  return fragrances.filter(
    (f) =>
      (!term ||
        `${f.name} ${f.brand} ${f.family} ${Object.values(f.notes).flat().join(" ")}`
          .toLocaleLowerCase()
          .includes(term)) &&
      (!brand || f.brand === brand) &&
      (!concentration || f.concentration === concentration),
  );
}
