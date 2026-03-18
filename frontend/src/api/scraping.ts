// TODO: Implement scraping trigger API functions
import client from './client'

export const triggerSwimmerScrape = (data: { source: string; external_id?: string; name?: string }) =>
  client.post('/scrape/swimmer/', data).then(res => res.data)

export const getScrapeJob = (id: string) =>
  client.get(`/scrape/jobs/${id}/`).then(res => res.data)

export const getScrapeJobs = () =>
  client.get('/scrape/jobs/').then(res => res.data)
