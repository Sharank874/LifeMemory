"use client"

import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { journalApi } from "@/lib/api"

interface JournalSidebarProps {
  selectedDate: Date | null
  onSelectDate: (date: Date) => void
}

interface JournalEntry {
  id: string
  date: Date
  title: string
  content: string
}

export function JournalSidebar({ selectedDate, onSelectDate }: JournalSidebarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [daysWithEntries, setDaysWithEntries] = useState<Set<string>>(new Set())

  // Load days with entries for calendar checkmarks
  const loadDaysWithEntries = useCallback(async () => {
    try {
      const year = currentMonth.getFullYear()
      const month = String(currentMonth.getMonth() + 1).padStart(2, '0')
      const monthStr = `${year}-${month}`
      
      const response = await journalApi.getDaysWithEntries(monthStr)
      setDaysWithEntries(new Set(response.dates))
    } catch (error) {
      console.error('Failed to load days with entries:', error)
      setDaysWithEntries(new Set())
    }
  }, [currentMonth])

  useEffect(() => {
    // Wait a bit to ensure auth is ready, then check if user is authenticated
    const timer = setTimeout(async () => {
      // Check if user is authenticated before loading
      const { getSession } = await import('@/lib/supabase')
      try {
        const session = await getSession()
        if (session) {
          loadEntries()
          loadDaysWithEntries()
        } else {
          console.warn('Not authenticated, skipping journal load')
        }
      } catch (error) {
        console.error('Auth check failed:', error)
      }
    }, 500) // Increased delay to ensure auth is ready

    // Listen for journal save events to refresh the list and calendar
    const handleJournalSaved = () => {
      loadEntries()
      loadDaysWithEntries()
    }
    window.addEventListener('journal-saved', handleJournalSaved)
    
    return () => {
      clearTimeout(timer)
      window.removeEventListener('journal-saved', handleJournalSaved)
    }
  }, [loadDaysWithEntries])

  const loadEntries = async () => {
    try {
      setIsLoading(true)
      const response = await journalApi.list(1, 100) // Get more entries for calendar
      
      const formattedEntries: JournalEntry[] = response.journals.map((journal) => ({
        id: journal.id,
        // Use entry_date if available, fallback to created_at
        date: new Date(journal.entry_date || journal.created_at),
        title: journal.content.substring(0, 50) + (journal.content.length > 50 ? '...' : ''),
        content: journal.content,
      }))
      
      setEntries(formattedEntries)
    } catch (error) {
      console.error('Failed to load entries:', error)
      setEntries([])
    } finally {
      setIsLoading(false)
    }
  }
  
  // Reload calendar when month changes
  useEffect(() => {
    loadDaysWithEntries()
  }, [loadDaysWithEntries])

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  }

  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay()
  }

  const days = Array.from({ length: getDaysInMonth(currentMonth) }, (_, i) => i + 1)
  const firstDay = getFirstDayOfMonth(currentMonth)
  const monthName = currentMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" })

  const previousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  return (
    <div className="p-6">
      <div className="space-y-8">
        {/* Calendar */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-foreground text-sm">{monthName}</h3>
            <div className="flex gap-1">
              <button onClick={previousMonth} className="p-1 hover:bg-primary/10 rounded transition-colors">
                <ChevronLeft className="w-4 h-4 text-muted-foreground" />
              </button>
              <button onClick={nextMonth} className="p-1 hover:bg-primary/10 rounded transition-colors">
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div key={day} className="h-8 flex items-center justify-center text-xs text-muted-foreground font-medium">
                {day[0]}
              </div>
            ))}
            {Array.from({ length: firstDay }).map((_, i) => (
              <div key={`empty-${i}`} />
            ))}
            {days.map((day) => {
              const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
              const isSelected = selectedDate?.toDateString() === date.toDateString()
              
              // Format date as YYYY-MM-DD to check against daysWithEntries
              const year = date.getFullYear()
              const month = String(date.getMonth() + 1).padStart(2, '0')
              const dayStr = String(date.getDate()).padStart(2, '0')
              const dateKey = `${year}-${month}-${dayStr}`
              const hasEntry = daysWithEntries.has(dateKey)

              return (
                <motion.button
                  key={day}
                  onClick={() => onSelectDate(date)}
                  whileHover={{ scale: 1.1 }}
                  className={`h-8 rounded-lg text-sm font-medium transition-all relative ${
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : hasEntry
                        ? "bg-primary/20 text-primary"
                        : "text-foreground hover:bg-primary/10"
                  }`}
                >
                  {day}
                  {hasEntry && !isSelected && (
                    <span className="absolute top-0 right-0 text-xs">✓</span>
                  )}
                </motion.button>
              )
            })}
          </div>
        </div>

        {/* Recent Entries */}
        <div className="space-y-3 border-t border-border pt-4">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recent Entries</h4>
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground">Loading...</div>
            ) : entries.length === 0 ? (
              <div className="text-sm text-muted-foreground">No entries yet. Start writing!</div>
            ) : (
              entries.slice(0, 10).map((entry, i) => (
                <motion.button
                  key={entry.id}
                  onClick={() => onSelectDate(entry.date)}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="w-full text-left p-3 rounded-lg hover:bg-primary/10 transition-colors group"
                >
                  <p className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                    {entry.date.toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                  <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                    {entry.title}
                  </p>
                </motion.button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
