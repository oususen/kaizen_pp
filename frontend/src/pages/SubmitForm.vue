<script setup>
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { createProposal, fetchDepartments, fetchEmployees } from '../api/client'

const departments = ref([])
const employees = ref([])
const loading = ref(false)
const message = ref('')
const success = ref('')

const form = reactive({
  department: '',
  group: '',
  team: '',
  proposer_name: '',
  deployment_item: '',
  problem_summary: '',
  improvement_plan: '',
  improvement_result: '',
  contribution_business: [],
  comment: '',
  reduction_hours: '',
  before_images: [],
  after_images: [],
})

const toId = (value) => (value === null || value === undefined ? '' : String(value))

const parentMap = computed(() => {
  const map = new Map()
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), toId(dept.parent))
  })
  return map
})

const isDescendantOf = (childId, ancestorId) => {
  let cursor = toId(childId)
  const target = toId(ancestorId)
  if (!cursor || !target) return false
  const seen = new Set()
  while (cursor && !seen.has(cursor)) {
    seen.add(cursor)
    const parent = parentMap.value.get(cursor)
    if (!parent) return false
    if (parent === target) return true
    cursor = parent
  }
  return false
}

const divisionOptions = computed(() => departments.value.filter((dept) => dept.level === 'division'))
const groupOptions = computed(() => departments.value.filter((dept) => dept.level === 'group'))
const teamOptions = computed(() => departments.value.filter((dept) => dept.level === 'team'))
const filteredGroupOptions = computed(() =>
  groupOptions.value.filter((dept) => isDescendantOf(dept.id, form.department)),
)
const filteredTeamOptions = computed(() =>
  teamOptions.value.filter((dept) => isDescendantOf(dept.id, form.group)),
)
const contributorOptions = computed(() => departments.value)
const effectDepartmentOptions = computed(() => 
  departments.value
    .filter((dept) => dept.level === 'division' || dept.level === 'section')
    .sort((a, b) => {
      // Sort by display_id first, then by name
      const idDiff = (a.display_id || 0) - (b.display_id || 0)
      if (idDiff !== 0) return idDiff
      return a.name.localeCompare(b.name)
    })
)

const effectAmount = computed(() => {
  const hours = Number(form.reduction_hours) || 0
  return Math.round(hours * 1700)
})

const loadMaster = async () => {
  try {
    departments.value = await fetchDepartments()
  } catch (error) {
    message.value = error.message ?? 'マスターデータの取得に失敗しました'
  }
}

const loadEmployees = async (departmentId = null) => {
  try {
    const params = departmentId ? { department: departmentId } : {}
    employees.value = await fetchEmployees(params)
  } catch (error) {
    message.value = error.message ?? '従業員データの取得に失敗しました'
  }
}

const resetForm = () => {
  Object.assign(form, {
    department: '',
    group: '',
    team: '',
    proposer: '',
    proposer_name: '',
    proposer_email: '',
    deployment_item: '',
    problem_summary: '',
    improvement_plan: '',
    improvement_result: '',
    contribution_business: [],
    comment: '',
    reduction_hours: '',
    before_images: [],
    after_images: [],
  })
  employees.value = []
  success.value = ''
  message.value = ''
}

// 提案者選択時に名前とメールアドレスを自動入力
watch(() => form.proposer, (proposerId) => {
  if (proposerId) {
    const employee = employees.value.find(emp => String(emp.id) === String(proposerId))
    if (employee) {
      form.proposer_name = employee.name
      form.proposer_email = employee.email || ''
    }
  }
})

watch(() => form.department, (newDepartment) => {
  if (!filteredGroupOptions.value.some((dept) => toId(dept.id) === toId(form.group))) {
    form.group = ''
  }
  form.team = ''
  form.proposer = ''

  // 部門が選択されたら、その部門に所属する従業員を読み込む
  if (newDepartment) {
    loadEmployees(newDepartment)
  } else {
    employees.value = []
  }
})

watch(() => form.group, (newGroup) => {
  if (!filteredTeamOptions.value.some((dept) => toId(dept.id) === toId(form.team))) {
    form.team = ''
  }
  form.proposer = ''

  // 係が選択されたら、その係に所属する従業員に絞り込む
  if (newGroup) {
    loadEmployees(newGroup)
  } else if (form.department) {
    loadEmployees(form.department)
  }
})

watch(() => form.team, (newTeam) => {
  form.proposer = ''

  // 班が選択されたら、その班に所属する従業員に絞り込む
  if (newTeam) {
    loadEmployees(newTeam)
  } else if (form.group) {
    loadEmployees(form.group)
  } else if (form.department) {
    loadEmployees(form.department)
  }
})

const handleFilesChange = (event, field) => {
  const files = Array.from(event.target.files || [])
  form[field] = files
}

const removeImage = (field, index) => {
  form[field].splice(index, 1)
}

const getImagePreviewUrl = (file) => {
  try {
    if (file instanceof File || file instanceof Blob) {
      return URL.createObjectURL(file)
    }
    return ''
  } catch (error) {
    console.error('Failed to create object URL:', error)
    return ''
  }
}

const submitProposal = async () => {
  message.value = ''
  success.value = ''
  if (!form.department || !form.proposer || !form.deployment_item || !form.problem_summary || !form.improvement_plan) {
    message.value = '必須項目を入力してください'
    return
  }
  loading.value = true
  try {
    // FormDataを使って複数画像を送信
    const formData = {
      department: form.department,
      group: form.group,
      team: form.team,
      proposer: form.proposer,
      proposer_name: form.proposer_name,
      proposer_email: form.proposer_email,
      deployment_item: form.deployment_item,
      problem_summary: form.problem_summary,
      improvement_plan: form.improvement_plan,
      improvement_result: form.improvement_result,
      contribution_business: form.contribution_business.join(', '),
      comment: form.comment,
      reduction_hours: form.reduction_hours,
      before_images: form.before_images,
      after_images: form.after_images,
    }
    await createProposal(formData)
    success.value = '改善提案を提出しました'
    resetForm()
  } catch (error) {
    message.value = error.message ?? '送信に失敗しました'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMaster()
})
</script>

<template>
  <section class="card">
    <header class="section-header">
      <div>
        <h2>📝 改善提案 提出フォーム</h2>
        <p>削減時間を入力すると効果額が自動計算されます。</p>
      </div>
      <div class="effect">
        <span>月間効果額</span>
        <strong>¥{{ effectAmount.toLocaleString() }}</strong>
      </div>
    </header>

    <div v-if="message" class="alert error">{{ message }}</div>
    <div v-if="success" class="alert success">{{ success }}</div>

    <form class="form-grid" @submit.prevent="submitProposal">
      <label>
        部門*
        <select v-model="form.department" required>
          <option value="" disabled>選択してください</option>
          <option v-for="dept in divisionOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>

      <label>
        係
        <select v-model="form.group">
          <option value="">選択してください</option>
          <option v-for="dept in filteredGroupOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>

      <label>
        班
        <select v-model="form.team">
          <option value="">選択してください</option>
          <option v-for="dept in filteredTeamOptions" :key="dept.id" :value="toId(dept.id)">
            {{ dept.name }}
          </option>
        </select>
      </label>


      <label>
        提案者*
        <select v-model="form.proposer" required>
          <option value="" disabled>選択してください</option>
          <option v-for="emp in employees" :key="emp.id" :value="toId(emp.id)">
            {{ emp.name }} ({{ emp.code }})
          </option>
        </select>
      </label>

      <label>
        提案者名
        <input v-model="form.proposer_name" type="text" readonly />
      </label>

      <label class="span">
        展開項目(テーマ)*
        <input v-model="form.deployment_item" type="text" required />
      </label>

      <label class="span">
        困っている事・問題点*
        <textarea v-model="form.problem_summary" rows="3" required></textarea>
      </label>

      <label class="span">
        この様に改善したい*
        <textarea v-model="form.improvement_plan" rows="3" required></textarea>
      </label>

      <label class="span">
        改善結果
        <textarea v-model="form.improvement_result" rows="3"></textarea>
      </label>

      <label>
        削減時間 (Hr/月)*
        <input v-model.number="form.reduction_hours" type="number" min="0" step="0.5" required />
      </label>

      <label>
        効果部門
        <select v-model="form.contribution_business" multiple>
          <option v-for="dept in effectDepartmentOptions" :key="dept.id" :value="dept.name">
            {{ dept.name }}
          </option>
        </select>
        <small>Ctrlキーで複数選択</small>
      </label>

      <label class="span">
        コメント・備考
        <textarea v-model="form.comment" rows="2"></textarea>
      </label>

      <div class="image-upload-section span">
        <div class="image-upload-container">
          <div class="image-upload-column">
            <h3>改善前の写真 </h3>
            <!-- <h3>改善前の写真 <span class="required-badge">必須</span></h3> -->
            <input
              type="file"
              accept="image/*"
              multiple
              @change="(event) => handleFilesChange(event, 'before_images')"
              class="file-input"
            />
            <div v-if="form.before_images.length > 0" class="image-preview-grid">
              <div v-for="(file, index) in form.before_images" :key="index" class="image-preview-item">
                <img v-if="getImagePreviewUrl(file)" :src="getImagePreviewUrl(file)" :alt="`改善前 ${index + 1}`" />
                <button type="button" @click="removeImage('before_images', index)" class="remove-btn">×</button>
                <span class="image-name">{{ file.name }}</span>
              </div>
            </div>
            <p v-else class="upload-hint">複数枚選択可能</p>
          </div>

          <div class="image-upload-column">
            <h3>改善後の写真</h3>
            <input
              type="file"
              accept="image/*"
              multiple
              @change="(event) => handleFilesChange(event, 'after_images')"
              class="file-input"
            />
            <div v-if="form.after_images.length > 0" class="image-preview-grid">
              <div v-for="(file, index) in form.after_images" :key="index" class="image-preview-item">
                <img v-if="getImagePreviewUrl(file)" :src="getImagePreviewUrl(file)" :alt="`改善後 ${index + 1}`" />
                <button type="button" @click="removeImage('after_images', index)" class="remove-btn">×</button>
                <span class="image-name">{{ file.name }}</span>
              </div>
            </div>
            <p v-else class="upload-hint">複数枚選択可能</p>
          </div>
        </div>
      </div>

      <div class="span actions">
        <button type="submit" :disabled="loading">{{ loading ? '送信中…' : '提案を提出' }}</button>
        <button type="button" class="ghost" @click="resetForm">クリア</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.effect {
  text-align: right;
  background: #eef2ff;
  padding: 0.7rem 1rem;
  border-radius: 8px;
}
.effect span {
  display: block;
  font-size: 0.8rem;
  color: #4c1d95;
}
.effect strong {
  font-size: 1.3rem;
  color: #1d4ed8;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
label {
  display: flex;
  flex-direction: column;
  font-weight: 600;
  gap: 0.4rem;
}
input,
select,
textarea {
  padding: 0.5rem 0.6rem;
  border: 1px solid #d4dbe5;
  border-radius: 8px;
  font-size: 1rem;
}
textarea {
  resize: vertical;
}
.span {
  grid-column: 1 / -1;
}
.actions {
  display: flex;
  gap: 0.6rem;
}
button {
  padding: 0.7rem 1.4rem;
  border-radius: 8px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}
button.ghost {
  background: #e2e8f0;
  color: #1f2933;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.alert {
  margin: 1rem 0;
  padding: 0.8rem 1rem;
  border-radius: 8px;
}
.alert.error {
  background: #fee2e2;
  color: #991b1b;
}
.alert.success {
  background: #dcfce7;
  color: #166534;
}

/* 画像アップロードセクション */
.image-upload-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
}

.image-upload-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.image-upload-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.image-upload-column h3 {
  font-size: 1.1rem;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.required-badge {
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.file-input {
  padding: 0.8rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
}

.file-input:hover {
  border-color: #3b82f6;
}

.upload-hint {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0;
  text-align: center;
  font-style: italic;
}

.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.image-preview-item {
  position: relative;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.image-preview-item img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
}

.image-name {
  display: block;
  padding: 0.4rem;
  font-size: 0.75rem;
  color: #64748b;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  padding: 0;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 50%;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  background: #dc2626;
}

@media (max-width: 768px) {
  .image-upload-container {
    grid-template-columns: 1fr;
  }
}
</style>











