import { COUNTRIES } from "@/lib/countries"

type Props = {
  onSelect: (country: string) => void
}

export default function CountrySelector({ onSelect }: Props) {
    return (
      <div className="grid grid-cols-2 gap-4 mb-6">
        {COUNTRIES.map((c) => (
          <button
            key={c.code}
            className="flex items-center gap-3 p-4 border rounded-xl bg-white shadow-sm hover:shadow-md hover:scale-[1.02] transition-all duration-200"
            onClick={() => onSelect(c.name)}
          >
            {/* Кружочек с флагом */}
            <div className="w-10 h-10 flex items-center justify-center rounded-full bg-gray-100 text-xl">
              {c.flag}
            </div>
  
            {/* Название страны */}
            <span className="font-medium">
              {c.name}
            </span>
          </button>
        ))}
      </div>
    )
  }