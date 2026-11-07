// формула IGPA Положения «Туран» (п. 5.4): IGPA = 0,5·GPA + 0,35·iROS + 0,15·SSCI, где iROS и SSCI – доли от 0 до 1,
// переведённые на шкалу 0–4. Правила (Положение, EduScore, потолок 95%) отличаются только тем, как записи АСУ
// превращаются в iROS и SSCI, – сама формула одна, поэтому быстрый расчёт по готовым долям считается здесь же

export const WEIGHTS = { gpa: 0.5, iros: 0.35, ssci: 0.15 } as const
export const SCALE = 4

export interface Parts {
  gpa: number
  iros: number
  ssci: number
  igpa: number
}

const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x))

export function igpaParts(gpa: number, iros: number, ssci: number): Parts {
  const parts = {
    gpa: WEIGHTS.gpa * clamp(gpa, 0, SCALE),
    iros: WEIGHTS.iros * clamp(iros, 0, 1) * SCALE,
    ssci: WEIGHTS.ssci * clamp(ssci, 0, 1) * SCALE,
  }
  return { ...parts, igpa: parts.gpa + parts.iros + parts.ssci }
}

// какой GPA нужен для целевого IGPA при данных долях; null – недостижимо даже с GPA 4,0
export function gpaForTarget(target: number, iros: number, ssci: number): number | null {
  const rest = igpaParts(0, iros, ssci).igpa
  const need = (target - rest) / WEIGHTS.gpa
  if (need > SCALE + 1e-9) return null
  return Math.max(0, need)
}

// доли частей в шкале 0–4 (для полосы формулы): ширины сегментов в процентах
export function shares(p: Parts): { gpa: number; iros: number; ssci: number } {
  return { gpa: (p.gpa / SCALE) * 100, iros: (p.iros / SCALE) * 100, ssci: (p.ssci / SCALE) * 100 }
}
