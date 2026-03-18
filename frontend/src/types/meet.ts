// TODO: Fill in once backend serializers are defined
export interface Meet {
  id: number
  name: string
  start_date: string
  end_date: string
  course: 'SCY' | 'SCM' | 'LCM'
  meet_type: string
  location_city: string
  location_state: string | null
  location_country: string
}
