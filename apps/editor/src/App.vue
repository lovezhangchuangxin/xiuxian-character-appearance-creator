<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import CharacterCanvas from "./components/CharacterCanvas.vue";
import {
  bodies,
  dyeColors,
  groups,
  makeAppearance,
  options,
  selectedPart,
  slots,
  type Body,
  type Slot,
} from "./character/catalog";
import { shapeThumbnailUrl, spriteUrl } from "./character/spriteUrls";
import { decodeAppearance, encodeAppearance, savedAppearanceKey } from "./character/appearanceCode";

const appearance = ref(makeAppearance("female"));
const locked = ref<Slot[]>([]);
const group = ref(groups[0]);
const activeSlots = ref<Record<string, Slot>>(
  Object.fromEntries(groups.map((entry) => [entry.id, entry.slots[0]])),
);
const announcement = ref("");
const labels = Object.fromEntries(slots.map((slot) => [slot.id, slot.label]));
const outfit = computed(() => selectedPart(appearance.value, "outfit"));
const canvas = ref<InstanceType<typeof CharacterCanvas>>();
const view = ref<"full" | "portrait">("full");
const views = [
  { id: "full", label: "全身" },
  { id: "portrait", label: "面部" },
] as const;
const codeDialog = ref<HTMLDialogElement>();
const currentCodeInput = ref<HTMLInputElement>();
const currentCode = computed(() => encodeAppearance(appearance.value));
const importCodeText = ref("");
const codeFeedback = ref("");
const saveFeedback = ref("");
const hasSavedAppearance = ref(false);

const activeSlot = computed(() => activeSlots.value[group.value.id]);
const activeLocked = computed(() => locked.value.includes(activeSlot.value));
const gridParts = computed(() => {
  const list = options(activeSlot.value, appearance.value.body);
  const none = list.find((part) => part.id === "none");
  const rest = list.filter((part) => part.id !== "none");
  return none ? [none, ...rest] : rest;
});

function syncSavedAppearance() {
  try {
    hasSavedAppearance.value = localStorage.getItem(savedAppearanceKey) !== null;
  } catch {
    hasSavedAppearance.value = false;
  }
}

function onStorageChange(event: StorageEvent) {
  if (event.key === savedAppearanceKey || event.key === null) syncSavedAppearance();
}

onMounted(() => {
  window.addEventListener("storage", onStorageChange);
  syncSavedAppearance();
});
onUnmounted(() => window.removeEventListener("storage", onStorageChange));

function applyCode(code: string) {
  const next = decodeAppearance(code);
  if (!next) return false;
  appearance.value = next;
  return true;
}

function saveAppearance() {
  try {
    localStorage.setItem(savedAppearanceKey, currentCode.value);
    hasSavedAppearance.value = true;
    saveFeedback.value = "当前外观已保存到此浏览器。";
  } catch {
    saveFeedback.value = "浏览器无法保存。可以复制外观码留存。";
  }
}

function loadAppearance() {
  try {
    const code = localStorage.getItem(savedAppearanceKey);
    hasSavedAppearance.value = code !== null;
    if (code === null) saveFeedback.value = "此浏览器还没有外观存档。";
    else saveFeedback.value = applyCode(code) ? "已读取本地存档。" : "本地存档无法读取。";
  } catch {
    saveFeedback.value = "浏览器无法读取本地存档。";
  }
}

function openCodeDialog() {
  codeFeedback.value = "";
  codeDialog.value?.showModal();
}

function importAppearance() {
  if (!applyCode(importCodeText.value)) {
    codeFeedback.value = "外观码无效，请检查是否粘贴完整。";
    return;
  }
  importCodeText.value = "";
  saveFeedback.value = "已导入外观。";
  codeDialog.value?.close();
}

async function copyAppearance() {
  try {
    await navigator.clipboard.writeText(currentCode.value);
    codeFeedback.value = "已复制当前外观码。";
  } catch {
    currentCodeInput.value?.focus();
    currentCodeInput.value?.select();
    codeFeedback.value = "当前外观码已选中，请手动复制。";
  }
}

function chooseBody(body: Body) {
  if (body === appearance.value.body) return;
  appearance.value = makeAppearance(body);
}

function chooseGroup(next: typeof group.value) {
  group.value = next;
}

function chooseSlot(slot: Slot) {
  activeSlots.value[group.value.id] = slot;
}

function choosePart(slot: Slot, id: string) {
  const current = appearance.value;
  if (current.parts[slot] === id) return;
  appearance.value = {
    ...current,
    parts: { ...current.parts, [slot]: id },
    dye: slot === "outfit" ? null : current.dye,
  };
}

function toggleLock(slot: Slot) {
  locked.value = locked.value.includes(slot)
    ? locked.value.filter((id) => id !== slot)
    : [...locked.value, slot];
}

function randomize() {
  const current = appearance.value;
  const parts = { ...current.parts };
  for (const { id } of slots) {
    if (locked.value.includes(id)) continue;
    const pool = options(id, current.body).filter((part) => {
      if (part.id === parts[id]) return false;
      if (id === "frontHair" || id === "outfit") return part.id !== "none";
      if ((id === "backHair" || id === "topHair") && parts.frontHair === "none")
        return part.id === "none";
      return true;
    });
    if (pool.length) parts[id] = pool[Math.floor(Math.random() * pool.length)].id;
  }
  appearance.value = {
    ...current,
    parts,
    dye: parts.outfit === current.parts.outfit ? current.dye : null,
  };
  announcement.value = "已随机组合未锁定的部件";
}
</script>

<template>
  <main class="studio">
    <header class="topbar">
      <div class="wordmark">
        <span class="seal" aria-hidden="true">修</span>
        <div>
          <p class="brand">修仙</p>
          <h1>角色外观</h1>
        </div>
      </div>
      <button type="button" class="random" @click="randomize">随机组合</button>
    </header>

    <div class="workspace">
      <section class="stage" :class="{ 'is-portrait': view === 'portrait' }" aria-label="预览">
        <div class="stage-orbit" aria-hidden="true"></div>
        <CharacterCanvas ref="canvas" :appearance="appearance" :view="view" />
        <div class="canvas-tools view-modes" role="group" aria-label="预览范围">
          <button
            v-for="mode in views"
            :key="mode.id"
            type="button"
            :aria-pressed="view === mode.id"
            @click="view = mode.id"
          >
            {{ mode.label }}
          </button>
        </div>
        <div class="canvas-tools" role="group" aria-label="视角控制">
          <button type="button" aria-label="缩小" title="缩小" @click="canvas?.zoomStep(-1)">
            −
          </button>
          <button type="button" title="还原视角（双击画面同样生效）" @click="canvas?.resetView()">
            还原
          </button>
          <button type="button" aria-label="放大" title="放大" @click="canvas?.zoomStep(1)">
            ＋
          </button>
        </div>
        <p class="stage-hint" aria-hidden="true">拖拽平移 · 滚轮缩放 · 双击还原</p>
        <div v-if="view === 'full'" class="stage-caption">
          <span class="caption-rule" aria-hidden="true"></span>
          <span>{{ outfit.id === "none" ? outfit.label : `服装 ${outfit.label}` }}</span>
          <span class="caption-rule" aria-hidden="true"></span>
        </div>
      </section>

      <aside class="editor" aria-label="外观编辑">
        <div class="editor-head">
          <div class="panel-row">
            <h2>体型</h2>
            <div class="segmented" role="group" aria-label="体型">
              <button
                v-for="body in ['female', 'male'] as const"
                :key="body"
                type="button"
                :aria-pressed="appearance.body === body"
                @click="chooseBody(body)"
              >
                {{ bodies[body].label }}
              </button>
            </div>
          </div>
          <div class="action-row save-actions" role="group" aria-label="外观存档">
            <button type="button" @click="saveAppearance">保存外观</button>
            <button type="button" :disabled="!hasSavedAppearance" @click="loadAppearance">
              读取存档
            </button>
            <button type="button" aria-haspopup="dialog" @click="openCodeDialog">外观码</button>
          </div>
          <p v-if="saveFeedback" class="save-feedback" role="status">{{ saveFeedback }}</p>
        </div>

        <nav class="tabs" aria-label="部件分类">
          <button
            v-for="category in groups"
            :key="category.id"
            type="button"
            :aria-pressed="group.id === category.id"
            @click="chooseGroup(category)"
          >
            {{ category.label }}
          </button>
        </nav>

        <div class="slot-row">
          <div class="slot-chips" role="group" :aria-label="`${group.label}部位`">
            <button
              v-for="slot in group.slots"
              :key="slot"
              type="button"
              class="slot-chip"
              :aria-pressed="activeSlot === slot"
              @click="chooseSlot(slot)"
            >
              {{ labels[slot] }}
              <span v-if="locked.includes(slot)" class="chip-lock" title="随机时保留该部位">
                锁
              </span>
            </button>
          </div>
          <button
            type="button"
            class="lock-toggle"
            :aria-pressed="activeLocked"
            title="随机组合时保留当前部位"
            @click="toggleLock(activeSlot)"
          >
            {{ activeLocked ? "已锁定" : "锁定" }}
          </button>
        </div>

        <div class="part-panel">
          <fieldset v-if="activeSlot === 'outfit' && outfit.dyeable" class="part-group">
            <legend>布料颜色</legend>
            <div class="swatches">
              <button
                v-for="color in dyeColors"
                :key="color.label"
                type="button"
                :aria-pressed="appearance.dye === color.value"
                @click="appearance = { ...appearance, dye: color.value }"
              >
                <span class="swatch" :style="{ background: color.swatch }" aria-hidden="true"></span
                >{{ color.label }}
              </button>
            </div>
          </fieldset>
          <fieldset class="part-group">
            <legend>{{ labels[activeSlot] }}</legend>
            <div class="part-grid">
              <button
                v-for="part in gridParts"
                :key="part.id"
                type="button"
                class="part"
                :class="{
                  'has-preview': part.image && part.id !== 'none',
                  'outfit-part': activeSlot === 'outfit' && part.id !== 'none',
                  'shape-part': activeSlot === 'shape',
                }"
                :aria-pressed="appearance.parts[activeSlot] === part.id"
                @click="choosePart(activeSlot, part.id)"
              >
                <img
                  v-if="part.image && part.id !== 'none'"
                  :src="
                    activeSlot === 'shape'
                      ? shapeThumbnailUrl(part.image)
                      : spriteUrl(part.thumbnail ?? part.image)
                  "
                  alt=""
                  draggable="false"
                />
                <span>{{
                  part.id === "none" ? (activeSlot === "outfit" ? "内搭" : "无") : part.label
                }}</span>
              </button>
            </div>
          </fieldset>
        </div>
      </aside>
    </div>
    <dialog ref="codeDialog" class="code-dialog" aria-labelledby="code-title">
      <div class="code-panel">
        <div class="panel-row">
          <h2 id="code-title">外观码</h2>
          <div class="action-row">
            <button type="button" @click="codeDialog?.close()">关闭</button>
          </div>
        </div>
        <label for="current-appearance-code">当前外观码</label>
        <input id="current-appearance-code" ref="currentCodeInput" :value="currentCode" readonly />
        <div class="action-row">
          <button type="button" @click="copyAppearance">复制当前外观码</button>
        </div>
        <form class="code-panel code-import" @submit.prevent="importAppearance">
          <label for="appearance-code-input">导入外观码</label>
          <input
            id="appearance-code-input"
            v-model="importCodeText"
            maxlength="128"
            spellcheck="false"
            autocomplete="off"
            autocapitalize="off"
            placeholder="粘贴已有外观码"
          />
          <div class="action-row">
            <button type="submit">导入外观码</button>
          </div>
        </form>
        <p v-if="codeFeedback" class="save-feedback" role="status">{{ codeFeedback }}</p>
      </div>
    </dialog>

    <p class="visually-hidden" aria-live="polite">{{ announcement }}</p>
  </main>
</template>
