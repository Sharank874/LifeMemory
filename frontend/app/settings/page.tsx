"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Trash2, Lock } from "lucide-react"
import Link from "next/link"
import { useState } from "react"

export default function SettingsPage() {
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="h-16 border-b border-border bg-card/50 flex items-center px-6"
      >
        <Link href="/" className="flex items-center gap-2 text-primary hover:text-primary/80 transition-colors">
          <ArrowLeft className="w-5 h-5" />
          <span>Back</span>
        </Link>
      </motion.header>

      <div className="max-w-2xl mx-auto p-8 space-y-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <h1 className="text-3xl font-bold text-foreground mb-2">Settings</h1>
          <p className="text-muted-foreground">Manage your privacy and account preferences</p>
        </motion.div>

        {/* Privacy Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="bg-card border border-border rounded-xl p-6 space-y-4"
        >
          <div className="flex items-start gap-3">
            <Lock className="w-5 h-5 text-primary mt-1" />
            <div className="flex-1">
              <h3 className="font-semibold text-foreground mb-2">Privacy & Data</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Your journal entries are isolated to your account with row-level security, and this app never uses
                them to train models. To answer questions, relevant entries are sent to the embedding and LLM
                providers you configure.
              </p>
              <ul className="text-sm text-muted-foreground space-y-2">
                <li>✓ Row-level security: only your account can read your entries</li>
                <li>✓ Encrypted in transit (HTTPS) and at rest (Supabase)</li>
                <li>✓ You own all your data</li>
                <li>✓ Answers cite the entries they are based on</li>
              </ul>
            </div>
          </div>
        </motion.div>

        {/* Data Ownership */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="bg-card border border-border rounded-xl p-6"
        >
          <h3 className="font-semibold text-foreground mb-3">Your Data</h3>
          <p className="text-sm text-muted-foreground mb-4">
            LifeMemory AI is built on the principle that your memories belong to you. All your journal entries and data
            are yours to keep, use, and delete as you wish.
          </p>
          <Button variant="outline" className="text-foreground border-border hover:bg-primary/10 bg-transparent">
            Download My Data
          </Button>
        </motion.div>

        {/* Danger Zone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="bg-destructive/5 border border-destructive/20 rounded-xl p-6"
        >
          <div className="flex items-start gap-3">
            <Trash2 className="w-5 h-5 text-destructive mt-1" />
            <div className="flex-1">
              <h3 className="font-semibold text-destructive mb-2">Delete Account</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Permanently delete your account and all your journal entries. (Not wired to the backend yet:
                this button is a placeholder in the current version.)
              </p>
              {confirmDelete ? (
                <div className="space-y-3">
                  <p className="text-sm text-destructive font-medium">
                    Are you sure? All your memories will be deleted permanently.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      className="bg-destructive hover:bg-destructive/90 text-white"
                      onClick={() => setConfirmDelete(false)}
                    >
                      Delete Everything
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setConfirmDelete(false)}
                      className="text-foreground border-border"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => setConfirmDelete(true)}
                  className="text-destructive border-destructive/20 hover:bg-destructive/10"
                >
                  Delete Account
                </Button>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
