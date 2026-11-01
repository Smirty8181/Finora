<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import Icon from '../components/Icon.vue'

const tokenKey = 'finora_staff_token'
const token = ref(localStorage.getItem(tokenKey) || '')
const username = ref('')
const password = ref('')
const loginError = ref('')
const busy = ref(false)
const tickets = ref([])
const unanswered = ref([])
const selected = ref(null)
const messages = ref([])
const reply = ref('')
const filter = ref('all')
const query = ref('')
const notice = ref('')
const markingNovaWrong = ref(false)
const socket = ref(null)
const messagesEnd = ref(null)
const unansweredPanel = ref(null)

const currentTicket = computed(() => tickets.value.find(ticket => String(ticket.id) === String(selected.value)))
const normalizedStatus = status => {
  const value = String(status || 'new').toLowerCase().replace(/[\s-]+/g, '_')
  if (['closed', 'resolved', 'done'].includes(value)) return 'closed'
  if (['in_progress', 'assigned', 'active', 'working'].includes(value)) return 'in_progress'
  return 'new'
}
const statusLabel = status => ({
  new: 'Новое',
  in_progress: 'В работе',
  closed: 'Закрыто',
}[normalizedStatus(status)])
const queueCount = computed(() => tickets.value.filter(ticket => normalizedStatus(ticket.status) === 'new').length)
const activeTicketCount = computed(() => tickets.value.filter(ticket => normalizedStatus(ticket.status) !== 'closed').length)
const isStaffMessage = message => ['staff', 'agent', 'employee'].includes(String(message.sender || message.role).toLowerCase())
const isNovaMessage = message => ['bot', 'nova', 'assistant'].includes(String(message.sender || message.role).toLowerCase())
const filteredTickets = computed(() => tickets.value.filter(ticket => {
  const status = normalizedStatus(ticket.status)
  const matchesFilter = filter.value === 'all' || (filter.value === 'open' ? status !== 'closed' : status === 'closed')
  const needle = query.value.toLowerCase()
  const title = `${ticket.client_name || ticket.name || ''} ${ticket.id} ${ticket.subject || ''}`.toLowerCase()
  return matchesFilter && title.includes(needle)
}))
const formatTime = value => value ? new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : ''
const formatDate = value => value ? new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' }).format(new Date(value)) : 'Сегодня'
const formatTicketCount = count => {
  const form = new Intl.PluralRules('ru-RU').select(count)
  return `${count} ${{ one: 'диалог', few: 'диалога', many: 'диалогов' }[form]}`
}
const formatQuestionCount = count => {
  const form = new Intl.PluralRules('ru-RU').select(count)
  return `${count} ${{ one: 'вопрос', few: 'вопроса', many: 'вопросов' }[form]}`
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      ...options.headers,
    },
  })
  if (response.status === 401) {
    logout()
    throw new Error('Сессия истекла. Войдите снова.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || data.message || 'Не удалось выполнить запрос')
  }
  if (response.status === 204) return null
  return response.json()
}
async function login() {
  busy.value = true
  loginError.value = ''
  try {
    const response = await fetch('/api/staff/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    const data = await response.json()
    if (!response.ok) {
      const message = data.detail === 'Invalid username or password'
        ? 'Неверный логин или пароль.'
        : data.detail || 'Проверьте логин и пароль.'
      throw new Error(message)
    }
    token.value = data.access_token || data.token
    if (!token.value) throw new Error('Сервер не вернул токен авторизации')
    localStorage.setItem(tokenKey, token.value)
    password.value = ''
    await loadDashboard()
  } catch (error) { loginError.value = error.message }
  finally { busy.value = false }
}
function logout() {
  token.value = ''
  localStorage.removeItem(tokenKey)
  selected.value = null
  messages.value = []
  closeSocket()
}
async function loadDashboard() {
  if (!token.value) return
  try {
    const ticketsData = await request('/api/tickets')
    tickets.value = Array.isArray(ticketsData) ? ticketsData : ticketsData.items || ticketsData.tickets || []
    try {
      const unansweredData = await request('/api/unanswered-questions')
      unanswered.value = Array.isArray(unansweredData) ? unansweredData : unansweredData.items || unansweredData.questions || []
    } catch (error) {
      unanswered.value = []
      notice.value = `Не удалось загрузить журнал вопросов Новы: ${error.message}`
    }
    if (selected.value) await selectTicket(selected.value)
    else if (tickets.value.length) await selectTicket(tickets.value[0].id)
  } catch (error) { notice.value = error.message }
}
function addMessage(message) {
  if (message.id && messages.value.some(entry => String(entry.id) === String(message.id))) return
  messages.value.push(message)
}
async function selectTicket(id) {
  selected.value = id
  closeSocket()
  try {
    const data = await request(`/api/tickets/${encodeURIComponent(id)}/messages`)
    messages.value = Array.isArray(data) ? data : data.messages || []
    connectSocket(id)
    await nextTick(scrollMessages)
  } catch (error) { notice.value = error.message }
}
function connectSocket(id) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  socket.value = new WebSocket(`${protocol}//${location.host}/ws/tickets/${encodeURIComponent(id)}?token=${encodeURIComponent(token.value)}`)
  socket.value.onmessage = event => {
    try {
      const data = JSON.parse(event.data)
      const item = data.message && typeof data.message === 'object' ? data.message : data
      const text = data.text || (typeof data.message === 'string' ? data.message : item.text || item.content)
      if (text) {
        addMessage({
          id: item.id || crypto.randomUUID(),
          sender: data.sender || item.sender || item.role || (item.staff_id ? 'staff' : 'client'),
          sender_name: data.sender_name || item.sender_name,
          text,
          created_at: item.created_at || new Date().toISOString(),
        })
        nextTick(scrollMessages)
      }
    } catch { /* Ignore malformed socket events. */ }
  }
  socket.value.onclose = () => { socket.value = null }
}
function closeSocket() {
  if (socket.value) { socket.value.onclose = null; socket.value.close(); socket.value = null }
}
function scrollMessages() { messagesEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }
function showUnanswered() {
  unansweredPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
async function setStatus(status) {
  if (!currentTicket.value) return
  try {
    const data = await request(`/api/tickets/${encodeURIComponent(selected.value)}`, {
      method: 'PATCH', body: JSON.stringify({ status }),
    })
    const index = tickets.value.findIndex(ticket => String(ticket.id) === String(selected.value))
    if (index >= 0) tickets.value[index] = { ...tickets.value[index], ...(data || {}), status: data?.status || status }
    notice.value = status === 'closed'
      ? 'Обращение закрыто'
      : status === 'new'
        ? 'Обращение возвращено в очередь'
        : 'Вы взяли обращение в работу'
    window.setTimeout(() => { notice.value = '' }, 3000)
  } catch (error) { notice.value = error.message }
}
async function markNovaAnswerWrong() {
  if (!currentTicket.value || currentTicket.value.nova_answer_wrong || markingNovaWrong.value) return
  markingNovaWrong.value = true
  try {
    const data = await request(`/api/tickets/${encodeURIComponent(selected.value)}`, {
      method: 'PATCH',
      body: JSON.stringify({ nova_answer_wrong: true }),
    })
    const index = tickets.value.findIndex(ticket => String(ticket.id) === String(selected.value))
    if (index >= 0) tickets.value[index] = { ...tickets.value[index], ...(data || {}), nova_answer_wrong: true }
    notice.value = 'Ответ Новы отмечен как неверный'
    window.setTimeout(() => { notice.value = '' }, 3000)
  } catch (error) {
    notice.value = error.message
  } finally {
    markingNovaWrong.value = false
  }
}
async function sendReply() {
  if (!reply.value.trim() || !selected.value) return
  const text = reply.value.trim()
  reply.value = ''
  try {
    const data = await request(`/api/tickets/${encodeURIComponent(selected.value)}/messages`, {
      method: 'POST', body: JSON.stringify({ message: text }),
    })
    addMessage(data || { id: crypto.randomUUID(), sender: 'staff', text, created_at: new Date().toISOString() })
    await nextTick(scrollMessages)
  } catch (error) { reply.value = text; notice.value = error.message }
}
function handleReplyKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendReply() }
}
watch(token, value => { if (value) loadDashboard() })
onMounted(() => { if (token.value) loadDashboard() })
onBeforeUnmount(closeSocket)
</script>

<template>
  <main class="staff-page">
    <section v-if="!token" class="staff-login-shell">
      <a class="brand login-brand" href="/"><span class="brand-mark"><Icon name="spark" :size="18" /></span>finora<span class="brand-period">.</span></a>
      <div class="login-card">
        <div class="login-icon"><Icon name="lock" :size="22" /></div>
        <div class="eyebrow">РАБОЧЕЕ ПРОСТРАНСТВО</div>
        <h1>С возвращением.</h1><p>Войдите, чтобы продолжить заботиться о клиентах Finora.</p>
        <form @submit.prevent="login">
          <label for="username">Логин</label><input id="username" v-model="username" autocomplete="username" required placeholder="Ваш рабочий логин" />
          <label for="password">Пароль</label><input id="password" v-model="password" type="password" autocomplete="current-password" required placeholder="Введите пароль" />
          <p v-if="loginError" class="form-error" role="alert">{{ loginError }}</p>
          <button class="button button-primary login-submit" :disabled="busy">{{ busy ? 'Входим…' : 'Войти в рабочее пространство' }} <Icon name="arrow" :size="17" /></button>
        </form>
        <a href="/" class="back-home"><Icon name="arrow" :size="14" /> На главную</a>
      </div>
      <div class="login-footer">Finora · Внутренняя система поддержки</div>
    </section>

    <section v-else class="staff-app">
      <aside class="staff-sidebar">
        <a class="brand staff-brand" href="/"><span class="brand-mark"><Icon name="spark" :size="17" /></span>finora<span class="brand-period">.</span></a>
        <div class="sidebar-caption">РАБОЧЕЕ ПРОСТРАНСТВО</div>
        <div class="sidebar-item selected"><Icon name="headset" /> Поддержка <span class="side-count">{{ activeTicketCount }}</span></div>
        <button class="sidebar-item" type="button" @click="showUnanswered"><Icon name="spark" /> Вопросы для Новы <span class="side-count muted-count">{{ unanswered.length }}</span></button>
        <div class="sidebar-bottom"><div class="staff-profile"><div class="profile-avatar">С</div><div><strong>Сотрудник Finora</strong><small>На связи</small></div><button class="icon-button" title="Выйти" @click="logout"><Icon name="logout" :size="17" /></button></div><a href="/" class="staff-home-link">← На сайт Finora</a></div>
      </aside>
      <div class="staff-main">
        <header class="staff-topbar"><div><div class="eyebrow">СЛУЖБА ЗАБОТЫ</div><h1>Поддержка</h1></div><div class="topbar-actions"><span class="status-online"><i></i> На связи</span><button class="icon-button mobile-logout" aria-label="Выйти" @click="logout"><Icon name="logout" /></button></div></header>
        <div class="support-layout">
          <section class="ticket-list-pane">
            <div class="ticket-list-header"><div><h2>Обращения</h2><span>{{ formatTicketCount(filteredTickets.length) }} · {{ queueCount }} в очереди</span></div><button class="icon-button" aria-label="Обновить список" @click="loadDashboard"><Icon name="arrow" :size="17" /></button></div>
            <div class="ticket-search"><Icon name="search" :size="17" /><input v-model="query" placeholder="Поиск обращений" /></div>
            <div class="ticket-filters"><button :class="{ active: filter === 'all' }" @click="filter = 'all'">Все</button><button :class="{ active: filter === 'open' }" @click="filter = 'open'">Открытые</button><button :class="{ active: filter === 'closed' }" @click="filter = 'closed'">Закрытые</button></div>
            <div class="ticket-list">
              <button v-for="ticket in filteredTickets" :key="ticket.id" class="ticket-item" :class="{ active: String(selected) === String(ticket.id) }" @click="selectTicket(ticket.id)">
                <div class="ticket-avatar">{{ (ticket.client_name || ticket.name || 'К').slice(0, 1).toUpperCase() }}</div>
                <div class="ticket-info"><div class="ticket-title"><strong>{{ ticket.client_name || ticket.name || `Клиент #${ticket.id}` }}</strong><time>{{ formatTime(ticket.updated_at || ticket.created_at) }}</time></div><p>{{ ticket.last_message || ticket.subject || 'Новое обращение' }}</p><span class="ticket-id">Обращение #{{ ticket.id }}</span><span class="ticket-status" :class="`status-${normalizedStatus(ticket.status)}`">{{ statusLabel(ticket.status) }}</span></div>
              </button>
              <div v-if="!filteredTickets.length" class="empty-list"><Icon name="check" :size="24" /><strong>Пока тихо</strong><span>Здесь появятся обращения клиентов</span></div>
            </div>
            <div ref="unansweredPanel" class="unanswered-box">
              <div class="unanswered-title"><span class="unanswered-symbol"><Icon name="spark" :size="15" /></span><div><strong>Нова не ответила</strong><small>{{ formatQuestionCount(unanswered.length) }} на проверку</small></div></div>
              <article v-for="question in unanswered.slice(0, 2)" :key="question.id" class="unanswered-item"><p>«{{ question.question || question.text }}»</p></article>
              <div v-if="!unanswered.length" class="unanswered-empty">Нет вопросов для проверки</div>
            </div>
          </section>

          <section class="conversation-pane">
            <template v-if="currentTicket">
              <header class="conversation-header">
                <div class="conversation-person"><div class="ticket-avatar large">{{ (currentTicket.client_name || currentTicket.name || 'К').slice(0, 1).toUpperCase() }}</div><div><h2>{{ currentTicket.client_name || currentTicket.name || `Клиент #${currentTicket.id}` }}</h2><span><i></i> Обращение #{{ currentTicket.id }} · {{ formatDate(currentTicket.created_at) }}</span></div><span class="ticket-status conversation-status" :class="`status-${normalizedStatus(currentTicket.status)}`">{{ statusLabel(currentTicket.status) }}</span></div>
                <div class="conversation-actions">
                  <button
                    class="button button-outline small nova-wrong-action"
                    :class="{ marked: currentTicket.nova_answer_wrong }"
                    :disabled="currentTicket.nova_answer_wrong || markingNovaWrong"
                    @click="markNovaAnswerWrong"
                  ><Icon name="check" :size="15" />{{ currentTicket.nova_answer_wrong ? 'Ответ отмечен как неверный' : markingNovaWrong ? 'Отмечаем…' : 'Ответ Новы был неверным' }}</button>
                  <button v-if="normalizedStatus(currentTicket.status) === 'closed'" class="button button-outline small" @click="setStatus('new')"><Icon name="check" :size="15" /> Вернуть в очередь</button>
                  <button v-else-if="normalizedStatus(currentTicket.status) !== 'in_progress'" class="button button-outline small" @click="setStatus('in_progress')">Взять в работу</button>
                  <button v-if="normalizedStatus(currentTicket.status) !== 'closed'" class="icon-button close-ticket" title="Закрыть обращение" @click="setStatus('closed')"><Icon name="check" :size="17" /></button>
                </div>
              </header>
              <div class="conversation-history">
                <div class="history-date"><span>НАЧАЛО ДИАЛОГА</span></div>
                <article v-for="(message, index) in messages" :key="message.id || index" class="history-row" :class="{ mine: isStaffMessage(message), nova: isNovaMessage(message) }">
                  <div v-if="!isStaffMessage(message)" class="history-avatar" :class="{ 'nova-avatar-history': isNovaMessage(message) }"><Icon v-if="isNovaMessage(message)" name="spark" :size="14" /><template v-else>{{ String(message.sender_name || currentTicket.client_name || 'К').slice(0, 1).toUpperCase() }}</template></div>
                  <div class="history-content"><span>{{ isStaffMessage(message) ? 'Вы' : isNovaMessage(message) ? 'Нова' : (message.sender_name || currentTicket.client_name || 'Клиент') }}</span><div class="history-bubble">{{ message.text || message.message || message.content }}</div><time>{{ formatTime(message.created_at || message.time) }}</time></div>
                  <div v-if="isStaffMessage(message)" class="history-avatar staff-avatar">С</div>
                </article>
                <div v-if="!messages.length" class="history-empty">Пока нет сообщений в этом диалоге</div>
                <div ref="messagesEnd"></div>
              </div>
              <form class="reply-composer" @submit.prevent="sendReply">
                <textarea v-model="reply" rows="2" :disabled="normalizedStatus(currentTicket.status) === 'closed'" :placeholder="normalizedStatus(currentTicket.status) === 'closed' ? 'Обращение закрыто — верните его в очередь, чтобы ответить.' : 'Напишите ответ клиенту…'" @keydown="handleReplyKey"></textarea>
                <div class="composer-controls"><span><Icon name="clock" :size="14" /> {{ normalizedStatus(currentTicket.status) === 'closed' ? 'Ответы отключены для закрытого обращения' : 'Ответьте в течение нескольких минут' }}</span><button class="button button-primary small" :disabled="!reply.trim() || normalizedStatus(currentTicket.status) === 'closed'">Отправить <Icon name="send" :size="15" /></button></div>
              </form>
            </template>
            <div v-else class="conversation-empty"><div class="empty-art"><Icon name="headset" :size="28" /></div><h2>Выберите обращение</h2><p>Откройте диалог из списка слева, чтобы продолжить разговор с клиентом.</p></div>
          </section>
        </div>
      </div>
      <Transition name="fade"><div v-if="notice" class="staff-toast">{{ notice }}</div></Transition>
    </section>
  </main>
</template>
