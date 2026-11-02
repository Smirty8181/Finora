<script setup>
import { RouterLink } from 'vue-router'
import Icon from '../components/Icon.vue'
import ChatWidget from '../components/ChatWidget.vue'
</script>

<template>
  <main class="static-account-page">
    <header class="static-account-header">
      <RouterLink class="brand" to="/" aria-label="Finora — главная"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></RouterLink>
      <RouterLink class="account-back" to="/">На главную <Icon name="arrow" :size="15" /></RouterLink>
    </header>
    <section class="static-account-content">
      <div class="static-preview-banner"><Icon name="shield" :size="19" /><div><strong>Статический preview · только для просмотра</strong><span>API не подключён. Все данные вымышлены; вход, переводы, платежи и изменение баланса недоступны.</span></div></div>
      <div class="static-account-heading"><div class="eyebrow">ДЕМО-МАКЕТ КАБИНЕТА</div><h1>Ваши финансы<br />в одном месте.</h1><p>Этот экран показывает пример интерфейса — не реальный банковский счёт.</p></div>
      <div class="static-balance-card">
        <div><span>Примерный баланс · вымышленные данные</span><strong>125 430 ₽</strong><small>Макетный счёт · •••• 2849</small></div>
        <span class="static-card-mark"><Icon name="wallet" :size="24" /></span>
      </div>
      <section class="static-account-panel">
        <div class="static-panel-heading"><div><div class="eyebrow">ПРИМЕР ДАННЫХ</div><h2>Недавние операции</h2></div><span>Не реальные транзакции</span></div>
        <article class="static-operation"><span class="static-operation-icon"><Icon name="basket" :size="17" /></span><div><strong>Продукты</strong><small>Вымышленная запись · сегодня</small></div><b>− 1 248 ₽</b></article>
        <article class="static-operation"><span class="static-operation-icon income"><Icon name="arrow" :size="17" /></span><div><strong>Поступление</strong><small>Вымышленная запись · сегодня</small></div><b class="income-text">+ 84 500 ₽</b></article>
        <article class="static-operation"><span class="static-operation-icon"><Icon name="coffee" :size="17" /></span><div><strong>Кафе</strong><small>Вымышленная запись · вчера</small></div><b>− 460 ₽</b></article>
      </section>
      <p class="static-account-footnote">Действия, авторизация и любые запросы к финансовой или поддерживающей системе в этом preview отключены.</p>
    </section>
    <ChatWidget />
  </main>
</template>
