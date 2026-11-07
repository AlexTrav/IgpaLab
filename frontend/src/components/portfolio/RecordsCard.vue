<script setup lang="ts">
import { onClickOutside } from '@vueuse/core'
import { ChevronDown, Plus, Sparkles, Trash2, Trophy, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMeta } from '../../composables/useMeta'
import { usePortfolio } from '../../composables/usePortfolio'
import { SAMPLES } from '../../utils/samples'

// достижения так же, как в АСУ: тип из 16, статус – только из тех, что подходят типу; новые записи «влетают» сверху
const { t } = useI18n()
const { meta, categories, statuses } = useMeta()
const { state, result, add, remove, clear, loadSample, counts } = usePortfolio()

const category = ref('IROS_EVENT')
const status = ref('')
const allowed = computed(() => categories.value.get(category.value)?.statuses ?? [])
watch(allowed, (list) => {
  if (!list.includes(status.value)) status.value = list[0] ?? ''
}, { immediate: true })
const groups = computed(() => [
  { key: 'IROS', items: (meta.value?.categories ?? []).filter((c) => c.profile === 'IROS') },
  { key: 'SSCI', items: (meta.value?.categories ?? []).filter((c) => c.profile === 'SSCI') },
])

// пометки калькулятора к записям (сверх предела пяти записей, тип не считается в этом правиле); индекс – порядок
// записей в запросе, он совпадает с порядком списка
const flags = computed(() => {
  const out = new Map<number, string>()
  for (const f of result.value?.now.flags ?? []) {
    const rec = state.records[f.index]
    if (rec) out.set(rec.id, f.kind)
  }
  return out
})

const samplesOpen = ref(false)
const samplesBox = ref<HTMLElement | null>(null)
onClickOutside(samplesBox, () => (samplesOpen.value = false))
</script>

<template>
  <div class="card p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="flex items-center gap-2 font-bold"><Trophy class="h-5 w-5 text-accent" />{{ t('portfolio.records') }}</h2>
      <div class="flex gap-2">
        <div ref="samplesBox" class="relative">
          <button class="btn-ghost !py-1.5" :aria-expanded="samplesOpen" @click="samplesOpen = !samplesOpen">
            <Sparkles class="h-4 w-4" />{{ t('portfolio.sample') }}<ChevronDown class="h-4 w-4" />
          </button>
          <div v-if="samplesOpen" class="absolute right-0 z-20 mt-2 w-56 rounded-2xl border border-line bg-surface p-1.5 shadow-xl">
            <button
              v-for="s in SAMPLES"
              :key="s.key"
              class="block w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-2"
              @click="loadSample(s), (samplesOpen = false)"
            >
              {{ t(`samples.${s.key}`) }}
            </button>
          </div>
        </div>
        <button v-if="state.records.length" class="btn-ghost !py-1.5" @click="clear"><Trash2 class="h-4 w-4" />{{ t('portfolio.clear') }}</button>
      </div>
    </div>

    <!-- добавление записи -->
    <form class="mt-5 grid gap-3 rounded-2xl bg-surface-2 p-4" @submit.prevent="add(category, status)">
      <div>
        <label class="label" for="cat">{{ t('portfolio.type') }}</label>
        <select id="cat" v-model="category" class="field" :disabled="!meta">
          <optgroup v-for="g in groups" :key="g.key" :label="t(`portfolio.group${g.key}`)">
            <option v-for="c in g.items" :key="c.code" :value="c.code">{{ c.name }}</option>
          </optgroup>
        </select>
      </div>
      <div class="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <label class="label" for="status">{{ t('portfolio.status') }}</label>
          <select id="status" v-model="status" class="field" :disabled="!meta">
            <option v-for="s in allowed" :key="s" :value="s">{{ statuses.get(s)?.name ?? s }}</option>
          </select>
        </div>
        <button v-ripple type="submit" class="btn-primary" :disabled="!meta || !status"><Plus class="h-4 w-4" />{{ t('portfolio.add') }}</button>
      </div>
    </form>

    <p class="mt-5 text-sm text-muted">
      {{ t('portfolio.count', { iros: counts.iros, ssci: counts.ssci }) }}
    </p>
    <TransitionGroup tag="ul" name="list" class="relative mt-3 space-y-2">
      <li
        v-for="r in state.records"
        :key="r.id"
        class="flex items-start gap-3 rounded-2xl border border-line px-3.5 py-2.5"
        :class="flags.get(r.id) && 'border-dashed opacity-70'"
      >
        <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" :class="r.category.startsWith('IROS') ? 'bg-iros' : 'bg-ssci'" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="text-sm leading-snug font-medium">{{ categories.get(r.category)?.name ?? r.category }}</p>
          <p class="text-xs text-faint">
            {{ statuses.get(r.status)?.name ?? r.status }}
            <span v-if="flags.get(r.id)" class="ml-1 font-semibold text-accent">· {{ t(`flags.${flags.get(r.id)}`) }}</span>
          </p>
        </div>
        <button class="rounded-full p-1 text-faint transition-colors hover:bg-surface-2 hover:text-bad" :aria-label="t('portfolio.remove')" @click="remove(r.id)">
          <X class="h-4 w-4" />
        </button>
      </li>
    </TransitionGroup>
    <p v-if="!state.records.length" class="mt-3 rounded-2xl border border-dashed border-line px-4 py-6 text-center text-sm text-faint">
      {{ t('portfolio.empty') }}
    </p>
  </div>
</template>
