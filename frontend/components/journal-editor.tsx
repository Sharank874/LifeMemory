"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"

interface JournalEditorProps {
  selectedDate: Date | null
}

export function JournalEditor({ selectedDate }: JournalEditorProps) {
  const [content, setContent] = useState("")
  const [mood, setMood] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentEntryId, setCurrentEntryId] = useState<string | null>(null)

  const moods = ["😔", "😐", "🙂", "😊", "😄"]
  const moodMap: Record<string, string> = {
    "😔": "sad",
    "😐": "neutral",
    "🙂": "content",
    "😊": "happy",
    "😄": "excited"
  }
  const reverseMoodMap: Record<string, string> = {
    "sad": "😔",
    "neutral": "😐",
    "content": "🙂",
    "happy": "😊",
    "excited": "😄"
  }

  const dateString = selectedDate
    ? selectedDate.toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Today's Journal"

  const loadEntryForDate = async (date: Date) => {
    setIsLoading(true)
    try {
      const { journalApi } = await import('@/lib/api')
      
      // Format date as YYYY-MM-DD
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const entryDate = `${year}-${month}-${day}`
      
      // Use the new get endpoint for specific date
      try {
        const entry = await journalApi.get(entryDate)
        setContent(entry.content)
        setCurrentEntryId(entry.id)
        // Convert text mood back to emoji
        if (entry.mood && reverseMoodMap[entry.mood]) {
          setMood(reverseMoodMap[entry.mood])
        } else {
          setMood(null)
        }
      } catch (error: any) {
        // If entry not found (404), that's okay - just clear the editor
        if (error.message?.includes('404') || error.message?.includes('Not Found')) {
          setContent("")
          setMood(null)
          setCurrentEntryId(null)
        } else {
          throw error
        }
      }
    } catch (error) {
      console.error('Failed to load entry:', error)
      setContent("")
      setMood(null)
      setCurrentEntryId(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!content.trim()) return

    setIsSaving(true)
    try {
      const { journalApi } = await import('@/lib/api')
      
      // Format date as YYYY-MM-DD (or use today if no date selected)
      const dateToSave = selectedDate || new Date()
      const year = dateToSave.getFullYear()
      const month = String(dateToSave.getMonth() + 1).padStart(2, '0')
      const day = String(dateToSave.getDate()).padStart(2, '0')
      const entryDate = `${year}-${month}-${day}`
      
      // Convert emoji mood to text (convert null to undefined for API)
      const moodText = mood ? moodMap[mood] || undefined : undefined

      // Use the new save endpoint (UPSERT - replaces existing entry for that date)
      await journalApi.save(content, moodText, entryDate)
      
      // Reload entry after save to get updated data
      if (selectedDate) {
        await loadEntryForDate(selectedDate)
      } else {
        // For today, reload to get the saved entry
        await loadEntryForDate(new Date())
      }
      
      // Trigger page refresh to update sidebar
      window.dispatchEvent(new Event('journal-saved'))
    } catch (error: any) {
      console.error('Failed to save journal entry:', error)
      alert(`Failed to save: ${error.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    if (selectedDate) {
      loadEntryForDate(selectedDate)
    } else {
      setContent("")
      setMood(null)
      setCurrentEntryId(null)
    }
  }, [selectedDate])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="p-8 h-full flex flex-col"
    >
      <div className="flex-1 flex flex-col">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">{dateString}</h2>
          <p className="text-muted-foreground">Write your thoughts, feelings, and reflections.</p>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            Loading entry...
          </div>
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start writing your journal entry here... Your words are yours alone and private to your account."
            className="flex-1 bg-background border border-border rounded-xl p-6 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary font-[family-name:var(--font-sans)] text-base leading-relaxed"
          />
        )}

        <div className="flex items-center justify-between mt-6">
          <div className="flex gap-2">
            {moods.map((m) => (
              <motion.button
                key={m}
                whileHover={{ scale: 1.2 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setMood(m)}
                className={`text-2xl p-3 rounded-lg transition-all ${
                  mood === m ? "bg-primary/20 scale-110" : "hover:bg-primary/10"
                }`}
              >
                {m}
              </motion.button>
            ))}
          </div>

          <Button
            onClick={handleSave}
            disabled={!content.trim() || isSaving}
            className="bg-primary hover:bg-primary/90 text-primary-foreground px-6"
          >
            {isSaving ? "Saving..." : "Save Entry"}
          </Button>
        </div>
      </div>

      <div className="text-xs text-muted-foreground mt-6 pt-6 border-t border-border">
        🔒 One entry per day. Saved entries are visible only to your account (row-level security).
      </div>
    </motion.div>
  )
}
