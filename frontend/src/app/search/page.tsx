'use client'

import { SearchComponent } from '@/components/Search'

export default function SearchPage() {
  return (
    <div className="container mx-auto py-8">
      <SearchComponent allowTransactionActions={true} />
    </div>
  )
} 