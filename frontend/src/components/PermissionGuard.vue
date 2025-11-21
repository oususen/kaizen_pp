<script setup>
import { usePermissions } from '../composables/usePermissions'

const props = defineProps({
  resource: {
    type: String,
    required: true,
  },
  requireEdit: {
    type: Boolean,
    default: false,
  },
})

const { canView, canEdit } = usePermissions()

const hasPermission = () => {
  if (props.requireEdit) {
    return canEdit(props.resource)
  }
  return canView(props.resource)
}
</script>

<template>
  <div v-if="hasPermission()">
    <slot></slot>
  </div>
  <div v-else class="no-permission">
    <p>この操作を実行する権限がありません。</p>
  </div>
</template>

<style scoped>
.no-permission {
  padding: 2rem;
  text-align: center;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 8px;
  color: #92400e;
}
</style>
