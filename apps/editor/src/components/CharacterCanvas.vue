<script setup lang="ts">
import {
  Application,
  Assets,
  Container,
  defaultFilterVert,
  Filter,
  Graphics,
  Sprite,
  type Texture,
} from "pixi.js";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  bodies,
  layers,
  selectedPart,
  type Appearance,
  type Body,
  type Part,
  type Slot,
} from "../character/catalog";
import { spriteUrl } from "../character/spriteUrls";

const props = defineProps<{
  appearance: Appearance;
  view: keyof (typeof bodies)[Body]["views"];
}>();
const host = ref<HTMLDivElement>();
const error = ref("");
const busy = ref(true);

let app: Application | undefined;
let observer: ResizeObserver | undefined;
let world: Container | undefined;
let character: Container | undefined;
const slotLayers = new Map<Slot, Container>();
const renderedParts = new Map<Slot, string>();
const slotFilters = new Map<Slot, Filter>();
let renderedBody: Body | undefined;
let renderedDye: string | null = null;
let fit = { scale: 1, x: 0, y: 0 };
let user = { zoom: 1, x: 0, y: 0 };
let renderedSize = { width: 0, height: 0 };
let revision = 0;
let frame = 0;
let disposed = false;
const pointers = new Map<number, { x: number; y: number }>();
let pinchSpan = 0;

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;

async function texture(path: string) {
  const url = spriteUrl(path);
  if (!url) throw new Error(`Missing sprite: ${path}`);
  return Assets.load<Texture>(url);
}

function scheduleRender() {
  if (frame || !app) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    if (app && !disposed) app.render();
  });
}

function applyTransform() {
  if (!world) return;
  world.scale.set(fit.scale * user.zoom);
  world.position.set(fit.x + user.x, fit.y + user.y);
}

function layout() {
  if (!app || !host.value) return;
  const width = Math.max(1, host.value.clientWidth);
  const height = Math.max(1, host.value.clientHeight);
  if (renderedSize.width !== width || renderedSize.height !== height) {
    renderedSize = { width, height };
    app.renderer.resize(width, height);
  }
  if (renderedBody) {
    const view = bodies[renderedBody].views[props.view];
    const scale = Math.min(width / view.width, height / view.height);
    fit = { scale, x: width / 2 - view.x * scale, y: height / 2 - view.y * scale };
    applyTransform();
  }
  scheduleRender();
}

function resetView() {
  user = { zoom: 1, x: 0, y: 0 };
  applyTransform();
  scheduleRender();
}

function zoomAt(clientX: number, clientY: number, factor: number) {
  if (!host.value) return;
  const bounds = host.value.getBoundingClientRect();
  const px = clientX - bounds.left;
  const py = clientY - bounds.top;
  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, user.zoom * factor));
  if (zoom === user.zoom) return;
  const ratio = (fit.scale * zoom) / (fit.scale * user.zoom);
  user.x = px - fit.x - (px - fit.x - user.x) * ratio;
  user.y = py - fit.y - (py - fit.y - user.y) * ratio;
  user.zoom = zoom;
  applyTransform();
  scheduleRender();
}

function zoomStep(direction: 1 | -1) {
  if (!host.value) return;
  const bounds = host.value.getBoundingClientRect();
  const factor = direction === 1 ? 1.25 : 0.8;
  zoomAt(bounds.left + bounds.width / 2, bounds.top + bounds.height / 2, factor);
}

function onWheel(event: WheelEvent) {
  event.preventDefault();
  const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
  zoomAt(event.clientX, event.clientY, Math.exp(-delta * 0.0015));
}

function midpoint() {
  const [a, b] = [...pointers.values()];
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function span() {
  const [a, b] = [...pointers.values()];
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function onPointerDown(event: PointerEvent) {
  if (!host.value) return;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  try {
    host.value.setPointerCapture(event.pointerId);
  } catch {
    // 指针可能在捕获前已失效；跳过捕获仍可平移，只是移出画布后不再追踪
  }
  if (pointers.size === 2) pinchSpan = span();
}

function onPointerMove(event: PointerEvent) {
  const previous = pointers.get(event.pointerId);
  if (!previous) return;
  const before = pointers.size === 2 ? midpoint() : undefined;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (pointers.size === 1) {
    user.x += event.clientX - previous.x;
    user.y += event.clientY - previous.y;
    applyTransform();
    scheduleRender();
    return;
  }
  if (pointers.size === 2) {
    const now = midpoint();
    user.x += now.x - (before?.x ?? now.x);
    user.y += now.y - (before?.y ?? now.y);
    const distance = span();
    if (pinchSpan > 0 && distance > 0) zoomAt(now.x, now.y, distance / pinchSpan);
    pinchSpan = distance;
    applyTransform();
    scheduleRender();
  }
}

function onPointerUp(event: PointerEvent) {
  pointers.delete(event.pointerId);
  if (pointers.size < 2) pinchSpan = 0;
}

function dyeFilter(hex: string) {
  const color = [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255);
  return Filter.from({
    gl: {
      vertex: defaultFilterVert,
      fragment: `
        in vec2 vTextureCoord;
        out vec4 finalColor;
        uniform sampler2D uTexture;
        uniform vec3 uDye;
        void main() {
          vec4 src = texture(uTexture, vTextureCoord);
          vec3 color = src.rgb / max(src.a, 0.001);
          float cloth = smoothstep(0.025, 0.08, min(color.g, color.b) - color.r);
          float shade = dot(color, vec3(0.2126, 0.7152, 0.0722));
          vec3 dyed = clamp(uDye * (shade / 0.55), 0.0, 1.0);
          finalColor = vec4(mix(color, dyed, cloth) * src.a, src.a);
        }`,
    },
    resources: { dyeUniforms: { uDye: { value: new Float32Array(color), type: "vec3<f32>" } } },
  });
}

function rebuildCharacter() {
  for (const filter of slotFilters.values()) filter?.destroy();
  slotFilters.clear();
  renderedParts.clear();
  character?.destroy({ children: true });
  character = new Container();
  for (const slot of layers) {
    const layer = new Container();
    slotLayers.set(slot, layer);
    character.addChild(layer);
  }
  world?.addChild(character);
}

function buildSlot(slot: Slot, part: Part, tex: Texture | null, dye: string | null) {
  const layer = slotLayers.get(slot);
  if (!layer) return;
  layer.removeChildren().forEach((child) => child.destroy({ children: true }));
  slotFilters.get(slot)?.destroy();
  slotFilters.delete(slot);
  renderedParts.set(slot, part.id);
  if (!tex || !part.rect) return;

  const sprite = new Sprite(tex);
  const { x, y, width, height } = part.rect;
  sprite.position.set(x, y);
  sprite.width = width;
  sprite.height = height;
  layer.addChild(sprite);

  if (part.clip) {
    const clip = part.clip;
    const mask = new Graphics().rect(clip.x, clip.y, clip.width, clip.height).fill(0xffffff);
    layer.addChild(mask);
    sprite.mask = mask;
  }
  if (slot === "outfit" && part.dyeable && dye) {
    const filter = dyeFilter(dye);
    sprite.filters = [filter];
    slotFilters.set(slot, filter);
  }
}

async function render() {
  if (!app || disposed) return;
  const id = ++revision;
  const appearance = props.appearance;
  const rebuilding = appearance.body !== renderedBody || !character;
  if (rebuilding) {
    busy.value = true;
    if (character) character.visible = false;
  }
  error.value = "";

  try {
    const pending = layers
      .map((slot) => ({ slot, part: selectedPart(appearance, slot) }))
      .filter(({ slot, part }) => {
        if (rebuilding) return true;
        if (renderedParts.get(slot) !== part.id) return true;
        return slot === "outfit" && part.dyeable === true && renderedDye !== appearance.dye;
      });
    const images = await Promise.all(
      pending.map(({ part }) => (part.image ? texture(part.image) : null)),
    );
    if (!app || disposed || revision !== id) return;

    if (rebuilding) rebuildCharacter();
    for (const [index, { slot, part }] of pending.entries()) {
      buildSlot(slot, part, images[index], appearance.dye);
    }

    const offsets: Record<string, number> = bodies[appearance.body].topHairOffsets;
    slotLayers.get("topHair")?.position.set(0, offsets[appearance.parts.frontHair] ?? 0);

    renderedBody = appearance.body;
    renderedDye = appearance.dye;
    if (character) character.visible = true;
    if (rebuilding) user = { zoom: 1, x: 0, y: 0 };
    layout();
  } catch (reason) {
    if (revision === id && !disposed) {
      console.error(reason);
      error.value = "角色素材加载失败，或浏览器不支持 WebGL。";
    }
  } finally {
    if (revision === id) busy.value = false;
  }
}

onMounted(async () => {
  const target = host.value;
  if (!target) return;
  target.addEventListener("wheel", onWheel, { passive: false });
  target.addEventListener("pointerdown", onPointerDown);
  target.addEventListener("pointermove", onPointerMove);
  target.addEventListener("pointerup", onPointerUp);
  target.addEventListener("pointercancel", onPointerUp);
  target.addEventListener("dblclick", resetView);
  const next = new Application();
  try {
    await next.init({
      preference: "webgl",
      autoStart: false,
      antialias: true,
      backgroundAlpha: 0,
      autoDensity: true,
      resolution: Math.min(devicePixelRatio, 2),
    });
    if (disposed) {
      next.destroy(true, { children: true });
      return;
    }
    app = next;
    world = new Container();
    next.stage.addChild(world);
    // The preview host controls touch gestures and page scrolling.
    next.canvas.style.removeProperty("touch-action");
    target.appendChild(next.canvas);
    observer = new ResizeObserver(layout);
    observer.observe(target);
    void render();
  } catch (reason) {
    console.error(reason);
    error.value = "预览无法启动，请检查浏览器的 WebGL 支持。";
    busy.value = false;
  }
});

watch(() => props.appearance, render);
watch(
  () => props.view,
  () => {
    user = { zoom: 1, x: 0, y: 0 };
    layout();
  },
);
onBeforeUnmount(() => {
  disposed = true;
  if (frame) cancelAnimationFrame(frame);
  observer?.disconnect();
  for (const filter of slotFilters.values()) filter?.destroy();
  slotFilters.clear();
  character?.destroy({ children: true });
  app?.destroy(true, { children: true });
});

defineExpose({ resetView, zoomStep });
</script>

<template>
  <div class="renderer" ref="host" role="img" aria-label="角色外观预览">
    <p v-if="busy || error" class="render-notice" role="status">
      {{ error || "正在加载角色素材…" }}
    </p>
  </div>
</template>
