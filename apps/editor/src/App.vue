<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
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
import { spriteUrl } from "./character/spriteUrls";
import { decodeAppearance, encodeAppearance, savedAppearanceKey } from "./character/appearanceCode";

const appearance = ref(makeAppearance("female"));
const locked = ref<Slot[]>([]);
const locksVisible = ref(false);
const group = ref(groups[0]);
const view = ref<"full" | "portrait">("full");
const announcement = ref("");
const labels = Object.fromEntries(slots.map((slot) => [slot.id, slot.label]));
const outfit = computed(() => selectedPart(appearance.value, "outfit"));
const codeVisible = ref(false);
const codeInput = ref<HTMLInputElement>();
const codeText = ref("");
const saveFeedback = ref("");
const hasSavedAppearance = ref(false);

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

function applyCode(code: string, success: string, invalid: string) {
  const next = decodeAppearance(code);
  if (!next) {
    saveFeedback.value = invalid;
    return;
  }
  appearance.value = next;
  codeText.value = encodeAppearance(next);
  saveFeedback.value = success;
}

function saveAppearance() {
  try {
    localStorage.setItem(savedAppearanceKey, encodeAppearance(appearance.value));
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
    applyCode(
      code ?? "",
      "已读取本地存档。",
      code ? "本地存档无法读取。" : "此浏览器还没有外观存档。",
    );
  } catch {
    saveFeedback.value = "浏览器无法读取本地存档。";
  }
}

function toggleCode() {
  codeVisible.value = !codeVisible.value;
  if (codeVisible.value) codeText.value = encodeAppearance(appearance.value);
}

async function copyAppearance() {
  const code = encodeAppearance(appearance.value);
  codeText.value = code;
  try {
    await navigator.clipboard.writeText(code);
    saveFeedback.value = "已复制当前外观码。";
  } catch {
    await nextTick();
    codeInput.value?.focus();
    codeInput.value?.select();
    saveFeedback.value = "当前外观码已选中，请手动复制。";
  }
}

function chooseBody(body: Body) {
  if (body === appearance.value.body) return;
  appearance.value = makeAppearance(body);
}

function chooseGroup(next: typeof group.value) {
  group.value = next;
  view.value = next.view;
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

function preset(style: "calm" | "wandering") {
  appearance.value = makeAppearance(appearance.value.body, style);
  view.value = "full";
  announcement.value = style === "calm" ? "已应用清修预设" : "已应用游历预设";
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
      <section class="stage" aria-label="预览">
        <div class="stage-controls segmented" role="group" aria-label="预览范围">
          <button type="button" :aria-pressed="view === 'full'" @click="view = 'full'">全身</button>
          <button type="button" :aria-pressed="view === 'portrait'" @click="view = 'portrait'">
            近景
          </button>
        </div>
        <div class="stage-orbit" aria-hidden="true"></div>
        <CharacterCanvas :appearance="appearance" :view="view" />
        <div class="stage-caption">
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
          <div class="panel-row presets">
            <h2>预设</h2>
            <div class="preset-buttons">
              <button type="button" @click="preset('calm')">清修</button>
              <button type="button" @click="preset('wandering')">游历</button>
            </div>
          </div>
          <div class="preset-buttons save-actions" role="group" aria-label="外观存档">
            <button type="button" @click="saveAppearance">保存外观</button>
            <button type="button" :disabled="!hasSavedAppearance" @click="loadAppearance">
              读取存档
            </button>
            <button
              type="button"
              :aria-expanded="codeVisible"
              aria-controls="appearance-code"
              @click="toggleCode"
            >
              外观码
            </button>
          </div>
          <form
            v-show="codeVisible"
            id="appearance-code"
            class="code-panel"
            @submit.prevent="
              applyCode(codeText, '已导入外观。', '外观码无效，请检查是否粘贴完整。')
            "
          >
            <label for="appearance-code-input">复制当前外观，或粘贴已有外观码</label>
            <input
              id="appearance-code-input"
              ref="codeInput"
              v-model="codeText"
              maxlength="128"
              spellcheck="false"
              autocomplete="off"
              autocapitalize="off"
            />
            <div class="preset-buttons">
              <button type="button" @click="copyAppearance">复制当前外观码</button>
              <button type="submit">导入外观码</button>
            </div>
          </form>
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

        <div class="part-panel">
          <fieldset v-for="slot in group.slots" :key="slot" class="part-group">
            <legend>{{ labels[slot] }}</legend>
            <div class="part-grid">
              <button
                v-for="part in options(slot, appearance.body).filter((part) => part.id !== 'none')"
                :key="part.id"
                type="button"
                class="part"
                :class="{ 'has-preview': part.image, 'outfit-part': slot === 'outfit' }"
                :aria-pressed="appearance.parts[slot] === part.id"
                @click="choosePart(slot, part.id)"
              >
                <img
                  v-if="part.image"
                  :src="spriteUrl(part.thumbnail ?? part.image)"
                  alt=""
                  draggable="false"
                />
                <span>{{ part.label }}</span>
              </button>
            </div>
            <button
              v-if="options(slot, appearance.body).some((part) => part.id === 'none')"
              type="button"
              class="part part-clear"
              :aria-pressed="appearance.parts[slot] === 'none'"
              @click="choosePart(slot, 'none')"
            >
              {{ slot === "outfit" ? "内搭" : "无" }}
            </button>
          </fieldset>

          <fieldset v-if="group.id === 'outfit' && outfit.dyeable" class="part-group">
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
        </div>

        <div class="lock-panel">
          <button
            type="button"
            class="lock-toggle"
            :aria-expanded="locksVisible"
            aria-controls="locked-parts"
            @click="locksVisible = !locksVisible"
          >
            随机时锁定部件<span v-if="locked.length">（{{ locked.length }}）</span>
          </button>
          <div id="locked-parts" v-show="locksVisible" class="lock-options">
            <label v-for="slot in slots" :key="slot.id">
              <input
                type="checkbox"
                :checked="locked.includes(slot.id)"
                @change="toggleLock(slot.id)"
              />
              {{ slot.label }}
            </label>
          </div>
        </div>
      </aside>
    </div>
    <p class="visually-hidden" aria-live="polite">{{ announcement }}</p>
  </main>
</template>
