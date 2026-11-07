// типы ответов API IgpaLab (backend/api): поля – как в JSON, числа – доли и баллы шкалы 0–4

export type AppLocale = 'ru' | 'kk' | 'en'
export type RulesCode = 'default' | 'eduscore' | 'percentile'
export type Level = 'bachelor' | 'master_research' | 'master_profile'
export type Profile = 'IROS' | 'SSCI'
export type Block = 'research' | 'one_time' | 'permanent'

export interface Category {
  code: string
  column: string
  block: Block
  profile: Profile
  name: string
  asu_title: string
  statuses: string[]
}

export interface Status {
  code: string
  family: 'research' | 'one_time' | 'permanent'
  name: string
}

export interface Meta {
  categories: Category[]
  statuses: Status[]
  rules: { code: RulesCode; name: string; note: string }[]
  faculties: string[]
  levels: Level[]
  current_year: number
}

export interface RecordIn {
  category: string
  status: string
}

export interface CategoryScore {
  code: string
  name: string
  points: number
  counted: number
  contribution: number
  profile: Profile
}

export interface Calc {
  rules: RulesCode
  rules_name: string
  igpa: number
  gpa: number
  iros: number
  ssci: number
  gpa_part: number
  iros_part: number
  ssci_part: number
  categories: CategoryScore[]
  flags: { index: number; kind: string }[]
}

export interface PortfolioIn {
  gpa: number
  gpa_prev: number | null
  year_of_study: number
  level: Level
  rules: RulesCode
  records: RecordIn[]
  lang: AppLocale
}

export interface Factor {
  feature: string
  name: string
  value: number
}

export interface Advice {
  kind: 'gpa' | 'record'
  category: string | null
  status: string | null
  gpa_step: number | null
  gain: number
  feasibility: number
  expected: number
  igpa_after: number
  text: string
}

export interface Portfolio {
  now: Calc
  // IGPA-Hybrid: среднее и квантили 300 розыгрышей следующего года, доля розыгрышей со снижением на 0,1+
  forecast: { mean: number; p10: number; p90: number; risk: number; gpa: number; iros: number; ssci: number }
  catboost: { pred: number; risk: number; p10: number; p90: number }
  explanation: Factor[]
  advice: Advice[]
}

export interface StudentBrief {
  student_id: string
  fio: string
  faculty: string
  school: string
  program: string
  level: Level
  intake_year: number
  form: string
  language: string
}

export interface StudentsPage {
  total: number
  items: StudentBrief[]
}

export interface HistoryYear {
  year: number
  year_of_study: number
  gpa: number | null
  true_iros: number
  true_ssci: number
  true_igpa: number | null
  obs_iros: number
  obs_ssci: number
  obs_igpa: number | null
  obs_n: number
  true_n: number
}

export interface StudentRecord {
  year: number
  category: string
  status: string
  title: string
  event_date: string
  state: string
  category_name: string
  status_name: string
}

export interface Student {
  student: StudentBrief
  history: HistoryYear[]
  enrollment: { year: number; year_of_study: number; outcome: string; gpa_year: number | null; gpa_cum: number | null }[]
  records: StudentRecord[]
  backtest: Record<string, number | string | null>[]
  forecast: { igpa_now: number; pred: number; p10: number; p90: number; risk: number; factors: Factor[] } | null
}

// результаты исследования (model/artifacts/v1/research.json): таблицы строками, состав уточняется на страницах
export type ResearchRow = Record<string, number | string | null>
// API отдаёт таблицы и словарь feature_names одним объектом; на сайте они разделены
export type ResearchRaw = Record<string, ResearchRow[]> & { feature_names?: Record<string, string> }
export interface Research {
  tables: Record<string, ResearchRow[]>
  names: Record<string, string>
}
