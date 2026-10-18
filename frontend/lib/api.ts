/**
 * API client for backend communication
 */

import { supabase } from './supabase'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Get authentication token from Supabase
 */
async function getAuthToken(): Promise<string | null> {
  const { data: { session }, error } = await supabase.auth.getSession()
  
  if (error) {
    console.error('Error getting session:', error)
    return null
  }
  
  if (!session) {
    console.warn('No active session found')
    return null
  }
  
  if (!session.access_token) {
    console.warn('Session exists but no access_token found')
    return null
  }
  
  console.debug('Token retrieved successfully:', session.access_token.substring(0, 20) + '...')
  return session.access_token
}

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken()
  
  if (!token) {
    // Try to refresh the session first
    try {
      const { data: { session } } = await supabase.auth.refreshSession()
      if (!session?.access_token) {
        throw new Error('Not authenticated. Please sign in again.')
      }
      // Use the refreshed token
      const refreshedToken = session.access_token
      return await makeRequest(endpoint, options, refreshedToken)
    } catch (error: any) {
      if (error.message.includes('Not authenticated')) {
        throw error
      }
      throw new Error('Not authenticated. Please sign in again.')
    }
  }

  return await makeRequest(endpoint, options, token)
}

/**
 * Make the actual HTTP request with error handling
 */
async function makeRequest<T>(
  endpoint: string,
  options: RequestInit,
  token: string
): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    })

    if (!response.ok) {
      // Handle 401 specifically - might need to refresh session
      if (response.status === 401) {
        // Try to refresh the session
        const { data: { session } } = await supabase.auth.refreshSession()
        if (session?.access_token) {
          // Retry with new token
          const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${session.access_token}`,
              ...options.headers,
            },
          })
          if (retryResponse.ok) {
            return retryResponse.json()
          }
        }
        throw new Error('Authentication failed. Please sign in again.')
      }
      
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `API error: ${response.statusText}`)
    }

    return response.json()
  } catch (error: any) {
    // Handle network errors (backend not running, CORS, etc.)
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error(
        `Cannot connect to backend at ${API_BASE_URL}. ` +
        `Please make sure the backend server is running.`
      )
    }
    // Re-throw other errors
    throw error
  }
}

/**
 * Journal API
 */
export const journalApi = {
  /**
   * Save a journal entry (UPSERT - one entry per day)
   * @param content Journal entry content
   * @param mood Mood/emotion label
   * @param entryDate Date in YYYY-MM-DD format (defaults to today)
   */
  async save(content: string, mood?: string, entryDate?: string) {
    return apiRequest<{
      id: string
      user_id: string
      entry_date: string
      content: string
      mood: string | null
      created_at: string
      updated_at: string
    }>('/journal/save', {
      method: 'POST',
      body: JSON.stringify({ content, mood, entry_date: entryDate }),
    })
  },

  /**
   * Get a journal entry for a specific date
   * @param entryDate Date in YYYY-MM-DD format
   */
  async get(entryDate: string) {
    return apiRequest<{
      id: string
      user_id: string
      entry_date: string
      content: string
      mood: string | null
      created_at: string
      updated_at: string
    }>(`/journal/get?entry_date=${entryDate}`)
  },

  /**
   * Get all dates in a month that have journal entries (for calendar)
   * @param month Month in YYYY-MM format
   */
  async getDaysWithEntries(month: string) {
    return apiRequest<{
      dates: string[]
    }>(`/journal/days-with-entries?month=${month}`)
  },

  /**
   * List journal entries
   */
  async list(page: number = 1, page_size: number = 20) {
    return apiRequest<{
      journals: Array<{
        id: string
        user_id: string
        entry_date: string
        content: string
        mood: string | null
        created_at: string
        updated_at: string
      }>
      total: number
      page: number
      page_size: number
    }>(`/journal/list?page=${page}&page_size=${page_size}`)
  },
}

/**
 * Memory/Ask API
 */
export const memoryApi = {
  /**
   * Ask a question about memories
   */
  async ask(question: string) {
    return apiRequest<{
      answer: string
      evidence: Array<{
        id: string
        date: string
        content: string
        mood: string | null
        score: number
      }>
      intent: string
      retrieved_count: number
      llm_provider: string
    }>('/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    })
  },
}

/**
 * Insights API
 */
export const insightsApi = {
  /**
   * Get summary insights
   */
  async getSummary() {
    return apiRequest<{
      total_entries: number
      entries_this_week: number
      entries_this_month: number
      mood_distribution: Record<string, number>
      most_active_day: string | null
      most_active_time: string | null
      recent_themes: string[]
    }>('/insights/summary')
  },
}

