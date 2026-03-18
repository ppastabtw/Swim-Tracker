// TODO: Implement rankings API query functions
import client from './client'

export const getRankings = (params: Record<string, string>) =>
  client.get('/rankings/', { params }).then(res => res.data)
