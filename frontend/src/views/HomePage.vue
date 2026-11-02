<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from '../components/Icon.vue'
import ChatWidget from '../components/ChatWidget.vue'
import { APP_BASE_URL, IS_STATIC_DEMO } from '../config'

const menuOpen = ref(false)
const features = [
  { icon: 'wallet', title: 'Всё в одном месте', text: 'Счета, карты и цели — удобно управлять финансами в одном приложении.' },
  { icon: 'shield', title: 'Спокойствие каждый день', text: 'Защита операций и внимательная поддержка, когда она действительно нужна.' },
  { icon: 'chart', title: 'Понятно, куда уходит', text: 'Умная аналитика помогает держать бюджет под контролем без лишних усилий.' },
]
const products = [
  { icon: 'wallet', category: 'КАРТЫ', title: 'Карта на каждый день', description: 'Платите удобно, получайте больше с каждой покупки.', rate: 'До 5%', detail: 'кэшбэк в категориях месяца', tag: 'Обслуживание 0 ₽', theme: 'coral' },
  { icon: 'chart', category: 'ВКЛАДЫ', title: 'Накопления с планом', description: 'Откладывайте на важное и заранее знайте свой доход.', rate: 'до 14,5%', detail: 'годовых на срок до 12 месяцев', tag: 'От 10 000 ₽', theme: 'sage' },
  { icon: 'bank', category: 'КРЕДИТЫ', title: 'На большие планы', description: 'Понятный платёж и ставка, которая не меняется по пути.', rate: 'от 16,9%', detail: 'годовых · от 50 000 до 3 млн ₽', tag: 'До 5 лет', theme: 'sand' },
  { icon: 'arrow', category: 'ПЕРЕВОДЫ', title: 'Деньги — без границ', description: 'Переводите близким в пару касаний, без лишних комиссий.', rate: '0 ₽', detail: 'за переводы до 100 000 ₽ в месяц', tag: 'Мгновенно', theme: 'lilac' },
]
const tariffDetails = [
  { label: 'Обслуживание карты', value: '0 ₽', note: 'без условий и скрытых платежей' },
  { label: 'Снятие в банкоматах', value: 'до 100 000 ₽', note: 'в месяц без комиссии' },
  { label: 'Переводы по номеру телефона', value: '0 ₽', note: 'до 100 000 ₽ в месяц' },
]
const steps = [
  { number: '01', title: 'Откройте демо-кабинет', text: 'Нажмите кнопку и перейдите к тестовой форме входа.' },
  { number: '02', title: 'Введите любой номер', text: 'Для демонстрации используйте код 1234 — СМС не отправляется.' },
  { number: '03', title: 'Изучите макет', text: 'Попробуйте операции: баланс и история изменятся только в интерфейсе.' },
]
let revealObserver

onMounted(() => {
  if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  revealObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      entry.target.classList.add('is-visible')
      revealObserver.unobserve(entry.target)
    }
  }, { threshold: 0.12 })
  document.querySelectorAll('.products-section, .tariffs-section, .benefits-section, .steps-section, .product-card, .feature-card, .step-item')
    .forEach(element => {
      element.classList.add('reveal-in')
      revealObserver.observe(element)
    })
})

onBeforeUnmount(() => revealObserver?.disconnect())

function openChat() { window.dispatchEvent(new Event('finora:open-chat')) }

function moveCard(event) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || event.pointerType !== 'mouse') return
  const bounds = event.currentTarget.getBoundingClientRect()
  const x = (event.clientX - bounds.left) / bounds.width - 0.5
  const y = (event.clientY - bounds.top) / bounds.height - 0.5
  event.currentTarget.style.setProperty('--tilt-x', `${-y * 7}deg`)
  event.currentTarget.style.setProperty('--tilt-y', `${x * 9}deg`)
}

function resetCard(event) {
  event.currentTarget.style.removeProperty('--tilt-x')
  event.currentTarget.style.removeProperty('--tilt-y')
}
</script>

<template>
  <main>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" :href="APP_BASE_URL" aria-label="Finora — главная"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></a>
        <button class="mobile-menu icon-button" aria-label="Открыть меню" @click="menuOpen = !menuOpen"><Icon :name="menuOpen ? 'close' : 'menu'" /></button>
        <nav class="main-nav" :class="{ expanded: menuOpen }">
          <a href="#products" @click="menuOpen = false">Продукты</a><a href="#advantages" @click="menuOpen = false">Преимущества</a><a href="#how" @click="menuOpen = false">Как начать</a><a href="#about" @click="menuOpen = false">О Finora</a>
        </nav>
        <a class="header-login" :href="`${APP_BASE_URL}account`">Личный кабинет <Icon name="arrow" :size="16" /></a>
      </div>
    </header>

    <section class="hero container">
      <div class="hero-copy">
        <div class="eyebrow"><span class="eyebrow-dot"></span> ДЕМО-ПРОЕКТ ВЫМЫШЛЕННОГО БАНКА</div>
        <p v-if="IS_STATIC_DEMO" class="static-demo-notice">Статический preview: API не подключён, ответы чата локальные, все операции отключены.</p>
        <h1>Деньги любят<br />простые <span>решения.</span></h1>
        <p>Финансы могут быть понятными. В Finora всё устроено так, чтобы вы меньше думали о банке и больше — о том, что важно.</p>
        <div class="hero-actions"><a class="button button-primary" :href="`${APP_BASE_URL}account`">Открыть демо-кабинет <Icon name="arrow" :size="17" /></a><a class="button button-quiet" href="#advantages">Узнать больше <Icon name="arrow" :size="16" /></a></div>
        <div class="hero-proof demo-proof"><span class="demo-proof-icon"><Icon name="shield" :size="17" /></span><div><strong>Демонстрационный проект</strong><small>Банк, продукты и все данные вымышлены</small></div></div>
      </div>
      <div class="hero-art" aria-label="Карта Finora" @pointermove="moveCard" @pointerleave="resetCard">
        <div class="art-grid" aria-hidden="true"></div>
        <div class="art-glow"></div>
        <div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div>
        <div class="float-pill pill-top"><span class="float-icon"><Icon name="check" :size="17" /></span><span><strong>Платёж прошёл</strong><small>Только что · 2 450 ₽</small></span></div>
        <div class="bank-card">
          <div class="card-top"><span class="card-logo"><span class="brand-mark"><Icon name="spark" :size="15" /></span> finora</span><span class="card-contactless">)))</span></div>
          <div class="card-chip"><span></span><span></span><span></span><span></span></div>
          <div class="card-number">•••• &nbsp; •••• &nbsp; •••• &nbsp; 2849</div>
          <div class="card-bottom"><span>FINORA DEBIT</span><strong>DEMO</strong></div>
        </div>
        <div class="float-pill pill-bottom"><div class="round-chart"><Icon name="chart" :size="18" /></div><span><small>За этот месяц</small><strong>Всё под контролем</strong></span><span class="trend">↗</span></div>
        <div class="float-pill pill-cashback"><span class="cashback-mark"><Icon name="spark" :size="15" /></span><span><small>Кэшбэк за месяц</small><strong>+1 240 ₽</strong></span><span class="cashback-bars"><i></i><i></i><i></i><i></i><i></i></span></div>
        <div class="art-index"><span>01</span><i></i><span>04</span></div>
        <div class="art-caption"><span class="caption-line"></span>Ваши деньги. Ваши правила.</div>
      </div>
    </section>

    <section id="products" class="products-section">
      <div class="container">
        <div class="section-top products-heading">
          <div><div class="eyebrow">ВАШИ ДЕНЬГИ — ВАШ ВЫБОР</div><h2>Всё нужное.<br /><span>Без лишнего.</span></h2></div>
          <p>Повседневные платежи, накопления и большие планы — под рукой и на понятных условиях.</p>
        </div>
        <div class="product-grid">
          <article v-for="product in products" :key="product.category" class="product-card" :class="`product-${product.theme}`">
            <div class="product-card-top"><span class="product-icon"><Icon :name="product.icon" :size="21" /></span><span class="product-category">{{ product.category }}</span><span class="product-tag">{{ product.tag }}</span></div>
            <h3>{{ product.title }}</h3><p>{{ product.description }}</p>
            <div class="product-rate"><strong>{{ product.rate }}</strong><span>{{ product.detail }}</span></div>
            <a href="#start" class="product-link">Подробнее <Icon name="arrow" :size="16" /></a>
          </article>
        </div>
        <p class="product-disclaimer">Условия и ставки приведены для примера и являются частью вымышленного предложения Finora.</p>
      </div>
    </section>

    <section class="tariffs-section">
      <div class="container tariffs-layout">
        <div class="tariffs-intro">
          <div class="eyebrow">ЧЕСТНО О ТАРИФАХ</div>
          <h2>Прозрачно.<br />С самого начала.</h2>
          <p>Никаких мелких звёздочек: основные условия карты собраны здесь.</p>
          <a href="#start" class="text-link" @click.prevent="openChat">Задать вопрос Нове <Icon name="arrow" :size="16" /></a>
          <div class="tariff-footnote"><Icon name="shield" :size="15" /> Без платы за выпуск и обслуживание</div>
        </div>
        <div class="tariff-table">
          <div class="tariff-table-head"><span>ТАРИФ FINORA DAILY</span><span>УСЛОВИЯ</span></div>
          <article v-for="tariff in tariffDetails" :key="tariff.label" class="tariff-row"><div><strong>{{ tariff.label }}</strong><small>{{ tariff.note }}</small></div><b>{{ tariff.value }}</b></article>
          <div class="tariff-bottom"><span>Кэшбэк в выбранных категориях</span><strong>до 5% <small>· до 3 000 ₽ в месяц</small></strong></div>
          <p>Ставки и лимиты вымышлены и приведены для демонстрации интерфейса. Перед оформлением уточняйте актуальные условия.</p>
        </div>
      </div>
    </section>

    <section id="advantages" class="benefits-section">
      <div class="container">
        <div class="section-top"><div><div class="eyebrow">ВАША ФИНАНСОВАЯ СВОБОДА</div><h2>Банк, который<br />на вашей стороне.</h2></div><p>Понятные условия, никаких неожиданных мелочей. Только то, что помогает жить проще.</p></div>
        <div class="feature-grid">
          <article v-for="(feature, index) in features" :key="feature.title" class="feature-card">
            <span class="feature-number">0{{ index + 1 }}</span><div class="feature-icon"><Icon :name="feature.icon" :size="23" /></div><h3>{{ feature.title }}</h3><p>{{ feature.text }}</p><a href="#start" aria-label="Подробнее"><Icon name="arrow" :size="17" /></a>
          </article>
        </div>
      </div>
    </section>

    <section id="how" class="steps-section container">
      <div class="steps-heading"><div class="eyebrow">ПОПРОБУЙТЕ ДЕМО</div><h2>Три шага —<br />и макет готов.</h2><p>Проверьте клиентский сценарий без регистрации и реальных финансовых операций.</p><a :href="`${APP_BASE_URL}account`" class="text-link">Открыть демо-кабинет <Icon name="arrow" :size="16" /></a></div>
      <div class="steps-list"><article v-for="step in steps" :key="step.number" class="step-item"><span>{{ step.number }}</span><div><h3>{{ step.title }}</h3><p>{{ step.text }}</p></div><Icon name="chevron" :size="19" /></article></div>
    </section>

    <section id="start" class="cta-band container">
      <div class="cta-shape"></div><div class="cta-content"><div class="eyebrow">ИНТЕРАКТИВНЫЙ МАКЕТ</div><h2>Посмотрите,<br />как устроена Finora.</h2><p>Проверьте интерфейс кабинета и работу чат-помощника на демонстрационных данных.</p><a class="button button-light" :href="`${APP_BASE_URL}account`">Открыть демо-кабинет <Icon name="arrow" :size="17" /></a></div><div class="cta-stamp"><Icon name="spark" :size="28" /> <span>Демо-<br />проект</span></div>
    </section>
    <footer id="about" class="site-footer"><div class="container footer-inner"><a class="brand" :href="APP_BASE_URL"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></a><span>Finora — демонстрационный проект. Все данные вымышлены.</span><a :href="`${APP_BASE_URL}staff`">Для сотрудников <Icon name="arrow" :size="14" /></a></div></footer>
    <ChatWidget />
  </main>
</template>
