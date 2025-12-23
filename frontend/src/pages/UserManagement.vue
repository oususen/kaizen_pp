<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchUsers, fetchDepartments, createUser, updateUser, deleteUser } from '../api/client'
import { usePermissions } from '../composables/usePermissions'

const { canEdit } = usePermissions()
const canEditUsers = computed(() => canEdit('user_management'))

const users = ref([])
const departments = ref([])
const roleOptions = [
  { value: 'staff', label: '一般社員' },
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '部門長・課長' },
  { value: 'committee', label: '改善委員' },
  { value: 'committee_chair', label: '改善委員長' },
  { value: 'admin', label: 'システム管理者' },
]

const showModal = ref(false)
const editingUser = ref(null)
const formData = ref({
  username: '',
  name: '',
  email: '',
  password: '',
  profile_role: 'staff',
  profile_responsible_department: null,
  smtp_host: '',
  smtp_port: null,
  smtp_user: '',
  smtp_password: '',
})

const responsibleDepartments = computed(() => {
  const role = formData.value.profile_role
  if (role === 'supervisor') {
    // 班長: 班のみ
    return departments.value.filter(d => d.level === 'team')
  } else if (role === 'chief') {
    // 係長: 係のみ
    return departments.value.filter(d => d.level === 'group')
  } else if (role === 'manager' || role === 'committee' || role === 'committee_chair') {
    // 部門長・課長・改善委員・改善委員長: 部・課のみ
    return departments.value.filter(d => d.level === 'division' || d.level === 'section')
  } else if (role === 'admin') {
    // システム管理者: 担当部署不要
    return []
  }
  return []
})

const loadData = async () => {
  try {
    const [usersData, deptData] = await Promise.all([
      fetchUsers(),
      fetchDepartments(),
    ])
    users.value = usersData
    departments.value = deptData
  } catch (error) {
    console.error('データの取得に失敗:', error)
    alert('データの取得に失敗しました')
  }
}

const openCreateModal = () => {
  editingUser.value = null
  formData.value = {
    username: '',
    name: '',
    email: '',
    password: '',
    profile_role: 'staff',
    profile_responsible_department: null,
    smtp_host: '',
    smtp_port: null,
    smtp_user: '',
    smtp_password: '',
  }
  showModal.value = true
}

const openEditModal = (user) => {
  editingUser.value = user
  formData.value = {
    username: user.username,
    name: user.name || '',
    email: user.email,
    password: '',
    profile_role: user.profile?.role || 'staff',
    profile_responsible_department: user.profile?.responsible_department || null,
    smtp_host: user.profile?.smtp_host || '',
    smtp_port: user.profile?.smtp_port || null,
    smtp_user: user.profile?.smtp_user || '',
    smtp_password: '',
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingUser.value = null
}

const saveUser = async () => {
  if (!formData.value.username) {
    alert('ユーザーIDを入力してください')
    return
  }

  if (!formData.value.email) {
    alert('メールアドレスを入力してください')
    return
  }

  if (!editingUser.value && !formData.value.password) {
    alert('パスワードを入力してください')
    return
  }

  try {
    const payload = {
      username: formData.value.username,
      name: formData.value.name,
      email: formData.value.email,
      profile_role: formData.value.profile_role,
      profile_responsible_department: formData.value.profile_responsible_department,
      smtp_host: formData.value.smtp_host,
      smtp_port: formData.value.smtp_port,
      smtp_user: formData.value.smtp_user,
    }

    if (formData.value.password) {
      payload.password = formData.value.password
    }

    if (formData.value.smtp_password) {
      payload.smtp_password = formData.value.smtp_password
    }

    if (editingUser.value) {
      await updateUser(editingUser.value.id, payload)
      alert('ユーザーを更新しました')
    } else {
      await createUser(payload)
      alert('ユーザーを作成しました')
    }

    closeModal()
    await loadData()
  } catch (error) {
    console.error('保存に失敗:', error)
    alert('保存に失敗しました')
  }
}

const handleDelete = async (user) => {
  if (!confirm(`ユーザー「${user.username}」を削除しますか？`)) {
    return
  }

  try {
    await deleteUser(user.id)
    alert('ユーザーを削除しました')
    await loadData()
  } catch (error) {
    console.error('削除に失敗:', error)
    alert('削除に失敗しました')
  }
}

const getRoleLabel = (role) => {
  const option = roleOptions.find(o => o.value === role)
  return option ? option.label : role
}

const shouldHideEmployeeName = (user) => {
  const username = (user?.username || '').toLowerCase()
  return username === 'admin' || username === 'daiso'
}

const getEmployeeName = (user) => {
  if (shouldHideEmployeeName(user)) return ''
  return user.employee_name || '-'
}

const getDepartmentName = (deptId) => {
  const dept = departments.value.find(d => d.id === deptId)
  return dept ? dept.name : ''
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="container">
    <div class="header">
      <h1>ユーザー管理</h1>
      <button v-if="canEditUsers" @click="openCreateModal" class="btn-primary">
        新規ユーザー追加
      </button>
    </div>

    <div class="user-list">
      <table>
        <thead>
          <tr>
            <th>ユーザーID</th>
            <th>ユーザー名</th>
            <th>メールアドレス</th>
            <th>役職</th>
            <th>担当部署</th>
            <th>従業員名</th>
            <th v-if="canEditUsers">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td><strong>{{ user.username }}</strong></td>
            <td>{{ user.name || '-' }}</td>
            <td>{{ user.profile?.email || user.email || '-' }}</td>
            <td>{{ getRoleLabel(user.profile?.role) }}</td>
            <td>{{ getDepartmentName(user.profile?.responsible_department) }}</td>
            <td>{{ getEmployeeName(user) }}</td>
            <td v-if="canEditUsers" class="actions">
              <button @click="openEditModal(user)" class="btn-edit">編集</button>
              <button @click="handleDelete(user)" class="btn-delete">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>{{ editingUser ? 'ユーザー編集' : '新規ユーザー追加' }}</h2>
        <form @submit.prevent="saveUser">
          <div class="form-group">
            <label>ユーザーID（ログインID） <span class="required">*</span></label>
            <input
              v-model="formData.username"
              type="text"
              :disabled="!canEditUsers || editingUser"
              required
            />
            <small v-if="editingUser" class="hint">ユーザーIDは変更できません</small>
          </div>

          <div class="form-group">
            <label>ユーザー名</label>
            <input
              v-model="formData.name"
              type="text"
              :disabled="!canEditUsers"
            />
          </div>

          <div class="form-group">
            <label>メールアドレス <span class="required">*</span></label>
            <input
              v-model="formData.email"
              type="email"
              :disabled="!canEditUsers"
              required
            />
          </div>

          <div class="form-group">
            <label>
              パスワード
              <span v-if="!editingUser" class="required">*</span>
              <span v-else class="hint">（変更する場合のみ入力）</span>
            </label>
            <input
              v-model="formData.password"
              type="password"
              :disabled="!canEditUsers"
              :required="!editingUser"
            />
          </div>

          <div class="form-group">
            <label>役職</label>
            <select v-model="formData.profile_role" :disabled="!canEditUsers">
              <option v-for="option in roleOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>担当部署</label>
            <select
              v-model="formData.profile_responsible_department"
              :disabled="!canEditUsers || responsibleDepartments.length === 0"
            >
              <option :value="null">未設定</option>
              <option
                v-for="dept in responsibleDepartments"
                :key="dept.id"
                :value="dept.id"
              >
                {{ dept.name }}
              </option>
            </select>
            <small class="hint">
              役職に応じた部署のみ選択できます
            </small>
          </div>

          <h3 style="margin-top: 2rem; margin-bottom: 0.5rem; color: #374151;">メール送信設定（SMTP）</h3>
          <p class="hint smtp-warning">SMTP設定は運用上変更禁止です</p>

          <div class="form-group">
            <label>SMTPホスト</label>
            <input
              v-model="formData.smtp_host"
              type="text"
              :disabled="!canEditUsers"
              placeholder="例: smtp.gmail.com"
            />
            <small class="hint">SMTPサーバーのホスト名</small>
          </div>

          <div class="form-group">
            <label>SMTPポート</label>
            <input
              v-model.number="formData.smtp_port"
              type="number"
              :disabled="!canEditUsers"
              placeholder="例: 587"
            />
            <small class="hint">SMTPポート番号（通常 587 または 465）</small>
          </div>

          <div class="form-group">
            <label>SMTP認証ユーザー</label>
            <input
              v-model="formData.smtp_user"
              type="text"
              :disabled="!canEditUsers"
              placeholder="例: user@example.com"
            />
            <small class="hint">SMTP認証に使用するユーザー名またはメールアドレス</small>
          </div>

          <div class="form-group">
            <label>
              SMTP認証パスワード
              <span v-if="editingUser" class="hint">（変更する場合のみ入力）</span>
            </label>
            <input
              v-model="formData.smtp_password"
              type="password"
              :disabled="!canEditUsers"
              placeholder="パスワード"
            />
            <small class="hint">SMTP認証に使用するパスワード</small>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-cancel">
              キャンセル
            </button>
            <button v-if="canEditUsers" type="submit" class="btn-primary">
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

h1 {
  font-size: 1.8rem;
  color: #1f2937;
}

.user-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f3f4f6;
}

th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
}

td {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

tbody tr:hover {
  background: #f9fafb;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-edit {
  background: #10b981;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-edit:hover {
  background: #059669;
}

.btn-delete {
  background: #ef4444;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-delete:hover {
  background: #dc2626;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin-bottom: 1.5rem;
  color: #1f2937;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
}

.required {
  color: #ef4444;
}

.hint {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 400;
}
.smtp-warning {
  color: #dc2626;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
}

.form-group input:disabled,
.form-group select:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-cancel {
  background: #e5e7eb;
  color: #374151;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-cancel:hover {
  background: #d1d5db;
}
</style>
