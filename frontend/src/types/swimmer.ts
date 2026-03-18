// TODO: Fill in once backend serializers are defined
export interface Swimmer {
  id: string
  full_name: string
  gender: string
  nationality: string
  birth_year: number | null
  current_team_name?: string
}

export interface SwimmerDetail extends Swimmer {
  sources: SwimmerSource[]
  recruiting_profile: RecruitingProfile | null
}

export interface SwimmerSource {
  source: string
  external_id: string
  profile_url: string | null
  last_scraped_at: string | null
}

export interface RecruitingProfile {
  graduation_year: number | null
  high_school: string | null
  home_state: string | null
  power_index: number | null
  committed_to_team: string | null
}
