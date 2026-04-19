<template>
  <div id="app-root">
    <router-view />
  
  </div>
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #f0f0f0;
  background-color: #0a0a0a;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #111111;
}

::-webkit-scrollbar-thumb {
  background: #333333;
}

::-webkit-scrollbar-thumb:hover {
  background: #555555;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

/* 右下角悬浮红色小球 */
.floating-ball {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: #ff3b30;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
  z-index: 9999;
  cursor: pointer;
}
</style>
