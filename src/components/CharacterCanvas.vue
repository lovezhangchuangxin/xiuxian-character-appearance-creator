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
  canvas,
  headReference,
  selectedPart,
  type Appearance,
  type Slot,
} from "../character/catalog";
import { spriteUrl } from "../character/spriteUrls";

const props = defineProps<{ appearance: Appearance; view: "full" | "portrait" }>();
const host = ref<HTMLDivElement>();
const error = ref("");
const busy = ref(true);
let app: Application | undefined;
let observer: ResizeObserver | undefined;
let active: Container | undefined;
let disposeActive: (() => void) | undefined;
let renderedBody = props.appearance.body;
let revision = 0;
let disposed = false;

async function texture(path: string) {
  const url = spriteUrl(path);
  if (!url) throw new Error(`Missing sprite: ${path}`);
  return Assets.load<Texture>(url);
}

function layout() {
  if (!app || !host.value || !active) return;
  const width = Math.max(1, host.value.clientWidth);
  const height = Math.max(1, host.value.clientHeight);
  const profile = bodies[renderedBody];
  app.renderer.resize(width, height);
  const close = props.view === "portrait";
  const scale = close ? Math.min(width / 350, height / 365) : Math.min(width / 720, height / 1595);
  active.scale.set(scale);
  active.position.set(
    width / 2 - profile.center * scale,
    close
      ? height / 2 - (profile.crown + 101) * scale
      : height / 2 - (profile.ground - 753) * scale,
  );
  app.render();
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

async function render() {
  if (!app || disposed) return;
  const id = ++revision;
  const appearance = props.appearance;
  const profile = bodies[appearance.body];
  const slotOrder: Slot[] = [
    "backHair",
    "outfit",
    "shape",
    "brows",
    "eyes",
    "nose",
    "mouth",
    "frontHair",
    "topHair",
  ];
  const parts = Object.fromEntries(slotOrder.map((slot) => [slot, selectedPart(appearance, slot)]));
  const changingBody = appearance.body !== renderedBody;
  if (active) {
    active.visible = !changingBody;
    if (changingBody) app.render();
  }
  busy.value = !active || changingBody;
  error.value = "";

  try {
    const outfit = parts.outfit;
    const [base, ...images] = await Promise.all([
      outfit.sprite ? undefined : texture(profile.sprite),
      ...slotOrder.map((slot) => (parts[slot].sprite ? texture(parts[slot].sprite) : undefined)),
    ]);
    if (!app || disposed || revision !== id) return;
    const next = new Container();
    const dye = outfit.dyeable && appearance.dye ? dyeFilter(appearance.dye) : undefined;

    function draw(slot: Slot, coordinate = 0, centered = true) {
      const tex = images[slotOrder.indexOf(slot)];
      if (!tex) return;
      const part = parts[slot];
      const sprite = new Sprite(tex);
      if (part.headOffset) {
        const [x, y] = part.headOffset;
        sprite.scale.set(headReference.scale);
        sprite.position.set(
          profile.headOrigin[0] + x * headReference.scale,
          profile.headOrigin[1] + y * headReference.scale,
        );
        next.addChild(sprite);
        return;
      }
      if (part.width) sprite.width = part.width;
      if (part.height) sprite.height = part.height;
      if (centered) {
        sprite.anchor.set(0.5, slot === "backHair" || slot === "frontHair" ? 0 : 0.5);
        sprite.position.set(profile.center + (part.dx ?? 0), coordinate + (part.dy ?? 0));
      }
      if (slot === "outfit" && dye) sprite.filters = [dye];
      next.addChild(sprite);
    }

    draw("backHair", profile.crown);
    draw("shape");
    if (base) {
      const body = new Sprite(base);
      const mask = new Graphics()
        .rect(0, profile.neck, canvas.width, canvas.height - profile.neck)
        .fill(0xffffff);
      next.addChild(body, mask);
      body.mask = mask;
    }
    draw("outfit", 0, false);

    draw("topHair", profile.crown);
    for (const slot of ["brows", "eyes", "nose", "mouth"] as const) draw(slot);
    draw("frontHair", profile.crown);

    disposeActive?.();
    active = next;
    disposeActive = () => {
      next.destroy({ children: true });
      dye?.destroy();
    };
    app.stage.addChild(next);
    renderedBody = appearance.body;
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
watch(() => props.view, layout);
onBeforeUnmount(() => {
  disposed = true;
  observer?.disconnect();
  disposeActive?.();
  app?.destroy(true, { children: true });
});
</script>

<template>
  <div class="renderer" ref="host" role="img" aria-label="角色外观预览">
    <p v-if="busy || error" class="render-notice" role="status">
      {{ error || "正在加载角色素材…" }}
    </p>
  </div>
</template>
