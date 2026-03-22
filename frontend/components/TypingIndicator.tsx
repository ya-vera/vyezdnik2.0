"use client"

import { useEffect, useState } from "react"

export default function TypingIndicator() {
  const [dots, setDots] = useState(".")

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "." : prev + "."))
    }, 500)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex justify-start mb-3">
      <div className="bg-gray-200 px-4 py-2 rounded-lg text-gray-600 text-sm">
        Думает{dots}
      </div>
    </div>
  )
}