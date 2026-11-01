<script setup>
import { computed, nextTick, ref } from 'vue'
import { RouterLink } from 'vue-router'
import Icon from '../components/Icon.vue'
import ChatWidget from '../components/ChatWidget.vue'

const isSignedIn = ref(sessionStorage.getItem('finora_demo_account') === 'true')
const phone = ref('')
const code = ref('')
const codeInput = ref(null)
const loginStep = ref('phone')
const loginError = ref('')
const search = ref('')
const selectedPeriod = ref('За месяц')
const selectedExpensePeriod = ref('Октябрь')
const balance = ref(125430)
const savingsBalance = ref(0)
const hasSavingsAccount = ref(false)
const activeDialog = ref('')
const actionName = ref('')
const actionRecipient = ref('')
const actionAmount = ref('')
const actionError = ref('')
const accountNotice = ref('')
const showNotifications = ref(false)
const isNotificationsRead = ref(false)
const isSearchOpen = ref(false)
const showAccountBalance = ref(localStorage.getItem('finora_show_account_balance') !== 'false')
const highlightUnreadNotifications = ref(localStorage.getItem('finora_highlight_notifications') !== 'false')
const draftShowAccountBalance = ref(showAccountBalance.value)
const draftHighlightUnreadNotifications = ref(highlightUnreadNotifications.value)
const monthlyChart = [24, 35, 29, 45, 37, 53, 46, 63, 54, 72, 66, 86, 74, 94, 82, 100, 91, 112]
const weeklyChart = [31, 44, 37, 56, 49, 66, 58, 80, 72, 94, 84, 108]
const actions = [
  { icon: 'arrow', title: 'Перевод', type: 'transfer' },
  { icon: 'wallet', title: 'Пополнение', type: 'topup' },
  { icon: 'home', title: 'Оплата ЖКУ', type: 'utility' },
  { icon: 'more', title: 'Ещё', type: 'more' },
]
const operations = ref([
  { merchant: 'Пятёрочка', detail: 'Сегодня, 14:32 · Продукты', amount: '− 1 248 ₽', icon: 'basket', kind: 'spend' },
  { merchant: 'Зарплата', detail: 'Сегодня, 09:14 · Перевод', amount: '+ 84 500 ₽', icon: 'arrow', kind: 'income' },
  { merchant: 'Кофемания', detail: 'Вчера, 18:07 · Кафе', amount: '− 460 ₽', icon: 'coffee', kind: 'spend' },
  { merchant: 'Кэшбэк за покупки', detail: 'Вчера, 10:00 · Бонусы', amount: '+ 1 240 ₽', icon: 'spark', kind: 'income' },
])
const visibleOperations = computed(() => operations.value.filter(operation =>
  `${operation.merchant} ${operation.detail}`.toLowerCase().includes(search.value.toLowerCase()),
))
const totalBalance = computed(() => balance.value + savingsBalance.value)
const codeDigits = computed(() => code.value.padEnd(4, ' ').slice(0, 4).split(''))

function formatPhoneInput(event) {
  let digits = event.target.value.replace(/\D/g, '')
  if (digits.length > 10 && ['7', '8'].includes(digits[0])) digits = digits.slice(1)
  digits = digits.slice(0, 10)
  const first = digits.slice(0, 3)
  const second = digits.slice(3, 6)
  const third = digits.slice(6, 8)
  const fourth = digits.slice(8, 10)
  phone.value = `+7${first ? ` (${first}${first.length === 3 ? ')' : ''}` : ''}${second ? ` ${second}` : ''}${third ? `-${third}` : ''}${fourth ? `-${fourth}` : ''}`
}

function formatCodeInput(event) {
  code.value = event.target.value.replace(/\D/g, '').slice(0, 4)
}

function requestCode() {
  const digits = phone.value.replace(/\D/g, '')
  if (digits.length < 11) {
    loginError.value = 'Введите номер телефона целиком.'
    return
  }
  loginError.value = ''
  loginStep.value = 'code'
  code.value = ''
  nextTick(() => codeInput.value?.focus())
}

function enterDemo() {
  if (code.value !== '1234') {
    loginError.value = 'Для демонстрации введите код 1234.'
    return
  }
  sessionStorage.setItem('finora_demo_account', 'true')
  isSignedIn.value = true
  loginError.value = ''
}

function logout() {
  sessionStorage.removeItem('finora_demo_account')
  isSignedIn.value = false
  loginStep.value = 'phone'
  code.value = ''
}

function changePhone() {
  loginStep.value = 'phone'
  loginError.value = ''
  code.value = ''
}

function openChat() {
  window.dispatchEvent(new Event('finora:open-chat'))
}

const dialogTitle = computed(() => ({
  transfer: 'Новый перевод',
  topup: 'Пополнение карты',
  utility: 'Оплата услуг',
  cards: 'Ваши карты',
  savings_topup: 'Пополнение накопительного счёта',
  savings: 'Накопительный счёт',
  settings: 'Настройки кабинета',
  more: 'Другие действия',
}[activeDialog.value] || 'Finora'))

function openDialog(type) {
  activeDialog.value = type
  actionRecipient.value = ''
  actionAmount.value = ''
  actionError.value = ''
  if (type === 'settings') {
    draftShowAccountBalance.value = showAccountBalance.value
    draftHighlightUnreadNotifications.value = highlightUnreadNotifications.value
  }
  showNotifications.value = false
}

function closeDialog() {
  activeDialog.value = ''
  actionError.value = ''
}

function showNotice(message) {
  accountNotice.value = message
  window.setTimeout(() => {
    if (accountNotice.value === message) accountNotice.value = ''
  }, 3200)
}

function openSavingsAccount() {
  hasSavingsAccount.value = true
  showNotice('Демо-накопительный счёт открыт. Реальные деньги не перемещались.')
}

function confirmAction() {
  const amount = Number(actionAmount.value)
  if (!Number.isFinite(amount) || amount <= 0) {
    actionError.value = 'Укажите сумму больше нуля.'
    return
  }
  if (activeDialog.value === 'transfer' || activeDialog.value === 'utility') {
    if (!actionRecipient.value.trim()) {
      actionError.value = activeDialog.value === 'transfer'
        ? 'Укажите имя или телефон получателя.'
        : 'Укажите лицевой счёт или поставщика.'
      return
    }
  }
  if (activeDialog.value === 'savings_topup' || activeDialog.value === 'transfer' || activeDialog.value === 'utility') {
    if (amount > balance.value) {
      actionError.value = activeDialog.value === 'savings_topup'
        ? 'На основной карте недостаточно средств.'
        : 'На демо-счёте недостаточно средств.'
      return
    }
    balance.value -= amount
    if (activeDialog.value === 'savings_topup') savingsBalance.value += amount
  } else {
    balance.value += amount
  }
  const date = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date())
  const isSavingsTopup = activeDialog.value === 'savings_topup'
  operations.value.unshift({
    merchant: activeDialog.value === 'transfer'
      ? `Перевод · ${actionRecipient.value.trim()}`
      : activeDialog.value === 'utility'
        ? `Оплата · ${actionRecipient.value.trim()}`
        : isSavingsTopup
          ? 'Пополнение накопительного счёта'
          : 'Пополнение карты',
    detail: `Сегодня, ${date} · Демо-операция`,
    amount: `${activeDialog.value === 'topup' ? '+' : '−'} ${amount.toLocaleString('ru-RU')} ₽`,
    icon: activeDialog.value === 'topup' ? 'wallet' : activeDialog.value === 'utility' ? 'home' : isSavingsTopup ? 'chart' : 'arrow',
    kind: activeDialog.value === 'topup' ? 'income' : 'spend',
  })
  search.value = ''
  closeDialog()
  showNotice(isSavingsTopup
    ? 'Демо-перевод в накопления выполнен. Реальные деньги не перемещались.'
    : 'Демо-операция выполнена. Реальные деньги не перемещались.')
}

function cycleExpensePeriod() {
  selectedExpensePeriod.value = selectedExpensePeriod.value === 'Октябрь' ? 'Сентябрь' : 'Октябрь'
}

function markNotificationsRead() {
  isNotificationsRead.value = true
  showNotice('Уведомления отмечены как прочитанные.')
}

function saveSettings() {
  showAccountBalance.value = draftShowAccountBalance.value
  highlightUnreadNotifications.value = draftHighlightUnreadNotifications.value
  localStorage.setItem('finora_show_account_balance', String(showAccountBalance.value))
  localStorage.setItem('finora_highlight_notifications', String(highlightUnreadNotifications.value))
  closeDialog()
  showNotice('Настройки демо-кабинета сохранены.')
}
</script>

<template>
  <main class="account-page">
    <header class="account-topbar">
      <RouterLink class="brand" to="/" aria-label="Finora — главная"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></RouterLink>
      <div v-if="isSignedIn" class="account-top-actions">
        <div class="account-search" :class="{ 'mobile-search-open': isSearchOpen }"><Icon name="search" :size="16" /><input v-model="search" aria-label="Поиск по операциям" placeholder="Поиск по операциям…" /><button v-if="search" type="button" aria-label="Очистить поиск" @click="search = ''"><Icon name="close" :size="15" /></button></div>
        <button class="account-icon-button account-search-toggle" :aria-label="isSearchOpen ? 'Закрыть поиск' : 'Открыть поиск'" :aria-expanded="isSearchOpen" @click="isSearchOpen = !isSearchOpen"><Icon :name="isSearchOpen ? 'close' : 'search'" :size="17" /></button>
        <div class="account-notification-wrap">
          <button class="account-icon-button" :class="{ 'has-unread': !isNotificationsRead && highlightUnreadNotifications }" aria-label="Открыть уведомления" :aria-expanded="showNotifications" @click="showNotifications = !showNotifications"><Icon name="bell" :size="17" /></button>
          <section v-if="showNotifications" class="account-notification-popover">
            <div class="notification-heading"><strong>Уведомления</strong><button @click="markNotificationsRead">Прочитать все</button></div>
            <article :class="{ read: isNotificationsRead }"><span class="notification-dot"></span><div><strong>Кешбэк начислен</strong><p>На счёт поступило 1 240 ₽ за покупки.</p><small>Сегодня, 10:00</small></div></article>
            <article class="read"><span class="notification-dot muted"></span><div><strong>Платёж прошёл</strong><p>Оплата в «Пятёрочке» на 1 248 ₽.</p><small>Сегодня, 14:32</small></div></article>
          </section>
        </div>
        <button class="account-user" @click="logout"><span>А</span><strong>Артём</strong><Icon name="logout" :size="14" /></button>
      </div>
      <RouterLink v-else class="account-back" to="/">На главную <Icon name="arrow" :size="15" /></RouterLink>
    </header>

    <section v-if="!isSignedIn" class="account-login-wrap">
      <div class="account-login-art">
        <span class="login-art-orbit"></span>
        <span class="login-art-glow"></span>
        <div class="account-card-preview">
          <div class="card-logo"><span class="brand-mark"><Icon name="spark" :size="14" /></span> finora</div>
          <span class="account-chip"></span>
          <strong>•••• &nbsp; •••• &nbsp; •••• &nbsp; 2849</strong>
          <div><small>FINORA DEBIT</small><b>DEMO</b></div>
        </div>
        <div class="login-security-chip"><span><Icon name="shield" :size="16" /></span><div><strong>Тестовый вход</strong><small>Данные не отправляются</small></div></div>
        <p>Ваши финансы<br />в одном месте.</p>
        <span class="account-demo-note">Демонстрационный кабинет · все данные вымышлены</span>
      </div>
      <div class="account-login-card">
        <div class="account-login-topline"><div class="account-login-icon"><Icon name="lock" :size="21" /></div><span class="login-step-indicator"><i :class="{ active: loginStep === 'phone' }"></i><i :class="{ active: loginStep === 'code' }"></i></span></div>
        <div class="eyebrow">ДЕМО-КАБИНЕТ FINORA</div>
        <h1>{{ loginStep === 'phone' ? 'Рады вас видеть.' : 'Введите демо-код.' }}</h1>
        <p>{{ loginStep === 'phone' ? 'Введите любой номер, чтобы открыть демонстрационный кабинет.' : `Введите демонстрационный код для номера ${phone}.` }}</p>
        <form v-if="loginStep === 'phone'" @submit.prevent="requestCode">
          <label for="account-phone">Номер телефона</label>
          <div class="login-input-wrap"><Icon name="phone" :size="18" /><input id="account-phone" :value="phone" type="tel" inputmode="tel" autocomplete="tel" maxlength="18" placeholder="+7 (___) ___-__-__" required @input="formatPhoneInput" /></div>
          <button class="button button-primary account-submit">Продолжить <Icon name="arrow" :size="16" /></button>
        </form>
        <form v-else @submit.prevent="enterDemo">
          <label for="account-code">Демонстрационный код</label>
          <div class="otp-input">
            <div class="otp-slots" aria-hidden="true">
              <span v-for="(digit, index) in codeDigits" :key="index" :class="{ filled: code.length > index, current: code.length === index }">{{ code.length > index ? '•' : '' }}</span>
            </div>
            <input id="account-code" ref="codeInput" :value="code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="12" aria-label="Введите четыре цифры кода" required @input="formatCodeInput" />
          </div>
          <p class="demo-code-hint"><Icon name="lock" :size="13" /> Код для демонстрации: <strong>1234</strong></p>
          <button class="button button-primary account-submit">Войти в кабинет <Icon name="arrow" :size="16" /></button>
          <button type="button" class="account-back-step" @click="changePhone">Изменить номер</button>
        </form>
        <p v-if="loginError" class="form-error account-error" role="alert">{{ loginError }}</p>
        <div class="account-safety"><Icon name="shield" :size="15" /><span>Здесь нет реального входа: проект демонстрационный, данные не отправляются на сервер.</span></div>
        <button class="account-login-help" @click="openChat"><Icon name="headset" :size="15" /> Нужна помощь с входом? Спросите Нову</button>
      </div>
    </section>

    <section v-else class="account-dashboard">
      <aside class="account-sidebar">
        <div class="account-nav-label">МЕНЮ</div>
        <a class="account-nav-item active" href="#overview"><Icon name="home" :size="16" />Главная</a>
        <a class="account-nav-item" href="#transfers" @click.prevent="openDialog('transfer')"><Icon name="arrow" :size="16" />Переводы</a>
        <a class="account-nav-item" href="#cards" @click.prevent="openDialog('cards')"><Icon name="wallet" :size="16" />Карты</a>
        <a class="account-nav-item" href="#analytics"><Icon name="chart" :size="16" />Аналитика</a>
        <a class="account-nav-item" href="#support" @click.prevent="openChat"><Icon name="headset" :size="16" />Поддержка</a>
        <button class="account-nav-item account-nav-button" @click="openDialog('settings')"><Icon name="settings" :size="16" />Настройки</button>
        <div class="account-sidebar-promo"><span class="promo-icon"><Icon name="spark" :size="17" /></span><strong>Копите больше<br />с Finora</strong><small>Накопительный счёт — до 14,5% годовых</small><button @click="openDialog('savings')">Подробнее <Icon name="arrow" :size="13" /></button></div>
        <RouterLink class="account-staff-link" to="/staff">Для сотрудников</RouterLink>
      </aside>

      <div id="overview" class="account-content">
        <header class="account-welcome">
          <div><div class="eyebrow">ВОСКРЕСЕНЬЕ, 1 НОЯБРЯ</div><h1>Привет, Артём</h1><p>Хорошего дня. Пусть финансы работают на вас.</p></div>
          <span class="account-demo-badge"><i></i> Демо-режим</span>
        </header>

        <div class="account-dashboard-grid">
          <section id="analytics" class="account-balance-panel">
            <div class="account-panel-heading"><span>Общий баланс</span><button aria-label="Изменить период баланса" @click="selectedPeriod = selectedPeriod === 'За месяц' ? 'За неделю' : 'За месяц'">{{ selectedPeriod }} <Icon name="chevron" :size="13" /></button></div>
            <strong class="balance-amount">{{ showAccountBalance ? totalBalance.toLocaleString('ru-RU') : '••••••' }} <small v-if="showAccountBalance">₽</small></strong>
            <div class="balance-change"><Icon name="arrow" :size="14" /> {{ selectedPeriod === 'За месяц' ? '+12,8% за месяц' : '+3,2% за неделю' }}</div>
            <div class="balance-chart" :aria-label="`График баланса ${selectedPeriod.toLowerCase()}`">
              <span v-for="(height, index) in selectedPeriod === 'За месяц' ? monthlyChart : weeklyChart" :key="index" :style="{ height: `${height}px` }"></span>
            </div>
            <div class="chart-labels"><span>{{ selectedPeriod === 'За месяц' ? '1 окт' : 'Пн' }}</span><span>{{ selectedPeriod === 'За месяц' ? '15 окт' : 'Чт' }}</span><span>{{ selectedPeriod === 'За месяц' ? '31 окт' : 'Вс' }}</span></div>
          </section>

          <section class="account-shortcuts">
            <button v-for="action in actions" :key="action.title" class="account-shortcut" @click="action.type === 'more' ? openDialog('more') : openDialog(action.type)">
              <span><Icon :name="action.icon" :size="17" /></span>{{ action.title }}
            </button>
          </section>

          <section id="cards" class="account-panel account-card-panel">
            <div class="account-panel-heading"><h2>Ваши карты</h2><button @click="openDialog('cards')">Все карты <Icon name="arrow" :size="13" /></button></div>
            <div class="account-card-row">
              <div class="account-mini-card"><span>finora</span><strong>•••• 2849</strong><small>DEMO</small></div>
              <div><span class="account-muted">Основная карта</span><strong class="mini-balance">{{ showAccountBalance ? `${balance.toLocaleString('ru-RU')} ₽` : '••••••' }}</strong><button class="button button-primary mini-button" @click="openDialog('topup')">Пополнить</button></div>
            </div>
          </section>

          <section class="account-panel spending-panel">
            <div class="account-panel-heading"><h2>Расходы за месяц</h2><button aria-label="Сменить месяц расходов" @click="cycleExpensePeriod">{{ selectedExpensePeriod }} <Icon name="chevron" :size="13" /></button></div>
            <div class="spending-content"><div class="spending-ring" :style="{ '--spending-purchases': selectedExpensePeriod === 'Октябрь' ? '72%' : '64%', '--spending-transfers': selectedExpensePeriod === 'Октябрь' ? '91%' : '88%' }"><strong>{{ selectedExpensePeriod === 'Октябрь' ? '72' : '64' }}<small>%</small></strong></div><ul><li><i></i><span>Покупки</span><b>{{ selectedExpensePeriod === 'Октябрь' ? '72' : '64' }}%</b></li><li><i></i><span>Переводы</span><b>{{ selectedExpensePeriod === 'Октябрь' ? '18' : '24' }}%</b></li><li><i></i><span>Другое</span><b>10%</b></li></ul></div>
          </section>

          <section id="transfers" class="account-panel operations-panel">
            <div class="account-panel-heading"><h2>Последние операции</h2><button @click="search = ''; showNotice('Показаны все операции демо-счёта.')">Все операции <Icon name="arrow" :size="13" /></button></div>
            <article v-for="operation in visibleOperations" :key="operation.merchant" class="account-operation">
              <span class="operation-icon" :class="operation.kind"><Icon :name="operation.icon" :size="16" /></span>
              <div><strong>{{ operation.merchant }}</strong><small>{{ operation.detail }}</small></div>
              <b :class="operation.kind">{{ operation.amount }}</b>
            </article>
            <p v-if="!visibleOperations.length" class="account-no-results">Операций по этому запросу нет.</p>
          </section>

          <section class="account-panel account-savings-panel">
            <div class="savings-decoration"></div>
            <span class="account-muted">НАКОПИТЕЛЬНЫЙ СЧЁТ</span>
            <h2>{{ hasSavingsAccount ? 'Ваши накопления' : 'Копите больше с Finora' }}</h2>
            <p>{{ hasSavingsAccount ? `На счёте ${savingsBalance.toLocaleString('ru-RU')} ₽. Демо-условия — до 14,5% годовых.` : 'Попробуйте отложить на цель — проценты начисляются каждый день.' }}</p>
            <button @click="openDialog('savings')">{{ hasSavingsAccount ? 'Управлять счётом' : 'Открыть накопительный счёт' }} <Icon name="arrow" :size="14" /></button>
          </section>
        </div>
        <p class="account-disclaimer">Демонстрационный интерфейс. Все суммы, операции и условия вымышлены.</p>
      </div>
    </section>
    <Transition name="fade">
      <div v-if="activeDialog" class="account-dialog-backdrop" @click.self="closeDialog" @keydown.esc.window="closeDialog">
        <section class="account-dialog" role="dialog" aria-modal="true" :aria-label="dialogTitle">
          <header><div><span class="eyebrow">ДЕМО-КАБИНЕТ FINORA</span><h2>{{ dialogTitle }}</h2></div><button class="account-dialog-close" aria-label="Закрыть окно" @click="closeDialog"><Icon name="close" :size="19" /></button></header>
          <form v-if="['transfer', 'topup', 'utility', 'savings_topup'].includes(activeDialog)" @submit.prevent="confirmAction">
            <p class="dialog-explanation">
              {{ activeDialog === 'transfer' ? 'Переведите деньги на другой демо-счёт.' : activeDialog === 'utility' ? 'Запишите демонстрационный платёж за услугу.' : activeDialog === 'savings_topup' ? 'Переведите деньги с основной карты на накопительный счёт.' : 'Добавьте сумму к балансу демо-карты.' }}
              Реальные деньги не перемещаются.
            </p>
            <label v-if="['transfer', 'utility'].includes(activeDialog)" for="action-recipient">{{ activeDialog === 'transfer' ? 'Получатель' : 'Поставщик или лицевой счёт' }}</label>
            <input v-if="['transfer', 'utility'].includes(activeDialog)" id="action-recipient" v-model="actionRecipient" :placeholder="activeDialog === 'transfer' ? 'Имя или телефон' : 'Например, ЖКУ'" required />
            <label for="action-amount">Сумма, ₽</label>
            <input id="action-amount" v-model="actionAmount" type="number" min="1" step="1" placeholder="Например, 1500" required />
            <p v-if="actionError" class="form-error account-error" role="alert">{{ actionError }}</p>
            <div class="dialog-actions"><button type="button" class="button account-cancel" @click="closeDialog">Отмена</button><button class="button button-primary">Подтвердить демо-операцию</button></div>
          </form>
          <div v-else-if="activeDialog === 'more'" class="dialog-option-list">
            <button @click="openDialog('utility')"><Icon name="home" :size="19" /><span><strong>Оплатить услуги</strong><small>Создать демо-платёж ЖКУ</small></span><Icon name="chevron" :size="17" /></button>
            <button @click="openDialog('savings')"><Icon name="chart" :size="19" /><span><strong>Накопления</strong><small>Посмотреть условия демо-вклада</small></span><Icon name="chevron" :size="17" /></button>
            <button @click="openDialog('cards')"><Icon name="wallet" :size="19" /><span><strong>Мои карты</strong><small>Просмотр карты Finora</small></span><Icon name="chevron" :size="17" /></button>
          </div>
          <div v-else-if="activeDialog === 'cards'" class="dialog-product">
            <div class="account-mini-card large"><span>finora</span><strong>•••• 2849</strong><small>DEMO</small></div>
            <p><strong>Основная дебетовая карта</strong><br />Обслуживание — 0 ₽ в демо-тарифе. Все данные вымышлены.</p>
            <button class="button button-primary" @click="openDialog('topup')">Пополнить карту</button>
          </div>
          <div v-else-if="activeDialog === 'savings'" class="dialog-product">
            <div class="savings-rate">{{ hasSavingsAccount ? `${savingsBalance.toLocaleString('ru-RU')} ₽` : 'до 14,5%' }} <small>{{ hasSavingsAccount ? 'на счёте' : 'годовых*' }}</small></div>
            <p>{{ hasSavingsAccount ? 'Демо-накопительный счёт открыт. Пополните его переводом с основной карты.' : 'Откройте демо-накопительный счёт, чтобы следить за накоплениями. Условия и ставка приведены только для макета.' }}</p>
            <button v-if="hasSavingsAccount" class="button button-primary" @click="openDialog('savings_topup')">Пополнить накопления</button>
            <button v-else class="button button-primary" @click="openSavingsAccount">Открыть демо-счёт</button>
            <small class="dialog-footnote">* Вымышленная ставка, не является предложением банка.</small>
          </div>
          <div v-else class="dialog-settings">
            <p>Параметры демонстрационного кабинета</p>
            <label><input v-model="draftShowAccountBalance" type="checkbox" /> Показывать баланс на главной</label>
            <label><input v-model="draftHighlightUnreadNotifications" type="checkbox" /> Подсвечивать новые уведомления</label>
            <button class="button button-primary" @click="saveSettings">Сохранить настройки</button>
          </div>
        </section>
      </div>
    </Transition>
    <Transition name="fade"><div v-if="accountNotice" class="account-toast" role="status">{{ accountNotice }}</div></Transition>
    <ChatWidget />
  </main>
</template>
