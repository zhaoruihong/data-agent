<template>
  <div ref="rootEl" class="theme-switcher">
    <button class="ts-trigger" @click="open = !open" :title="'切换主题'">
      <span class="ts-swatch">
        <i
          v-for="(c, i) in currentSwatch"
          :key="i"
          class="ts-dot"
          :style="{ background: c }"
        ></i>
      </span>
      <span class="ts-name">{{ currentName }}</span>
      <span class="ts-chevron" :class="{ open }">▾</span>
    </button>

    <transition name="ts-fade">
      <div v-if="open" class="ts-panel" @click.stop>
        <div class="ts-panel-title">选择界面主题</div>
        <div class="ts-list">
          <button
            v-for="t in themes"
            :key="t.key"
            class="ts-item"
            :class="{ active: t.key === modelValue }"
            @click="select(t.key)"
          >
            <span class="ts-swatch">
              <i
                v-for="(c, i) in t.swatch"
                :key="i"
                class="ts-dot"
                :style="{ background: c }"
              ></i>
            </span>
            <span class="ts-meta">
              <span class="ts-item-name">{{ t.name }}</span>
              <span class="ts-item-desc">{{ t.desc }}</span>
            </span>
            <span v-if="t.key === modelValue" class="ts-check">✓</span>
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { themes } from '../themes.js';

const props = defineProps({
  modelValue: { type: String, required: true },
});
const emit = defineEmits(['update:modelValue']);

const open = ref(false);
const rootEl = ref(null);

const currentName = computed(
  () => themes.find((t) => t.key === props.modelValue)?.name || '主题'
);
const currentSwatch = computed(
  () => themes.find((t) => t.key === props.modelValue)?.swatch || ['#888']
);

function select(key) {
  emit('update:modelValue', key);
  open.value = false;
}

function onDocClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) open.value = false;
}
function onEsc(e) {
  if (e.key === 'Escape') open.value = false;
}

onMounted(() => {
  document.addEventListener('click', onDocClick);
  document.addEventListener('keydown', onEsc);
});
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick);
  document.removeEventListener('keydown', onEsc);
});
</script>

<style scoped>
.theme-switcher {
  position: relative;
  z-index: 50;
}

.ts-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  color: var(--text-primary);
  backdrop-filter: blur(12px);
  cursor: pointer;
  font-size: 13px;
  transition: border-color 0.2s, transform 0.15s;
}
.ts-trigger:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.ts-swatch {
  display: inline-flex;
  gap: -3px;
}
.ts-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
  border: 1.5px solid rgba(255, 255, 255, 0.6);
  margin-left: -4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.ts-dot:first-child {
  margin-left: 0;
}

.ts-name {
  font-weight: 500;
}
.ts-chevron {
  font-size: 11px;
  opacity: 0.7;
  transition: transform 0.2s;
}
.ts-chevron.open {
  transform: rotate(180deg);
}

.ts-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 280px;
  padding: 10px;
  border-radius: 14px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}
.ts-panel-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  padding: 4px 8px 8px;
}
.ts-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ts-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  color: var(--text-primary);
  transition: background 0.15s;
}
.ts-item:hover {
  background: var(--table-hover);
}
.ts-item.active {
  background: var(--table-head-bg);
}
.ts-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.ts-item-name {
  font-size: 13px;
  font-weight: 600;
}
.ts-item-desc {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ts-check {
  color: var(--accent);
  font-weight: 700;
}

.ts-fade-enter-active,
.ts-fade-leave-active {
  transition: opacity 0.18s, transform 0.18s;
}
.ts-fade-enter-from,
.ts-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>