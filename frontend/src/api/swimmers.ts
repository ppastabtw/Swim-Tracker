// TODO: Implement swimmer API query functions
import client from './client'

export const getSwimmers = (params?: Record<string, string>) =>
  client.get('/swimmers/', { params }).then(res => res.data)

export const getSwimmer = (id: string) =>
  client.get(`/swimmers/${id}/`).then(res => res.data)

export const getSwimmerTimes = (id: string, params?: Record<string, string>) =>
  client.get(`/swimmers/${id}/times/`, { params }).then(res => res.data)

export const getSwimmerBestTimes = (id: string) =>
  client.get(`/swimmers/${id}/best_times/`).then(res => res.data)

export const getSwimmerProgression = (id: string, event: string) =>
  client.get(`/swimmers/${id}/progression/${event}/`).then(res => res.data)
