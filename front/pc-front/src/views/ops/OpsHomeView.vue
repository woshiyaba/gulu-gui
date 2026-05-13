<template>
  <div class="ops-page">
    <section class="ops-card-padded">
      <div class="ops-hero">
        <span class="ops-badge ops-badge--accent">运营工作台</span>
        <h1 class="ops-hero-title">欢迎进入数据维护平台</h1>
        <p class="ops-hero-desc">这里用于维护图鉴相关基础数据，后续功能会逐步接入。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ops-hero { display: grid; gap: 10px; min-height: 120px; align-content: center; }
.ops-hero-title { font-size: 24px; font-weight: 600; letter-spacing: -0.01em; color: var(--ops-text); }
.ops-hero-desc { color: var(--ops-text-secondary); font-size: 14px; max-width: 640px; }
</style>
