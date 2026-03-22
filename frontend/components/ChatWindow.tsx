"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import type { Components } from "react-markdown"
import { Message } from "@/types/chat"
import MessageBubble from "./MessageBubble"
import TypingIndicator from "./TypingIndicator"
import { sendMessage, sendAnalyticsEvent } from "@/lib/api"
import { countryCodeFromUiName } from "@/lib/countries"
import { v4 as uuidv4 } from "uuid"

function isFormDownloadLink(text: string, href: string) {
  const s = `${text} ${href}`.toLowerCase()
  return /скачать|download|анкет|форма|form|pdf|заполн|manual|faq|tdac|evisa/i.test(
    s
  )
}

type Props = {
  country: string
}

export default function ChatWindow({ country }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  const [sessionId] = useState(uuidv4())

  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isTyping])

  const backendCountry = countryCodeFromUiName(country)

  const markdownComponents = useMemo<Components>(
    () => ({
      a: ({ href, children }) => (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 underline"
          onClick={() => {
            const text = String(children)
            if (href && isFormDownloadLink(text, href)) {
              sendAnalyticsEvent({
                event_type: "form_download_click",
                country_code: backendCountry,
                country_label: country,
                link_url: href,
                link_text: text,
              })
            }
          }}
        >
          {children}
        </a>
      ),
    }),
    [backendCountry, country]
  )

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      role: "user",
      content: input
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    try {
      const response = await sendMessage(input, sessionId, backendCountry)

      const botMessage: Message = {
        role: "assistant",
        content: response.answer
      }

      setMessages((prev) => [...prev, botMessage])
    } catch (error) {
      const msg =
        error instanceof Error && error.message
          ? error.message
          : "Критическая ошибка: сервис ответа недоступен. Сообщите администратору."
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: msg,
        },
      ])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="border rounded-lg p-4">
      <div className="h-96 overflow-y-auto mb-4">
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            message={m}
            markdownComponents={markdownComponents}
          />
        ))}

        {isTyping && <TypingIndicator />}

        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 border p-2 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Введите вопрос..."
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />

        <button
          onClick={handleSend}
          className="bg-blue-500 text-white px-4 rounded"
        >
          Отправить
        </button>
      </div>
    </div>
  )
}