<script setup lang="ts">
import { onMounted } from 'vue'
import FooterSection from './components/FooterSection.vue'
import NavBar from './components/NavBar.vue'
import ServerBanner from './components/ServerBanner.vue'
import { useServerStatus } from './composables/useServerStatus'
import { viewTransitions } from './router/transitions'

const { wake } = useServerStatus()
onMounted(wake) // будим API сразу при открытии сайта
</script>

<template>
  <NavBar />
  <ServerBanner />
  <main class="min-h-[70dvh]">
    <!-- переход между страницами: старая гаснет, новая проявляется снизу -->
    <RouterView v-slot="{ Component, route }">
      <Transition :name="viewTransitions ? 'none' : 'page'" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </RouterView>
  </main>
  <FooterSection />
</template>
