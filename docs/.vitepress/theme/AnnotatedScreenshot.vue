<script setup>
import {ref} from 'vue'
import {withBase} from 'vitepress'

defineProps({
  src: String,
  alt: String,
  caption: String,
  width: Number,
  height: Number,
  steps: Array,
})

const viewer = ref(null)
const boxStyle = step => ({
  left: `${step.x}%`, top: `${step.y}%`,
  width: `${step.width}%`, height: `${step.height}%`,
})
</script>

<template>
  <figure class="guide-shot">
    <figcaption>
      <strong>{{ caption }}</strong>
      <span>点图放大 · 演示数据</span>
    </figcaption>
    <button class="shot-open" type="button" :aria-label="`放大图解：${caption}`" @click="viewer.showModal()">
      <span class="shot-frame">
        <img :src="withBase(src)" :alt="alt" :width="width" :height="height" loading="lazy" decoding="async">
        <span v-for="(step, i) in steps" :key="i" class="shot-mark" :style="boxStyle(step)" aria-hidden="true"><b>{{ i + 1 }}</b></span>
      </span>
    </button>
    <ol class="shot-notes">
      <li v-for="(step, i) in steps" :key="i">
        <span class="step-number" aria-hidden="true">{{ i + 1 }}</span>
        <div><strong>{{ step.title }}</strong><p>{{ step.text }}</p></div>
      </li>
    </ol>
    <dialog ref="viewer" class="shot-viewer" :aria-label="caption" @click="event => event.target === viewer && viewer.close()">
      <div class="viewer-bar"><strong>{{ caption }}</strong><button type="button" @click="viewer.close()">关闭</button></div>
      <div class="viewer-scroll">
        <div class="shot-frame">
          <img :src="withBase(src)" :alt="alt" :width="width" :height="height" decoding="async">
          <span v-for="(step, i) in steps" :key="i" class="shot-mark" :style="boxStyle(step)" aria-hidden="true"><b>{{ i + 1 }}</b></span>
        </div>
      </div>
      <p class="viewer-hint">可滚动查看整张图；按 Esc 或点击“关闭”返回文档。</p>
      <ol class="shot-notes">
        <li v-for="(step, i) in steps" :key="i"><span class="step-number" aria-hidden="true">{{ i + 1 }}</span><div><strong>{{ step.title }}</strong><p>{{ step.text }}</p></div></li>
      </ol>
    </dialog>
  </figure>
</template>

<style scoped>
.guide-shot { margin: 24px 0 32px; padding: 18px; border: 1px solid var(--vp-c-divider); border-radius: 10px; background: var(--vp-c-bg-soft); }
figcaption { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; font-size: 14px; }
figcaption > span { color: var(--vp-c-text-2); font-size: 12px; }
.shot-open { display: block; width: 100%; padding: 0; border: 0; background: transparent; cursor: zoom-in; text-align: left; }
.shot-open:focus-visible { outline: 3px solid var(--vp-c-brand-1); outline-offset: 6px; }
.shot-frame { display: block; position: relative; line-height: 0; }
.shot-frame img { display: block; width: 100%; height: auto; border-radius: 5px; }
.shot-mark { position: absolute; border: 2px solid #b66d0b; border-radius: 4px; pointer-events: none; background: rgba(228, 159, 53, .04); }
.shot-mark b, .step-number { display: flex; align-items: center; justify-content: center; width: 25px; height: 25px; border-radius: 50%; background: #a96108; color: #fff; font: 700 13px/1 'Segoe UI', sans-serif; }
.shot-mark b { position: absolute; left: 0; top: 0; transform: translate(-45%, -45%); box-shadow: 0 0 0 2px #fff; }
.guide-shot .shot-notes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 22px; list-style: none; padding: 0; margin: 22px 0 0; }
.guide-shot .shot-notes li { display: grid; grid-template-columns: 25px minmax(0, 1fr); gap: 10px; margin: 0; font-size: 13px; line-height: 1.7; }
.guide-shot .shot-notes strong { font-size: 14px; }
.guide-shot .shot-notes p { margin: 5px 0 0; line-height: 1.75; color: var(--vp-c-text-2); }
.shot-viewer { width: min(1140px, calc(100vw - 32px)); max-width: none; max-height: calc(100dvh - 32px); padding: 20px; border: 1px solid var(--vp-c-divider); border-radius: 10px; background: var(--vp-c-bg); color: var(--vp-c-text-1); }
.shot-viewer::backdrop { background: rgba(12, 24, 18, .75); }
.viewer-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.viewer-bar button { padding: 5px 14px; border: 1px solid var(--vp-c-divider); border-radius: 5px; font-size: 14px; }
.viewer-scroll { overflow: auto; max-height: 65vh; padding: 14px; background: #f5f7f5; border-radius: 6px; }
.viewer-scroll .shot-frame { min-width: 760px; }
.guide-shot .viewer-hint { font-size: 12px; color: var(--vp-c-text-2); margin: 12px 0; }
@media (max-width: 640px) {
  .guide-shot { padding: 14px 12px; }
  .guide-shot .shot-notes { grid-template-columns: 1fr; gap: 16px; }
  .shot-mark { border-width: 1.5px; }
  .shot-mark b { width: 22px; height: 22px; font-size: 12px; }
  .shot-viewer { padding: 14px; }
}
</style>
