<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import PageHeader from '../components/PageHeader.vue'

// раздел в работе: заменяется полной страницей в следующих подшагах 9
const { t } = useI18n()
</script>

<template>
  <PageHeader :eyebrow="t('nav.quick')" :title="t('nav.quick')" :lead="t('common.soon')" />
</template>
