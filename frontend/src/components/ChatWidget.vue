<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import Icon from './Icon.vue'

const chat = useChatStore()
const open = ref(false)
const draft = ref('')
const messagesPanel = ref(null)
const quickQuestions = ['Что ты умеешь?', 'Кешбэк', 'Как заблокировать карту?', 'Что делать, если карта потерялась?']
let voiceTimer

const formatTime = value => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))
const isUncertain = text => /не удалось уверенно|не смог|не знаю|не наш[её]л|не уверен|уточн|попробуйте обратиться/i.test(text)

async function submit(text = draft.value) {
  const raw = text.trim()
  if (!raw) return
  const cardPattern = /(?:\d[ -]?){13,19}/g
  const hasCard = cardPattern.test(raw)
  cardPattern.lastIndex = 0
  const safeText = raw.replace(cardPattern, value => {
    return '****'
  })
  if (hasCard) {
    draft.value = safeText
    chat.append({ role: 'system', text: 'Для вашей безопасности номер карты скрыт. Никогда не отправляйте полный номер карты или CVV.' })
  }
  const sent = await chat.sendMessage(safeText)
  if (!sent) return
  draft.value = ''
  await nextTick()
  chat.scrollToBottom()
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
function setMessagesEnd(element) { chat.messagesEnd = element }
function openChat() { open.value = true }
watch(open, value => { if (value) nextTick(chat.scrollToBottom) })
onMounted(() => {
  window.addEventListener('finora:open-chat', openChat)
  chat.detectVoice()
  chat.resumeTicket()
  if ('speechSynthesis' in window) {
    speechSynthesis.addEventListener('voiceschanged', chat.detectVoice)
    voiceTimer = window.setTimeout(chat.detectVoice, 500)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('finora:open-chat', openChat)
  window.clearTimeout(voiceTimer)
  if ('speechSynthesis' in window) speechSynthesis.removeEventListener('voiceschanged', chat.detectVoice)
  chat.closeSocket()
})
</script>

<template>
  <div class="chat-launcher-wrap">
    <Transition name="chat-pop">
      <section v-if="open" class="chat-panel" aria-label="Чат с Новой">
        <header class="chat-head">
          <div class="nova-avatar"><Icon name="spark" :size="19" /></div>
          <div class="chat-head-copy"><strong>Нова</strong><span><i></i>{{ chat.isLive ? (chat.handoffState === 'waiting' ? 'Ищем сотрудника' : 'Сотрудник на связи') : 'Ваш помощник Finora' }}</span></div>
          <button class="chat-handoff-header" :disabled="chat.isLive" aria-label="Позвать сотрудника" title="Позвать сотрудника" @click="chat.requestHandoff()"><Icon name="headset" :size="14" /><span>Позвать сотрудника</span></button>
          <button v-if="chat.ruVoiceAvailable" class="icon-button tts-button" :class="{ active: chat.speakingEnabled }" :aria-label="chat.speakingEnabled ? 'Выключить озвучивание' : 'Включить озвучивание'" @click="chat.setSpeaking(!chat.speakingEnabled)"><Icon name="sound" /></button>
          <button class="icon-button" aria-label="Закрыть чат" @click="open = false"><Icon name="close" /></button>
        </header>
        <div ref="messagesPanel" class="chat-messages">
          <div class="chat-day">СЕГОДНЯ</div>
          <template v-for="(message, index) in chat.messages" :key="message.id || index">
            <div v-if="message.role === 'system'" class="system-message">{{ message.text }}</div>
            <article v-else class="chat-row" :class="message.role">
              <div v-if="message.role === 'nova'" class="message-avatar"><Icon name="spark" :size="14" /></div>
              <div class="message-body">
                <span v-if="message.role === 'staff'" class="sender-name">{{ message.sender || 'Сотрудник' }}</span>
                <div class="bubble">{{ message.text }}</div>
                <time>{{ formatTime(message.time) }}</time>
                <div v-if="message.suggestions?.length" class="suggestion-list">
                  <button v-for="suggestion in message.suggestions.slice(0, 6)" :key="suggestion" @click="submit(suggestion)">{{ suggestion }}</button>
                </div>
                <div v-if="message.role === 'nova' && isUncertain(message.text)" class="suggestion-list">
                  <button @click="chat.requestHandoff()">Позвать сотрудника</button>
                </div>
              </div>
            </article>
          </template>
          <div v-if="chat.loading" class="chat-row nova">
            <div class="message-avatar"><Icon name="spark" :size="14" /></div>
            <div class="typing-indicator" aria-label="Нова печатает"><i></i><i></i><i></i></div>
          </div>
          <div v-if="chat.isLive && !chat.canSendLiveMessage" class="live-status">
            <span><span class="typing-dots"><i></i><i></i><i></i></span>{{ chat.socketState === 'error' || chat.socketState === 'closed' ? 'Связь с сотрудником прервалась.' : 'Подключаем защищённый чат…' }}</span>
            <button v-if="chat.socketState === 'error' || chat.socketState === 'closed'" @click="chat.reconnectTicket">Повторить подключение</button>
          </div>
          <div :ref="setMessagesEnd" class="chat-end"></div>
        </div>
        <footer class="chat-compose">
          <label class="sr-only" for="chat-input">Ваше сообщение</label>
          <textarea id="chat-input" v-model="draft" rows="1" maxlength="500" :disabled="chat.isLive && !chat.canSendLiveMessage" :placeholder="chat.isLive && !chat.canSendLiveMessage ? 'Подключаем защищённый чат…' : 'Напишите сообщение…'" @keydown="onKeydown"></textarea>
          <button class="send-button" :disabled="!draft.trim() || chat.loading || (chat.isLive && !chat.canSendLiveMessage)" aria-label="Отправить сообщение" @click="submit()"><Icon name="send" :size="18" /></button>
          <div class="compose-meta">
            <span v-if="chat.isLive"><i class="online-dot"></i> Диалог передан сотруднику</span>
            <span v-else>Напишите Нове — она поможет разобраться</span>
            <small><Icon name="lock" :size="12" /> Не отправляйте данные карты</small>
          </div>
        </footer>
        <div class="chat-quick" v-if="chat.messages.length <= 1 && chat.handoffState === 'idle'">
          <span>Популярные вопросы</span>
          <button v-for="question in quickQuestions" :key="question" @click="submit(question)">{{ question }} <Icon name="arrow" :size="14" /></button>
        </div>
      </section>
    </Transition>
    <button class="chat-launcher" :class="{ opened: open }" :aria-label="open ? 'Закрыть чат' : 'Открыть чат с Новой'" @click="open = !open">
      <Icon :name="open ? 'close' : 'spark'" :size="23" />
      <span v-if="!open">Нова <small>на связи</small></span>
    </button>
  </div>
</template>
