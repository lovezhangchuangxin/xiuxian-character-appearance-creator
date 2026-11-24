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
import { bodies, layers, selectedPart, type Appearance } from "../character/catalog";
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
  const view = profile.views[props.view];
  const scale = Math.min(width / view.width, height / view.height);
  active.scale.set(scale);
  active.position.set(width / 2 - view.x * scale, height / 2 - view.y * scale);
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
  const parts = layers.map((slot) => ({ slot, part: selectedPart(appearance, slot) }));
  const changingBody = appearance.body !== renderedBody;
  if (active) {
    active.visible = !changingBody;
    if (changingBody) app.render();
  }
  busy.value = !active || changingBody;
  error.value = "";

  try {
    const images = await Promise.all(
      parts.map(({ part }) => (part.image ? texture(part.image) : undefined)),
    );
    if (!app || disposed || revision !== id) return;
    const next = new Container();
    let dye: Filter | undefined;

    for (const [index, { slot, part }] of parts.entries()) {
      const tex = images[index];
      if (!tex || !part.rect) continue;

      const sprite = new Sprite(tex);
      const { x, y, width, height } = part.rect;
      sprite.position.set(x, y);
      sprite.width = width;
      sprite.height = height;
      next.addChild(sprite);

      if (part.clip) {
        const clip = part.clip;
        const mask = new Graphics().rect(clip.x, clip.y, clip.width, clip.height).fill(0xffffff);
        next.addChild(mask);
        sprite.mask = mask;
      }
      if (slot === "outfit" && part.dyeable && appearance.dye) {
        dye = dyeFilter(appearance.dye);
        sprite.filters = [dye];
      }
    }

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
