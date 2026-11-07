import type { RecordIn } from '../types'

// примеры портфелей для живой формулы на главной и кнопки «Пример» в «Моём портфеле»: три типичных профиля
// синтетического вуза (статусы – из справочника АСУ: ОВПО … за рубежом для науки, университетские … международные
// для разовых, «в течение года» для постоянных проектов)
export interface Sample {
  key: 'scholar' | 'activist' | 'researcher'
  gpa: number
  gpa_prev: number
  year_of_study: number
  records: RecordIn[]
}

export const SAMPLES: Sample[] = [
  { key: 'scholar', gpa: 3.7, gpa_prev: 3.6, year_of_study: 3, records: [{ category: 'IROS_EVENT', status: 'IROS_OVPO' }] },
  {
    key: 'activist',
    gpa: 2.9,
    gpa_prev: 3.0,
    year_of_study: 2,
    records: [
      { category: 'SSCI_STUDENT_ORG', status: 'SSCI_PERMANENT' },
      { category: 'SSCI_LEADERSHIP', status: 'SSCI_PERMANENT' },
      { category: 'SSCI_VOLUNTEER', status: 'SSCI_UNIVERSITY' },
      { category: 'SSCI_VOLUNTEER', status: 'SSCI_CITY_REGION' },
      { category: 'SSCI_INTELLECTUAL', status: 'SSCI_UNIVERSITY' },
      { category: 'SSCI_SPORT', status: 'SSCI_REPUBLIC' },
    ],
  },
  {
    key: 'researcher',
    gpa: 3.3,
    gpa_prev: 3.1,
    year_of_study: 3,
    records: [
      { category: 'IROS_EVENT', status: 'IROS_OVPO' },
      { category: 'IROS_EVENT', status: 'IROS_REP_CITY' },
      { category: 'IROS_TALK', status: 'IROS_INT_RK' },
      { category: 'IROS_PUBLICATION', status: 'IROS_REP_CITY' },
      { category: 'IROS_PRIZE', status: 'IROS_OVPO' },
      { category: 'SSCI_VOLUNTEER', status: 'SSCI_UNIVERSITY' },
    ],
  },
]
