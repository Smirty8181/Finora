import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { IS_STATIC_DEMO } from '../config'

const keySuffix = IS_STATIC_DEMO ? '_static_preview' : ''
const sessionKey = `finora_chat_session${keySuffix}`
const messagesKey = `finora_chat_messages${keySuffix}`
const ticketKey = `finora_chat_ticket${keySuffix}`
const handoffKey = `finora_chat_handoff${keySuffix}`
const initialMessages = () => [{
  id: 'welcome',
  role: 'nova',
  text: IS_STATIC_DEMO
    ? 'Это локальный демонстрационный помощник. Ответы заранее заданы, сервис Finora и его API не подключены.'
    : 'Привет! Я Нова, ваш помощник Finora. Чем могу помочь?',
  time: new Date().toISOString(),
}]

function restoreMessages(sessionId) {
  if (IS_STATIC_DEMO) return initialMessages()
  const saved = sessionStorage.getItem(`${messagesKey}:${sessionId}`)
  if (!saved) return initialMessages()
  try {
    const restored = JSON.parse(saved)
    if (!Array.isArray(restored)) throw new TypeError('Chat history must be a list')
    return restored
      .filter(message => message && ['client', 'nova', 'staff', 'system'].includes(message.role) && typeof message.text === 'string')
      .slice(-100)
  } catch (error) {
    if (!(error instanceof SyntaxError) && !(error instanceof TypeError)) throw error
    sessionStorage.removeItem(`${messagesKey}:${sessionId}`)
    return initialMessages()
  }
}

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(localStorage.getItem(sessionKey) || crypto.randomUUID())
  const messages = ref(restoreMessages(sessionId.value))
  const loading = ref(false)
  const handoffState = ref(sessionStorage.getItem(handoffKey) || 'idle')
  const ticketId = ref(sessionStorage.getItem(ticketKey) || null)
  const socketState = ref('closed')
  const socket = ref(null)
  const messagesEnd = ref(null)
  const speakingEnabled = ref(localStorage.getItem('finora_tts') === 'true')
  const ruVoiceAvailable = ref(false)
  const voiceOptions = ref([])
  const isLive = computed(() => handoffState.value === 'waiting' || handoffState.value === 'connected')
  const canSendLiveMessage = computed(() => isLive.value && socketState.value === 'open')

  localStorage.setItem(sessionKey, sessionId.value)
  if (!ticketId.value) handoffState.value = 'idle'

  watch(handoffState, value => sessionStorage.setItem(handoffKey, value))
  watch(ticketId, value => {
    if (value) sessionStorage.setItem(ticketKey, value)
    else sessionStorage.removeItem(ticketKey)
  })

  function append(message) {
    const appended = { id: crypto.randomUUID(), time: new Date().toISOString(), ...message }
    messages.value.push(appended)
    messages.value = messages.value.slice(-100)
    if (!IS_STATIC_DEMO) sessionStorage.setItem(`${messagesKey}:${sessionId.value}`, JSON.stringify(messages.value))
    scrollToBottom()
    if (message.role === 'nova' && speakingEnabled.value) speak(message.text)
    return appended
  }
  function scrollToBottom() {
    requestAnimationFrame(() => messagesEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }))
  }
  function stripMarkup(value) {
    const node = document.createElement('div')
    node.innerHTML = value || ''
    return (node.textContent || node.innerText || '').replace(/https?:\/\/\S+/gi, 'ссылка').trim()
  }
  function detectVoice() {
    if (!('speechSynthesis' in window)) return
    voiceOptions.value = speechSynthesis.getVoices().filter(voice => voice.lang.toLowerCase().startsWith('ru'))
    ruVoiceAvailable.value = voiceOptions.value.length > 0
  }
  function speak(value) {
    if (!('speechSynthesis' in window)) return
    detectVoice()
    if (!ruVoiceAvailable.value) return
    speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(stripMarkup(value))
    utterance.lang = 'ru-RU'
    utterance.rate = 0.95
    utterance.pitch = 1
    const priority = [
      /svetlana|светлана/i,
      /dmitry|дмитрий/i,
      /microsoft/i,
      /google.*russian|google русский/i,
    ]
    utterance.voice = priority.map(pattern => voiceOptions.value.find(voice => pattern.test(voice.name))).find(Boolean) || voiceOptions.value[0]
    speechSynthesis.speak(utterance)
  }
  function setSpeaking(enabled) {
    speakingEnabled.value = enabled
    localStorage.setItem('finora_tts', String(enabled))
    if (!enabled && 'speechSynthesis' in window) speechSynthesis.cancel()
    detectVoice()
  }
  async function sendMessage(text) {
    const message = text.trim()
    if (!message || loading.value) return false
    if (isLive.value) {
      if (socketState.value !== 'open' || socket.value?.readyState !== WebSocket.OPEN) return false
      try {
        socket.value.send(JSON.stringify({ message }))
        return true
      } catch {
        return false
      }
    }
    const outgoing = append({ role: 'client', text: message })
    loading.value = true
    if (IS_STATIC_DEMO) {
      const question = message.toLowerCase()
      const answer = /что ты умеешь|как пользоваться|демо|preview/.test(question)
        ? 'Локальный демо-ответ: здесь можно осмотреть макет и задать вопросы о его интерфейсе. Данные и сценарии не связаны с банком или реальным сервисом.'
        : /перевод|оплат|платеж|платёж|пополн|операц/.test(question)
          ? 'Локальный демо-ответ: переводы и платежи в этом preview отключены. Никаких финансовых операций выполнить нельзя.'
          : /кешбэк|кэшбэк|карта|сч[её]т|баланс/.test(question)
            ? 'Локальный демо-ответ: показанные в макете карта, баланс и продукты вымышлены и не отражают реальные предложения.'
            : 'Локальный демо-ответ: этот статический preview не подключён к API, поэтому я могу только показать этот заранее заданный ответ.'
      await new Promise(resolve => window.setTimeout(resolve, 300))
      append({ role: 'nova', text: answer })
      loading.value = false
      return true
    }
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId.value }),
      })
      if (!response.ok) throw new Error('Не удалось получить ответ')
      const data = await response.json()
      const answer = data.answer || data.response || data.message || 'Не смогла найти точный ответ.'
      append({ role: 'nova', text: answer, suggestions: data.suggestions || data.related_questions || [] })
    } catch (error) {
      messages.value = messages.value.filter(entry => entry.id !== outgoing.id)
      sessionStorage.setItem(`${messagesKey}:${sessionId.value}`, JSON.stringify(messages.value))
      append({ role: 'nova', text: 'Похоже, сейчас нет связи с сервером. Попробуйте ещё раз или позовите сотрудника.' })
      return false
    } finally {
      loading.value = false
    }
    return true
  }
  async function requestHandoff() {
    if (IS_STATIC_DEMO) {
      append({ role: 'system', text: 'Передача сотруднику отключена в статическом preview: рабочее место поддержки и сервер не подключены.' })
      return
    }
    if (handoffState.value !== 'idle') return
    handoffState.value = 'waiting'
    append({ role: 'system', text: 'Передаю диалог сотруднику. Обычно это занимает пару минут.' })
    try {
      const response = await fetch('/api/chat/handoff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId.value }),
      })
      if (!response.ok) throw new Error('handoff failed')
      const data = await response.json()
      ticketId.value = data.ticket_id ?? data.id
      if (!ticketId.value) throw new Error('ticket id missing')
      connectTicket()
    } catch {
      handoffState.value = 'idle'
      append({ role: 'system', text: 'Не удалось создать обращение. Попробуйте ещё раз чуть позже.' })
    }
  }
  function reconnectTicket() {
    if (!ticketId.value || !isLive.value) return
    connectTicket()
  }
  function connectTicket() {
    if (IS_STATIC_DEMO) return
    closeSocket()
    socketState.value = 'connecting'
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    try {
      socket.value = new WebSocket(`${protocol}//${location.host}/ws/tickets/${encodeURIComponent(ticketId.value)}?session_id=${encodeURIComponent(sessionId.value)}`)
    } catch {
      socketState.value = 'error'
      return
    }
    socket.value.onopen = () => { socketState.value = 'open' }
    socket.value.onmessage = event => {
      try {
        const data = JSON.parse(event.data)
        const payload = data.message && typeof data.message === 'object' ? data.message : data
        const text = typeof data.message === 'string' ? data.message : (payload.text || payload.content)
        const status = data.status || data.type || payload.status || payload.type
        const sender = data.sender || data.role || payload.sender || payload.role
        const name = data.sender_name || payload.sender_name
        if (status === 'closed' || status === 'ticket_closed') {
          handoffState.value = 'idle'
          ticketId.value = null
          append({ role: 'system', text: 'Обращение закрыто. Вы можете продолжить разговор с Новой или создать новое обращение.' })
          closeSocket()
          return
        }
        const isAssignment = ['connected', 'assigned', 'ticket_assigned'].includes(status)
        if (isAssignment && handoffState.value !== 'connected') {
          handoffState.value = 'connected'
          append({ role: 'system', text: 'Сотрудник подключился к диалогу.' })
        }
        if (text) {
          append({ role: sender === 'client' ? 'client' : sender === 'bot' || sender === 'nova' ? 'nova' : 'staff', text, sender: name || (sender === 'bot' || sender === 'nova' ? 'Нова' : 'Сотрудник') })
        }
      } catch { /* Ignore malformed socket events. */ }
    }
    socket.value.onerror = () => { socketState.value = 'error' }
    socket.value.onclose = () => { socketState.value = 'closed' }
  }
  function resumeTicket() {
    if (IS_STATIC_DEMO) return
    if (ticketId.value && isLive.value) connectTicket()
  }
  function closeSocket() {
    socket.value?.close()
    socket.value = null
  }
  return {
    sessionId, messages, loading, handoffState, ticketId, socketState, socket, messagesEnd,
    speakingEnabled, ruVoiceAvailable, voiceOptions, isLive, canSendLiveMessage, append, sendMessage, requestHandoff,
    reconnectTicket, resumeTicket, setSpeaking, detectVoice, scrollToBottom, closeSocket,
  }
})
