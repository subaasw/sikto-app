'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiBase } from '@/lib/config';
import type { Job } from '@/types/api';

const JobEventsContext = createContext<Record<string, Job>>({});

export function JobEventsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Record<string, Job>>({});

  useEffect(() => {
    const source = new EventSource(`${apiBase()}/events`, { withCredentials: true });
    source.onmessage = (event) => {
      try {
        const job = JSON.parse(event.data) as Job;
        setJobs((prev) => ({ ...prev, [job.id]: job }));
      } catch {
        /* ignore malformed frame; the next tick resends state */
      }
    };
    return () => source.close();
  }, []);

  return <JobEventsContext.Provider value={jobs}>{children}</JobEventsContext.Provider>;
}

export function useJobEvent(jobId: string | undefined): Job | undefined {
  const jobs = useContext(JobEventsContext);
  return jobId ? jobs[jobId] : undefined;
}
