'use client'

import { useState } from 'react'
import { TradesTableComponent } from '../components/TradesTable'
import { ReportAreaComponent } from '../components/ReportArea'

export default function Page() {
  const [dateFilter, setDateFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Blue Deer Trading Dashboard</h1>
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="lg:w-2/3">
          <div className="mb-4 flex flex-wrap gap-4">
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="border p-2 rounded"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border p-2 rounded"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <TradesTableComponent
            dateFilter={dateFilter}
            statusFilter={statusFilter}
          />
        </div>
        <div className="lg:w-1/3">
          <ReportAreaComponent />
        </div>
      </div>
    </div>
  )
}