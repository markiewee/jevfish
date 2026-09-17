import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useWidth(minWidth = 320, fallback = 640) {
  const el = ref(null)
  const width = ref(fallback)
  let ro = null
  onMounted(() => {
    const update = () => {
      if (el.value) width.value = Math.max(minWidth, Math.floor(el.value.clientWidth))
    }
    update()
    ro = new ResizeObserver(update)
    ro.observe(el.value)
  })
  onBeforeUnmount(() => ro && ro.disconnect())
  return { el, width }
}
