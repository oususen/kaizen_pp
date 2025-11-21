<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchUsers, fetchPermissions, updatePermission, createPermission } from '../api/client'
import { usePermissions } from '../composables/usePermissions'

const users = ref([])
const permissions = ref([])
const originalPermissions = ref([])
const loading = ref(false)
const message = ref('')
const hasChanges = ref(false)

const { canEdit } = usePermissions()
const canEditPermissions = computed(() => canEdit('permissions'))

const resources = [
  { key: 'submit', label: '提出フォーム' },
  { key: 'proposals', label: '提出済み一覧' },
  { key: 'approvals', label: '承認センター' },
  { key: 'confirmed', label: '確認済み一覧' },
  { key: 'reports', label: 'レポート' },
  { key: 'analytics', label: '分析・レポート' },
  { key: 'permissions', label: '権限設定' },
  { key: 'user_management', label: 'ユーザー管理' },
]

const loadData = async () => {
  loading.value = true
  message.value = ''
  try {
    users.value = await fetchUsers()
    permissions.value = await fetchPermissions()
    originalPermissions.value = JSON.parse(JSON.stringify(permissions.value))
    hasChanges.value = false
  } catch (error) {
    message.value = error.message ?? 'データの取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const getPermission = (userId, resource) => {
  return permissions.value.find(p => p.user === userId && p.resource === resource)
}

const togglePermission = (userId, resource, field) => {
  const perm = getPermission(userId, resource)
  if (perm) {
    perm[field] = !perm[field]
  } else {
    permissions.value.push({
      user: userId,
      resource,
      can_view: field === 'can_view',
      can_edit: field === 'can_edit',
      id: null
    })
  }
  hasChanges.value = true
}

const savePermissions = async () => {
  loading.value = true
  message.value = ''
  try {
    for (const perm of permissions.value) {
      if (perm.id) {
        // 既存の権限を更新
        await updatePermission(perm.id, perm)
      } else {
        // 新規権限を作成
        const created = await createPermission(perm)
        perm.id = created.id
      }
    }
    originalPermissions.value = JSON.parse(JSON.stringify(permissions.value))
    hasChanges.value = false
    message.value = '権限を保存しました'
    setTimeout(() => message.value = '', 2000)
  } catch (error) {
    message.value = error.message ?? '権限の保存に失敗しました'
  } finally {
    loading.value = false
  }
}

const cancelChanges = () => {
  permissions.value = JSON.parse(JSON.stringify(originalPermissions.value))
  hasChanges.value = false
  message.value = '変更をキャンセルしました'
  setTimeout(() => message.value = '', 2000)
}

onMounted(loadData)
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>🔒 権限設定</h2>
        <p>ユーザーごとのページ閲覧・編集権限を管理します。</p>
      </div>
      <div class="action-buttons" v-if="hasChanges && canEditPermissions">
        <button @click="savePermissions" class="btn btn-primary" :disabled="loading">
          {{ loading ? '保存中...' : '変更を保存' }}
        </button>
        <button @click="cancelChanges" class="btn btn-secondary" :disabled="loading">
          キャンセル
        </button>
      </div>
      <div v-else-if="!canEditPermissions" class="read-only-notice">
        <span>閲覧のみ（編集権限がありません）</span>
      </div>
    </header>

    <div v-if="message" class="alert" :class="message.includes('失敗') ? 'error' : 'success'">{{ message }}</div>

    <div v-if="loading" class="placeholder">読み込み中です…</div>
    <div v-else class="table-container">
      <table class="permissions-table">
        <thead>
          <tr>
            <th class="sticky-col">ユーザー</th>
            <th v-for="res in resources" :key="res.key" colspan="2">{{ res.label }}</th>
          </tr>
          <tr>
            <th class="sticky-col">部門</th>
            <template v-for="res in resources" :key="res.key">
              <th class="sub-header">閲覧</th>
              <th class="sub-header">編集</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td class="sticky-col">
              <div class="employee-info">
                <strong>{{ user.username }}</strong>
                <small>{{ user.profile?.responsible_department_detail?.name || '担当部署未設定' }}</small>
              </div>
            </td>
            <template v-for="res in resources" :key="res.key">
              <td class="checkbox-cell">
                <input
                  type="checkbox"
                  :checked="getPermission(user.id, res.key)?.can_view ?? false"
                  @change="togglePermission(user.id, res.key, 'can_view')"
                  :disabled="!canEditPermissions"
                />
              </td>
              <td class="checkbox-cell">
                <input
                  type="checkbox"
                  :checked="getPermission(user.id, res.key)?.can_edit ?? false"
                  @change="togglePermission(user.id, res.key, 'can_edit')"
                  :disabled="!canEditPermissions"
                />
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}
.action-buttons {
  display: flex;
  gap: 0.5rem;
}
.read-only-notice {
  background: #fef3c7;
  color: #92400e;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
}
.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #2563eb;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-secondary {
  background: #6b7280;
  color: white;
}
.btn-secondary:hover:not(:disabled) {
  background: #4b5563;
}
.alert {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.alert.success {
  background: #dcfce7;
  color: #065f46;
}
.alert.error {
  background: #fee2e2;
  color: #991b1b;
}
.placeholder {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
}
.table-container {
  overflow-x: auto;
}
.permissions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.permissions-table th,
.permissions-table td {
  border: 1px solid #e5e7eb;
  padding: 0.5rem;
  text-align: center;
}
.permissions-table th {
  background: #f8fafc;
  font-weight: 600;
}
.sub-header {
  font-size: 0.75rem;
  font-weight: 500;
  background: #f1f5f9;
}
.sticky-col {
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 1;
  text-align: left;
  min-width: 180px;
}
.sticky-col th {
  background: #f8fafc;
}
.employee-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.employee-info small {
  color: #6b7280;
  font-size: 0.75rem;
}
.checkbox-cell {
  padding: 0.25rem;
}
.checkbox-cell input[type="checkbox"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}
.checkbox-cell input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
