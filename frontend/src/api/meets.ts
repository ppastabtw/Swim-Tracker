// TODO: Implement meet API query functions
import client from './client'

export const getMeets = (params?: Record<string, string>) =>
  client.get('/meets/', { params }).then(res => res.data)

export const getMeet = (id: string) =>
  client.get(`/meets/${id}/`).then(res => res.data)

export const getMeetResults = (id: string, params?: Record<string, string>) =>
  client.get(`/meets/${id}/results/`, { params }).then(res => res.data)
