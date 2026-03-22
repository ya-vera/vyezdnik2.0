"use client"

import { useState } from "react"
import CountrySelector from "@/components/CountrySelector"
import ChatWindow from "@/components/ChatWindow"
import { sendAnalyticsEvent } from "@/lib/api"
import { countryCodeFromUiName } from "@/lib/countries"

export default function Home() {
  const [country, setCountry] = useState<string | null>(null)

  const onSelectCountry = (name: string) => {
    sendAnalyticsEvent({
      event_type: "country_select",
      country_label: name,
      country_code: countryCodeFromUiName(name),
    })
    setCountry(name)
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-100 flex items-center justify-center p-8">
      <div className="w-full max-w-3xl bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-2 text-center">
          Въездник
        </h1>
        <p className="text-gray-500 text-center mb-8">
          Цифровой гид по правилам въезда
        </p>

        {!country && (
          <>
            <h2 className="mb-4 font-semibold">
              Выберите страну
            </h2>
            <CountrySelector onSelect={onSelectCountry} />
          </>
        )}

        {country && (
          <>
            <button
              onClick={() => setCountry(null)}
              className="mb-4 text-sm text-blue-600 hover:underline"
            >
              ← Вернуться назад
            </button>
            <p className="mb-4 text-gray-600">
              Страна: <b>{country}</b>
            </p>
            <ChatWindow country={country} />
          </>
        )}

        <footer className="text-xs text-gray-400 mt-8 text-center">
          Информация носит справочный характер.
        </footer>
      </div>
    </main>
  )
}