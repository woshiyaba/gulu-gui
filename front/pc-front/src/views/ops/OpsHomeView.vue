<template>
  <div class="ops-home">
    <section class="hero panel">
      <div class="hero-copy">
        <span class="hero-badge">运营工作台</span>
        <h3>欢迎进入数据维护平台</h3>
        <p>这里用于维护图鉴相关基础数据，后续功能会逐步接入。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ops-home {
  display: grid;
  gap: 16px;
}

.panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 20px;
  box-shadow: none;
}

.hero {
  min-height: 180px;
  display: flex;
  align-items: center;
  background: #fff;
}

.hero-copy {
  display: grid;
  gap: 10px;
}

.hero-badge {
  display: inline-flex;
  width: fit-content;
  padding: 0 12px;
  min-height: 28px;
  align-items: center;
  border-radius: 4px;
  background: #ecf5ff;
  color: #409eff;
  font-size: 12px;
  font-weight: 700;
}

.hero h3 {
  font-size: 26px;
}

.hero p {
  color: var(--color-muted);
  max-width: 640px;
}
</style>
