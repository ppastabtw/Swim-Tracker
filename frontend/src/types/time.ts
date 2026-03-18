// TODO: Fill in once backend serializers are defined
export interface SwimTime {
  id: number
  event: {
    distance: number
    stroke: string
  }
  meet: {
    id: number
    name: string
    date: string
    course: string
  }
  time_display: string
  time_seconds: number
  place: number | null
  dq: boolean
  splits: Split[]
}

export interface Split {
  distance: number
  time_seconds: number
}

export interface ProgressionDataPoint {
  date: string
  time_seconds: number
  time_display: string
  meet_name: string
}
