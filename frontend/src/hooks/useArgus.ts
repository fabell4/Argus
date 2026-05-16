import { useContext } from 'react'
import { ArgusContext, type ArgusContextType } from '@/context/argusContextDef'

export function useArgus(): ArgusContextType {
  const ctx = useContext(ArgusContext)
  if (!ctx) throw new Error('useArgus must be used within ArgusProvider')
  return ctx
}
