<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchEmployees, fetchDepartments, createEmployee, updateEmployee, deleteEmployee } from '../api/client'
import { usePermissions } from '../composables/usePermissions'

const { canEdit } = usePermissions()
const canEditEmployees = computed(() => canEdit('employee_management'))

const employees = ref([])
const departments = ref([])
const roleOptions = [
  { value: 'staff', label: '従業員' },
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '部門長' },
  { value: 'committee', label: '改善委員' },
  { value: 'admin', label: 'システム管理者' },
]

const employmentTypeOptions = [
  { value: 'regular', label: '社員' },
  { value: 'intern', label: '実習生' },
  { value: 'temporary', label: '人材派遣' },
  { value: 'skilled', label: '特定技能' },
  { value: 'contract', label: '嘱託' },
  { value: 'part_time', label: 'パート' },
]

const showModal = ref(false)
const editingEmployee = ref(null)
const formData = ref({
  code: '',
  name: '',
  email: '',
  department: null,
  division: '',
  group: '',
  team: '',
  position: '',
  role: 'staff',
  employment_type: 'regular',
  joined_on: '',
})

const filterKeyword = ref('')
const filterDepartment = ref(null)
const includeInactive = ref(false)

const filteredEmployees = computed(() => {
  let result = employees.value
  if (filterKeyword.value) {
    const keyword = filterKeyword.value.toLowerCase()
    result = result.filter(emp =>
      emp.code?.toLowerCase().includes(keyword) ||
      emp.name?.toLowerCase().includes(keyword) ||
      emp.email?.toLowerCase().includes(keyword)
    )
  }
  if (filterDepartment.value) {
    result = result.filter(emp => emp.department === filterDepartment.value)
  }
  return result
})

const loadData = async () => {
  try {
    const params = { include_inactive: includeInactive.value ? '1' : '' }
    const [employeesData, deptData] = await Promise.all([
      fetchEmployees(params),
      fetchDepartments(),
    ])
    employees.value = employeesData
    departments.value = deptData
  } catch (error) {
    console.error('データの取得に失敗:', error)
    alert('データの取得に失敗しました')
  }
}

const openCreateModal = () => {
  editingEmployee.value = null
  formData.value = {
    code: '',
    name: '',
    email: '',
    department: null,
    division: '',
    group: '',
    team: '',
    position: '',
    role: 'staff',
    employment_type: 'regular',
    joined_on: '',
  }
  showModal.value = true
}

const openEditModal = (employee) => {
  editingEmployee.value = employee
  formData.value = {
    code: employee.code,
    name: employee.name,
    email: employee.email || '',
    department: employee.department,
    division: employee.division || '',
    group: employee.group || '',
    team: employee.team || '',
    position: employee.position || '',
    role: employee.role,
    employment_type: employee.employment_type,
    joined_on: employee.joined_on || '',
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingEmployee.value = null
}

const saveEmployee = async () => {
  if (!formData.value.code || !formData.value.name || !formData.value.department) {
    alert('従業員コード、名前、部署は必須です')
    return
  }

  try {
    if (editingEmployee.value) {
      await updateEmployee(editingEmployee.value.id, formData.value)
    } else {
      await createEmployee(formData.value)
    }
    await loadData()
    closeModal()
  } catch (error) {
    console.error('保存に失敗:', error)
    alert('保存に失敗しました: ' + (error.message || ''))
  }
}

const handleDelete = async (employee) => {
  if (!confirm(`${employee.name}を削除してもよろしいですか？`)) {
    return
  }

  try {
    await deleteEmployee(employee.id)
    await loadData()
  } catch (error) {
    console.error('削除に失敗:', error)
    alert('削除に失敗しました')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>従業員管理</h1>
      <button v-if="canEditEmployees" class="primary" @click="openCreateModal">
        ＋ 新規登録
      </button>
    </header>

    <div class="filters">
      <input v-model="filterKeyword" type="text" placeholder="検索（コード、名前、メール）" />
      <select v-model="filterDepartment">
        <option :value="null">すべての部署</option>
        <option v-for="dept in departments" :key="dept.id" :value="dept.id">
          {{ dept.name }}
        </option>
      </select>
      <label class="checkbox-label">
        <input type="checkbox" v-model="includeInactive" @change="loadData" />
        退職者を含む
      </label>
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>従業員コード</th>
            <th>名前</th>
            <th>雇用形態</th>
            <th>部署</th>
            <th>役職</th>
            <th>ロール</th>
            <th>メール</th>
            <th>入社日</th>
            <th v-if="canEditEmployees">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in filteredEmployees" :key="emp.id">
            <td>{{ emp.code }}</td>
            <td>{{ emp.name }}</td>
            <td>{{ emp.employment_type_display }}</td>
            <td>{{ emp.department_detail?.name }}</td>
            <td>{{ emp.position }}</td>
            <td>{{ emp.role_display }}</td>
            <td>{{ emp.email }}</td>
            <td>{{ emp.joined_on }}</td>
            <td v-if="canEditEmployees" class="actions">
              <button class="ghost small" @click="openEditModal(emp)">編集</button>
              <button class="ghost small danger" @click="handleDelete(emp)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <header class="modal-header">
          <h2>{{ editingEmployee ? '従業員編集' : '従業員新規登録' }}</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </header>
        <div class="modal-body">
          <div class="form-group">
            <label>従業員コード <span class="required">*</span></label>
            <input v-model="formData.code" type="text" :disabled="!!editingEmployee" />
          </div>
          <div class="form-group">
            <label>名前 <span class="required">*</span></label>
            <input v-model="formData.name" type="text" />
          </div>
          <div class="form-group">
            <label>メールアドレス</label>
            <input v-model="formData.email" type="email" />
          </div>
          <div class="form-group">
            <label>部署 <span class="required">*</span></label>
            <select v-model="formData.department">
              <option :value="null">選択してください</option>
              <option v-for="dept in departments" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>事業部/課</label>
            <input v-model="formData.division" type="text" />
          </div>
          <div class="form-group">
            <label>係</label>
            <input v-model="formData.group" type="text" />
          </div>
          <div class="form-group">
            <label>班</label>
            <input v-model="formData.team" type="text" />
          </div>
          <div class="form-group">
            <label>役職</label>
            <input v-model="formData.position" type="text" />
          </div>
          <div class="form-group">
            <label>ロール</label>
            <select v-model="formData.role">
              <option v-for="role in roleOptions" :key="role.value" :value="role.value">
                {{ role.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>雇用形態</label>
            <select v-model="formData.employment_type">
              <option v-for="type in employmentTypeOptions" :key="type.value" :value="type.value">
                {{ type.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>入社日</label>
            <input v-model="formData.joined_on" type="date" />
          </div>
        </div>
        <footer class="modal-footer">
          <button class="ghost" @click="closeModal">キャンセル</button>
          <button class="primary" @click="saveEmployee">保存</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  align-items: center;
}

.filters input[type="text"],
.filters select {
  padding: 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.95rem;
}

.filters input[type="text"] {
  flex: 1;
  max-width: 300px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
}

th {
  text-align: left;
  padding: 1rem;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
}

td {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

button {
  cursor: pointer;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
}

button.primary {
  background: #2563eb;
  color: white;
}

button.ghost {
  background: transparent;
  border: 1px solid #cbd5e1;
  color: #475569;
}

button.small {
  padding: 0.3rem 0.6rem;
  font-size: 0.85rem;
}

button.danger {
  color: #dc2626;
  border-color: #dc2626;
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
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.2rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 600;
  color: #334155;
}

.required {
  color: #dc2626;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.95rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
}
</style>
