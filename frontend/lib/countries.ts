/** Единый список 5 стран UI ↔ код API ↔ backend/data/metadata/countries.json */
export const COUNTRIES = [
  { code: "thailand", name: "Таиланд", flag: "🇹🇭" },
  { code: "uae", name: "ОАЭ", flag: "🇦🇪" },
  { code: "turkey", name: "Турция", flag: "🇹🇷" },
  { code: "vietnam", name: "Вьетнам", flag: "🇻🇳" },
  { code: "srilanka", name: "Шри-Ланка", flag: "🇱🇰" },
] as const

export type CountryCode = (typeof COUNTRIES)[number]["code"]

export function countryCodeFromUiName(uiName: string): string {
  const row = COUNTRIES.find((c) => c.name === uiName)
  return row?.code ?? uiName.toLowerCase().replace(/\s+/g, "")
}
