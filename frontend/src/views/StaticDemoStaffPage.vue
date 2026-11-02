<script setup>
import { RouterLink } from 'vue-router'
import Icon from '../components/Icon.vue'
</script>

<template>
  <main class="static-staff-page">
    <RouterLink class="brand" to="/" aria-label="Finora — главная"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></RouterLink>
    <section>
      <div class="static-preview-banner"><Icon name="lock" :size="19" /><div><strong>Рабочее место поддержки отключено</strong><span>Статический preview не подключается к API, не принимает учётные данные и не показывает обращения.</span></div></div>
      <h1>Только публичная демонстрация</h1>
      <p>В этом preview нет входа для сотрудников, клиентских сообщений или действий с обращениями.</p>
      <RouterLink class="button button-primary" to="/">Вернуться на главную <Icon name="arrow" :size="16" /></RouterLink>
    </section>
  </main>
</template>
