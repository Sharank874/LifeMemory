"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { JournalSidebar } from "./journal-sidebar"
import { JournalEditor } from "./journal-editor"
import { MemoryChat } from "./memory-chat"
import { Header } from "./header"

interface DashboardProps {
  onLogout: () => void
}

export function Dashboard({ onLogout }: DashboardProps) {
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)

  return (
    <div className="min-h-screen bg-background">
      <Header onLogout={onLogout} />

      <div className="flex h-[calc(100vh-64px)]">
        {/* Left Panel - Calendar & History */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="w-64 border-r border-border bg-card/50 overflow-y-auto"
        >
          <JournalSidebar selectedDate={selectedDate} onSelectDate={setSelectedDate} />
        </motion.div>

        {/* Center Panel - Journal Editor */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex-1 border-r border-border overflow-y-auto"
        >
          <JournalEditor selectedDate={selectedDate} />
        </motion.div>

        {/* Right Panel - AI Chat */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="w-80 bg-card/50 overflow-y-auto"
        >
          <MemoryChat />
        </motion.div>
      </div>
    </div>
  )
}
